# LFM2.5-24B-A2B Q5_K_M: KV cache q4_0 vs q8_0 baseline (~/llama-opt = amd-opt bcdf324d3, unchanged)

Measured 2026-10-14, RX 7900 XTX (gfx1100, 285 W cap), ROCm 10.0, `llama-bench -ngl 99 -fa 1`, one run per KV type
(tg: `-p 0 -n 128 -r 3 -d 0,8192,32768,98304`; pp: `-p 4096 -n 0 -r 3`). Raw output: `~/wt/lfm2-prof/kvbase.q4_0.md`,
`kvbase.q8_0.md`.

## Decode (tg128) at depth

| depth | q4_0 t/s | q4_0 ms/token | q8_0 t/s | q8_0 ms/token | q8_0 - q4_0 |
|---|---|---|---|---|---|
| 0 | 224.27 ± 4.75 | 4.459 | 218.63 ± 4.65 | 4.574 | +0.115 ms (+2.6%) |
| 8192 | 224.13 ± 3.26 | 4.462 | 213.42 ± 2.91 | 4.686 | +0.224 ms (+5.0%) |
| 32768 | 212.88 ± 3.03 | 4.697 | 188.83 ± 2.53 | 5.296 | +0.599 ms (+12.7%) |
| 98304 | 187.03 ± 2.45 | 5.347 | 143.81 ± 0.87 | 6.954 | +1.607 ms (+30.1%) |

Cost of context (ms/token over depth 0): q4_0 +0.89 ms at 98k (K+V read 566 MB/token over the 10 attention layers,
~640 GB/s); q8_0 +2.38 ms at 98k (1070 MB/token, ~450 GB/s). Kernel paths: q4_0 KV decodes with the fork's
`flash_attn_ext_kvq` (RDNA3 WMMA kernel reading q4_0 directly, all 4 Q heads of a KV head in one pass); q8_0 KV has no
kvq instance and falls back to the generic `flash_attn_ext_vec` (one block per Q head, so every K/V byte is fetched once
per Q head of the GQA group = 4x from L2/MALL), which is why q8_0 is slower per KV byte.

## Prefill (pp4096, depth 0)

| KV | t/s |
|---|---|
| q4_0 | 6098.50 ± 2.93 |
| q8_0 | 6084.06 ± 9.79 |

## VRAM at ctx 131072 (llama-server -np 1 -fa on -ngl 999, after load, rocm-smi used VRAM; total 25753 MB)

| KV | KV buffer | VRAM used | free |
|---|---|---|---|
| q4_0 | 720.00 MiB | 18648 MB (17784 MiB) | 7105 MB |
| q8_0 | 1360.00 MiB | 19320 MB (18425 MiB) | 6433 MB |

Both: model buffer 16232.83 MiB (+205 MiB CPU-mapped token embedding), compute buffer 404.05 MiB, recurrent state
0.47 MiB, idle desktop ~27 MB. q8_0 costs +640 MiB of VRAM at 131k.
