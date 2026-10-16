#include "ggml-cuda/common.cuh"
#include "ggml.h"
#include "topk-moe.cuh"

#include <cmath>
#include <initializer_list>

// Kernel config struct - passed by value to CUDA kernel
struct topk_moe_config {
    bool use_sigmoid;
    bool use_sqrt_softplus;
    bool with_norm;
    bool delayed_softmax;
};

// Warp-local softmax used for both the pre-top-k logits and the post-top-k delayed path.
template <int experts_per_thread, bool use_limit>
__device__ void softmax_warp_inplace(float (&vals)[experts_per_thread], const int limit, const int lane) {
    float max_val = -INFINITY;

#pragma unroll
    for (int i = 0; i < experts_per_thread; i++) {
        const int  idx    = lane + i * WARP_SIZE;
        const bool active = !use_limit || (idx < limit);
        if (active) {
            max_val = max(max_val, vals[i]);
        }
    }

    max_val = warp_reduce_max(max_val);

    float sum = 0.f;

#pragma unroll
    for (int i = 0; i < experts_per_thread; i++) {
        const int  idx    = lane + i * WARP_SIZE;
        const bool active = !use_limit || (idx < limit);
        if (active) {
            const float val = expf(vals[i] - max_val);
            vals[i]         = val;
            sum += val;
        } else {
            vals[i] = 0.f;
        }
    }

    sum = warp_reduce_sum(sum);

    const float inv_sum = 1.0f / sum;

#pragma unroll
    for (int i = 0; i < experts_per_thread; i++) {
        const int  idx    = lane + i * WARP_SIZE;
        const bool active = !use_limit || (idx < limit);
        if (active) {
            vals[i] *= inv_sum;
        }
    }
}

template <int experts_per_thread, bool use_limit>
__device__ void sigmoid_warp_inplace(float (&vals)[experts_per_thread], const int limit, const int lane) {
#pragma unroll
    for (int i = 0; i < experts_per_thread; i++) {
        const int  idx    = lane + i * WARP_SIZE;
        const bool active = !use_limit || (idx < limit);
        vals[i]           = active ? 1.f / (1.f + expf(-vals[i])) : -INFINITY;
    }
}

template <int experts_per_thread, bool use_limit>
__device__ void sqrt_softplus_warp_inplace(float (&vals)[experts_per_thread], const int limit, const int lane) {
#pragma unroll
    for (int i = 0; i < experts_per_thread; i++) {
        const int  idx    = lane + i * WARP_SIZE;
        const bool active = !use_limit || (idx < limit);
        vals[i]           = active ? sqrtf(vals[i] > 20.0f ? vals[i] : logf(1.0f + expf(vals[i]))) : -INFINITY;
    }
}

/*
    This kernel does the following:
    1. optionally softmax over the logits per token [n_experts, n_tokens]
    2. argmax reduce over the top-k (n_experts_used) logits
    3. write weights + ids to global memory
    4. optionally normalize the weights or apply softmax over the selected logits

    It is intended as fusion of softmax->top-k->get_rows pipeline for MoE models
*/
// Everything of topk_moe_cuda after the logits of the row are in wt (one warp per row): gating, top-k selection, the
// weights and ids of the row. Also the tail of the fused single-token routing kernel (norm_router_topk_f32).
template <int n_experts, bool has_bias>
static __device__ __forceinline__ void topk_moe_select(float (&wt)[(n_experts > WARP_SIZE) ? n_experts / WARP_SIZE : 1],
                                                       float *               weights,
                                                       int32_t *             ids,
                                                       const float *         bias,
                                                       const int             n_expert_used,
                                                       const float           clamp_val,
                                                       const float           scale_val,
                                                       const topk_moe_config config) {
    constexpr int experts_per_thread = (n_experts > WARP_SIZE) ? n_experts / WARP_SIZE : 1;

    if (!config.delayed_softmax) {
        if (config.use_sigmoid) {
           sigmoid_warp_inplace<experts_per_thread, false>(wt, n_experts, threadIdx.x);
        } else if (config.use_sqrt_softplus) {
           sqrt_softplus_warp_inplace<experts_per_thread, false>(wt, n_experts, threadIdx.x);
        } else {
           softmax_warp_inplace<experts_per_thread, false>(wt, n_experts, threadIdx.x);
        }
    }

    // Sanitize NaN to -FLT_MAX so the iterative argmax produces unique expert IDs.
    // NaN comparisons always return false, which would cause the same expert to be
    // selected repeatedly. -FLT_MAX compares normally and is still excluded by the
    // -INFINITY sentinel used after each selection round.
    // More relevant for the cuBLAS path. See https://github.com/ggml-org/llama.cpp/issues/19659
#pragma unroll
    for (int i = 0; i < experts_per_thread; i++) {
        if (__isnanf(wt[i])) {
            wt[i] = -FLT_MAX;
        }
    }

    // selection_wt is only needed when bias is present (selection uses wt + bias)
    // when no bias, we use wt directly for both selection and weight values
    [[maybe_unused]] float selection_wt[has_bias ? experts_per_thread : 1];

    if constexpr (has_bias) {
#pragma unroll
        for (int i = 0; i < experts_per_thread; i++) {
            selection_wt[i] = -INFINITY;
        }
#pragma unroll
        for (int i = 0; i < n_experts; i += WARP_SIZE) {
            const int expert = i + threadIdx.x;
            selection_wt[i / WARP_SIZE] =
                (n_experts % WARP_SIZE == 0 || expert < n_experts) ? wt[i / WARP_SIZE] + bias[expert] : -INFINITY;
        }
    }

    //at this point, each thread holds either a portion of the softmax distribution
    //or the raw logits. We do the argmax reduce over n_expert_used, each time marking
    //the expert weight as -inf to exclude from the next iteration

    float wt_sum = 0.f;

    float output_weights[experts_per_thread];

#pragma unroll
    for (int i = 0; i < experts_per_thread; i++) {
        output_weights[i] = 0.f;
    }

    ggml_cuda_pdl_lc();
    for (int k = 0; k < n_expert_used; k++) {
        float max_val    = wt[0];
        int   max_expert = threadIdx.x;

        if constexpr (has_bias) {
            float max_val_s = selection_wt[0];

#pragma unroll
            for (int i = 1; i < experts_per_thread; i++) {
                const int expert = threadIdx.x + i * WARP_SIZE;
                if ((n_experts % WARP_SIZE == 0 || expert < n_experts) && selection_wt[i] > max_val_s) {
                    max_val    = wt[i];
                    max_val_s  = selection_wt[i];
                    max_expert = expert;
                }
            }

#pragma unroll
            for (int mask = WARP_SIZE / 2; mask > 0; mask /= 2) {
                const float val    = __shfl_xor_sync(0xFFFFFFFF, max_val, mask, WARP_SIZE);
                const float val_s  = __shfl_xor_sync(0xFFFFFFFF, max_val_s, mask, WARP_SIZE);
                const int   expert = __shfl_xor_sync(0xFFFFFFFF, max_expert, mask, WARP_SIZE);
                if (val_s > max_val_s || (val_s == max_val_s && expert < max_expert)) {
                    max_val    = val;
                    max_val_s  = val_s;
                    max_expert = expert;
                }
            }

            if ((max_expert & (WARP_SIZE - 1)) == threadIdx.x) {
                selection_wt[max_expert / WARP_SIZE] = -INFINITY;
            }
        } else {
#pragma unroll
            for (int i = 1; i < experts_per_thread; i++) {
                const int expert = threadIdx.x + i * WARP_SIZE;
                if ((n_experts % WARP_SIZE == 0 || expert < n_experts) && wt[i] > max_val) {
                    max_val    = wt[i];
                    max_expert = expert;
                }
            }

#pragma unroll
            for (int mask = WARP_SIZE / 2; mask > 0; mask /= 2) {
                const float val    = __shfl_xor_sync(0xFFFFFFFF, max_val, mask, WARP_SIZE);
                const int   expert = __shfl_xor_sync(0xFFFFFFFF, max_expert, mask, WARP_SIZE);
                if (val > max_val || (val == max_val && expert < max_expert)) {
                    max_val    = val;
                    max_expert = expert;
                }
            }

            if ((max_expert & (WARP_SIZE - 1)) == threadIdx.x) {
                wt[max_expert / WARP_SIZE] = -INFINITY;
            }
        }

        if ((k & (WARP_SIZE - 1)) == threadIdx.x) {
            output_weights[k / WARP_SIZE] = max_val;
        }

        if ((max_expert & (WARP_SIZE - 1)) == threadIdx.x) {
            ids[k] = max_expert;
            if (config.with_norm) {
                wt_sum += max_val;
            }
        }
    }

    if (config.with_norm) {
        wt_sum              = warp_reduce_sum(wt_sum);
        wt_sum              = max(wt_sum, clamp_val);
        const float inv_sum = 1.0f / wt_sum;

        for (int i = 0; i < experts_per_thread; i++) {
            output_weights[i] *= inv_sum;
        }
    }

    if (config.delayed_softmax) {
        softmax_warp_inplace<experts_per_thread, true>(output_weights, n_expert_used, threadIdx.x);
    }

#pragma unroll
    for (int i = 0; i < experts_per_thread; i++) {
        const int idx = i * WARP_SIZE + threadIdx.x;
        if (idx < n_expert_used) {
            weights[idx] = output_weights[i] * scale_val;
        }
    }
}

template <int n_experts, bool has_bias>
__launch_bounds__(TOPK_MOE_ROWS_PER_BLOCK * WARP_SIZE, 1)
__global__ void topk_moe_cuda(const float *         logits,
                              float *               weights,
                              int32_t *             ids,
                              float *               bias,
                              const int             n_rows,
                              const int             n_expert_used,
                              const float           clamp_val,
                              const float           scale_val,
                              const topk_moe_config config) {
#if defined(GGML_USE_MUSA)
    // MUSA: every warp of a partially filled block must reach the barrier below.
    const int row = MIN(blockIdx.x * blockDim.y + threadIdx.y, n_rows - 1);
#else
    const int row = blockIdx.x * blockDim.y + threadIdx.y;
#endif // defined(GGML_USE_MUSA)
    if (row >= n_rows) {
        return;
    }

    logits += n_experts * row;
    weights += n_expert_used * row;
    ids += n_experts * row;

    constexpr int experts_per_thread = (n_experts > WARP_SIZE) ? n_experts / WARP_SIZE : 1;

    float wt[experts_per_thread];

    // Initialize all slots to -INFINITY
#pragma unroll
    for (int i = 0; i < experts_per_thread; i++) {
        wt[i] = -INFINITY;
    }

    ggml_cuda_pdl_sync();
#pragma unroll
    for (int i = 0; i < n_experts; i += WARP_SIZE) {
        const int expert  = i + threadIdx.x;
        wt[i / WARP_SIZE] = (n_experts % WARP_SIZE == 0 || expert < n_experts) ? logits[expert] : -INFINITY;
    }

    // Weights and IDs can alias logits, so wait until every row in the block reads its logits.
    __syncthreads();

    topk_moe_select<n_experts, has_bias>(wt, weights, ids, bias, n_expert_used, clamp_val, scale_val, config);
}

// [GGML_HIP_NORM_ROUTER] Single-token MoE routing in one launch: rms_norm*mul of the FFN input (F32 output plus its
// q8_1 copy for the gate/up MUL_MAT_ID), the F32 router matvec and topk_moe. One block per router row, each block
// recomputes the norm scale from x. Every value is formed exactly as by the three kernels it replaces:
//   - the sum of squares as rms_norm_mul_f32_unrolled<2> (1024 threads x 2 columns, x[t]^2 then x[t + 1024]^2 as fmas,
//     DPP warp sums, then the DPP sum of the 32 warp sums), the normalized values as scale * x * w,
//   - the router row as mul_mat_vec_f<float, float, 1, 256> (thread t: float2 columns t + 256*k in order, warp sums,
//     then the warp sum of the 8 warp sums padded with zeros),
//   - the top-k as topk_moe_cuda (same code), run by the first warp of the block that finishes last (atomic ticket in
//     ticket[0], reset by that block).
// Block b writes the F32 norm output and its q8_1 copy for values 32*(b + n_experts*m) + lane (quantize_q8_1_group as
// the norm kernel).
static constexpr int norm_router_ncols      = 2048;
static constexpr int norm_router_block_size = 256;

template <int n_experts, bool has_bias>
__launch_bounds__(norm_router_block_size, 1)
static __global__ void norm_router_topk_f32(const float * __restrict__ x,
                                            const float * __restrict__ norm_w,
                                            const float                eps,
                                            float * __restrict__       y,
                                            block_q8_1 * __restrict__  y_q8,
                                            const float * __restrict__ router_w,
                                            const int64_t              router_stride_row,
                                            float *                    logits,
                                            float *                    weights,
                                            int32_t *                  ids,
                                            const float * __restrict__ bias,
                                            const int                  n_expert_used,
                                            const float                clamp_val,
                                            const float                scale_val,
                                            const topk_moe_config      config,
                                            unsigned int *             ticket) {
    constexpr int ncols       = norm_router_ncols;
    constexpr int block_size  = norm_router_block_size;
    constexpr int nwarps      = block_size / WARP_SIZE;
    constexpr int nwarps_norm = 1024 / WARP_SIZE;     // warps of rms_norm_mul_f32_unrolled<2>
    constexpr int nsum        = nwarps_norm / nwarps; // of its warp sums per warp of this block
    constexpr int niter       = ncols / (2*block_size);
    static_assert(ncols == 2*1024, "the norm is that of rms_norm_mul_f32_unrolled<2>");

    const int tid  = threadIdx.x;
    const int lane = tid % WARP_SIZE;
    const int warp = tid / WARP_SIZE;
    const int row  = blockIdx.x;

    __shared__ float s_norm[nwarps_norm];
    __shared__ float buf_iw[WARP_SIZE];
    __shared__ bool  s_last;

    float xa[nsum];
    float xb[nsum];
#pragma unroll
    for (int j = 0; j < nsum; ++j) {
        const int t = (warp + nwarps*j)*WARP_SIZE + lane;
        xa[j] = x[t];
        xb[j] = x[t + 1024];
    }
    const float2 * x2 = (const float2 *) x;
    const float2 * m2 = (const float2 *) norm_w;
    const float2 * w2 = (const float2 *) (router_w + row*router_stride_row);
    float2 xr[niter];
    float2 mr[niter];
    float2 wr[niter];
#pragma unroll
    for (int k = 0; k < niter; ++k) {
        xr[k] = x2[tid + k*block_size];
        mr[k] = m2[tid + k*block_size];
        wr[k] = w2[tid + k*block_size];
    }
    // the norm output (F32 and q8_1): block b writes values 32*(b + n_experts*m) + lane from its first warp, one q8_1
    // block each (measured faster than whole 128-byte lines from fewer blocks)
    constexpr int ny = (ncols/WARP_SIZE + n_experts - 1) / n_experts;
    float yx[ny];
    float ym[ny];
    if (warp == 0) {
#pragma unroll
        for (int m = 0; m < ny; ++m) {
            const int i = (row + n_experts*m)*WARP_SIZE + lane;
            if (i < ncols) {
                yx[m] = x[i];
                ym[m] = norm_w[i];
            }
        }
    }

#pragma unroll
    for (int j = 0; j < nsum; ++j) {
        float tmp = 0.0f;
        tmp = fmaf(xa[j], xa[j], tmp);
        tmp = fmaf(xb[j], xb[j], tmp);
        tmp = warp_reduce_sum_dpp(tmp);
        if (lane == 0) {
            s_norm[warp + nwarps*j] = tmp;
        }
    }
    if (tid < WARP_SIZE) {
        buf_iw[tid] = 0.0f;
    }
    __syncthreads();
    const float mean  = warp_reduce_sum_dpp(s_norm[lane]) / ncols;
    const float scale = rsqrtf(mean + eps);

    if (warp == 0) {
#pragma unroll
        for (int m = 0; m < ny; ++m) {
            const int i = (row + n_experts*m)*WARP_SIZE + lane;
            if (i < ncols) {
                const float v = scale * yx[m] * ym[m];
                y[i] = v;
                if (y_q8 != nullptr) {
                    quantize_q8_1_group<true>(v, y_q8 + i/QK8_1, lane);
                }
            }
        }
    }

    float sumf = 0.0f;
#pragma unroll
    for (int k = 0; k < niter; ++k) {
        const float yx = scale * xr[k].x * mr[k].x;
        const float yy = scale * xr[k].y * mr[k].y;
        ggml_cuda_mad(sumf, wr[k].x, yx);
        ggml_cuda_mad(sumf, wr[k].y, yy);
    }
    sumf = warp_reduce_sum<WARP_SIZE>(sumf);
    buf_iw[warp] = sumf;
    __syncthreads();
    if (tid < WARP_SIZE) {
        const float v = warp_reduce_sum<WARP_SIZE>(buf_iw[tid]);
        if (tid == 0) {
            logits[row] = v;
        }
    }

    // the last block to finish does the top-k over all logits
    __threadfence();
    __syncthreads();
    if (tid == 0) {
        s_last = atomicAdd(ticket, 1u) == gridDim.x - 1;
    }
    __syncthreads();
    if (!s_last || warp != 0) {
        return;
    }
    if (lane == 0) {
        *ticket = 0;
    }
    __threadfence();

    constexpr int experts_per_thread = (n_experts > WARP_SIZE) ? n_experts / WARP_SIZE : 1;
    float wt[experts_per_thread];
#pragma unroll
    for (int i = 0; i < experts_per_thread; i++) {
        wt[i] = -INFINITY;
    }
#pragma unroll
    for (int i = 0; i < n_experts; i += WARP_SIZE) {
        const int expert  = i + lane;
        wt[i / WARP_SIZE] = (n_experts % WARP_SIZE == 0 || expert < n_experts) ? logits[expert] : -INFINITY;
    }
    topk_moe_select<n_experts, has_bias>(wt, weights, ids, bias, n_expert_used, clamp_val, scale_val, config);
}

template<bool has_bias>
static void launch_topk_moe_cuda(ggml_backend_cuda_context & ctx,
                                 const float *               logits,
                                 float *                     weights,
                                 int32_t *                   ids,
                                 float *                     bias,
                                 const int                   n_rows,
                                 const int                   n_expert,
                                 const int                   n_expert_used,
                                 const float                 clamp_val,
                                 const float                 scale_val,
                                 const topk_moe_config       config) {
    GGML_ASSERT(!(config.with_norm && config.delayed_softmax) &&
                "delayed softmax is not supported with weight normalization");
    const int    rows_per_block = TOPK_MOE_ROWS_PER_BLOCK;
    dim3         grid_dims((n_rows + rows_per_block - 1) / rows_per_block, 1, 1);
    dim3         block_dims(WARP_SIZE, rows_per_block, 1);
    cudaStream_t stream = ctx.stream();
    const ggml_cuda_kernel_launch_params launch_params = ggml_cuda_kernel_launch_params(grid_dims, block_dims, 0, stream);

    switch (n_expert) {
        case 1:
            ggml_cuda_kernel_launch(topk_moe_cuda<1, has_bias>, launch_params,
                logits, weights, ids, bias, n_rows, n_expert_used, clamp_val, scale_val, config);
            break;
        case 2:
            ggml_cuda_kernel_launch(topk_moe_cuda<2, has_bias>, launch_params,
                logits, weights, ids, bias, n_rows, n_expert_used, clamp_val, scale_val, config);
            break;
        case 4:
            ggml_cuda_kernel_launch(topk_moe_cuda<4, has_bias>, launch_params,
                logits, weights, ids, bias, n_rows, n_expert_used, clamp_val, scale_val, config);
            break;
        case 8:
            ggml_cuda_kernel_launch(topk_moe_cuda<8, has_bias>, launch_params,
                logits, weights, ids, bias, n_rows, n_expert_used, clamp_val, scale_val, config);
            break;
        case 16:
            ggml_cuda_kernel_launch(topk_moe_cuda<16, has_bias>, launch_params,
                logits, weights, ids, bias, n_rows, n_expert_used, clamp_val, scale_val, config);
            break;
        case 32:
            ggml_cuda_kernel_launch(topk_moe_cuda<32, has_bias>, launch_params,
                logits, weights, ids, bias, n_rows, n_expert_used, clamp_val, scale_val, config);
            break;
        case 64:
            ggml_cuda_kernel_launch(topk_moe_cuda<64, has_bias>, launch_params,
                logits, weights, ids, bias, n_rows, n_expert_used, clamp_val, scale_val, config);
            break;
        case 128:
            ggml_cuda_kernel_launch(topk_moe_cuda<128, has_bias>, launch_params,
                logits, weights, ids, bias, n_rows, n_expert_used, clamp_val, scale_val, config);
            break;
        case 256:
            ggml_cuda_kernel_launch(topk_moe_cuda<256, has_bias>, launch_params,
                logits, weights, ids, bias, n_rows, n_expert_used, clamp_val, scale_val, config);
            break;
        case 288: // StepFun 3.7
            ggml_cuda_kernel_launch(topk_moe_cuda<288, has_bias>, launch_params,
                logits, weights, ids, bias, n_rows, n_expert_used, clamp_val, scale_val, config);
            break;
        case 512:
            ggml_cuda_kernel_launch(topk_moe_cuda<512, has_bias>, launch_params,
                logits, weights, ids, bias, n_rows, n_expert_used, clamp_val, scale_val, config);
            break;
        case 576:
            ggml_cuda_kernel_launch(topk_moe_cuda<576, has_bias>, launch_params,
                logits, weights, ids, bias, n_rows, n_expert_used, clamp_val, scale_val, config);
            break;
        default:
            GGML_ASSERT(false && "fatal error");
            break;
    }
}

void ggml_cuda_op_topk_moe(ggml_backend_cuda_context &     ctx,
                           const ggml_tensor *             logits,
                           ggml_tensor *                   weights,
                           ggml_tensor *                   ids,
                           const ggml_tensor *             clamp,
                           const ggml_tensor *             scale,
                           const ggml_tensor *             bias,
                           const ggml_cuda_topk_moe_args & args) {
    GGML_ASSERT(logits->type == GGML_TYPE_F32);
    GGML_ASSERT(weights->type == GGML_TYPE_F32);
    GGML_ASSERT(ids->type == GGML_TYPE_I32);

    const int n_experts = logits->ne[0];
    const int n_rows    = logits->ne[1];

    const float * logits_d  = (const float *) logits->data;
    float *       weights_d = (float *) weights->data;
    int32_t *     ids_d     = (int32_t *) ids->data;
    float *       bias_d    = bias ? (float *) bias->data : nullptr;

    float scale_val = scale ? ggml_get_op_params_f32(scale, 0) : 1.0f;

    GGML_ASSERT(ids->nb[1] / ggml_type_size(ids->type) == (size_t) n_experts);

    const int n_expert_used = weights->ne[1];

    const bool with_norm = clamp != nullptr;

    float clamp_val = -INFINITY;
    if (clamp) {
        clamp_val = ggml_get_op_params_f32(clamp, 0);
    }

    topk_moe_config config;
    config.use_sigmoid       = args.sigmoid;
    config.use_sqrt_softplus = args.sqrt_softplus;
    config.with_norm         = with_norm;
    config.delayed_softmax   = args.delayed_softmax;

    if (bias) {
        launch_topk_moe_cuda<true>(ctx, logits_d, weights_d, ids_d, bias_d, n_rows, n_experts, n_expert_used, clamp_val,
                             scale_val, config);
    } else {
        launch_topk_moe_cuda<false>(ctx, logits_d, weights_d, ids_d, bias_d, n_rows, n_experts, n_expert_used, clamp_val,
                             scale_val, config);
    }
}

bool ggml_cuda_should_use_topk_moe(const ggml_tensor * gating_op,
                                   const ggml_tensor * weights,
                                   const ggml_tensor * logits,
                                   const ggml_tensor * ids) {
    // must match an instantiation of launch_topk_moe_cuda: a power of 2 up to 512,
    // or one of the non-power-of-2 expert counts of supported models
    const int n_expert = ids->nb[1] / ids->nb[0];
    if (((n_expert & (n_expert - 1)) != 0 || n_expert > 512) && n_expert != 288 && n_expert != 576) {
        return false;
    }

    if (!ggml_is_contiguous(weights) || !ggml_is_contiguous(logits)) {
        return false;
    }

    if (gating_op->op == GGML_OP_SOFT_MAX) {
        const ggml_tensor * softmax  = gating_op;
        float               scale    = 1.0f;
        float               max_bias = 0.0f;

        memcpy(&scale, (const float *) softmax->op_params + 0, sizeof(float));
        memcpy(&max_bias, (const float *) softmax->op_params + 1, sizeof(float));

        if (!ggml_is_contiguous(softmax->src[0])) {
            return false;
        }

        if (scale != 1.0f || max_bias != 0.0f) {
            return false;
        }

        // don't fuse when masks or sinks are present
        if (softmax->src[1] || softmax->src[2]) {
            return false;
        }
    } else if (gating_op->op == GGML_OP_UNARY) {
        ggml_unary_op op = ggml_get_unary_op(gating_op);

        if (op != GGML_UNARY_OP_SIGMOID && op != GGML_UNARY_OP_SOFTPLUS) {
            return false;
        }
    }

    return true;
}

bool ggml_cuda_norm_router_topk_supported(const ggml_tensor * x, const ggml_tensor * norm_w, const ggml_tensor * norm_out,
                                          const ggml_tensor * router_w, const ggml_tensor * logits) {
    const int64_t n_expert = router_w->ne[1];
    const auto aligned = [](const ggml_tensor * t) { return (uintptr_t) t->data % (2*sizeof(float)) == 0; };
    return x->type == GGML_TYPE_F32 && norm_w->type == GGML_TYPE_F32 && norm_out->type == GGML_TYPE_F32 &&
           router_w->type == GGML_TYPE_F32 && logits->type == GGML_TYPE_F32 &&
           x->ne[0] == norm_router_ncols && ggml_nrows(x) == 1 && ggml_is_contiguous(x) &&
           ggml_are_same_shape(norm_w, x) && ggml_is_contiguous(norm_w) &&
           ggml_are_same_shape(norm_out, x) && ggml_is_contiguous(norm_out) &&
           router_w->ne[0] == norm_router_ncols && router_w->ne[2] == 1 && router_w->ne[3] == 1 &&
           router_w->nb[0] == sizeof(float) && router_w->nb[1] % (2*sizeof(float)) == 0 &&
           (n_expert == 32 || n_expert == 64 || n_expert == 128 || n_expert == 256) &&
           logits->ne[0] == n_expert && ggml_nrows(logits) == 1 && ggml_is_contiguous(logits) &&
           aligned(x) && aligned(norm_w) && aligned(router_w);
}

void ggml_cuda_op_norm_router_topk(ggml_backend_cuda_context &     ctx,
                                   const ggml_tensor *             x,
                                   const ggml_tensor *             norm_w,
                                   const float                     eps,
                                   ggml_tensor *                   norm_out,
                                   block_q8_1 *                    norm_q8,
                                   const ggml_tensor *             router_w,
                                   ggml_tensor *                   logits,
                                   ggml_tensor *                   weights,
                                   ggml_tensor *                   ids,
                                   const ggml_tensor *             clamp,
                                   const ggml_tensor *             scale,
                                   const ggml_tensor *             bias,
                                   const ggml_cuda_topk_moe_args & args,
                                   unsigned int *                  ticket) {
    GGML_ASSERT(weights->type == GGML_TYPE_F32 && ids->type == GGML_TYPE_I32);
    const int n_experts     = router_w->ne[1];
    const int n_expert_used = weights->ne[1];
    GGML_ASSERT(ids->nb[1] / ggml_type_size(ids->type) == (size_t) n_experts);

    topk_moe_config config;
    config.use_sigmoid       = args.sigmoid;
    config.use_sqrt_softplus = args.sqrt_softplus;
    config.with_norm         = clamp != nullptr;
    config.delayed_softmax   = args.delayed_softmax;
    GGML_ASSERT(!config.delayed_softmax);
    const float clamp_val = clamp ? ggml_get_op_params_f32(clamp, 0) : -INFINITY;
    const float scale_val = scale ? ggml_get_op_params_f32(scale, 0) : 1.0f;

    const ggml_cuda_kernel_launch_params launch_params(dim3(n_experts, 1, 1), dim3(norm_router_block_size, 1, 1), 0, ctx.stream());
    const auto launch = [&](auto n_experts_tag, auto has_bias_tag) {
        constexpr int  ne = decltype(n_experts_tag)::value;
        constexpr bool hb = decltype(has_bias_tag)::value;
        ggml_cuda_kernel_launch(norm_router_topk_f32<ne, hb>, launch_params,
            (const float *) x->data, (const float *) norm_w->data, eps, (float *) norm_out->data, norm_q8,
            (const float *) router_w->data, (int64_t) (router_w->nb[1] / sizeof(float)), (float *) logits->data,
            (float *) weights->data, (int32_t *) ids->data, bias ? (const float *) bias->data : nullptr,
            n_expert_used, clamp_val, scale_val, config, ticket);
    };
    const auto launch_bias = [&](auto n_experts_tag) {
        if (bias) {
            launch(n_experts_tag, std::true_type{});
        } else {
            launch(n_experts_tag, std::false_type{});
        }
    };
    switch (n_experts) {
        case  32: launch_bias(std::integral_constant<int,  32>{}); break;
        case  64: launch_bias(std::integral_constant<int,  64>{}); break;
        case 128: launch_bias(std::integral_constant<int, 128>{}); break;
        case 256: launch_bias(std::integral_constant<int, 256>{}); break;
        default: GGML_ABORT("fatal error");
    }
}
