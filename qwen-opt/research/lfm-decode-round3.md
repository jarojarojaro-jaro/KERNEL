# LFM2.5-24B-A2B Q5_K_M decode on RX 7900 XTX — round 3 (branch opt-lfm3, KV q8_0)

Worktree `~/wt/lfm3`, branch `opt-lfm3` from `amd-opt` 5909da1f1, build `~/wt/lfm3/build-hip`, installed to
`~/wt/lfm3/inst`. KV cache q8_0 for every LFM number. Tools in `~/wt/lfm3-prof` (copies of the round 2 tools plus):
`kld.sh` (KLD of the decode path, see 1), `kvq_depth.sh`, `final.sh` (the final A/B), `slowmode.sh` (repeated
profiles, Q5_K n=1 MMVQ class per process), `bygrid.py` (per kernel+grid medians), `gap.py` (head of token t to the
first graph kernel of token t+1), `hunks.py` (stages/undoes change blocks for the per-change commits).

## Result (interleaved, ~/llama-opt = 5909da1f1 vs ~/wt/lfm3/inst, LFM KV q8_0)

Official run (`~/wt/lfm3-prof/final2.log`, inst = final branch 9d493cf6e):

| measurement | ~/llama-opt (5909da1f1) | opt-lfm3 (inst) | change |
|---|---|---|---|
| llama-bench tg128 -r 5, 3 rounds, depth 0 | 241.08 t/s, 4.148 ms/token | 262.05 t/s, 3.816 ms/token | -8.0 % ms/token |
| same, depth 32768 | 205.44 t/s, 4.867 ms/token | 231.03 t/s, 4.328 ms/token | -11.1 % |
| same, depth 98304 | 152.42 t/s, 6.561 ms/token | 191.44 t/s, 5.224 ms/token | -20.4 % (+25.6 % t/s) |
| spec_sweep `lfm none` 6x3, T=1, round 1 / 2 | 242.83 / 237.01 t/s, 4.118 / 4.219 ms/step | 251.28 / 252.04 t/s, 3.980 / 3.968 ms/step | -3.4 % / -6.0 % |
| spec_sweep `qwen mtp` 6x3, T=1, round 1 / 2 | 103.75 / 103.77 t/s, 29.152 / 29.149 ms/step | 103.81 / 103.69 t/s, 29.153 / 29.155 ms/step | no change (same tok/step per class) |

An earlier identical run (`final.log`, inst = 4f67c7ddc, which differs only by the scatter chunking and the
zero-size fix of the last commit): llama-bench 4.090 -> 3.881 / 4.896 -> 4.369 / 6.589 -> 5.191 ms/token at depth
0 / 32k / 98k; spec_sweep `lfm none` 242.7 / 242.9 -> 260.0 / 259.6 t/s (4.12 -> 3.85 ms/step); `qwen mtp` 103.7 /
103.6 -> 103.6 / 103.6 t/s. The spread of the LFM server numbers between the two runs (lfm3 3.85 vs 3.97 ms/step)
is the per-process expert gate+up "slow mode" (section 3, +3 us x 38 per token when it hits).

Kernels per token 416 -> 305 (depth 0); GPU busy (rocprofv3, tg64) 3.23 -> 3.11 ms; at 98k context the attention
is 128.7 us per layer (was 223.5 us with the vec kernel).

## 1. q8_0 decode attention: the kvq kernel reads q8_0 (GGML_HIP_KVQ_Q8)

The fork's RDNA3 kvq kernel (WMMA, all Q heads of a KV head per pass) got q8_0 instances (D 64 and 128):
K dequantized into the WMMA A fragments with the exact `0x6400 | (q ^ 0x80)` - 1152 trick times d, V into the
transposed f16 tile with the lane-pair exchange, half rows of 34-byte blocks that start 2 bytes into a word loaded as
whole words with a per-lane shift. D 256 spills 32 VGPRs and stays on the vec kernel.

KV split per block count, in the model at 98k (FA per call, 10 calls/token): 3 splits 200.6 us, 4 164.9, 6 (= 1 block
per WGP) 129.3, 8 161.8 (unbalanced), 12 (2 per WGP, the q4_0 setting) 146.8, 18 (3 per WGP) 146.6. 32k: 47.4 (1 per
WGP) vs 52.8 us. Taken: 1 block per WGP for q8_0 (q4_0 unchanged, stays bitwise). The test-backend-ops perf mode is
useless for this: K/V up to ~96 MB stay in the Infinity Cache between repetitions (32k: 35 MB).
D 128 q8_0 (perf mode, 98k): kvq 283 us vs vec 634 us.

### KLD gate (llama-perplexity --kl-divergence, wikitext-2 test, 3 chunks x 16384 tokens, ubatch 1 = the decode
kernels, reference: f16 KV of the same build, scored: second half of each chunk = 24573 tokens)

| KV / FA kernel | mean KLD | 99.9 % KLD | max KLD | same top p | RMS dp | PPL(Q)/PPL(f16) |
|---|---|---|---|---|---|---|
| q8_0, vec (incumbent), run 1 | 0.044171 +- 0.001726 | 4.1295 | 15.85 | 92.248 +- 0.171 % | 4.995 % | 1.0138 |
| q8_0, vec (incumbent), run 2 | 0.044171 +- 0.001726 | 4.1295 | 15.85 | 92.248 +- 0.171 % | 4.995 % | 1.0138 |
| q8_0, kvq (new) | 0.044196 +- 0.001775 | 4.2485 | 13.10 | 92.345 +- 0.170 % | 4.848 % | 1.0026 |
| q4_0, kvq | 0.128359 +- 0.002629 | 6.9328 | 15.29 | 85.215 +- 0.226 % | 8.648 % | 0.9042 |

Per chunk (cumulative) mean KLD vec / kvq: 0.06477 / 0.05954, 0.04866 / 0.04679, 0.04417 / 0.04420; same top p
91.43 / 91.98, 92.08 / 92.23, 92.25 / 92.35 %. The incumbent is deterministic (two runs identical, floor 0); the new
kernel's mean KLD is +0.000025 (1.4 % of its standard error) over the full set and lower in the first two chunks, its
same-top-p, RMS dp and PPL ratio are better: accepted. A bitwise variant (vec kernel with the 4 heads of a KV head in
one block) was not built: the WMMA kernel's numerics are at least as good and it is the faster design.
Note: q8_0 KV vs f16 KV costs 0.044 KLD on LFM2 with the decode kernels, q4_0 0.128 (the gap the user bought).

## 2. Fusions

- **GGML_HIP_GATE_UP_Q8 (kept)**: the single-token gate/up(+GLU) MMVQ writes the q8_1 input of the down matvec;
  the block that completes a 32-row group (ticket per group) quantizes it. -40 quantize_q8_1 launches.
  4.070 -> 3.973 ms/token. Bitwise.
- **GGML_HIP_ATTN_PREP (kept)**: q norm+rope+FWHT, v FWHT, k norm+rope+FWHT, SET_ROWS K and V (5 launches) in one
  launch after the V and K matvecs, shared code (rms_norm_mul_rope_f32_rows, fwht_row_warp, quantize_f32_q8_0_block).
  The first version never triggered in the model: the allocator gives K the memory of the dead V etc., the overlap
  checks bailed out; V, K and the k/v FWHT rows (read only inside the region) now live in pool scratch.
  376 -> 336 kernels/token, attn_prep 5.9 us vs 13.1 us of kernels; 4.043 -> 3.907 ms/token. Bitwise.
- **GGML_HIP_KVQ_FWHT (kept)**: the kvq combine launch also applies the output FWHT and writes the q8_1 input of the
  o projection. 336 -> 316 kernels/token; 3.1 us vs 1.7 + 1.1 + 1.8 us; 3.928 -> 3.879 ms/token. Bitwise.
- **Graph inputs, GGML_HIP_INPUT_BATCH (kept)**: the 12 per-token uploads are rs_s_copy (i32), inp_pos, the two
  64x64 Hadamard matrices attn_inp_k_rot / attn_inp_v_rot (16 KiB each, uploaded every step although the FWHT path
  never reads them), attn_inp_kq_mask (f16, n_kv values: 512 B at depth 0, 192 KiB at 98k), attn_inp_k_idxs,
  attn_inp_v_idxs (i64), out_ids, the CPU-side token embedding row (model.embed_tokens get_rows, 8 KiB), node_1,
  inp_mixed_slots, inp_mixed_embd. They cannot be skipped by the backend (it cannot know a tensor is unread), but they
  can be batched: set_tensor_async stages uploads <= 256 KiB in pinned memory, the next other stream operation issues
  one H2D copy and one scatter kernel. 316 -> 305 kernels/token; head-to-first-kernel gap under the profiler
  168.7 -> 112.6 us (depth 0), 162.7 -> 153.4 us (98k); 3.840 -> 3.806 ms/token (5 rounds), 98k 5.230 -> 5.198
  (2 rounds). Bitwise.
  A first version (one scatter block per upload) took 11.4 us for the 192 KiB mask at 98k (now 8 KiB chunks per
  block: 4.0 us) and failed on zero-size uploads (empty grid; caught at 98k depth under the profiler, fixed: zero-size
  uploads take the direct path).
- **GGML_HIP_MOE_DOWN_NORM (rejected)**: the next layer's attn_norm (+q8_1) as a one-warp tail of the MoE
  down+reduce+residual kernel (2048 blocks), bitwise version of rms_norm_mul_f32_unrolled<2>:
  - one ticket counter for 2048 blocks: down kernel 13.0 -> 55.7 us/call, 4.12 -> 5.46 ms/token;
  - two-level tickets (32-block groups): no change -> not atomic contention;
  - isolated: ticket only 13.7 us; tail alone ~40 us. The fully unrolled one-warp tail is ~17k instructions of
    straight-line code run once per launch from a cold instruction cache; hoisting loads (restrict) 43 us,
    the per-group quantization as a real call (2.8k instructions) 30 us/call = still +16 us vs the separate norm
    kernel (2.9 us + one boundary). Lesson: a tail that is not tiny code loses on RDNA3 (I-cache misses at ~60 ns per
    64-byte line, no reuse).

## 3. The expert gate+up slow mode

- Only the expert gate+up launch (mul_mat_vec_q Q5_K n=1 with fused gate, grid 768 x 4) slows down: 25.1 -> 28.1
  us/call in some processes; in the same processes in_proj (14.1 us), the down+reduce of the same experts
  (12.6 / 14.7 us), out_proj, the head are unchanged.
- Frequency (separate processes, depth 0): 4 of 12 baseline runs slow; with the model buffer rounded up to a 2 MiB
  multiple (17021352448 B is not; the pointer is 2 MiB aligned; amdgpu uses 2 MiB blocks only for 2 MiB-multiple
  BOs) 3 of 12 -> not the cause (no commit).
- Nontemporal/DLC weight loads (see 4) do not remove it either. Cause still open; it is the only kernel that streams
  two large tensors (gate_exps and up_exps rows of the same experts) at the same time, so a physical-placement
  conflict between the two streams (DRAM channel/bank aliasing of their per-process physical offsets) is the
  remaining hypothesis; testing it needs control of physical placement (or repacking gate+up per expert into one
  tensor in the loader, which is bitwise but larger work).

## 4. MMVQ bandwidth

- Nontemporal (slc dlc) loads of the Q5_K weights in the n=1 dot product: Q5_K n=1 class 12.90 (fast mode) /
  13.9 (slow mode) -> 14.42 us/call (worse, reverted).
- The gate+up kernel uses 50 VGPRs (16 waves/SIMD) and its 3072 single-wave blocks fill the GPU once: occupancy is
  maxed; round 1/2 tried more rows per block and unrolled K loops (negative). Changing the K split per row (more
  waves per row, split-K) changes the summation order, which the bitwise rule forbids. Not improved this round
  (gate+up 25.1 us = 690 GB/s, in_proj 14.2 us, down 12.6 / 14.7 us, head 238 us = 903 GB/s).

## 5. Final per-kernel picture (rocprofv3, llama-bench tg64, depth 0, final build)

305 kernels/token, busy 3107 us, wall under the profiler 4243 us.

| kernel | us/token | calls | us/call |
|---|---|---|---|
| mul_mat_vec_q Q5_K n=1 (expert gate+up 38 x 25.1, out_proj/o 39 x 5.1, q/k 15 x 2.9 + 11 x 5.6, dense) | 1366.1 | 106 | 12.89 |
| mul_mat_vec_q_conv Q5_K (in_proj + shortconv) | 412.5 | 29 | 14.23 |
| mul_mat_vec_q Q6_K n=1 (head 238.4, dense down, v) | 320.3 | 9 | 35.59 |
| mul_mat_vec_q_moe_down_reduce Q5_K / Q6_K | 254.4 / 250.0 | 20 / 17 | 12.72 / 14.71 |
| norm_router_topk_f32 | 187.6 | 38 | 4.94 |
| rms_norm_mul_f32_unrolled (attn norms, output norm, dense ffn norms) | 117.0 | 43 | 2.72 |
| flash_attn_ext_kvq (q8_0) | 81.2 | 10 | 8.12 |
| attn_prep_f32 (new) | 60.9 | 10 | 6.09 |
| flash_attn_kvq_combine_fwht (new) | 31.1 | 10 | 3.11 |
| rest (last layer: bin_bcast, get_rows, cpy, concat, weighted reduction, conv; scatter 3.3) | ~25 | 14 | |

At 98k context: flash_attn_ext_kvq 128.7 us/call (1287 us/token), combine+FWHT 4.3 us, attn_prep 7.6 us.

Per shortconv+MoE layer still 7 launches (rms_norm(q8) -> in_proj+conv -> out_proj(+res) -> norm+router+topk ->
gate+up(+q8 for down) -> down+reduce+res); attention+MoE layer 9 (norm -> q -> v -> k -> attn_prep -> FA -> combine+FWHT
-> o(+res) -> norm+router+topk -> gate+up -> down).

## 6. Attempts in order (numbers in the sections above)

1. q8_0 kvq kernel, first version (2 blocks/WGP): FA at 98k 223.5 -> 146.8 us; llama-bench 98k 6.495 -> 5.611 ms.
2. KV split sweep (in model): 1 block/WGP best (129 us); perf-mode microbench rejected as a tool (Infinity Cache).
3. D 256 q8_0 excluded (register spills), D 128 q8_0 kvq 283 vs vec 634 us.
4. KLD gate (table in 1).
5. MoE down + next attn_norm tail: 3 variants, rejected (section 2).
6. gate+up q8_1 epilogue: kept.
7. attn_prep v1 (graph tensors, overlap checks): never fused in the model; v2 (scratch): kept.
8. Output FWHT + q8_1 in the kvq combine: kept.
9. Batched graph inputs: kept (+ fixes: chunked scatter, zero-size uploads).
10. Slow mode: per-grid analysis, 2 MiB-rounded model buffer (no fix).
11. Nontemporal weight loads in the n=1 MMVQ: negative.

## 7. Commits (5909da1f1..opt-lfm3)

- 5f6c03fa9 HIP/RDNA3 FA: the kvq decode kernel also reads a q8_0 KV cache (GGML_HIP_KVQ_Q8)
- 04f10413e CUDA/HIP: single-token gate/up(+GLU) MMVQ writes the q8_1 input of the down projection (GGML_HIP_GATE_UP_Q8)
- 7a963bc0c CUDA/HIP: single-token attention input (q/k norm+rope+FWHT, v FWHT, q8_0 SET_ROWS of k and v) in one launch (GGML_HIP_ATTN_PREP)
- 3a1279f95 CUDA/HIP: kvq attention applies the output FWHT (+ q8_1 for the o projection) in its combine launch (GGML_HIP_KVQ_FWHT)
- 9d493cf6e CUDA/HIP: batch the small async input uploads of a graph into one H2D copy + one scatter launch (GGML_HIP_INPUT_BATCH)

Every switch defaults on; `GGML_HIP_<NAME>=0` restores the previous path. Only GGML_HIP_KVQ_Q8 changes numerics
(KLD-gated, section 1); all others are bitwise.

Verification: test-backend-ops MUL_MAT 2476/2476, MUL_MAT_ID 931/931, ROPE 450/450, RMS_NORM 53/53,
RMS_NORM_MUL_ROPE 320/320, SET_ROWS 159/159, MUL 142/142, SSM_CONV 45/45, TOPK_MOE 416/416, NORM_ROUTER_TOPK 5/5,
SHORTCONV 4/4, MOE_DOWN_REDUCE 5/5, FFN_GATE_UP_DOWN 5/5 (new), ATTN_PREP 3/3 (new), FLASH_ATTN_EXT 4060/4060.
Logit hashes (64 greedy steps): with GGML_HIP_KVQ_Q8=0 equal to 5909da1f1 (q8_0 d0 a3c06fe69758819e, d3000
718efee0662e860e; q4_0 d0 b81cc99db07e6661 unchanged in all configurations); with the q8_0 kvq kernel d0
a7ce25b73f887fed, d3000 b47452b9380b665b (unchanged by every later commit). Greedy md5: LFM plain q8_0 with
GGML_HIP_KVQ_Q8=0 2c7ee8a28750f9bfbb09baa4e3027a72 (= baseline), with kvq 894e56e447243cf630214b4cfc1ffea6 (new
numerics, coherent text); Qwen plain c4708318411479c9530911e310f865bd, Qwen MTP 6f14e814bb6408aeea23a1dc50e96ba1.

This file is untracked.
KLD artefacts: `~/wt/lfm3-prof/ref.kld` (6.3 GB, f16-KV reference logits of the decode path, reusable with
`kld.sh NAME BIN q8_0 [ENV=..]`), logs `kld_*.log`; wikitext-2 in `~/wt/lfm3-prof/wikitext-2-raw/`.
