// Kernel Tuner harness: the production RDNA3 one-column MMVQ kernels of ggml-cuda/mmvq.cu, compiled from the tools6
// tree (amd-opt + the MMVQ_TUNE_NWARPS_N1 hook) so that the tunables are compile-time constants:
//   KT_TYPE              GGML_TYPE_Q4_K | GGML_TYPE_Q5_K | GGML_TYPE_Q6_K | GGML_TYPE_Q8_0
//   MMVQ_TUNE_NWARPS_N1  warps per block of the one-column kernels (calc_nwarps hook; unset = production table)
//   KT_ROWS              rows per block: n1_rows of mul_mat_vec_q and MMVQ_MOE_DOWN_RPB of the MoE down kernel
// One shared object per (KT_TYPE, MMVQ_TUNE_NWARPS_N1, KT_ROWS); the Kernel Tuner stub (kt_stub.c) dlopens it.
// Entry points (all return the mean kernel time in ms over `iters` launches, cache-cold by rotating weight copies):
//   kt_mmvq_n1      dense one-token MUL_MAT                           mul_mat_vec_q<T, 1, false, .., n1_rows>
//   kt_moe_gate_up  one-token MUL_MAT_ID up with fused gate + SWIGLU  mul_mat_vec_q<T, 1, true, .., n1_rows>
//                   (+ GGML_HIP_GATE_UP_Q8 q8_1 output when with_q8)
//   kt_moe_down     one-token MoE down + expert weighting + residual  mul_mat_vec_q_moe_down_reduce<T, n_used, rpb>
// Arguments are the host arrays of the Python side (weights as raw GGUF blocks, activations as block_q8_1).
#ifndef KT_ROWS
#define KT_ROWS 1
#endif
#define MMVQ_MOE_DOWN_RPB KT_ROWS

#include "ggml-cuda/mmvq.cu"

#include <cstdio>
#include <vector>

#define KT_CHECK(x) do { hipError_t e_ = (x); if (e_ != hipSuccess) { \
    fprintf(stderr, "kt: %s failed: %s (%s:%d)\n", #x, hipGetErrorString(e_), __FILE__, __LINE__); return 1e30f; } } while (0)

static constexpr ggml_type kt_type = KT_TYPE;
static constexpr int kt_n1_rows    = KT_ROWS == 1 ? 0 : KT_ROWS; // production instance for one row per block

// device copy of a host array in the process-wide cache of libkt_mem.so (kt_mem.hip), keyed by slot name
extern "C" char * kt_dev(const char * name, const void * host, size_t n, int ncopies, size_t * pitch_out);
struct kt_buf {
    const char * name;
    char *       dev    = nullptr;
    size_t       pitch  = 0;   // bytes between copies
    int          copies = 1;

    hipError_t get(const void * h, size_t n, int ncopies) {
        dev    = kt_dev(name, h, n, ncopies, &pitch);
        copies = ncopies;
        return dev ? hipSuccess : hipErrorOutOfMemory;
    }
    char * at(int i) const { return dev + size_t(i % copies) * pitch; }
};

// copies of the weights so that the rotating launches read at least cold_mb MiB in total (past the 96 MiB MALL)
static int kt_copies(size_t bytes, int cold_mb) {
    if (cold_mb <= 0) {
        return 1;
    }
    const size_t want = size_t(cold_mb) << 20;
    int n = int((want + bytes - 1) / bytes);
    return n < 1 ? 1 : n > 64 ? 64 : n;
}

template <typename F>
static float kt_time(F launch, int iters) {
    hipEvent_t a, b;
    KT_CHECK(hipEventCreate(&a));
    KT_CHECK(hipEventCreate(&b));
    for (int i = 0; i < 2; ++i) {
        launch(i);
    }
    KT_CHECK(hipGetLastError());
    KT_CHECK(hipEventRecord(a, 0));
    for (int i = 0; i < iters; ++i) {
        launch(i);
    }
    KT_CHECK(hipEventRecord(b, 0));
    KT_CHECK(hipEventSynchronize(b));
    KT_CHECK(hipGetLastError());
    float ms = 0.0f;
    KT_CHECK(hipEventElapsedTime(&ms, a, b));
    KT_CHECK(hipEventDestroy(a));
    KT_CHECK(hipEventDestroy(b));
    return ms / iters;
}

static size_t kt_row_bytes(int ncols) {
    return size_t(ncols / ggml_cuda_type_traits<kt_type>::qk) * ggml_cuda_type_traits<kt_type>::bs;
}

static size_t kt_q8_1_bytes(int ncols) {
    return size_t(GGML_PAD(ncols, MATRIX_ROW_PADDING) / QK8_1) * sizeof(block_q8_1);
}

extern "C" float kt_mmvq_n1(const void * w, const void * y, float * dst, int nrows, int ncols, int iters, int cold_mb) {
    kt_buf bw{"n1.w"}, by{"n1.y"}, bd{"n1.dst"};
    const size_t wbytes = size_t(nrows) * kt_row_bytes(ncols);
    const int ncopies = kt_copies(wbytes, cold_mb);
    KT_CHECK(bw.get(w, wbytes, ncopies));
    KT_CHECK(by.get(y, kt_q8_1_bytes(ncols), 1));
    KT_CHECK(bd.get(dst, size_t(nrows) * sizeof(float), 1));
    constexpr int nwarps = calc_nwarps(kt_type, 1, MMVQ_PARAMETERS_RDNA3_0);
    constexpr int rpb    = calc_rows_per_block(1, MMVQ_PARAMETERS_RDNA3_0, false, nwarps, kt_type, kt_n1_rows);
    if (nrows % rpb != 0) {
        fprintf(stderr, "kt: nrows %d not a multiple of %d rows per block\n", nrows, rpb);
        return 1e30f;
    }
    const uint3 one = init_fastdiv_values(1);
    const uint32_t stride_row_x = ncols / ggml_cuda_type_traits<kt_type>::qk;
    const uint32_t stride_col_y = GGML_PAD(ncols, MATRIX_ROW_PADDING) / QK8_1;
    const ggml_cuda_mm_fusion_args_device fusion{};
    const auto launch = [&](int i) {
        mul_mat_vec_q<kt_type, 1, false, false, false, false, kt_n1_rows><<<dim3(nrows / rpb, 1, 1), dim3(32, nwarps, 1)>>>(
            bw.at(i), by.dev, nullptr, fusion, (float *) bd.dev, ncols, one, stride_row_x, stride_col_y, nrows, one,
            0, 0, 0, one, 0, 0, 0, 0);
    };
    const float ms = kt_time(launch, iters);
    KT_CHECK(hipMemcpy(dst, bd.dev, size_t(nrows) * sizeof(float), hipMemcpyDeviceToHost));
    return ms;
}

// up/gate: [ncols, nrows, n_expert] each, y: one q8_1 row, ids: n_used experts, dst: [nrows, n_used],
// q8_out: [nrows*n_used/32] block_q8_1 (GGML_HIP_GATE_UP_Q8; written when with_q8)
extern "C" float kt_moe_gate_up(const void * w_up, const void * w_gate, const void * y, const int32_t * ids, float * dst,
                                void * q8_out, int nrows, int ncols, int n_expert, int n_used, int with_q8, int iters,
                                int cold_mb) {
    kt_buf bu{"gu.up"}, bg{"gu.gate"}, by{"gu.y"}, bi{"gu.ids"}, bd{"gu.dst"}, bq{"gu.q8"}, bt{"gu.tickets"};
    const size_t wbytes = size_t(n_expert) * nrows * kt_row_bytes(ncols);
    // the launches read n_used of the n_expert experts: copies sized by what one launch reads
    const int ncopies = kt_copies(2 * wbytes * n_used / n_expert, cold_mb);
    KT_CHECK(bu.get(w_up, wbytes, ncopies));
    KT_CHECK(bg.get(w_gate, wbytes, ncopies));
    KT_CHECK(by.get(y, kt_q8_1_bytes(ncols), 1));
    KT_CHECK(bi.get(ids, size_t(n_used) * sizeof(int32_t), 1));
    const size_t ndst = size_t(nrows) * n_used;
    KT_CHECK(bd.get(dst, ndst * sizeof(float), 1));
    KT_CHECK(bq.get(q8_out, ndst / QK8_1 * sizeof(block_q8_1), 1));
    static std::vector<unsigned int> tickets_host;
    tickets_host.assign(ndst / QK8_1, 0u);
    KT_CHECK(bt.get(tickets_host.data(), tickets_host.size() * sizeof(unsigned int), 1));
    KT_CHECK(hipMemset(bt.dev, 0, tickets_host.size() * sizeof(unsigned int)));
    constexpr int nwarps = calc_nwarps(kt_type, 1, MMVQ_PARAMETERS_RDNA3_0);
    constexpr int rpb    = calc_rows_per_block(1, MMVQ_PARAMETERS_RDNA3_0, false, nwarps, kt_type, kt_n1_rows);
    if (nrows % rpb != 0 || (with_q8 && (nrows % QK8_1 != 0 || QK8_1 % rpb != 0))) {
        fprintf(stderr, "kt: nrows %d does not fit %d rows per block\n", nrows, rpb);
        return 1e30f;
    }
    const uint32_t stride_row_x     = ncols / ggml_cuda_type_traits<kt_type>::qk;
    const uint32_t stride_channel_x = nrows * stride_row_x;
    const uint32_t s11              = GGML_PAD(ncols, MATRIX_ROW_PADDING) / QK8_1;
    // as ggml_cuda_mul_mat_vec_q for ids: src1 [ncols, 1, 1], dst [nrows, n_used, 1]
    const uint3    nchannels_y      = init_fastdiv_values(1);
    const uint32_t stride_col_dst   = nrows * n_used; // s2
    const uint32_t stride_col_y     = s11;            // s12 = ne11*s11
    const uint32_t stride_ch_dst    = nrows;          // s1
    const uint32_t stride_ch_y      = s11;
    const uint3    zero             = make_uint3(0, 0, 0);
    const uint3    one              = init_fastdiv_values(1);
    const auto launch = [&](int i) {
        ggml_cuda_mm_fusion_args_device fusion{};
        fusion.gate   = bg.at(i);
        fusion.glu_op = GGML_GLU_OP_SWIGLU;
        if (with_q8) {
            fusion.q8_out     = (block_q8_1 *) bq.dev;
            fusion.q8_tickets = (unsigned int *) bt.dev;
        }
        mul_mat_vec_q<kt_type, 1, true, false, false, false, kt_n1_rows><<<dim3(nrows / rpb, n_used, 1), dim3(32, nwarps, 1)>>>(
            bu.at(i), by.dev, (const int32_t *) bi.dev, fusion, (float *) bd.dev, ncols, nchannels_y, stride_row_x,
            stride_col_y, stride_col_dst, zero, stride_channel_x, stride_ch_y, stride_ch_dst, one, 0, 0, 0, n_used);
    };
    const float ms = kt_time(launch, iters);
    KT_CHECK(hipMemcpy(dst, bd.dev, ndst * sizeof(float), hipMemcpyDeviceToHost));
    if (with_q8) {
        KT_CHECK(hipMemcpy(q8_out, bq.dev, ndst / QK8_1 * sizeof(block_q8_1), hipMemcpyDeviceToHost));
    }
    return ms;
}

// down: [ncols, nrows, n_expert], y: n_used q8_1 rows (one per expert), dst = residual + sum_e w[e] * (W[ids[e]] . y_e)
extern "C" float kt_moe_down(const void * w, const void * y, const int32_t * ids, const float * weights,
                             const float * residual, float * dst, int nrows, int ncols, int n_expert, int n_used,
                             int iters, int cold_mb) {
    kt_buf bw{"dn.w"}, by{"dn.y"}, bi{"dn.ids"}, bwt{"dn.weights"}, br{"dn.residual"}, bd{"dn.dst"};
    const size_t wbytes = size_t(n_expert) * nrows * kt_row_bytes(ncols);
    const int ncopies = kt_copies(wbytes * n_used / n_expert, cold_mb);
    KT_CHECK(bw.get(w, wbytes, ncopies));
    const uint32_t stride_ch_y = GGML_PAD(ncols, MATRIX_ROW_PADDING) / QK8_1;
    KT_CHECK(by.get(y, size_t(n_used) * stride_ch_y * sizeof(block_q8_1), 1));
    KT_CHECK(bi.get(ids, size_t(n_used) * sizeof(int32_t), 1));
    KT_CHECK(bwt.get(weights, size_t(n_used) * sizeof(float), 1));
    KT_CHECK(br.get(residual, size_t(nrows) * sizeof(float), 1));
    KT_CHECK(bd.get(dst, size_t(nrows) * sizeof(float), 1));
    if (nrows % MMVQ_MOE_DOWN_RPB != 0) {
        fprintf(stderr, "kt: nrows %d not a multiple of %d\n", nrows, MMVQ_MOE_DOWN_RPB);
        return 1e30f;
    }
    constexpr int nwarps = calc_nwarps(kt_type, 1, MMVQ_PARAMETERS_RDNA3_0);
    const uint32_t stride_row_x     = ncols / ggml_cuda_type_traits<kt_type>::qk;
    const uint32_t stride_channel_x = nrows * stride_row_x;
    const auto launch_n = [&](auto n_tag, int i) {
        constexpr int ne = decltype(n_tag)::value;
        mul_mat_vec_q_moe_down_reduce<kt_type, ne, MMVQ_MOE_DOWN_RPB><<<dim3(nrows / MMVQ_MOE_DOWN_RPB, 1, 1), dim3(32, nwarps, 1)>>>(
            bw.at(i), (const block_q8_1 *) by.dev, (const int32_t *) bi.dev, (const float *) bwt.dev,
            (const float *) br.dev, (float *) bd.dev, ncols, stride_row_x, stride_channel_x, stride_ch_y, n_used);
    };
    const auto launch = [&](int i) {
        switch (n_used) {
            case 2: launch_n(std::integral_constant<int, 2>{}, i); break;
            case 4: launch_n(std::integral_constant<int, 4>{}, i); break;
            case 6: launch_n(std::integral_constant<int, 6>{}, i); break;
            case 8: launch_n(std::integral_constant<int, 8>{}, i); break;
            default: break;
        }
    };
    if (n_used != 2 && n_used != 4 && n_used != 6 && n_used != 8) {
        fprintf(stderr, "kt: n_used %d unsupported\n", n_used);
        return 1e30f;
    }
    const float ms = kt_time(launch, iters);
    KT_CHECK(hipMemcpy(dst, bd.dev, size_t(nrows) * sizeof(float), hipMemcpyDeviceToHost));
    return ms;
}
