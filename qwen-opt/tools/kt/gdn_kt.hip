// Kernel Tuner harness: the production GATED_DELTA_NET decode kernel of ggml-cuda/gated_delta_net.cu
// (gated_delta_net_cuda<S_v = 128, KDA = false, keep_rs = false, l2_qk = true, lag>), the instances the Qwen3.8 decode
// runs: plain decode (n_tokens 1, lag = false) and the MTP verify of the rollback by replay (lag = true,
// GATED_DELTA_NET_LAG, K pending rows). Tunables:
//   KT_CPW      columns per warp (template cols_per_warp, production gdn_cols_per_warp = 4); changes the lane split of
//               the reductions, so a value != 4 is not bitwise
//   num_warps   warps per block (runtime; production: 4, halved while H*n_seqs*(S_v/(4*num_warps)) < nsm), bitwise
// __launch_bounds__ of the kernel is warp_size*4, so num_warps <= 4.
// q/k/v are views of one conv output row per token (qwen35.cpp: q at 0, k at Hk*S_v, v at 2*Hk*S_v, row stride
// 2*Hk*S_v + H*S_v floats), g and beta [H, n_tokens] contiguous; the state [S_v, S_v, H] transposed per column.
#ifndef KT_CPW
#define KT_CPW 4
#endif

#include "ggml-cuda/gated_delta_net.cu"

#include <cstdio>

#define KT_CHECK(x) do { hipError_t e_ = (x); if (e_ != hipSuccess) { \
    fprintf(stderr, "kt: %s failed: %s (%s:%d)\n", #x, hipGetErrorString(e_), __FILE__, __LINE__); return 1e30f; } } while (0)

static constexpr int kt_S_v = 128;

// device copy of a host array in the process-wide cache of libkt_mem.so (kt_mem.hip), keyed by slot name
extern "C" char * kt_dev(const char * name, const void * host, size_t n, int ncopies, size_t * pitch_out);
struct kt_dbuf {
    const char * name;
    char * dev = nullptr;
    hipError_t get(const void * h, size_t n) {
        dev = kt_dev(name, h, n, 1, nullptr);
        return dev ? hipSuccess : hipErrorOutOfMemory;
    }
};

// qkv: [n_tokens][2*Hk*S_v + H*S_v] (pre-norm q, k; v), g, beta: [n_tokens][H], s_in: [H][S_v cols][S_v],
// attn: [n_tokens][H][S_v], s_out: like s_in, pend: [2 planes][K rows][H*(2*S_v+2)] (lag only),
// info: n_pend (lag only, planes: read 0, write 1)
extern "C" float kt_gdn(const float * qkv, const float * g, const float * beta, const float * s_in, float * attn,
                        float * s_out, float * pend, int H, int Hk, int n_tokens, int lag, int K, int n_pend,
                        int num_warps, float l2_eps, int iters) {
    kt_dbuf bqkv{"gdn.qkv"}, bg{"gdn.g"}, bb{"gdn.beta"}, bs{"gdn.s_in"}, ba{"gdn.attn"}, bso{"gdn.s_out"},
            bp{"gdn.pend"}, bi{"gdn.info"};
    const int64_t S_v  = kt_S_v;
    const int64_t row  = 2 * Hk * S_v + H * S_v;
    const int64_t R    = H * (2 * S_v + 2);
    KT_CHECK(bqkv.get(qkv, sizeof(float) * row * n_tokens));
    KT_CHECK(bg.get(g, sizeof(float) * H * n_tokens));
    KT_CHECK(bb.get(beta, sizeof(float) * H * n_tokens));
    KT_CHECK(bs.get(s_in, sizeof(float) * S_v * S_v * H));
    KT_CHECK(ba.get(attn, sizeof(float) * S_v * H * n_tokens));
    KT_CHECK(bso.get(s_out, sizeof(float) * S_v * S_v * H));
    // lag info [n_seqs = 1, 4]: src row 0, dst row 0, n_pend, planes (read 0, write 1); uploaded every call
    static int info_host[4];
    info_host[0] = 0; info_host[1] = 0; info_host[2] = n_pend; info_host[3] = 0 | (1 << 1);
    KT_CHECK(bi.get(info_host, sizeof(info_host)));
    KT_CHECK(hipMemcpy(bi.dev, info_host, sizeof(info_host), hipMemcpyHostToDevice));
    if (lag) {
        KT_CHECK(bp.get(pend, sizeof(float) * 2 * K * R));
    }
    if (num_warps < 1 || num_warps > 4 || S_v % (KT_CPW * num_warps) != 0) {
        fprintf(stderr, "kt: num_warps %d unsupported\n", num_warps);
        return 1e30f;
    }
    const float * q = (const float *) bqkv.dev;
    const float * k = q + Hk * S_v;
    const float * v = q + 2 * Hk * S_v;
    const dim3 grid(H, 1, S_v / (KT_CPW * num_warps));
    const dim3 block(32, num_warps, 1);
    const uint3 neqk1_magic = init_fastdiv_values(Hk);
    const uint3 rq3_magic   = init_fastdiv_values(1);
    const float scale    = 1.0f / sqrtf((float) S_v);
    const float l2_scale = 1.0f;
    const gdn_lag_args lagp = { (float *) bp.dev, 2 * K * R, (const int32_t *) bi.dev };
    const auto launch = [&]() {
        if (lag) {
            gated_delta_net_cuda<kt_S_v, false, false, true, true, KT_CPW><<<grid, block>>>(
                q, k, v, (const float *) bg.dev, (const float *) bb.dev, (const float *) bs.dev, nullptr, 0,
                (float *) ba.dev, (float *) bso.dev, H, n_tokens, 1, S_v, row, row * n_tokens, S_v, row, row * n_tokens,
                1, H, H * n_tokens, neqk1_magic, rq3_magic, scale, l2_eps, l2_scale, S_v * S_v * H, K, lagp);
        } else {
            gated_delta_net_cuda<kt_S_v, false, false, true, false, KT_CPW><<<grid, block>>>(
                q, k, v, (const float *) bg.dev, (const float *) bb.dev, (const float *) bs.dev, nullptr, 0,
                (float *) ba.dev, (float *) bso.dev, H, n_tokens, 1, S_v, row, row * n_tokens, S_v, row, row * n_tokens,
                1, H, H * n_tokens, neqk1_magic, rq3_magic, scale, l2_eps, l2_scale, S_v * S_v * H, 1, lagp);
        }
    };
    hipEvent_t a, b;
    KT_CHECK(hipEventCreate(&a));
    KT_CHECK(hipEventCreate(&b));
    launch();
    launch();
    KT_CHECK(hipGetLastError());
    KT_CHECK(hipEventRecord(a, 0));
    for (int i = 0; i < iters; ++i) {
        launch();
    }
    KT_CHECK(hipEventRecord(b, 0));
    KT_CHECK(hipEventSynchronize(b));
    KT_CHECK(hipGetLastError());
    float ms = 0.0f;
    KT_CHECK(hipEventElapsedTime(&ms, a, b));
    KT_CHECK(hipEventDestroy(a));
    KT_CHECK(hipEventDestroy(b));
    KT_CHECK(hipMemcpy(attn, ba.dev, sizeof(float) * S_v * H * n_tokens, hipMemcpyDeviceToHost));
    KT_CHECK(hipMemcpy(s_out, bso.dev, sizeof(float) * S_v * S_v * H, hipMemcpyDeviceToHost));
    if (lag) {
        KT_CHECK(hipMemcpy(pend, bp.dev, sizeof(float) * 2 * K * R, hipMemcpyDeviceToHost));
    }
    return ms / iters;
}
