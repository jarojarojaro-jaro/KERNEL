// Prints an FNV hash of the GPU MUL_MAT output for fixed pseudo-random data, per (type, ncols).
// Run against two builds (LD_LIBRARY_PATH) to check bit-identical results.
#include "ggml.h"
#include "ggml-alloc.h"
#include "ggml-backend.h"

#include <cstdint>
#include <cstdio>
#include <random>
#include <vector>

int main() {
    ggml_backend_load_all();
    ggml_backend_t be = ggml_backend_dev_init(ggml_backend_dev_by_type(GGML_BACKEND_DEVICE_TYPE_GPU), nullptr);
    const ggml_type types[] = {GGML_TYPE_Q4_K, GGML_TYPE_Q5_K, GGML_TYPE_Q6_K, GGML_TYPE_IQ4_XS, GGML_TYPE_IQ4_NL,
                               GGML_TYPE_Q8_0, GGML_TYPE_Q3_K, GGML_TYPE_IQ3_S, GGML_TYPE_Q2_K, GGML_TYPE_IQ2_XXS};
    const int64_t k = 5120, n = 1024;
    for (ggml_type t : types) {
        for (int nc : {1, 2, 4, 8}) {
            ggml_init_params ip = {ggml_tensor_overhead() * 8 + ggml_graph_overhead(), nullptr, true};
            ggml_context * ctx = ggml_init(ip);
            ggml_tensor * w = ggml_new_tensor_2d(ctx, t, k, n);
            ggml_tensor * y = ggml_new_tensor_2d(ctx, GGML_TYPE_F32, k, nc);
            ggml_tensor * o = ggml_mul_mat(ctx, w, y);
            ggml_cgraph * gf = ggml_new_graph(ctx);
            ggml_build_forward_expand(gf, o);
            ggml_backend_buffer_t buf = ggml_backend_alloc_ctx_tensors(ctx, be);
            std::mt19937 rng(7);
            std::normal_distribution<float> nd(0.0f, 1.0f);
            std::vector<float> f(k * n), yv(k * nc), imat(k, 1.0f);
            for (auto & v : f) v = nd(rng);
            for (auto & v : yv) v = nd(rng);
            std::vector<uint8_t> q(ggml_row_size(t, k) * n);
            ggml_quantize_chunk(t, f.data(), q.data(), 0, n, k, ggml_quantize_requires_imatrix(t) ? imat.data() : nullptr);
            ggml_backend_tensor_set(w, q.data(), 0, q.size());
            ggml_backend_tensor_set(y, yv.data(), 0, yv.size() * 4);
            ggml_backend_graph_compute(be, gf);
            std::vector<uint32_t> out(n * nc);
            ggml_backend_tensor_get(o, out.data(), 0, out.size() * 4);
            uint64_t h = 1469598103934665603ull;
            for (uint32_t v : out) { h ^= v; h *= 1099511628211ull; }
            printf("%-8s n%d %016llx\n", ggml_type_name(t), nc, (unsigned long long) h);
            ggml_backend_buffer_free(buf);
            ggml_free(ctx);
        }
    }
    ggml_backend_free(be);
}
