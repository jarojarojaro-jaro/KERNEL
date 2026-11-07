// CPU-only model of llama_kv_cache::set_input_kq_mask fast path (set_input_kq_mask_seq, topka-q63 llama-kv-cache.cpp:1843-1895)
// + std::vector staging resize (input_data, :1549-1555). fp16 stored as uint16_t. No GPU.
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>
int main() {
    const uint16_t keep = 0x0000, drop = 0xFC00; // f16 0, -inf
    for (int n_kv : {2048, 32768, 98304, 199936, 262144}) {
        std::vector<int32_t> pos(n_kv);
        for (int j = 0; j < n_kv; ++j) pos[j] = j;
        for (int n_tok : {1, 5}) {
            const int reps = 200;
            double best = 1e9, sum = 0;
            for (int r = 0; r < reps; ++r) {
                auto t0 = std::chrono::steady_clock::now();
                std::vector<uint16_t> staging;               // fresh per call, as input_data()
                staging.resize((size_t) n_kv * n_tok);
                uint16_t * data = staging.data();
                const int32_t p_lo = n_kv - n_tok;
                for (int j = 0; j < n_kv; ++j) data[j] = pos[j] >= 0 && pos[j] < p_lo ? keep : drop;
                for (int i = 1; i < n_tok; ++i) std::memcpy(data + (size_t) n_kv * i, data, n_kv * sizeof(uint16_t));
                for (int i = 0; i < n_tok; ++i) for (int c = p_lo; c <= p_lo + i; ++c) data[(size_t) n_kv * i + c] = keep;
                auto t1 = std::chrono::steady_clock::now();
                volatile uint16_t sink = data[n_kv / 2]; (void) sink;
                double us = std::chrono::duration<double, std::micro>(t1 - t0).count();
                best = us < best ? us : best; sum += us;
            }
            std::printf("n_kv %6d rows %d bytes %8zu  best %7.1f us  mean %7.1f us\n", n_kv, n_tok, (size_t) n_kv * n_tok * 2, best, sum / reps);
        }
    }
}
