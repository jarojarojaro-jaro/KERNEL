// Cache-cold microbenchmark for quantized mat-vec / small-batch mat-mat on a ggml GPU backend.
//
// For every (type, rows x cols, ncols) case it allocates enough weight copies to exceed the
// 96 MB Infinity Cache, builds one graph with one MUL_MAT per copy (round robin), and reports
// the effective weight-read bandwidth (GB/s) and microseconds per MUL_MAT.
// The shapes are exactly the Qwen3.8-27B decode / verify shapes.
//
// usage: mmvq_bench [ncols list, default 1,2,4,8] [filter substring on type name]

#include "ggml.h"
#include "ggml-alloc.h"
#include "ggml-backend.h"

#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <random>
#include <sstream>
#include <string>
#include <vector>

struct shape { int64_t k, n; };   // weight is k (cols, contiguous) x n (rows)

static double run_case(ggml_backend_t backend, ggml_type type, shape s, int ncols, int reps) {
    const size_t row_bytes = ggml_row_size(type, s.k);
    const size_t w_bytes   = row_bytes * s.n;
    const size_t target    = 512ull << 20; // 512 MB of weights >> 96 MB IC
    const int    ncopies   = (int) std::max<size_t>(4, std::min<size_t>(256, target / w_bytes));

    ggml_init_params ip = { ggml_tensor_overhead() * (3 * ncopies + 16) + ggml_graph_overhead_custom(4 * ncopies + 16, false), nullptr, true };
    ggml_context * ctx = ggml_init(ip);

    std::vector<ggml_tensor *> ws(ncopies), ys(ncopies), outs(ncopies);
    for (int i = 0; i < ncopies; ++i) {
        ws[i] = ggml_new_tensor_2d(ctx, type, s.k, s.n);
        ys[i] = ggml_new_tensor_2d(ctx, GGML_TYPE_F32, s.k, ncols);
    }
    ggml_cgraph * gf = ggml_new_graph_custom(ctx, 4 * ncopies + 16, false);
    for (int i = 0; i < ncopies; ++i) {
        outs[i] = ggml_mul_mat(ctx, ws[i], ys[i]);
        ggml_build_forward_expand(gf, outs[i]);
    }
    ggml_backend_buffer_t buf = ggml_backend_alloc_ctx_tensors(ctx, backend);
    if (!buf) { fprintf(stderr, "alloc failed\n"); exit(1); }

    // fill weights with valid quantized data from random floats (same data for every copy)
    std::mt19937 rng(42);
    std::normal_distribution<float> nd(0.0f, 0.02f);
    std::vector<float> f(s.k * s.n);
    for (auto & v : f) v = nd(rng);
    std::vector<uint8_t> q(w_bytes);
    std::vector<float> imat(s.k, 1.0f);
    ggml_quantize_chunk(type, f.data(), q.data(), 0, s.n, s.k, ggml_quantize_requires_imatrix(type) ? imat.data() : nullptr);
    std::vector<float> yv(s.k * ncols);
    std::normal_distribution<float> nd1(0.0f, 1.0f);
    for (auto & v : yv) v = nd1(rng);
    for (int i = 0; i < ncopies; ++i) {
        ggml_backend_tensor_set(ws[i], q.data(), 0, w_bytes);
        ggml_backend_tensor_set(ys[i], yv.data(), 0, yv.size() * sizeof(float));
    }

    ggml_backend_graph_compute(backend, gf); // warmup (also builds the HIP graph)
    ggml_backend_graph_compute(backend, gf);
    ggml_backend_synchronize(backend);
    auto t0 = std::chrono::high_resolution_clock::now();
    for (int r = 0; r < reps; ++r) {
        ggml_backend_graph_compute(backend, gf);
    }
    ggml_backend_synchronize(backend);
    auto t1 = std::chrono::high_resolution_clock::now();
    const double us = std::chrono::duration<double, std::micro>(t1 - t0).count() / (double(reps) * ncopies);

    ggml_backend_buffer_free(buf);
    ggml_free(ctx);
    return us;
}

int main(int argc, char ** argv) {
    std::vector<int> ncols_list = {1, 2, 4, 8};
    if (argc > 1) {
        ncols_list.clear();
        std::stringstream ss(argv[1]);
        std::string t;
        while (std::getline(ss, t, ',')) ncols_list.push_back(atoi(t.c_str()));
    }
    const char * filter = argc > 2 ? argv[2] : "";
    const int reps = getenv("REPS") ? atoi(getenv("REPS")) : 20;

    ggml_backend_load_all();
    ggml_backend_dev_t dev = ggml_backend_dev_by_type(GGML_BACKEND_DEVICE_TYPE_GPU);
    if (!dev) { fprintf(stderr, "no GPU backend\n"); return 1; }
    ggml_backend_t backend = ggml_backend_dev_init(dev, nullptr);
    printf("# device: %s\n", ggml_backend_dev_description(dev));

    // (type, shapes) as they occur in Qwen3.8-27B UD-Q4_K_XL
    struct item { ggml_type t; std::vector<shape> shapes; };
    const shape s_ffn_up{5120, 17408}, s_ffn_down{17408, 5120}, s_qkv{5120, 10240}, s_q{5120, 12288},
                s_gate{5120, 6144}, s_out{6144, 5120}, s_kv{5120, 1024}, s_ab{5120, 48}, s_head{5120, 248320};
    std::vector<item> items = {
        {GGML_TYPE_Q5_K,   {s_ffn_up, s_ffn_down, s_qkv, s_q, s_gate, s_out, s_kv}},
        {GGML_TYPE_IQ4_XS, {s_ffn_up, s_ffn_down, s_qkv, s_q, s_gate, s_out}},
        {GGML_TYPE_Q4_K,   {s_ffn_up, s_ffn_down, s_qkv, s_q, s_gate, s_out, s_kv}},
        {GGML_TYPE_Q6_K,   {s_ffn_up, s_ffn_down, s_qkv, s_out, s_kv, s_head}},
        {GGML_TYPE_IQ4_NL, {s_ffn_up, s_ffn_down, s_qkv}},
        {GGML_TYPE_Q8_0,   {s_out, s_kv, s_ab}},
        {GGML_TYPE_Q3_K,   {s_ffn_up}},
        {GGML_TYPE_IQ3_S,  {s_ffn_down}},
    };
    if (getenv("SALUKI")) {   // Underdog-Saluki-27B IQ2-mix types
        items = {
            {GGML_TYPE_IQ2_XXS, {s_ffn_up, s_ffn_down, s_qkv}},
            {GGML_TYPE_IQ3_S,   {s_ffn_up, s_ffn_down, s_qkv}},
            {GGML_TYPE_Q2_K,    {s_ffn_up, s_ffn_down}},
            {GGML_TYPE_IQ2_S,   {s_ffn_up, s_ffn_down}},
            {GGML_TYPE_IQ2_XS,  {s_ffn_up, s_ffn_down}},
            {GGML_TYPE_IQ1_M,   {s_ffn_up, s_ffn_down}},
            {GGML_TYPE_IQ3_XXS, {s_ffn_up, s_ffn_down}},
            {GGML_TYPE_IQ1_S,   {s_ffn_up, s_ffn_down}},
        };
    }

    // bring clocks up before the first measured case
    run_case(backend, GGML_TYPE_Q4_K, s_ffn_up, 1, 1000);

    printf("%-7s %6s %6s %5s %9s %8s\n", "type", "k", "n", "ncols", "us", "GB/s");
    for (const auto & it : items) {
        if (*filter && !strcasestr(ggml_type_name(it.t), filter)) continue;
        const size_t max_shapes = getenv("QUICK") ? 2 : it.shapes.size();
        for (size_t si = 0; si < std::min(max_shapes, it.shapes.size()); ++si) {
            const shape & s = it.shapes[si];
            for (int nc : ncols_list) {
                const double us = run_case(backend, it.t, s, nc, reps);
                const double gbs = ggml_row_size(it.t, s.k) * s.n / (us * 1e3);
                printf("%-7s %6lld %6lld %5d %9.2f %8.1f\n", ggml_type_name(it.t), (long long) s.k, (long long) s.n, nc, us, gbs);
                fflush(stdout);
            }
        }
    }
    ggml_backend_free(backend);
    return 0;
}
