# LOO report

results: /home/jaro/qwen-opt/k044/loo/loo-results.jsonl (316 trials)

off vs on = t/s with the patch removed relative to the full build, mean of the per-round (ABBA) paired ratios, Student t 95 % CI. NEUTRAL: CI contains 0; REMOVAL FASTER: CI above 0 (candidates to drop).

| # | patch | model | measure | rounds | on t/s | off t/s | off vs on (paired, 95 % CI) | flag |
|---|---|---|---|---|---|---|---|---|
| 24 | CUDA/HIP: MMVQ pair launch for two products of the | qwen | serve | 4 | 86.58 ± 0.31 | 85.45 ± 0.09 | -1.30 % ± 0.45 | helps |
| 24 | CUDA/HIP: MMVQ pair launch for two products of the | qwen | tg | 4 | 40.09 ± 0.01 | 40.13 ± 0.06 | +0.10 % ± 0.15 | NEUTRAL |
| 25 | CUDA/HIP: unrolled rms_norm*mul(+q8_1) for 2048..8 | lfm | serve | 2 | 236.89 ± 7.80 | 232.33 ± 12.19 | -1.93 % ± 1.92 | helps |
| 25 | CUDA/HIP: unrolled rms_norm*mul(+q8_1) for 2048..8 | lfm | tg | 2 | 239.30 ± 1.25 | 238.14 ± 0.02 | -0.48 % ± 0.51 | NEUTRAL |
| 25 | CUDA/HIP: unrolled rms_norm*mul(+q8_1) for 2048..8 | qwen | serve | 4 | 86.57 ± 0.20 | 85.78 ± 0.29 | -0.91 % ± 0.18 | helps |
| 25 | CUDA/HIP: unrolled rms_norm*mul(+q8_1) for 2048..8 | qwen | tg | 4 | 40.12 ± 0.06 | 39.86 ± 0.06 | -0.65 % ± 0.16 | helps |
| 26 | CUDA/HIP: argmax with 16 loads in flight and DPP e | qwen | serve | 4 | 86.67 ± 0.21 | 86.43 ± 0.38 | -0.28 % ± 0.23 | helps |
| 27 | CUDA/HIP: GDN gated output norm silu(z) * (rms_nor | qwen | serve | 4 | 86.59 ± 0.30 | 86.03 ± 0.42 | -0.65 % ± 0.61 | helps |
| 27 | CUDA/HIP: GDN gated output norm silu(z) * (rms_nor | qwen | tg | 4 | 40.09 ± 0.06 | 39.78 ± 0.05 | -0.79 % ± 0.15 | helps |
| 28 | CUDA/HIP: GDN fused SSM_CONV and alpha/beta projec | qwen | serve | 4 | 86.54 ± 0.37 | 85.74 ± 0.26 | -0.92 % ± 0.15 | helps |
| 28 | CUDA/HIP: GDN fused SSM_CONV and alpha/beta projec | qwen | tg | 4 | 40.12 ± 0.08 | 39.69 ± 0.04 | -1.09 % ± 0.09 | helps |
| 29 | ggml-backend/llama: asynchronous graph input uploa | lfm | serve | 2 | 237.24 ± 9.66 | 222.98 ± 0.97 | -6.01 % ± 3.42 | helps |
| 29 | ggml-backend/llama: asynchronous graph input uploa | lfm | tg | 2 | 239.48 ± 4.25 | 227.43 ± 8.40 | -5.03 % ± 5.19 | NEUTRAL |
| 29 | ggml-backend/llama: asynchronous graph input uploa | qwen | serve | 4 | 86.56 ± 0.29 | 85.31 ± 0.43 | -1.45 % ± 0.19 | helps |
| 29 | ggml-backend/llama: asynchronous graph input uploa | qwen | tg | 4 | 40.12 ± 0.05 | 39.83 ± 0.06 | -0.70 % ± 0.24 | helps |
| 30 | llama: MTP draft chain on its own scheduler (LLAMA | qwen | serve | 4 | 86.78 ± 0.23 | 86.07 ± 0.20 | -0.82 % ± 0.48 | helps |
| 31 | common/server: top-k candidates without the full c | lfm | serve | 2 | 235.15 ± 12.66 | 206.36 ± 3.28 | -12.24 % ± 3.33 | helps |
| 31 | common/server: top-k candidates without the full c | qwen | serve | 4 | 86.59 ± 0.21 | 84.23 ± 0.32 | -2.72 % ± 0.46 | helps |
| 33 | ggml/llama: delta-net speculative rollback by repl | qwen | serve | 4 | 86.70 ± 0.26 | 85.33 ± 0.45 | -1.58 % ± 0.50 | helps |
| 38 | llama/CUDA: lagged conv history for the delta-net  | qwen | serve | 4 | 86.68 ± 0.31 | 86.33 ± 0.20 | -0.40 % ± 0.39 | helps |
| 47 | llama/server: per-step host costs of the spec loop | lfm | serve | 2 | 235.89 ± 4.21 | 236.80 ± 8.11 | +0.39 % ± 5.23 | NEUTRAL |
| 47 | llama/server: per-step host costs of the spec loop | qwen | serve | 4 | 86.61 ± 0.41 | 85.55 ± 0.17 | -1.23 % ± 0.37 | helps |
| 48 | common: fast top-k candidates also behind a penalt | lfm | serve | 2 | 235.63 ± 6.21 | 203.43 ± 19.90 | -13.66 % ± 10.72 | helps |
| 48 | common: fast top-k candidates also behind a penalt | qwen | serve | 4 | 86.76 ± 0.19 | 86.76 ± 0.22 | -0.00 % ± 0.44 | NEUTRAL |
| 49 | CUDA/HIP: the FFN norm writes the q8_1 activations | lfm | serve | 2 | 234.86 ± 6.77 | 224.03 ± 9.58 | -4.61 % ± 6.83 | NEUTRAL |
| 49 | CUDA/HIP: the FFN norm writes the q8_1 activations | lfm | tg | 2 | 240.18 ± 10.64 | 227.39 ± 1.50 | -5.32 % ± 4.82 | helps |
| 50 | CUDA/HIP: LFM2 shortconv: b*x and c*conv folded in | lfm | serve | 2 | 235.89 ± 16.40 | 216.06 ± 15.67 | -8.40 % ± 13.01 | NEUTRAL |
| 50 | CUDA/HIP: LFM2 shortconv: b*x and c*conv folded in | lfm | tg | 2 | 241.11 ± 10.60 | 218.55 ± 3.15 | -9.36 % ± 5.29 | helps |
| 51 | CUDA/HIP: single-token MoE tail (down MUL_MAT_ID,  | lfm | serve | 2 | 237.25 ± 7.82 | 226.16 ± 0.90 | -4.67 % ± 3.52 | helps |
| 51 | CUDA/HIP: single-token MoE tail (down MUL_MAT_ID,  | lfm | tg | 2 | 240.08 ± 8.55 | 229.20 ± 5.75 | -4.53 % ± 1.00 | helps |
| 52 | HIP/RDNA3 one-column MMVQ: 2 rows per block for th | lfm | serve | 2 | 236.99 ± 9.21 | 239.88 ± 3.79 | +1.22 % ± 5.53 | NEUTRAL |
| 52 | HIP/RDNA3 one-column MMVQ: 2 rows per block for th | lfm | tg | 2 | 240.29 ± 11.23 | 242.33 ± 0.52 | +0.85 % ± 4.49 | NEUTRAL |
| 52 | HIP/RDNA3 one-column MMVQ: 2 rows per block for th | qwen | serve | 4 | 86.48 ± 0.43 | 86.73 ± 0.14 | +0.29 % ± 0.58 | NEUTRAL |
| 52 | HIP/RDNA3 one-column MMVQ: 2 rows per block for th | qwen | tg | 4 | 40.10 ± 0.06 | 40.63 ± 0.03 | +1.31 % ± 0.11 | REMOVAL FASTER |
| 53 | CUDA/HIP: single-token MoE routing (FFN norm, F32  | lfm | serve | 2 | 236.14 ± 4.28 | 220.64 ± 11.97 | -6.56 % ± 6.76 | NEUTRAL |
| 53 | CUDA/HIP: single-token MoE routing (FFN norm, F32  | lfm | tg | 2 | 241.89 ± 6.21 | 225.74 ± 4.20 | -6.68 % ± 4.13 | helps |
| 54 | CUDA/HIP: LFM2 shortconv in_proj MMVQ with the fus | lfm | serve | 2 | 238.00 ± 1.10 | 226.31 ± 25.72 | -4.91 % ± 10.36 | NEUTRAL |
| 54 | CUDA/HIP: LFM2 shortconv in_proj MMVQ with the fus | lfm | tg | 2 | 239.44 ± 0.83 | 229.53 ± 11.18 | -4.14 % ± 5.00 | NEUTRAL |
| 55 | HIP/RDNA3 FA: the kvq decode kernel also reads a q | lfm | serve | 2 | 235.64 ± 7.65 | 231.91 ± 1.94 | -1.58 % ± 2.37 | NEUTRAL |
| 55 | HIP/RDNA3 FA: the kvq decode kernel also reads a q | lfm | tg | 2 | 240.21 ± 11.42 | 236.66 ± 4.26 | -1.48 % ± 2.91 | NEUTRAL |
| 56 | CUDA/HIP: single-token gate/up(+GLU) MMVQ writes t | lfm | serve | 2 | 237.12 ± 31.45 | 230.28 ± 5.93 | -2.87 % ± 10.38 | NEUTRAL |
| 56 | CUDA/HIP: single-token gate/up(+GLU) MMVQ writes t | lfm | tg | 2 | 241.49 ± 17.98 | 236.03 ± 5.59 | -2.26 % ± 4.96 | NEUTRAL |
| 57 | CUDA/HIP: single-token attention input (q/k norm+r | lfm | serve | 2 | 235.21 ± 2.97 | 228.74 ± 7.35 | -2.75 % ± 4.35 | NEUTRAL |
| 57 | CUDA/HIP: single-token attention input (q/k norm+r | lfm | tg | 2 | 240.14 ± 9.97 | 232.03 ± 9.58 | -3.37 % ± 8.00 | NEUTRAL |
| 58 | CUDA/HIP: kvq attention applies the output FWHT (+ | lfm | serve | 2 | 239.13 ± 3.01 | 233.66 ± 2.88 | -2.29 % ± 2.43 | NEUTRAL |
| 58 | CUDA/HIP: kvq attention applies the output FWHT (+ | lfm | tg | 2 | 239.46 ± 2.39 | 237.49 ± 9.00 | -0.82 % ± 4.75 | NEUTRAL |
| 58 | CUDA/HIP: kvq attention applies the output FWHT (+ | qwen | serve | 4 | 86.51 ± 0.37 | 86.62 ± 0.26 | +0.13 % ± 0.48 | NEUTRAL |
| 58 | CUDA/HIP: kvq attention applies the output FWHT (+ | qwen | tg | 4 | 40.11 ± 0.05 | 40.12 ± 0.04 | +0.04 % ± 0.17 | NEUTRAL |
| 59 | CUDA/HIP: batch the small async input uploads of a | lfm | serve | 2 | 235.09 ± 0.92 | 232.78 ± 6.09 | -0.98 % ± 2.98 | NEUTRAL |
| 59 | CUDA/HIP: batch the small async input uploads of a | lfm | tg | 2 | 241.25 ± 12.33 | 239.43 ± 3.66 | -0.75 % ± 6.59 | NEUTRAL |
| 59 | CUDA/HIP: batch the small async input uploads of a | qwen | serve | 4 | 86.63 ± 0.19 | 86.58 ± 0.15 | -0.06 % ± 0.21 | NEUTRAL |
| 59 | CUDA/HIP: batch the small async input uploads of a | qwen | tg | 4 | 40.14 ± 0.03 | 40.06 ± 0.05 | -0.19 % ± 0.13 | helps |
| 62 | CUDA/HIP RDNA3: the shortconv in_proj MMVQ runs 4  | lfm | serve | 2 | 237.72 ± 14.80 | 233.71 ± 1.09 | -1.68 % ± 5.66 | NEUTRAL |
| 62 | CUDA/HIP RDNA3: the shortconv in_proj MMVQ runs 4  | lfm | tg | 2 | 239.22 ± 0.00 | 240.15 ± 0.09 | +0.39 % ± 0.04 | REMOVAL FASTER |
| 64 | HIP/RDNA3 one-column MMVQ: Q8_0 joins the 2-row pa | lfm | serve | 2 | 235.13 ± 15.75 | 236.01 ± 13.65 | +0.38 % ± 12.53 | NEUTRAL |
| 64 | HIP/RDNA3 one-column MMVQ: Q8_0 joins the 2-row pa | lfm | tg | 2 | 239.71 ± 0.32 | 241.60 ± 0.45 | +0.79 % ± 0.05 | REMOVAL FASTER |

## Flagged (removal neutral or faster)

- 24 qwen tg: NEUTRAL (+0.10 % ± 0.15)
- 25 lfm tg: NEUTRAL (-0.48 % ± 0.51)
- 29 lfm tg: NEUTRAL (-5.03 % ± 5.19)
- 47 lfm serve: NEUTRAL (+0.39 % ± 5.23)
- 48 qwen serve: NEUTRAL (-0.00 % ± 0.44)
- 49 lfm serve: NEUTRAL (-4.61 % ± 6.83)
- 50 lfm serve: NEUTRAL (-8.40 % ± 13.01)
- 52 lfm serve: NEUTRAL (+1.22 % ± 5.53)
- 52 lfm tg: NEUTRAL (+0.85 % ± 4.49)
- 52 qwen serve: NEUTRAL (+0.29 % ± 0.58)
- 52 qwen tg: REMOVAL FASTER (+1.31 % ± 0.11)
- 53 lfm serve: NEUTRAL (-6.56 % ± 6.76)
- 54 lfm serve: NEUTRAL (-4.91 % ± 10.36)
- 54 lfm tg: NEUTRAL (-4.14 % ± 5.00)
- 55 lfm serve: NEUTRAL (-1.58 % ± 2.37)
- 55 lfm tg: NEUTRAL (-1.48 % ± 2.91)
- 56 lfm serve: NEUTRAL (-2.87 % ± 10.38)
- 56 lfm tg: NEUTRAL (-2.26 % ± 4.96)
- 57 lfm serve: NEUTRAL (-2.75 % ± 4.35)
- 57 lfm tg: NEUTRAL (-3.37 % ± 8.00)
- 58 lfm serve: NEUTRAL (-2.29 % ± 2.43)
- 58 lfm tg: NEUTRAL (-0.82 % ± 4.75)
- 58 qwen serve: NEUTRAL (+0.13 % ± 0.48)
- 58 qwen tg: NEUTRAL (+0.04 % ± 0.17)
- 59 lfm serve: NEUTRAL (-0.98 % ± 2.98)
- 59 lfm tg: NEUTRAL (-0.75 % ± 6.59)
- 59 qwen serve: NEUTRAL (-0.06 % ± 0.21)
- 62 lfm serve: NEUTRAL (-1.68 % ± 5.66)
- 62 lfm tg: REMOVAL FASTER (+0.39 % ± 0.04)
- 64 lfm serve: NEUTRAL (+0.38 % ± 12.53)
- 64 lfm tg: REMOVAL FASTER (+0.79 % ± 0.05)
