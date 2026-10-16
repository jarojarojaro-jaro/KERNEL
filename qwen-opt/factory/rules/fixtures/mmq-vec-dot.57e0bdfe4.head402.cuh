#pragma once

#include "vecdotq.cuh"
#include "mma.cuh"

using namespace ggml_cuda_mma;

#include "mmq.cuh"

template <ggml_type type, int J, bool fallback> static __device__ __forceinline__ void ggml_cuda_mmq_vec_dot_q4_0_q8_1_dp4a(
        const int * __restrict__ x, const int * __restrict__ y, float * __restrict__ sum, const int k00) {
    constexpr int warp_size = ggml_cuda_get_physical_warp_size();
    constexpr int nwarps    = ggml_cuda_mmq_get_nthreads(type, J, fallback, GGML_PREC_Q8) / warp_size;
    constexpr int I         = ggml_cuda_mmq_get_I(type, J, fallback, GGML_PREC_Q8);

    constexpr tile_x_sizes txs = mmq_get_dp4a_tile_x_sizes(GGML_TYPE_Q4_0, I);
    const int   * x_qs = (const int   *) x;
    const float * x_df = (const float *) x_qs + txs.qs;
    const int   * y_qs = (const int   *) y + 4;
    const half2 * y_ds = (const half2 *) y;

// #pragma unroll
    for (int k01 = 0; k01 < MMQ_TILE_NE_K; k01 += QR4_0*VDR_Q4_0_Q8_1_MMQ) {
        const int k0 = k00 + k01;

#pragma unroll
        for (int j0 = 0; j0 < J; j0 += nwarps) {
            const int j = j0 + threadIdx.y;

#pragma unroll
            for (int i0 = 0; i0 < I; i0 += warp_size) {
                const int i = i0 + threadIdx.x;
                const int kyqs = QI8_1 * ((k01/2) / (QI8_1/2)) + (k01/2) % (QI8_1/2);

                int u[2*VDR_Q4_0_Q8_1_MMQ];

                constexpr int max_cpy = ggml_cuda_get_max_cpy_bytes();
                constexpr int mcpy_int = max_cpy / sizeof(int);
                static_assert(VDR_Q4_0_Q8_1_MMQ == 4, "bad VDR_Q4_0_Q8_1_MMQ");

                int tmp0[4], tmp1[4];

                #pragma unroll
                for (int l0 = 0; l0 < 4 / mcpy_int; ++l0) {
                    ggml_cuda_memcpy_1<max_cpy>(tmp0 + l0 * mcpy_int, &y_qs[j*MMQ_TILE_Y_K + kyqs + l0 * mcpy_int]  );
                    ggml_cuda_memcpy_1<max_cpy>(tmp1 + l0 * mcpy_int, &y_qs[j*MMQ_TILE_Y_K + kyqs + QI4_0 + l0 * mcpy_int]);
                }

                u[0]=tmp0[0]; u[2]=tmp0[1]; u[4]=tmp0[2]; u[6]=tmp0[3];
                u[1]=tmp1[0]; u[3]=tmp1[1]; u[5]=tmp1[2]; u[7]=tmp1[3];

                sum[j0/nwarps*I/warp_size + i0/warp_size] += vec_dot_q4_0_q8_1_impl<VDR_Q4_0_Q8_1_MMQ>
                    (&x_qs[i*(MMQ_TILE_NE_K + 1) + k0/QR4_0], u,
                     x_df[i*(MMQ_TILE_NE_K/QI4_0) + i/QI4_0 + k0/(QR4_0*QI4_0)], y_ds[j*MMQ_TILE_Y_K + k01/QI8_1]);
            }
        }
    }
}

template <ggml_type type, int J, bool fallback> static __device__ __forceinline__ void ggml_cuda_mmq_vec_dot_q4_1_q8_1_dp4a(
        const int * __restrict__ x, const int * __restrict__ y, float * __restrict__ sum, const int k00) {
    constexpr int warp_size = ggml_cuda_get_physical_warp_size();
    constexpr int nwarps    = ggml_cuda_mmq_get_nthreads(type, J, fallback, GGML_PREC_Q8) / warp_size;
    constexpr int I         = ggml_cuda_mmq_get_I(type, J, fallback, GGML_PREC_Q8);

    constexpr tile_x_sizes txs = mmq_get_dp4a_tile_x_sizes(GGML_TYPE_Q4_1, I);
    const int   * x_qs = (const int   *) x;
    const half2 * x_dm = (const half2 *) x_qs + txs.qs;
    const int   * y_qs = (const int   *) y + 4;
    const half2 * y_ds = (const half2 *) y;

// #pragma unroll
    for (int k01 = 0; k01 < MMQ_TILE_NE_K; k01 += QR4_1*VDR_Q4_1_Q8_1_MMQ) {
        const int k0 = k00 + k01;

#pragma unroll
        for (int j0 = 0; j0 < J; j0 += nwarps) {
            const int j = j0 + threadIdx.y;

#pragma unroll
            for (int i0 = 0; i0 < I; i0 += warp_size) {
                const int i = i0 + threadIdx.x;
                const int kyqs = QI8_1 * ((k01/2) / (QI8_1/2)) + (k01/2) % (QI8_1/2);

                int u[2*VDR_Q4_1_Q8_1_MMQ];

                constexpr int max_cpy = ggml_cuda_get_max_cpy_bytes();
                constexpr int mcpy_int = max_cpy / sizeof(int);
                static_assert(VDR_Q4_0_Q8_1_MMQ == 4, "bad VDR_Q4_0_Q8_1_MMQ");

                int tmp0[4], tmp1[4];

                #pragma unroll
                for (int l0 = 0; l0 < 4 / mcpy_int; ++l0) {
                    ggml_cuda_memcpy_1<max_cpy>(tmp0 + l0 * mcpy_int, &y_qs[j*MMQ_TILE_Y_K + kyqs + l0 * mcpy_int]  );
                    ggml_cuda_memcpy_1<max_cpy>(tmp1 + l0 * mcpy_int, &y_qs[j*MMQ_TILE_Y_K + kyqs + QI4_1 + l0 * mcpy_int]);
                }

                u[0]=tmp0[0]; u[2]=tmp0[1]; u[4]=tmp0[2]; u[6]=tmp0[3];
                u[1]=tmp1[0]; u[3]=tmp1[1]; u[5]=tmp1[2]; u[7]=tmp1[3];

                sum[j0/nwarps*I/warp_size + i0/warp_size] += vec_dot_q4_1_q8_1_impl<VDR_Q4_1_Q8_1_MMQ>
                    (&x_qs[i*(MMQ_TILE_NE_K + 1) + k0/QR4_1], u,
                     x_dm[i*(MMQ_TILE_NE_K/QI4_1) + i/QI4_1 + k0/(QR4_1*QI4_1)], y_ds[j*MMQ_TILE_Y_K + k01/QI8_1]);
            }
        }
    }
}

template <ggml_type type, int J, bool fallback> static __device__ __forceinline__ void ggml_cuda_mmq_vec_dot_q8_0_q8_1_dp4a(
        const int * __restrict__ x, const int * __restrict__ y, float * __restrict__ sum, const int k00) {
    constexpr int warp_size = ggml_cuda_get_physical_warp_size();
    constexpr int nwarps    = ggml_cuda_mmq_get_nthreads(type, J, fallback, GGML_PREC_Q8) / warp_size;
    constexpr int I         = ggml_cuda_mmq_get_I(type, J, fallback, GGML_PREC_Q8);

    constexpr tile_x_sizes txs = mmq_get_dp4a_tile_x_sizes(GGML_TYPE_Q8_0, I);
    const int   * x_qs = (const int   *) x;
    const float * x_df = (const float *) x_qs + txs.qs;
    const int   * y_qs = (const int   *) y + 4;
    const float * y_df = (const float *) y;

// #pragma unroll
    for (int k01 = 0; k01 < MMQ_TILE_NE_K; k01 += VDR_Q8_0_Q8_1_MMQ) {
        const int k0 = k00 + k01;

#pragma unroll
        for (int j0 = 0; j0 < J; j0 += nwarps) {
            const int j = j0 + threadIdx.y;

#pragma unroll
            for (int i0 = 0; i0 < I; i0 += warp_size) {
                const int i = i0 + threadIdx.x;

                sum[j0/nwarps*I/warp_size + i0/warp_size] += vec_dot_q8_0_q8_1_impl<float, VDR_Q8_0_Q8_1_MMQ>
                    (&x_qs[i*(2*MMQ_TILE_NE_K + 1) + k0], &y_qs[j*MMQ_TILE_Y_K + k0 % MMQ_TILE_NE_K],
                     x_df[i*(2*MMQ_TILE_NE_K/QI8_0) + i/(QI8_0/2) + k0/QI8_0], y_df[j*MMQ_TILE_Y_K + (k0/QI8_1) % (MMQ_TILE_NE_K/QI8_1)]);
            }
        }
    }
}

template <ggml_type type, int J, bool fallback, mmq_q8_1_ds_layout ds_layout>
static __device__ __forceinline__ void ggml_cuda_mmq_vec_dot_q8_0_q8_1_mma(
    const int * __restrict__ x, const int * __restrict__ y, float * __restrict__ sum, const int k00) {
#if defined(AMD_MFMA_AVAILABLE) || defined(AMD_WMMA_AVAILABLE)
    constexpr data_layout input_layout = get_input_data_layout();
    typedef tile<16,  8, int, input_layout>        tile_A;
    typedef tile<16,  8, int, input_layout>        tile_B;
    typedef tile<16, 16, int, DATA_LAYOUT_J_MAJOR> tile_C;

    constexpr int sram_stride   = ggml_cuda_mmq_get_sram_stride(type, J, fallback, GGML_PREC_Q8);
    constexpr int rows_per_warp = ggml_cuda_mmq_get_rows_per_warp(type, J, fallback, GGML_PREC_Q8);
    constexpr int ntx           = rows_per_warp/tile_C::I; // Number of x minitiles per warp.

    y += (threadIdx.y % ntx) * (tile_C::J*MMQ_TILE_Y_K);

    const int   * x_qs = (const int   *) x;
    const float * x_df = (const float *) x_qs + 2*MMQ_TILE_NE_K;
    const int   * y_qs = (const int   *) y + 4;
    const float * y_df = (const float *) y;
    const half2 * y_ds = (const half2 *) y;

    const int i0 = (threadIdx.y / ntx) * rows_per_warp;

    for (int k01 = 0; k01 < MMQ_TILE_NE_K; k01 += QI8_0) {
        const int k0 = k00 + k01;

        tile_A A[ntx];
#pragma unroll
        for (int n = 0; n < ntx; ++n) {
            load_ldmatrix(A[n], x_qs + (i0 + n*tile_A::I)*sram_stride + k0, sram_stride);
        }

#pragma unroll
        for (int j0 = 0; j0 < J; j0 += ntx*tile_C::J) {
            tile_B B;
            load_ldmatrix(B, y_qs + j0*MMQ_TILE_Y_K + k01, MMQ_TILE_Y_K);

            float dB;
            const int j = j0 + tile_C::get_j(0);
            if (ds_layout == MMQ_Q8_1_DS_LAYOUT_D4) {
                dB = y_df[j*MMQ_TILE_Y_K + k01/QI8_1];
            } else {
                dB = __low2float(y_ds[j*MMQ_TILE_Y_K + k01/QI8_1]);
            }

#pragma unroll
            for (int n = 0; n < ntx; ++n) {
                tile_C C;
                mma(C, A[n], B);

#pragma unroll
                for (int l = 0; l < tile_C::ne; ++l) {
                    const int i = i0 + n*tile_A::I + tile_C::get_i(l);
                    const float dA = x_df[i*sram_stride + k0/QI8_0];
                    sum[(j0/tile_C::J + n)*tile_C::ne + l] += C.x[l]*dA*dB;
                }
            }
        }
    }
#else
    typedef tile<16, 8, int> tile_A;
    typedef tile< 8, 8, int> tile_B;
    typedef tile<16, 8, int> tile_C;

    constexpr int sram_stride   = ggml_cuda_mmq_get_sram_stride(type, J, fallback, GGML_PREC_Q8);
    constexpr int rows_per_warp = ggml_cuda_mmq_get_rows_per_warp(type, J, fallback, GGML_PREC_Q8);
    constexpr int ntx           = rows_per_warp/tile_C::I; // Number of x minitiles per warp.

    y += (threadIdx.y % ntx) * (tile_C::J*MMQ_TILE_Y_K);

    const int   * x_qs = (const int   *) x;
    const float * x_df = (const float *) x_qs + 2*MMQ_TILE_NE_K;
    const int   * y_qs = (const int   *) y + 4;
    const float * y_df = (const float *) y;
    const half2 * y_ds = (const half2 *) y;

    tile_A A[ntx][MMQ_TILE_NE_K/QI8_0];
    float dA[ntx][tile_C::ne/2][MMQ_TILE_NE_K/QI8_0];

    const int i0 = (threadIdx.y/ntx)*rows_per_warp;

#pragma unroll
    for (int n = 0; n < ntx; ++n) {
#pragma unroll
        for (int k01 = 0; k01 < MMQ_TILE_NE_K; k01 += QI8_0) {
            const int k0 = k00 + k01;

            load_ldmatrix(A[n][k01/QI8_0], x_qs + (i0 + n*tile_A::I)*sram_stride + k0, sram_stride);
        }

#pragma unroll
        for (int l = 0; l < tile_C::ne/2; ++l) {
            const int i = i0 + n*tile_A::I + tile_C::get_i(2*l);

#pragma unroll
            for (int k01 = 0; k01 < MMQ_TILE_NE_K; k01 += QI8_0) {
                const int k0 = k00 + k01;

                dA[n][l][k01/QI8_0] = x_df[i*sram_stride + k0/QI8_0];
            }
        }
    }

#pragma unroll
    for (int j0 = 0; j0 < J; j0 += ntx*tile_C::J) {
#pragma unroll
        for (int k01 = 0; k01 < MMQ_TILE_NE_K; k01 += QI8_0) {
            tile_B B;
            float dB[tile_C::ne/2];

            load_generic(B, y_qs + j0*MMQ_TILE_Y_K + k01, MMQ_TILE_Y_K); // faster than load_ldmatrix

#pragma unroll
            for (int l = 0; l < tile_C::ne/2; ++l) {
                const int j = j0 + tile_C::get_j(l);

                if (ds_layout == MMQ_Q8_1_DS_LAYOUT_D4) {
                    dB[l] =             y_df[j*MMQ_TILE_Y_K + k01/QI8_1];
                } else {
                    dB[l] = __low2float(y_ds[j*MMQ_TILE_Y_K + k01/QI8_1]);
                }
            }

#pragma unroll
            for (int n = 0; n < ntx; ++n) {
                tile_C C;
                mma(C, A[n][k01/QI8_0], B);

#pragma unroll
                for (int l = 0; l < tile_C::ne; ++l) {
                    sum[(j0/tile_C::J + n)*tile_C::ne + l] += C.x[l]*dA[n][l/2][k01/QI8_0]*dB[l%2];
                }
            }
        }
    }
#endif // defined(AMD_MFMA_AVAILABLE) || defined(AMD_WMMA_AVAILABLE)
}


template <ggml_type type, int J, bool fallback> static __device__ __forceinline__ void ggml_cuda_mmq_vec_dot_q8_1_q8_1_dp4a(
        const int * __restrict__ x, const int * __restrict__ y, float * __restrict__ sum, const int k00) {
    constexpr int warp_size = ggml_cuda_get_physical_warp_size();
    constexpr int nwarps    = ggml_cuda_mmq_get_nthreads(type, J, fallback, GGML_PREC_Q8) / warp_size;
    constexpr int I         = ggml_cuda_mmq_get_I(type, J, fallback, GGML_PREC_Q8);

    constexpr tile_x_sizes txs = mmq_get_dp4a_tile_x_sizes(GGML_TYPE_Q5_1, I);
    const int   * x_qs = (const int   *) x;
    const half2 * x_dm = (const half2 *) x_qs + txs.qs;
    const int   * y_qs = (const int   *) y + 4;
    const half2 * y_ds = (const half2 *) y;

// #pragma unroll
    for (int k01 = 0; k01 < MMQ_TILE_NE_K; k01 += VDR_Q8_0_Q8_1_MMQ) {
        const int k0 = k00 + k01;

#pragma unroll
        for (int j0 = 0; j0 < J; j0 += nwarps) {
            const int j = j0 + threadIdx.y;

#pragma unroll
            for (int i0 = 0; i0 < I; i0 += warp_size) {
                const int i = i0 + threadIdx.x;

                sum[j0/nwarps*I/warp_size + i0/warp_size] += vec_dot_q8_1_q8_1_impl<QR5_1*VDR_Q5_1_Q8_1_MMQ>
                    (&x_qs[i*(2*MMQ_TILE_NE_K + 1) + k0], &y_qs[j*MMQ_TILE_Y_K + k01],
                    x_dm[i*(MMQ_TILE_NE_K/QI5_1) + i/QI5_1 + k0/QI8_1], y_ds[j*MMQ_TILE_Y_K + k01/QI8_1]);
            }
        }
    }
}

#if defined(GGML_USE_HIP)
// Makes n widened scales opaque to the compiler (otherwise the f16->f32 conversions fold back into v_fma_mix, which
// is not VOPD) and hands them over in runs of 4 (or 2) consecutive VGPRs, so that products of different scale pairs
// find the different register banks that a VOPD pair needs.
template <int n>
static __device__ __forceinline__ void ggml_cuda_mmq_epi_pin(float * v) {
    typedef float float4_t __attribute__((ext_vector_type(4)));
    typedef float float2_t __attribute__((ext_vector_type(2)));
    if constexpr (n % 4 == 0) {
#pragma unroll
        for (int c = 0; c < n; c += 4) {
            float4_t t = {v[c + 0], v[c + 1], v[c + 2], v[c + 3]};
            asm("" : "+v"(t));
            v[c + 0] = t.x; v[c + 1] = t.y; v[c + 2] = t.z; v[c + 3] = t.w;
        }
    } else if constexpr (n % 2 == 0) {
#pragma unroll
        for (int c = 0; c < n; c += 2) {
            float2_t t = {v[c + 0], v[c + 1]};
            asm("" : "+v"(t));
            v[c + 0] = t.x; v[c + 1] = t.y;
        }
    } else {
#pragma unroll
        for (int c = 0; c < n; ++c) {
            asm("" : "+v"(v[c]));
        }
    }
}
#endif // defined(GGML_USE_HIP)

// epi (RDNA3 only, GGML_HIP_MMQ_EPI): the same per-element IEEE operations in the same order, with the scale epilogue
// in VOPD-pairable f32 ops (v_dual_mul/add/fmac) instead of v_fma_mix and v_cvt_f32_i32:
// - the half2 scales are widened to f32 once per k01 step (the x scales are shared by all y minitiles); f16->f32 is
//   exact and the product of two f16 values is exact in f32 (11+11 significand bits, |a*b| in [2^-48, 2^32]), so
//   a.x*b.x and fma(a.y, b.y, sum) on the widened values give the bits of v_fma_mix on the f16 values;
// - the int32 accumulator starts at 0x4B400000 (the float 1.5*2^23) instead of 0: |C| <= 32*128*128 = 2^19 < 2^22, so
//   the WMMA sum is exact either way (no saturation), the bits of 0x4B400000 + C are the float 12582912 + C, and
//   subtracting 12582912 gives (float) C exactly (+0 for C == 0), as v_cvt_f32_i32 does.
template <ggml_type type, int J, bool fallback, bool epi = false> static __device__ __forceinline__ void ggml_cuda_mmq_vec_dot_q8_1_q8_1_mma(
        const int * __restrict__ x, const int * __restrict__ y, float * __restrict__ sum, const int k00) {
#if defined(RDNA3)
    if constexpr (epi) {
        constexpr data_layout input_layout = get_input_data_layout();
        typedef tile<16,  8, int, input_layout>        tile_A;
        typedef tile<16,  8, int, input_layout>        tile_B;
        typedef tile<16, 16, int, DATA_LAYOUT_J_MAJOR> tile_C;

        constexpr int sram_stride   = ggml_cuda_mmq_get_sram_stride(type, J, fallback, GGML_PREC_Q8);
        constexpr int rows_per_warp = ggml_cuda_mmq_get_rows_per_warp(type, J, fallback, GGML_PREC_Q8);
        constexpr int ntx           = rows_per_warp/tile_C::I; // Number of x minitiles per warp.

        constexpr int   c_bias_i = 0x4B400000;
        constexpr float c_bias_f = 12582912.0f;

        y += (threadIdx.y % ntx) * (tile_C::J*MMQ_TILE_Y_K);

        const int   * x_qs = (const int   *) x;
        const half2 * x_dm = (const half2 *) x_qs + 2*MMQ_TILE_NE_K;
        const int   * y_qs = (const int   *) y + 4;
        const half2 * y_dm = (const half2 *) y;

        const int i0 = (threadIdx.y / ntx) * rows_per_warp;

        constexpr int nj = (J + ntx*tile_C::J - 1) / (ntx*tile_C::J); // Number of y minitiles per warp.

#pragma unroll 1
        for (int k01 = 0; k01 < MMQ_TILE_NE_K; k01 += QI8_1) {
            const int k0 = k00 + k01;

            tile_A A[ntx];
            float ax[ntx*tile_C::ne];
            float ay[ntx*tile_C::ne];
            float bx[nj];
            float by[nj];
#pragma unroll
            for (int n = 0; n < ntx; ++n) {
                load_ldmatrix(A[n], x_qs + (i0 + n*tile_A::I)*sram_stride + k0, sram_stride);
#pragma unroll
                for (int l = 0; l < tile_C::ne; ++l) {
                    const int i = i0 + n*tile_A::I + tile_C::get_i(l);
                    const float2 dmA = __half22float2(x_dm[i*sram_stride + k0/QI8_1]);
                    ax[n*tile_C::ne + l] = dmA.x;
                    ay[n*tile_C::ne + l] = dmA.y;
                }
            }
#pragma unroll
            for (int jt = 0; jt < nj; ++jt) {
                const int j = jt*ntx*tile_C::J + tile_C::get_j(0);
                const float2 dsB = __half22float2(y_dm[j*MMQ_TILE_Y_K + k01/QI8_1]);
