# LFM2.5-24B-A2B Q5_K_M decode on RX 7900 XTX — round 2 (branch opt-lfm2)

Worktree `~/wt/lfm2`, branch `opt-lfm2` from `amd-opt` bcdf324d3, build `~/wt/lfm2/build-hip`, installed to
`~/wt/lfm2/inst`. KV cache **q8_0** for every LFM number (user decision 2026-10-14); q4_0 vs q8_0 baseline in
`KV-BASELINE.md` (same directory). Tools in `~/wt/lfm2-prof`: `prof.sh`/`tok.py` (rocprofv3 per-token breakdown,
llama-bench tg64), `ab.sh` (interleaved llama-bench A/B, also across builds: `"BIN::ENV"`), `launch_cost.hip`,
`chain_cost.hip` (microbenchmarks), `logit_hash.cpp` + `lh.sh` (bitwise check: FNV hash of the full logits of 64
greedy decode steps; a much stronger test than the greedy text md5), `multi.sh` (repeated profiles).
`~/qwen-opt/fusion/greedy.sh` now takes `KV` (default q8_0 for lfm, as run-llm.sh) and `PORT`.

## Result

| measurement | ~/llama-opt (bcdf324d3) | opt-lfm2 (inst) | change |
|---|---|---|---|
| llama-bench tg128 -r 5, KV q8_0, 3 rounds interleaved | 221.30 t/s, 4.519 ms/token | 244.06 t/s, 4.097 ms/token | -9.3% ms/token |
| spec_sweep `lfm none` 6x3, T=1 (2 rounds, interleaved) | 217.3 / 223.1 t/s, 4.60 / 4.48 ms/step | 237.7 / 242.9 t/s, 4.21 / 4.12 ms/step | -8.5% / -8.0% ms/step |
| spec_sweep `qwen mtp` 6x3, T=1 (1 round each) | 103.8 t/s, 29.15 ms/step | 103.8 t/s, 29.14 ms/step | no change (same tok/step per class) |

Kernels per token 521 -> 416; GPU busy (rocprofv3, tg64) 3.47 -> 3.23 ms; wall under the profiler 5.31 -> 4.74 ms.

## 1. What a launch boundary costs (measured)

`launch_cost.hip`, HIP graph of 500 dependent kernels on one stream, gfx1100, ROCm 10.0:

| case | cost |
|---|---|
| empty kernel, 1 .. 1024 blocks of 32 threads | 2.53 us per kernel |
| empty kernel, 4096 blocks | 2.62-2.71 us |
| kernel copying 2048 floats (8-256 blocks) | 2.53 us (the work hides inside the boundary) |
| persistent kernel, atomic grid barrier per phase, 16-48 blocks x 256 | 0.48-0.53 us per phase |
| same, 96 / 192 blocks | 0.54-0.58 / 0.72-0.77 us per phase |

`chain_cost.hip`, phases chained inside one launch (dynamic block index from an atomic, per-phase done counters,
waiting blocks spin with s_sleep): 1-block phases 0.45-0.70 us/phase (vs 2.8 us as separate kernels); 64-block
phases 0.93-0.99 us at 10 phases per launch but 4.4-5.6 us at 100 per launch; 1024-block phases 8-11 us per phase
(thousands of spinning waiters starve the producers). Last-block ticket tail (a 1-wave epilogue reading/writing 2048
floats): +0.8 us on a 1024-block kernel, +1.1 us on 2048 blocks, vs +2.8 us for the same work as its own kernel.

Conclusions used: every removed boundary is worth ~2.5 us plus the removed kernel's own latency; a ticket tail costs
~1 us; chaining big phases with spinning blocks inside one launch loses; a small persistent grid with barriers is
cheap (0.5 us) but would need the big matvecs rewritten as grid-stride loops (not attempted).

## 2. Final per-kernel picture (rocprofv3, llama-bench tg64, KV q8_0, inst build)

416 kernels/token, GPU busy 3235 us, wall under the profiler 4736 us (sum of inter-kernel gaps 1505 us, median gap
3.1 us under the profiler); llama-bench without the profiler 4.10 ms/token, i.e. ~0.87 ms/token idle.

| kernel | us/token | calls | us/call |
|---|---|---|---|
| mul_mat_vec_q Q5_K n=1 (expert gate+up, out_proj, attn q/k/v/o, dense, ...) | 1330.2 | 106 | 12.55 |
| mul_mat_vec_q_conv Q5_K (in_proj + shortconv tails, new) | 413.9 | 29 | 14.27 |
| mul_mat_vec_q Q6_K n=1 (head, dense down, v) | 320.6 | 9 | 35.62 |
| mul_mat_vec_q_moe_down_reduce Q5_K / Q6_K | 255.7 / 250.6 | 20 / 17 | 12.79 / 14.74 |
| norm_router_topk_f32 (new) | 186.9 | 38 | 4.92 |
| rms_norm_mul_f32_unrolled (attn norms, output norm, dense ffn norms) | 116.4 | 43 | 2.71 |
| flash_attn_ext_vec (q8_0 KV) | 85.5 | 10 | 8.55 |
| quantize_q8_1 (38 MoE down inputs, 10 attn o, 2 dense, 1) | 65.3 | 51 | 1.28 |
| rms_norm_mul_rope_f32 | 61.4 | 20 | 3.07 |
| set_rows q8_0 (K, V) | 54.4 | 20 | 2.72 |
| rocclr copyBuffer (graph inputs) | 32.1 | 12 | 2.68 |
| fwht / flash_attn_combine_results | 20.4 / 18.6 | 20 / 10 | |
| rest (last layer, bin_bcast, get_rows, cpy, concat) | ~20 | 12 | |

Per shortconv+MoE layer now 8 launches (was 10): rms_norm(q8) -> in_proj+conv -> out_proj(+res) ->
norm+router+topk -> gate+up(SwiGLU) -> quantize_q8_1 -> down+reduce+res.

## 3. Attempts (numbered, with numbers)

1. Launch-cost microbenchmarks (section 1).
2. Chained phases in one launch with spinning waiters (section 1): rejected for phases of 64+ blocks.
3. **GGML_HIP_NORM_ROUTER (c15c84e83, kept)**: FFN norm (+ q8_1 for gate/up) + F32 router + topk_moe in one kernel,
   one block per router row recomputing the norm scale in the order of rms_norm_mul_f32_unrolled<2>, router row as
   mul_mat_vec_f<.., 256>, topk_moe body (refactored into topk_moe_select) on the last block via an atomic ticket.
   521 -> 445 kernels/token, fused kernel 4.9 us vs 2.7 + 2.4 + 3.5 us + 2 gaps. A/B 4.451 -> 4.246 ms/token
   (another session 4.505 -> 4.234). Bitwise (logit hashes, greedy md5s).
   - 3a. norm output written by one block (all 2048 values): kernel 6.8 us; by blocks 0/1 in 1024-value chunks
     (whole 128-byte q8_1 lines): 5.9 us; distributed, one q8_1 block per router block: 4.9 us (taken).
   - 3b. A suspected slowdown of the following gate+up MMVQ (27.2 vs 24.3 us/call) turned out to be a per-process
     "slow mode" that also hits the unchanged bcdf324d3 build (4 of 8 profiles there; 1-2 of 5 per variant here):
     not caused by the fusion. Worth 3 us x 38 = 0.11 ms/token when it hits; cause not found (not clock-wide: the
     other MMVQ classes are unchanged in the slow runs). Any single-profile comparison of gate+up is unreliable.
4. **GGML_HIP_INPROJ_CONV (5909da1f1, kept)**: in_proj MMVQ with the shortconv (b*x, conv, c*conv, conv-state window,
   q8_1 for out_proj) as tails of the block that completes each 32-channel group (64 group tickets, 48 blocks per
   group). Needed a second q8_1-cache slot (producers write the slot that is not cached) because the conv tails
   write the out_proj activations while other blocks still read the in_proj activations. 445 -> 416 kernels/token,
   14.3-15.5 us vs 12.8 + 4.7 us + 1 gap. A/B 4.231 -> 4.100 ms/token. Bitwise.
5. q8_0 KV attention path, measured only (budget): the fork's RDNA3 kvq kernel (WMMA, reads q4_0, one pass over K/V
   for all 4 Q heads of a KV head) has no q8_0 instance, so q8_0 runs the generic flash_attn_ext_vec (one block per
   Q head: K/V fetched 4x from L2/MALL): 8.55 us/call at depth ~0-100 vs 6.9 us for kvq q4_0; at 98k context q8_0
   costs +2.38 ms/token over depth 0 (1070 MB of K/V per token -> ~450 GB/s) vs +0.89 ms for q4_0 (566 MB,
   ~640 GB/s). See KV-BASELINE.md.

## 4. Numerics-changing ideas (not committed; for the user to decide)

- **q8_0 instance of the kvq FA kernel** (dequantize q8_0 into the WMMA A fragments, f16 softmax/accumulate as the
  q4_0 path): different numerics from flash_attn_ext_vec (f16 WMMA vs the vec kernel's int8 dot + f32/half2 math).
  Estimate from the q4_0 kernel's per-byte rate (~640 GB/s; q8_0 rows are 1.9x larger): 98k context 6.95 -> ~5.8
  ms/token (-1.1 ms, +19% t/s), 32k -0.3 ms, 8k -0.07 ms, depth 0 -0.02 ms. A bitwise alternative exists but is more
  work: the vec kernel with the 4 Q heads of a KV head in one block (each head computed with exactly the per-head
  thread mapping and the parallel_blocks split of the 1-head launch), K/V read once instead of 4x; estimated about
  half of the gain above.

## 5. Not done (estimates from the measured ~2.5 us per boundary + kernel latency)

- MoE down+reduce+res kernel computing the next layer's attn_norm (+q8_1) as a 1-wave ticket tail: -40 launches,
  ~0.12 ms/token.
- gate+up(SwiGLU) writing the q8_1 input of down via 192 group tickets (32 rows = 16 blocks each): -38 launches
  (quantize_q8_1), ~0.1 ms/token.
- attention layers (10): q-norm/rope, set_rows K+V, fwht, combine, quantize — ~11 launches/layer could become ~6.
- MMVQ bandwidth (gate+up 711 GB/s in fast mode, in_proj ~670 GB/s, out_proj/attn ~560 GB/s): not attempted this
  round; also the gate+up slow mode (3b).
- 12 graph-input copies per token (~32 us) before the graph starts: one packed copy.

## 6. Commits (bcdf324d3..opt-lfm2)

- c15c84e83 CUDA/HIP: single-token MoE routing (FFN norm, F32 router, topk_moe) in one launch (GGML_HIP_NORM_ROUTER)
- 5909da1f1 CUDA/HIP: LFM2 shortconv in_proj MMVQ with the fused conv as per-group ticket tails (GGML_HIP_INPROJ_CONV)

This file and KV-BASELINE.md are untracked. Verification per commit: logit hashes (q8_0 d0 a3c06fe69758819e, q8_0
d3000 718efee0662e860e, q4_0 d0 b81cc99db07e6661) equal to bcdf324d3; greedy md5 LFM plain q8_0
2c7ee8a28750f9bfbb09baa4e3027a72 (new q8_0 baseline recorded on ~/llama-opt), Qwen plain c4708318..., Qwen MTP
6f14e814...; test-backend-ops NORM_ROUTER_TOPK 5/5, SHORTCONV 4/4 (new), TOPK_MOE 416/416, SSM_CONV 45/45, MUL_MAT
2476/2476, RMS_NORM 53/53, MUL 142/142, MOE_DOWN_REDUCE 5/5.
