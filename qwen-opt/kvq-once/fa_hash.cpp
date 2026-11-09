// fa_hash: FLASH_ATTN_EXT on one backend with fixed pseudo-random inputs, prints an FNV-1a hash of the output bytes.
// Bit-exactness check of GGML_HIP_KVQ_ONCE (env read once per process): run with =0 and =1, the hashes must match.
//   fa_hash BACKEND KV NB [HS=256 NH_KV=4 GQA=6]   e.g. fa_hash ROCm0 98304 5
// K/V are q4_0 views of a 2*KV row buffer (as a KV cache), mask f16 with the last NB-1-j rows of token j masked.
#include "ggml.h"
#include "ggml-alloc.h"
#include "ggml-backend.h"

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <vector>

static uint64_t rng = 0x9E3779B97F4A7C15ull;
static float frand() { // uniform [-1, 1)
    rng ^= rng << 13; rng ^= rng >> 7; rng ^= rng << 17;
    return (float) ((rng >> 40) * (1.0 / 8388608.0)) - 1.0f;
}

int main(int argc, char ** argv) {
    if (argc < 4) { fprintf(stderr, "usage: fa_hash BACKEND KV NB [HS NH_KV GQA]\n"); return 2; }
    const char *  bname = argv[1];
    const int64_t kv    = atoll(argv[2]);
    const int64_t nb    = atoll(argv[3]);
    const int64_t hs    = argc > 4 ? atoll(argv[4]) : 256;
    const int64_t nh    = argc > 5 ? atoll(argv[5]) : 4;
    const int64_t gqa   = argc > 6 ? atoll(argv[6]) : 6;

    ggml_backend_dev_t dev = ggml_backend_dev_by_name(bname);
    if (!dev) { fprintf(stderr, "no backend %s\n", bname); return 1; }
    ggml_backend_t be = ggml_backend_dev_init(dev, nullptr);

    ggml_init_params ip = { ggml_tensor_overhead()*16 + ggml_graph_overhead(), nullptr, true };
    ggml_context * ctx = ggml_init(ip);
    ggml_tensor * q  = ggml_new_tensor_4d(ctx, GGML_TYPE_F32,  hs, nb, nh*gqa, 1);
    ggml_tensor * k0 = ggml_new_tensor_4d(ctx, GGML_TYPE_Q4_0, hs, 2*kv, nh, 1);
    ggml_tensor * v0 = ggml_new_tensor_4d(ctx, GGML_TYPE_Q4_0, hs, 2*kv, nh, 1);
    ggml_tensor * k  = ggml_view_4d(ctx, k0, hs, kv, nh, 1, k0->nb[1], k0->nb[2], k0->nb[3], 0);
    ggml_tensor * v  = ggml_view_4d(ctx, v0, hs, kv, nh, 1, v0->nb[1], v0->nb[2], v0->nb[3], 0);
    ggml_tensor * m  = ggml_new_tensor_4d(ctx, GGML_TYPE_F16,  kv, nb, 1, 1);
    ggml_tensor * out = ggml_flash_attn_ext(ctx, q, k, v, m, 1.0f/sqrtf((float) hs), 0.0f, 0.0f);
    ggml_prec_set_acc(out, GGML_PREC_F32);
    ggml_backend_buffer_t buf = ggml_backend_alloc_ctx_tensors(ctx, be);

    std::vector<float> f(ggml_nelements(q));
    for (float & x : f) { x = 2.0f*frand(); }
    ggml_backend_tensor_set(q, f.data(), 0, ggml_nbytes(q));
    for (ggml_tensor * t : {k0, v0}) { // in chunks of rows (196608 x 2 x 4 rows of 256 floats would be 1.6 GB)
        const int64_t nrows = ggml_nrows(t), chunk = 65536;
        const size_t  row_bytes = ggml_row_size(GGML_TYPE_Q4_0, hs);
        std::vector<float>   src(hs*chunk);
        std::vector<uint8_t> dst(row_bytes*chunk);
        for (int64_t r0 = 0; r0 < nrows; r0 += chunk) {
            const int64_t n = std::min(chunk, nrows - r0);
            for (int64_t i = 0; i < hs*n; ++i) { src[i] = frand(); }
            ggml_quantize_chunk(GGML_TYPE_Q4_0, src.data(), dst.data(), 0, n, hs, nullptr);
            ggml_backend_tensor_set(t, dst.data(), r0*row_bytes, n*row_bytes);
        }
    }
    std::vector<float> mf(kv*nb);
    for (int64_t j = 0; j < nb; ++j) {
        for (int64_t i = 0; i < kv; ++i) {
            mf[j*kv + i] = i >= kv - (nb - 1 - j) ? -INFINITY : 0.0f;
        }
    }
    std::vector<ggml_fp16_t> mh(mf.size());
    ggml_fp32_to_fp16_row(mf.data(), mh.data(), (int64_t) mf.size());
    ggml_backend_tensor_set(m, mh.data(), 0, ggml_nbytes(m));

    ggml_cgraph * gf = ggml_new_graph(ctx);
    ggml_build_forward_expand(gf, out);
    if (ggml_backend_graph_compute(be, gf) != GGML_STATUS_SUCCESS) { fprintf(stderr, "compute failed\n"); return 1; }
    std::vector<uint8_t> res(ggml_nbytes(out));
    ggml_backend_tensor_get(out, res.data(), 0, res.size());
    uint64_t h = 0xcbf29ce484222325ull;
    for (uint8_t b : res) { h = (h ^ b) * 0x100000001b3ull; }
    double sum = 0.0;
    for (size_t i = 0; i < res.size()/4; ++i) { sum += ((const float *) res.data())[i]; }
    printf("fa_hash %s kv=%lld nb=%lld hs=%lld nh_kv=%lld gqa=%lld once=%s hash=%016llx sum=%.6f\n", bname, (long long) kv,
           (long long) nb, (long long) hs, (long long) nh, (long long) gqa, getenv("GGML_HIP_KVQ_ONCE") ? getenv("GGML_HIP_KVQ_ONCE") : "unset",
           (unsigned long long) h, sum);
    ggml_backend_buffer_free(buf);
    ggml_free(ctx);
    ggml_backend_free(be);
    return 0;
}
