# Qwen round 5 (branch opt-qwen5 from amd-opt c36fd2c87)

Worktree `~/wt/qwen5`, build `build-hip`, install `inst` (bin/ + lib/ copied from build-hip), ablation build
`build-abl` (`-DGGML_MMQ_ABLATION`, timing only). Tools: `~/wt/qwen5-tools`. Baseline for every A/B: `~/llama-opt`
(c36fd2c87).

- 2026-10-15 ~00:45: user ordered NO GPU work; ~02:00 GPU allowed again. Results below marked MEASURED.

## GPU results (2026-10-15)
- Greedy md5 (fresh servers, ~/wt/qwen5-tools/greedy.sh, same prompts as fusion/greedy.sh): ~/llama-opt reproduces
  plain c4708318 / mtp 6f14e814. With GDN fast (58e578967): plain 0b7b073b, mtp 21b0f25f -> NOT bitwise.
  With GGML_HIP_GDN_FAST=0 GGML_HIP_MMQ_YDB=0: plain still 0b7b073b (mtp 4fa536ce) -> the restructured *plain*
  GDN path already changed the rounding (the offline ISA showed 94 vs 83 FMAs: different contraction after the
  lambda refactor). GDN commit reverted (5b1fdbc2f); then plain c4708318 + mtp 6f14e814 again (with YDB=2 on),
  LFM q8_0 plain 894e56e4 (YDB on). A future GDN attempt must pin the contraction (explicit fmaf matching the base
  ISA) and keep the plain kernel source untouched.
- MMQ y double buffer (a6f218d0e), llama-bench Qwen UD, -fa 1 KV q4_0, 2 interleaved rounds, pp512 / pp4096:
  YDB=0 1045 / 1097, 1035 / 1091; YDB=2 1012 / 1066, 1009 / 1065 -> -2.6% at pp4096 (3 -> 2 blocks per WGP costs
  more than the 2 barriers save). Bitwise (md5 above). Reverted (2aa6999ed).
- MMQ P0 ablation (build-abl, whole-model pp4096, -r 2): normal 1094 / 1085; x tile loaded once 1173 (+7.6%);
  y tile once 1131 (+3.8%); no loads 1219 (+11.9%); no barriers 1173 (+7.6%); no vec_dot 3254 (3.0x).
  => per token 0.918 ms of which the MMQ vec_dot (WMMA + scale epilogue) ~0.61 ms (~66% of prefill), loads ~0.10 ms
  (11%), barriers ~0.07 ms. MMQ is math/epilogue-bound, not load-bound: tile prefetch can win at most ~12%, and
  only if it costs no occupancy (YDB showed it does). The lever is the epilogue (64 cvt + 128 fma_mix + 33 fmac per
  16 WMMA per k01 step), constrained by bitwise logits.
- DFlash greedy (T=0, 400 tok, EN code / PL prose): n=6 104.8 / 44.2 t/s (accepted 295 / 123), n=15 89.7 / 38.3
  (accepted 295 / 130: the same tokens accepted, 2.5x more drafted). Divergence from plain at char 229 for both
  (MTP diverges at 129): verify-batch numerics, as for MTP; no clamp warning at n=15, so the wide block runs.

## Attempts (numbered, with numbers)
1. Q1 DFlash2 block 16 (commit 6cb110bed, UNMEASURED). `LLAMA_DFLASH_WIDE` (default on) lets in-place
   DFlash/DFlash2 draft up to 2*block_size-1 = 15 tokens (drafter metadata `dflash.block_size` = 8, the clamp was 7).
   The DFlash2 selector lattice now has a row per runtime block position (it had min(tokens_per_block, 8) rows; the
   CPU walk would have read past it). `LLAMA_DFLASH_BLOCK=N`: denoise N tokens, keep n_max drafts ("draft 16,
   verify k", Lucebox +10% acceptance per position). Unchanged for n_max <= 7.
2. Q3 GDN fast (commit 58e578967, UNMEASURED, `GGML_HIP_GDN_FAST=0` off). Base ISA (S_v=128, lag, l2):
   15 ds_bpermute reductions, 87 global_load_b32 + 52 global_store_b32, 84 VGPRs. New: DPP reductions (0 bpermute,
   24 DPP adds), state as 4 global_load_b128 + 8 global_store_b128 through 8.5 KB LDS, kv[t+1] summed in the
   output pass of token t (both butterflies overlap), next token's loads + l2 norms before the update; 119 VGPRs,
   no spills. Meant to be bitwise (same lane mapping, sum order, butterfly); pending md5 + test-backend-ops.
3. Q4 in-kernel causal mask: NOT implemented (a started ggml API edit was reverted, nothing half-done is
   committed). Host cost measured offline (`maskbench.cpp`, best of 200, f16, 5 tokens): 1.7k 1.1 us, 6.6k 3.6 us,
   29.5k 17 us, 94k 56 us, plus an H2D of n_kv*n_tokens*2 B (920 KB at 94k, [INFERENCE] ~40-70 us). Upper bound of
   the gain ~0.1 ms/step at 94k (~0.3%), ~0 at short context. Worked-out design, ready to implement:
   - ggml: `ggml_flash_attn_ext_set_kq_bounds(fa, bounds)` sets src[5]: an I32 tensor [n_batch,1,1,ne3]. Row j sees
     K/V [0, bounds[j]); the mask (src[3]) must be NULL; no ALiBi.
   - CPU ops.cpp: both FA paths (one_chunk ~8949/8967, tiled ~9227) compute mv = ic < bounds[iq1] ? 0 : -inf.
   - CUDA: get_best_fattn_kernel treats src[5] like a mask (gqa_opt_applies, so the alloc size is the same); kvq
     computes mask_h2 from bounds (same 0/-inf f16 values, same fmaf, so bitwise); every other kernel gets a pool
     f16 mask expanded from the bounds and runs the unchanged path. supports_op: src[5] needs max_bias == 0.
   - llama: cparams.kq_bounds = env LLAMA_KQ_BOUNDS && flash_attn && every device backend is CUDA/ROCm (other
     backends would ignore src[5]); build_attn_inp_kq_mask makes the I32 tensor only when n_tokens <= 16, one
     stream, causal, no SWA/ALiBi, kv_beg 0, the sequence owns all used cells, used_max_p1() == get_used() and the
     cell positions rise strictly (one SIMD scan, ~10 us at 94k); bounds[j] = upper_bound(pos, p_j).
     can_reuse_kq_mask: reuse only while that mode decision is unchanged; build_attn_mha passes NULL +
     set_kq_bounds for an I32 "mask". Prefill (n_tokens > 16) keeps the f16 mask.
   - test-backend-ops: FA case with bounds vs CPU.
4. Q2 MMQ P0 ablation: hooks in `mul_mat_q_process_tile` (only with `-DGGML_MMQ_ABLATION`; production ISA
   unchanged because `ablate` is constexpr 0): `GGML_MMQ_ABLATE` bits 1 = x tile loaded only once, 2 = y tile only
   once, 4 = no vec_dot, 8 = no barriers. Pending: llama-bench pp512/pp4096 per mode.
5. DFlash restricted LM head (commit bbac7d7ae, UNMEASURED): `--spec-draft-vocab` (+ `-n`) now also applies to the
   DFlash drafter, whose LM head is the target's Q6_K output (1.04 GB per draft step; [INFERENCE] ~1.5 ms at
   ~700 GB/s, the 64k rows ~0.4 ms). DFlash2 runs top-k on the restricted logits and maps candidates to token ids.
   Pending: A/B within the DFlash sweep (`EXTRA_ARGS=--spec-draft-vocab,$HOME/models/draft/draft_vocab_qwen38.txt,--spec-draft-vocab-n,65536`).
6. Q2 MMQ y double buffer (commit a6f218d0e, UNMEASURED, `GGML_HIP_MMQ_YDB=0` off, `=1` only where the blocks per
   WGP stay the same, default 2 = wherever it fits). Second y half of each 256-K iteration gets its own LDS buffer
   behind the x tile: one load phase and 2 barriers per iteration instead of 4; same vec_dot calls in the same order
   (bitwise by construction). Q4_K J=128: 241 VGPRs (was 239), no spills, LDS 38.9 -> 57.3 KB (3 -> 2 blocks per
   WGP; mode 1 therefore almost never applies). Register prefetch of the next tile was not done: Q4_K J=128 (the
   prefill tile) already uses 239 VGPRs, the 36-72 extra registers would spill.
   Offline ISA analysis of the Q4_K J=128 inner vec_dot loop (one k01 step): 16 v_wmma_i32_16x16x16_iu8 against
   64 v_cvt_f32_i32 + 128 v_fma_mix_f32 + ~33 v_dual_fmac (epilogue ~3.5 VALU per C element per 32 K). If WMMA and
   VALU do not overlap on RDNA3 [INFERENCE], the epilogue alone caps the loop at ~2/3 of WMMA peak; the bitwise
   epilogue cannot drop operations (each element has its own (dmA, dsB) product). P5 decides whether loads or this
   epilogue dominate.
7. Q5 logits D2H: not implemented (parent: only after the D2H measurement shows >= 0.2 ms/step). Design agreed with
   the parent: GPU top-M per output row as extra graph outputs, full rows fetched lazily, sampling.cpp hook as a
   separate commit, ties at the M-th value / NaN -> lazy full row, PM4 dispatch shape unchanged, env off = old path.

## Commits
- 6cb110bed speculative: DFlash/DFlash2 blocks up to twice the trained width (UNMEASURED)
- 58e578967 HIP/RDNA GDN fast path (UNMEASURED)
- 48589fbe7 MMQ ablation hooks (ablation build only, production ISA unchanged)
- bbac7d7ae speculative: --spec-draft-vocab for the DFlash drafter (UNMEASURED)
- a6f218d0e HIP/RDNA3 MMQ: y halves double-buffered in LDS, 2 barriers per K iteration instead of 4 (UNMEASURED)

## Pending GPU verification (exact commands; every one under the locks, <= 5 min blocks, 30-60 s pauses,
## first `pgrep -f "llama-server.*--port 8080"` must be empty)
P1. GDN bitwise + tests:
    `cd ~/wt/qwen5 && flock /tmp/gpu.lock flock /tmp/quiet.lock env LD_LIBRARY_PATH=inst/lib inst/bin/test-backend-ops -o GATED_DELTA_NET`
    (and `-o GATED_DELTA_NET_LAG` if listed), then with `GGML_HIP_GDN_FAST=0`.
    `flock /tmp/gpu.lock flock /tmp/quiet.lock ~/wt/qwen5-tools/greedy.sh ~/wt/qwen5/inst/bin ~/wt/qwen5/inst/lib /tmp/q5g qwen`
    -> plain c4708318411479c9530911e310f865bd, mtp 6f14e814bb6408aeea23a1dc50e96ba1.
P2. GDN timing: rocprofv3 kernel trace with `GGML_HIP_PM4=0`, fast vs `GGML_HIP_GDN_FAST=0` (gated_delta_net_cuda us/verify).
P3. Q1 greedy exactness: `MODES="plain dflash6 dflash15"` greedy.sh -> dflash md5 == plain md5 (T=0 lossless).
P4. Q1 sweep: `cd ~/qwen-opt && for n in 6 8 10 12 15; do SEEDS=1,2,3 PORT=18440 RUN_ARGS="qwen dflash" ROCM_DIR=$HOME/wt/qwen5/inst flock /tmp/gpu.lock flock /tmp/quiet.lock ./spec_sweep.sh "DRAFT_N=$n LABEL=q5_dflash$n"; sleep 45; done`,
    plus `"DRAFT_N=8 LLAMA_DFLASH_BLOCK=16"`, T=0 run (`TEMPS=0.0`) for code, and `qwen mtp` on the same inst.
P5. MMQ ablation: `build-abl/bin/llama-bench -m Qwen UD -p 512,4096 -n 0 -fa 1 -ctk q4_0 -ctv q4_0` with GGML_MMQ_ABLATE=0,1,2,3,4,8.
P6. Logits D2H: `GGML_HIP_PM4=0 rocprofv3 --memory-copy-trace --kernel-trace` on a qwen mtp server request; size/time of the D2H per step.

P7. MMQ YDB A/B: `llama-bench -m ~/models/Qwen3.8-27B-UD-Q4_K_XL.gguf -p 512,4096 -n 0 -fa 1 -ctk q4_0 -ctv q4_0 -r 3` with
    GGML_HIP_MMQ_YDB=0/1/2, then LFM pp4096 (MoE MMQ) and llama-perplexity KLD vs c36fd2c87 (must be 0).
P8. DFlash short code prompts (parent request, compare with hipfire 318 t/s / AR 50.3): server `qwen dflash` with
    DRAFT_N=15 (and 7), then `~/wt/qwen5-tools/code_probe.py --port 18440 --label ...` (thinking off, T=0); also
    plain and MTP for the AR ratio.
P9. Final A/B vs ~/llama-opt per the brief (spec_sweep qwen/uncensored mtp 2 rounds, long_ctx_bench, lfm none).

## Recommended run-llm.sh changes
None yet: every change is unmeasured. Candidate after P4/P8: a DFlash variant with DRAFT_N=15 (accepted by the new
cap) and `EXTRA_ARGS=--spec-draft-vocab,$HOME/models/draft/draft_vocab_qwen38.txt,--spec-draft-vocab-n,65536` for
code prompts, e.g. `DRAFT_N=15 ROCM_DIR=$HOME/wt/qwen5/inst run-llm.sh qwen dflash`.
