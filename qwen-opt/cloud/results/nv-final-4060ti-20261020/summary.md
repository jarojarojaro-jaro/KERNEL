
### qwen  (`nv-final-4060ti-qwen-20261020`)

| metryka | U0 | U1 | T | T vs U0 | T vs U1 | log |
|---|---|---|---|---|---|---|
| chat T=1 (spec_sweep 6×3) t/s | 18.6 [18.7 / 18.6] | 30.6 [30.6 / 30.5] | 35.4 [35.3 / 35.4] | +89.8% | +15.8% | `logs/spec_sweep.jsonl` |
| chat T=1 ms/krok | 53.67 [53.61 / 53.72] | 97.74 [97.63 / 97.85] | 81.56 [81.67 / 81.45] | +52.0% | -16.6% | `logs/spec_sweep.jsonl` |
| chat T=1 tok/krok | 1.00 [1.00 / 1.00] | 2.99 [2.99 / 2.99] | 2.88 [2.88 / 2.88] | +188.5% | -3.6% | `logs/spec_sweep.jsonl` |
| code-edit mvs T=0 t/s | 18.5 | 50.0 | 170.9 | +823.6% | +242.0% | `logs/copy_bench.jsonl` |
| mvs ms/krok | 54.06 | 99.03 | 83.48 | +54.4% | -15.7% | `logs/copy_bench.jsonl` |
| mvs tok/krok | 1.00 | 4.95 | 14.32 | +1332.2% | +189.5% | `logs/copy_bench.jsonl` |
| decode po 512 kontekstu T=0 t/s | 18.6 | 35.3 | 41.3 | +121.7% | +17.1% | `logs/long.jsonl` |
| decode po 512 T=0 ms/krok | 53.45 | 97.66 | 81.20 | +51.9% | -16.9% | `logs/long.jsonl` |
| decode po 512 kontekstu T=1 t/s | 18.6 | 31.6 | 39.3 | +111.1% | +24.2% | `logs/long.jsonl` |
| decode po 512 T=1 ms/krok | 53.37 | 97.08 | 82.09 | +53.8% | -15.4% | `logs/long.jsonl` |
| decode po 16k kontekstu T=0 t/s | 17.6 | 33.3 | 40.1 | +128.1% | +20.5% | `logs/long.jsonl` |
| decode po 16k T=0 ms/krok | 56.61 | 104.81 | 89.44 | +58.0% | -14.7% | `logs/long.jsonl` |
| decode po 16k kontekstu T=1 t/s | 17.6 | 31.1 | 35.8 | +103.3% | +15.1% | `logs/long.jsonl` |
| decode po 16k T=1 ms/krok | 56.55 | 105.08 | 87.89 | +55.4% | -16.4% | `logs/long.jsonl` |
| prefill 512 t/s | 637.5 | 506.4 | 458.1 | -28.1% | -9.5% | `logs/long.jsonl` |
| TTFT 512 s | 1.07 | 1.18 | 1.37 | +27.3% | +16.2% | `logs/long.jsonl` |
| prefill 16k t/s | 727.4 | 674.9 | 659.7 | -9.3% | -2.2% | `logs/long.jsonl` |
| TTFT 16k s | 20.03 | 21.55 | 22.12 | +10.4% | +2.6% | `logs/long.jsonl` |
| tokeny promptu 512/2k/16k/32k/60k | 435, —, 14393, —, — | 435, —, 14393, —, — | 435, —, 14393, —, — | | | `logs/long.jsonl` |
| llama-bench pp512 t/s (diagn.) | 793.7 [795.0 / 792.4] | (= U0) | 762.7 [764.4 / 761.0] | -3.9% | (= vs U0) | `logs/lb.qwen.U.r1,r4 / lb.qwen.T.r2,r3.jsonl` |
| llama-bench pp4096 t/s (diagn.) | 788.4 [790.9 / 785.9] | (= U0) | 760.7 [759.5 / 761.8] | -3.5% | (= vs U0) | `logs/lb.qwen.U.r1,r4 / lb.qwen.T.r2,r3.jsonl` |
| llama-bench tg128 t/s (diagn.) | 18.8 [18.9 / 18.8] | (= U0) | 18.7 [18.7 / 18.7] | -0.8% | (= vs U0) | `logs/lb.qwen.U.r1,r4 / lb.qwen.T.r2,r3.jsonl` |
| llama-bench tg128@16k t/s (diagn.) | 16.8 [16.8 / 16.8] | (= U0) | 16.8 [16.7 / 16.8] | -0.1% | (= vs U0) | `logs/lbd.qwen.U.r1,r4 / lbd.qwen.T.r2,r3.jsonl` |
| VRAM po załadowaniu MiB | 14354 [14354 / 14354] | 14570 [14570 / 14570] | 14848 [14848 / 14848] | +3.4% | +1.9% | `logs/vram.jsonl` |
| n_ctx | 27904 [27904 / 27904] | 32768 [32768 / 32768] | 32768 [32768 / 32768] | +17.4% | +0.0% | `logs/vram.jsonl` |

### lfm  (`nv-final-4060ti-lfm-20261020`)

| metryka | U0 | U1 | T | T vs U0 | T vs U1 | log |
|---|---|---|---|---|---|---|
| chat T=1 (spec_sweep 6×3) t/s | 114.4 [114.4 / 114.3] | 113.3 [113.3 / 113.4] | 149.4 [149.4 / 149.4] | +30.6% | +31.8% | `logs/spec_sweep.jsonl` |
| chat T=1 ms/krok | 8.74 [8.74 / 8.75] | 8.82 [8.83 / 8.82] | 6.69 [6.69 / 6.69] | -23.5% | -24.1% | `logs/spec_sweep.jsonl` |
| chat T=1 tok/krok | 1.00 [1.00 / 1.00] | 1.00 [1.00 / 1.00] | 1.00 [1.00 / 1.00] | +0.0% | +0.0% | `logs/spec_sweep.jsonl` |
| tokeny promptu 512/2k/16k/32k/60k | —, —, —, —, — | —, —, —, —, — | —, —, —, —, — | | | `logs/long.jsonl` |
| llama-bench pp512 t/s (diagn.) | 3286.3 [3281.1 / 3291.5] | (= U0) | 3278.4 [3278.0 / 3278.8] | -0.2% | (= vs U0) | `logs/lb.lfm.U.r1,r4 / lb.lfm.T.r2,r3.jsonl` |
| llama-bench pp4096 t/s (diagn.) | 3272.8 [3262.4 / 3283.2] | (= U0) | 3267.8 [3262.2 / 3273.3] | -0.2% | (= vs U0) | `logs/lb.lfm.U.r1,r4 / lb.lfm.T.r2,r3.jsonl` |
| llama-bench tg128 t/s (diagn.) | 143.0 [143.0 / 142.9] | (= U0) | 155.1 [155.3 / 154.9] | +8.5% | (= vs U0) | `logs/lb.lfm.U.r1,r4 / lb.lfm.T.r2,r3.jsonl` |
| VRAM po załadowaniu MiB | 14944 [14944 / 14944] | 13914 [13914 / 13914] | 13924 [13924 / 13924] | -6.8% | +0.1% | `logs/vram.jsonl` |
| n_ctx | 85504 [85504 / 85504] | 32768 [32768 / 32768] | 32768 [32768 / 32768] | -61.7% | +0.0% | `logs/vram.jsonl` |
