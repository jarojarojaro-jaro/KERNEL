# LFM2.5-24B-A2B Q5_K_M decode on RX 7900 XTX (gfx1100, ROCm 10.0) — profile and changes

Branch `opt-lfm` (worktree `~/wt/lfm`), base `amd-opt` e84abb808. Profiling tools: `~/wt/lfm-prof/` (`prof.sh`,
`tok.py`: per-token split of a rocprofv3 kernel trace of `llama-bench -p 0 -n 64`, tokens cut at the output-head
matvec, first 25% skipped; `srv.sh` + `srv_variants.py`: server A/B of request parameters).

## Phase A — baseline (e84abb808, measured 2026-10-14)

### Kernels per decoded token (rocprofv3, llama-bench tg64, 48 tokens, median)

720 kernels/token, GPU busy 3.75 ms, wall under the profiler 6.34 ms (5.05 ms without it), median inter-kernel gap
3.1 us. 12 H2D input copies (rocclr copyBuffer) + 1 D2H (logits, 500 KB) per token.

| kernel | us/token | calls | us/call |
|---|---|---|---|
| mul_mat_vec_q Q5_K n=1 | 2129.5 | 155 | 13.7 |
| mul_mat_vec_q Q6_K n=1 | 566.2 | 26 | 21.8 |
| rms_norm_mul_f32_unrolled | 186.0 | 81 | 2.3 |
| quantize_q8_1 | 135.5 | 118 | 1.15 |
| k_bin_bcast | 129.6 | 99 | 1.31 |
| topk_moe_cuda | 128.0 | 38 | 3.37 |
| mul_mat_vec_f (router, F32 2048x64) | 93.2 | 38 | 2.45 |
| set_rows q4_0 (K, V) | 70.3 | 20 | 3.5 |
| ssm_conv_fused_f32 | 64.2 | 29 | 2.2 |
| rms_norm_mul_rope_f32 | 56.4 | 20 | 2.8 |
| flash_attn_ext_kvq | 56.1 | 10 | 5.6 |
| moe_weighted_reduction_f32 | 49.3 | 38 | 1.3 |
| rocclr copyBuffer (graph inputs) | 31.8 | 12 | 2.65 |
| fwht_cuda | 22.0 | 20 | 1.1 |
| flash_attn_combine_results | 18.6 | 10 | 1.9 |
| last layer (get_rows x3, concat, cpy, unfused ssm_conv) | 11.5 | 6 | |

### mul_mat_vec_q by call site (bytes = weight bytes read)

| class | calls | us/token | us/call | MB/call | GB/s |
|---|---|---|---|---|---|
| expert gate+up (ids, fused SwiGLU) 2x4x1536x2048 Q5_K | 38 | 976.5 | 25.7 | 17.30 | 673 |
| shortconv in_proj 6144x2048 Q5_K | 30 | 556.8 | 18.6 | 8.65 | 466 |
| expert down (ids) 4x2048x1536 Q6_K | 18 | 260.4 | 14.5 | 10.32 | 714 |
| output head 128000x2048 Q6_K | 1 | 237.4 | 237.4 | 215.0 | 906 |
| expert down (ids) 4x2048x1536 Q5_K | 20 | 225.9 | 11.3 | 8.65 | 766 |
| shortconv out_proj 2048x2048 Q5_K (+residual epilogue) | 30 | 150.7 | 5.0 | 2.88 | 574 |
| dense FFN gate+up (layers 0-1, fused SwiGLU) 2x11776x2048 | 2 | 79.7 | 39.8 | 33.16 | 833 |
| dense FFN down 2048x11776 Q6_K | 2 | 54.9 | 27.4 | 19.78 | 721 |
| attn o 2048x2048 Q5_K | 10 | 52.5 | 5.3 | 2.88 | 549 |
| attn q 2048x2048 Q5_K | 10 | 49.2 | 4.9 | 2.88 | 586 |
| attn k/v 512x2048 Q5_K | 15 | 39.5 | 2.6 | 0.72 | 274 |
| attn k/v 512x2048 Q6_K | 5 | 13.6 | 2.7 | 0.86 | 317 |
| total | 181 | 2697 | | 1756 MB | 651 |

All are the upstream `ncols_dst == 1` kernel (the fork's K1 work only covers 2-16 columns): one 32-lane wave per row
(Q5_K) or two waves per row (Q6_K), K=2048 is only 4 loop trips per lane. Small launches (512-2048 rows) are
dominated by ramp-up/tail (~2-3 us fixed), the 6144-row in_proj by low bytes in flight per wave (466 GB/s), the
ids launches additionally by the dependent `ids[]` load before the first weight load.

### Where the small kernels come from (graph nodes per layer)

Shortconv + MoE layer (28 of them; 16 kernels):
`rms_norm*mul` (attn_norm, writes q8_1) -> in_proj MMVQ -> **bin_bcast** `b*x` -> `ssm_conv_fused` ->
**bin_bcast** `c*conv` -> **quantize_q8_1** (out_proj input) -> out_proj MMVQ (+residual ADD epilogue) ->
`rms_norm*mul` (ffn_norm, F32 only) -> router `mul_mat_vec_f` (F32 2048x64) -> `topk_moe` (sigmoid, +exp_probs_b,
top-4, sum/clamp/div) -> **quantize_q8_1** (ffn_norm output for MUL_MAT_ID) -> gate+up MMVQ ids (SwiGLU fused) ->
**quantize_q8_1** (6x4 blocks, down input) -> down MMVQ ids -> `moe_weighted_reduction` -> **bin_bcast** (residual
ADD).

Attention + MoE layer (10; 21 kernels): rms_norm*mul (q8_1) -> q MMVQ -> rms_norm_mul_rope (q, FWHT folded) ->
v MMVQ -> fwht (v) -> k MMVQ -> rms_norm_mul_rope (k) -> set_rows K, set_rows V -> FA kvq -> FA combine -> fwht (out)
-> **quantize_q8_1** -> o MMVQ (+residual) -> MoE part as above.

Dense layers 0-1: shortconv as above, FFN `rms_norm*mul` -> gate+up MMVQ (SwiGLU fused) -> **quantize_q8_1** ->
down MMVQ (+residual).

- **118 quantize_q8_1** = 30 out_proj inputs (shortconv `c*conv` from a bin_bcast) + 10 attn o (after fwht) +
  38 MUL_MAT_ID gate/up inputs + 38 down inputs + 2 dense down inputs. The fork's producer-written q8_1
  (`ggml_cuda_q8_1_producer_target`) only serves a plain MUL_MAT whose src1 is the producer's output; the ffn_norm
  output goes to the F32 router first and to MUL_MAT_ID (ids path quantizes itself, no cache), the gate+up epilogue
  writes F32 SwiGLU output (a q8_1 block spans 32 rows = 32 blocks), bin_bcast/fwht have no q8_1 epilogue.
- **99 bin_bcast** = 30 x `b*x` + 30 x `c*conv` (shortconv) + 38 MoE residual ADDs + 1 (last layer).
- **81 rms_norm** = 40 attn_norm + 40 ffn_norm + output norm (already fused with MUL; attn_norm writes q8_1).
- **12 copyBuffer/token**: the H2D graph input uploads (token embedding row from the CPU get_rows, positions, KQ
  mask, recurrent-state copy ids, out_ids, ...), 12 hipMemcpyAsync before hipGraphLaunch, ~5.5 us each under the
  profiler (2.6 us copy + 3 us gap) = ~66 us/token on the critical path before the graph starts.
- HIP graph launch: hipGraphLaunch takes 0.72 ms of CPU under the profiler; the GPU runs out of submitted work
  once per token (242 us gap before the layer-0 dense FFN, under the profiler). Without the profiler the token is
  5.05 ms = 3.75 busy + 1.3 ms idle (~1.8 us per kernel boundary).

### Server path (llama-server, LFM, ctx 131072, KV q4_0; 2 prompts x 2 seeds x 200 tokens, ignore_eos)

| request | ms/token | t/s |
|---|---|---|
| default (GGUF sampling defaults top_k 50, repeat_penalty 1.05; T=1) | 5.81 | 172.0 |
| repeat_penalty 1.0 | 5.17 | 193.5 |
| repeat_penalty 1.0, top_k 0 | 6.56 | 152.5 |
| repeat_penalty 1.0, top_k 1 | 5.20 | 192.4 |
| --backend-sampling (request `backend_sampling`) | 5.22 | 191.5 |
| --backend-sampling, repeat_penalty 1.0 | 5.17 | 193.3 |

- The ~0.7 ms/token server-vs-bench gap is almost entirely the CPU sampler: the GGUF default
  `repeat_penalty = 1.05` makes the penalties sampler (first in the chain) non-trivial, which disables the fork's
  fast top-k path (`LLAMA_SAMPLER_FAST_TOPK`): every token fills 128000 candidates, does 128000 `unordered_map`
  lookups in the penalties sampler and a partial sort of 128000 for top-k. With repeat_penalty 1.0 the server is at
  5.17 ms/token (bench 5.05 ms).
- Logits D2H (128000 floats) is one 500 KB copy per token, not a bottleneck.
- Graphs are reused by the server for this model (server log: "graphs reused" 199 of 200 tokens per request).
- `--backend-sampling` is as fast as the fast path but is a different sampler implementation (not bit-identical);
  the fix taken is a bit-identical CPU fast path that covers the penalties sampler.

## Phase B — changes (branch opt-lfm)

| commit | change | switch | effect (A/B, same binary env off/on, llama-bench tg128 -r 5 interleaved) |
|---|---|---|---|
| 41bb3da6a | sampler: fast top-k also behind a penalties sampler that only lowers logits (GGUF default repeat_penalty 1.05) | `LLAMA_SAMPLER_FAST_PENALTIES=0` | server, T=1, GGUF defaults: 5.79 -> 5.11 ms/token (172.7 -> 195.8 t/s); bench unaffected |
| 605fccd9a | FFN norm writes the q8_1 input of the single-token MoE gate/up MUL_MAT_ID | `GGML_HIP_Q8_IDS=0` | 720 -> 682 kernels/token; 5.067 -> 4.979 ms/token |
| be05dc19c | shortconv `b*x` and `c*conv` folded into the fused SSM_CONV, which writes the out_proj q8_1 | `GGML_HIP_CONV_MUL=0` | 682 -> 595 kernels/token; 4.979 -> 4.800 ms/token |
| 862c02136 | MoE tail (down MUL_MAT_ID + expert weighting + residual ADD) in one MMVQ launch | `GGML_HIP_MOE_DOWN_REDUCE=0` | 595 -> 521 kernels/token; 4.817 -> 4.642 ms/token |
| bcdf324d3 | RDNA3 n=1 MMVQ (Q4_K/Q5_K/Q6_K): 2 rows per block for every launch | `GGML_HIP_MMVQ_N1_ROWS=0` | off 4.610, 2 rows only for >= 4096 blocks 4.567, 2 rows everywhere 4.509 ms/token (taken) |

All committed GPU changes are bitwise: greedy md5 equal to e84abb808 for LFM plain (62783d75...) after each of
605fccd9a, be05dc19c, 862c02136, bcdf324d3, and for Qwen plain (c4708318...) + MTP (6f14e814...) after 605fccd9a,
be05dc19c and on the final branch (862c02136 + bcdf324d3). test-backend-ops passing: MUL_MAT 2476/2476, SSM_CONV 45/45, RMS_NORM 53/53, MUL 142/142, MUL_MAT_ID 931/931,
MOE_DOWN_REDUCE 5/5 (new test, the fused kernel is taken in all 5 cases, checked in the kernel trace).
Seeded T=1 server outputs (GGUF defaults, 3 prompts x 2 seeds + greedy) md5-equal with LLAMA_SAMPLER_FAST_PENALTIES
off/on and to e84abb808.

Per-kernel picture after 862c02136 (rocprofv3, tg64): 521 kernels/token, busy 3.63 ms, wall under the profiler 5.46 ms
(was 6.34). Remaining per shortconv+MoE layer: rms_norm(q8) -> in_proj -> conv(fused, q8) -> out_proj(+res) ->
rms_norm(q8) -> router mmvf -> topk_moe -> gate+up(SwiGLU) -> quantize_q8_1 -> down+reduce+res (10 launches).
MMVQ classes unchanged by the fusions (expert gate+up 25.6 us / 677 GB/s, in_proj 18.2 us / 475 GB/s, down fused
12.4 (Q5_K) / 14.5 (Q6_K) us incl. reduction).

### Not done (measured payoff estimates)
- router `mul_mat_vec_f` + `topk_moe` in one launch (last-block-done epilogue, reuse topk_moe body): -38 launches,
  est. ~0.1 ms/token.
- gate+up MMVQ epilogue writing the q8_1 of the SwiGLU output (32-row blocks of single-row waves): -40 quantize
  launches, est. ~0.1 ms/token.
- attention layers: set_rows K+V in one launch, output FWHT + q8_1: -20 launches.
- conv kernel is latency bound (16 blocks, 4.2 us after the fold).
- graph inputs: 12 H2D copies/token before hipGraphLaunch (~66 us under the profiler) could be one packed copy.

### Negative / inconclusive results
- RDNA3 n=1 MMVQ 4 rows per block (all K-quant launches): total MMVQ 2697 -> 2624 us/token vs 2487 for 2 rows;
  small launches (512-2048 rows) get slower (o-proj 5.3 -> 6.6 us).
- n=1 K loop in unrolled chunks of 4/2 iterations (loads of a chunk issued together, same partial-sum order) on top
  of 2 rows: no gain (MMVQ 2487 -> 2589 us/token, within run-to-run noise but not better); reverted.
- `quantize_q8_1_group` with DPP exchanges in the conv epilogue: same bits, conv 4.39 -> 4.24 us (kept).
- `--backend-sampling`: as fast as the fixed CPU path (5.22 ms/token) but a different sampler implementation.
- Server ignore_eos requests add a logit-bias sampler, which keeps the full candidate path (benchmark artefact; the
  fast path needs no logit bias).

## Final results (opt-lfm vs amd-opt e84abb808 in ~/llama-opt, interleaved)

| measurement | amd-opt | opt-lfm | change |
|---|---|---|---|
| llama-bench tg128 -r 5, LFM, 3 rounds A/B | 197.4 t/s, 5.067 ms/token | 220.4 t/s, 4.536 ms/token | -10.5% ms/token |
| spec_sweep `lfm none`, 6 prompts x 3 seeds, T=1 (2 rounds) | 172.9 / 173.2 t/s, 5.78 / 5.77 ms/step | 218.6 / 218.4 t/s, 4.58 / 4.58 ms/step | +26% t/s |
| spec_sweep `qwen mtp`, 6 x 3, T=1 (2 rounds) | 103.8 / 103.7 t/s, 29.12 / 29.15 ms/step | 103.7 / 103.7 t/s, 29.17 / 29.17 ms/step | within noise |

Server LFM is now uniform over prompt classes (217.4-218.8 t/s) and 0.05 ms/token from llama-bench (the sampler fix
removed the 0.7 ms/token server overhead).

Final per-token kernel breakdown (rocprofv3, tg64, final build): 521 kernels/token (720 at e84abb808), GPU busy
3.46 ms (3.75), wall under the profiler 5.29 ms (6.34). mul_mat_vec_q 2010 us + fused MoE down 502 us; MMVQ classes:
expert gate+up 24.2 us (715 GB/s), in_proj 12.9 us (673 GB/s), expert down (incl. weighting + residual) 12.8 / 14.5 us,
head 239 us (902 GB/s), out_proj 5.1 us, attn q/o 5.1-5.2 us, total MMVQ 2513 us for 1756 MB (699 GB/s, was 651).
Remaining small kernels: rms_norm 220 us (81), conv 135 us (29), topk_moe 133 us (38), router mmvf 91 us (38),
set_rows 71 us (20), quantize_q8_1 65 us (51: 38 down inputs, 10 attn o, 2 dense, 1), copyBuffer 33 us (12).

### Phase B items measured as noise / not done
- FWHT of the attention output writing the q8_1 input of the o-projection (removes 10 quantize_q8_1, 521 -> 511
  kernels/token, bitwise; fwht 1.1 -> 1.9 us on those calls): 4.474 -> 4.490 ms/token (3 rounds) = noise, not committed.
- Not implemented (request budget): router mmvf + topk_moe in one launch (38 launches), gate+up epilogue writing the
  q8_1 down input (38 + 2), set_rows K+V in one launch (10). Estimated ~0.1 / 0.1 / <0.03 ms/token; the FWHT result
  (10 launches = noise) suggests the set_rows pair would be noise too.
- Phase C (speculative decoding) moved to another agent.

## Commit list (e84abb808..opt-lfm)

- 41bb3da6a common: fast top-k candidates also behind a penalties sampler that only lowers logits (LLAMA_SAMPLER_FAST_PENALTIES)
- 605fccd9a CUDA/HIP: the FFN norm writes the q8_1 activations of the single-token MoE gate/up MUL_MAT_ID (GGML_HIP_Q8_IDS)
- be05dc19c CUDA/HIP: LFM2 shortconv: b*x and c*conv folded into the fused SSM_CONV, which writes the q8_1 out_proj input (GGML_HIP_CONV_MUL)
- 862c02136 CUDA/HIP: single-token MoE tail (down MUL_MAT_ID, expert weighting, residual ADD) in one MMVQ launch (GGML_HIP_MOE_DOWN_REDUCE)
- bcdf324d3 HIP/RDNA3 one-column MMVQ: 2 rows per block for the K-quants (GGML_HIP_MMVQ_N1_ROWS)
- (this file)
