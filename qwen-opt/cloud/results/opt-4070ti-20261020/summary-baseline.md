
### qwen  (`/tmp/nv-final-4070ti-qwen-20261020/`)

| metryka | U0 | U1 | T | T vs U0 | T vs U1 | log |
|---|---|---|---|---|---|---|
| chat T=1 (spec_sweep 6×3) t/s | 40.8 [40.8 / 40.8] | 65.5 [65.4 / 65.7] | 93.3 [93.7 / 93.0] | +128.7% | +42.4% | `logs/spec_sweep.jsonl` |
| chat T=1 ms/krok | 24.51 [24.50 / 24.51] | 45.81 [45.85 / 45.76] | 31.98 [32.01 / 31.95] | +30.5% | -30.2% | `logs/spec_sweep.jsonl` |
| chat T=1 tok/krok | 1.00 [1.00 / 1.00] | 3.01 [3.01 / 3.01] | 3.00 [3.00 / 3.00] | +200.4% | -0.1% | `logs/spec_sweep.jsonl` |
| chat T=0 greedy (6×1) t/s | 40.8 | 67.2 | 95.3 | +134.0% | +41.8% | `logs/spec_sweep.jsonl` |
| chat T=0 ms/krok | 24.54 | 46.10 | 32.15 | +31.0% | -30.3% | `logs/spec_sweep.jsonl` |
| chat T=0 tok/krok | 1.00 | 3.10 | 3.07 | +206.5% | -1.2% | `logs/spec_sweep.jsonl` |
| code-edit mvs T=0 t/s | 40.3 [40.3 / 40.2] | 101.5 [100.9 / 102.2] | 295.0 [294.7 / 295.3] | +632.3% | +190.6% | `logs/copy_bench.jsonl` |
| mvs ms/krok | 24.82 [24.80 / 24.85] | 48.62 [48.93 / 48.30] | 48.37 [48.33 / 48.40] | +94.8% | -0.5% | `logs/copy_bench.jsonl` |
| mvs tok/krok | 1.00 [1.00 / 1.00] | 4.95 [4.95 / 4.95] | 14.32 [14.32 / 14.32] | +1332.2% | +189.5% | `logs/copy_bench.jsonl` |
| decode po 512 kontekstu T=0 t/s | 40.6 | 77.0 | 114.0 | +181.0% | +48.1% | `logs/long.jsonl` |
| decode po 512 T=0 ms/krok | 24.56 | 46.66 | 31.96 | +30.1% | -31.5% | `logs/long.jsonl` |
| decode po 512 kontekstu T=1 t/s | 40.6 | 69.4 | 107.8 | +165.5% | +55.2% | `logs/long.jsonl` |
| decode po 512 T=1 ms/krok | 24.54 | 46.28 | 32.42 | +32.1% | -29.9% | `logs/long.jsonl` |
| decode po 16k kontekstu T=0 t/s | — | 65.4 | 87.6 | — | +33.9% | `logs/long.jsonl` |
| decode po 16k T=0 ms/krok | — | 51.30 | 36.85 | — | -28.2% | `logs/long.jsonl` |
| decode po 16k kontekstu T=1 t/s | — | 58.9 | 80.3 | — | +36.4% | `logs/long.jsonl` |
| decode po 16k T=1 ms/krok | — | 51.52 | 36.48 | — | -29.2% | `logs/long.jsonl` |
| prefill 512 t/s | 1094.9 | 825.3 | 729.8 | -33.4% | -11.6% | `logs/long.jsonl` |
| TTFT 512 s | 0.79 | 0.78 | 0.95 | +20.1% | +20.9% | `logs/long.jsonl` |
| prefill 16k t/s | — | 1323.0 | 1295.2 | — | -2.1% | `logs/long.jsonl` |
| TTFT 16k s | — | 11.10 | 11.40 | — | +2.6% | `logs/long.jsonl` |
| tokeny promptu 512/2k/16k/32k/60k | 435, —, —, —, — | 435, —, 14393, —, — | 435, —, 14393, —, — | | | `logs/long.jsonl` |
| llama-bench pp512 t/s (diagn.) | 1554.7 [1556.2 / 1553.2] | (= U0) | 1501.3 [1496.9 / 1505.6] | -3.4% | (= vs U0) | `logs/lb.qwen.U.r1,r4 / lb.qwen.T.r2,r3.jsonl` |
| llama-bench tg128 t/s (diagn.) | 41.4 [41.2 / 41.5] | (= U0) | 44.2 [44.0 / 44.4] | +6.8% | (= vs U0) | `logs/lb.qwen.U.r1,r4 / lb.qwen.T.r2,r3.jsonl` |

Błędy long_bench (np. kontekst za mały): {('U0', 'err_16k'): 2}
