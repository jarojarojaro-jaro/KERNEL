# Prefill, long-context attention & prompt caching: Qwen3.8-27B (qwen35) on RX 7900 XTX (gfx1100), ROCm

Slice: prefill matmul path, GDN prefill, FA prefill and decode with q4_0 KV at long context, server prompt cache and checkpoints.
Tree: ~/llama-master (amd-opt, upstream e60eff95f, 2026-10-09). Build: `build-hip/CMakeCache.txt`: GPU_TARGETS=gfx1100, GGML_CUDA_FA_QUANTS=q4_0-q4_0;q8_0-q8_0;f16-f16;bf16-bf16, FORCE_MMQ/FORCE_CUBLAS OFF, HIP graphs ON.
Launch: `~/qwen-opt/run-llm.sh` has no -b/-ub, so the defaults apply: n_batch 2048, n_ubatch 512 (common/common.h:460-461). It also uses -np 1, `-ctk/-ctv q4_0`, and no `-ctkd/-ctvd`.
Nothing was run on the GPU. Every number is either cited or derived with the arithmetic shown. [INFERENCE] marks estimates that were not measured.

## 0. Verified facts that the arithmetic below uses

- **GGUF header** (read via gguf-py, header only):
  - qwen35 block_count 65 = 64 + MTP blk.64. Every 4th layer is full attention, so 16 attention layers and 48 GDN layers.
  - Attention: head_count 24, head_count_kv 4 (GQA 6), key/value_length 256.
  - GDN: ssm.inner 6144, state 128, group_count 16 (Q/K heads), time_step_rank 48 (V heads, one 128×128 state each).
  - embd 5120, FFN 17408, attn_q 5120×12288 (Q plus gate).
- **Matmul FLOPs per prompt token** (lm_head excluded; the server computes logits only for the last prompt token, server-context.cpp:4024-4025):
  - FFN: 64 × 3 × 5120×17408 = 17.11 G params.
  - GDN: 48 × (qkv 52.4M + z 31.5M + ssm_out 31.5M) = 5.54 G.
  - Attention: 16 × (62.9 + 5.2 + 5.2 + 31.5)M = 1.68 G.
  - Total ≈ 24.3 G params, i.e. **≈ 48.6 GFLOP/token** (54 GFLOP with lm_head on every token).
- **Q6_K share of the matmul FLOPs** (it matters because Q6_K takes a different path, see F7):
  - UD-Q4_K_XL ≈ 2.17 G params (8.9%).
  - Uncensored Q4_K_M ≈ 4.25 G params (17.5%): ffn_down ×33, attn_qkv ×24, attn_v ×9.
  - Everything else in both models is Q4_K, Q5_K, IQ4_XS, IQ4_NL, IQ3_S, Q3_K or Q8_0, and those go to MMQ.
- **Peak rates.** RDNA3 Navi31 (96 CU): FP16 matrix 123 TFLOPs, INT8 matrix 123 TOPs, INT4 245 TOPs ([AMD W7900 spec page](https://www.amd.com/en/products/graphics/workstations/radeon-pro/w7900.html), same die at 295 W TBP). The 7900 XTX is 122.8 TFLOPS FP16 ([flopper](https://flopper.io/gpu/amd-radeon-rx-7900-xtx-24gb)). **INT8 WMMA does not run faster than FP16 WMMA on RDNA3.**
- **q4_0 KV size:** 18 B per 32 values, so K and V together = 2 × 1024/32 × 18 = **1152 B per token per layer**, and 16 layers = **18,432 B per token**. q8_0 is 2176 B per token per layer (1.89×). f16 is 4096 B.
- **Measured prefill** (`~/qwen-opt/logs/e2e-rocm.log`, server, MTP on):

  | prompt tokens | time | rate |
  |---|---|---|
  | 1,714 | 2.28 s | 750 t/s |
  | 6,565 | 7.10 s | 924 t/s |
  | 29,510 | 34.2 s | 863 t/s |
  | 94,181 | 141.5 s | 666 t/s |

## 1. Ranked findings

| # | Finding | Applies here | Expected gain | Effort | Risk |
|---|---|---|---|---|---|
| F1 | The q4_0 verify and decode attention reads about 10× the KV floor at long context. The in-progress GQA kernel should also cover n=1 and the MTP draft context. | yes | step −10 ms @30k, up to −30 ms @94k; MTP decode 62→~73 t/s @30k, 43→~65-72 t/s @94k | in progress (high) | med |
| F2 | Prompt-cache and checkpoint configuration (flags only) | yes, chat + agent | avoids whole re-prefills: 34 s @30k, 142 s @94k → ~0.1-0.3 s restore | zero code | low |
| F3 | Fixed cost per request in prompt processing: 150 ms (no MTP) / 230 ms (MTP) for tiny prompts | yes, every turn | −40 ms (checkpoint taken from rollback snapshot) and −40…80 ms (MTP prompt hook) TTFT | med | low |
| F4 | The MTP draft context KV is f16 by default; switch to `-ctkd/-ctvd q4_0` | yes | −0.6 GB VRAM @204800; −1…5 ms per step at ≥94k | flag | acceptance only |
| F5 | KQ mask is built on the CPU with O(n_kv) work per graph eval, about 6 evals per spec step | yes at long ctx | ~1-3 ms per step @94k [INFERENCE] | low-med | low |
| F6 | FA prefill at long context: about 26% of a 94k prefill | yes | −6…8% at 94k, −3% at 30k | med-high | med |
| F7 | Matmul path: Q6_K goes to dequant + hipBLAS above 128 columns; RDNA3 MMQ runs at ~40% of WMMA peak | yes | 1-4% prefill (Q6_K); larger only with deep MMQ work | low → high | low |
| F8 | `-ub 1024/2048` | yes, but VRAM-tight | 0-3% prefill | flag | VRAM |
| F9 | GDN prefill uses a serial per-token kernel; the chunked (WY) form is not implemented | yes | ≤2-3% prefill | low (prefetch) / high (chunked) | low |

---

### F1. Long-context verify/decode attention

**Evidence for the current kernel path** (fattn.cu:541-720, gfx1100, D=256, GQA 6, q4_0):
- `gqa_ratio_eff` = 2 (6%4≠0), from fattn.cu:668-671.
- WMMA/MMA is taken only when `Q->ne[1]*2 > 16` (fattn.cu:700-702), i.e. ≥9 tokens.
- Quantized KV with ≤2 tokens uses VEC (fattn.cu:713-716). With 3-8 tokens it uses **TILE**.
- TILE and MMA_F16 set `need_f16_K/V` (fattn.cu:738-742). `launch_fattn` then converts the **whole K and V view** to f16 on every call (fattn-common.cuh:1031-1090).
- The rocprof trace (`~/qwen-opt/prof/rocm-mtp4-now/run_kernel_stats.csv`) shows `flash_attn_tile<256,256,{1,2,4,8},2>`, `flash_attn_ext_vec<256,{1,2},q4_0,q4_0>` and `flash_attn_ext_f16<256,256,32,2>` (prefill).

**Bandwidth floor vs measured.** One target forward reads at least L × 18,432 B of KV:

| ctx | KV bytes | time at 960 GB/s |
|---|---|---|
| 1.7k | 31 MB | 0.03 ms |
| 29.5k | 0.54 GB | 0.57 ms |
| 94k | 1.74 GB | 1.81 ms |
| 200k | 3.69 GB | 3.84 ms |

Measured MTP decode is 78.6 → 62.4 → 43.0 t/s at 1.7k/29.5k/94k (NOTES.md:191-194). Assuming tokens per step stay the same [INFERENCE], the step grows from 41.8 ms to 52.7 ms (+10.9) and 76.4 ms (+34.6).

The floor for each step's attention increment is verify (1 × KV) plus about 5 MTP-context passes over the blk.64 KV:
- 29.5k: 0.57 + 5 × 0.126 (f16 draft KV) ≈ 1.2 ms.
- 94k: 1.81 + 5 × 0.40 ≈ 3.8 ms.

So **≈ 9.7 ms is recoverable at 29.5k and ≈ 31 ms at 94k**:
- Perfect kernels: 62.4 → ~75 t/s and 43 → ~72 t/s.
- Realistic (~75% of bandwidth): about 73 and 65 t/s.

**llama-bench cross-check** (NOTES.md:202):
- At d32768, n=1 costs +3.6 ms over d2048. That equals 6 × 0.63 ms, i.e. the vec kernel re-reads KV once per Q head (6×).
- At d32768, n=5 costs +12.2 ms ≈ 0.6 GB q4_0 read + 2.15 GB f16 write + about 4 f16 passes. That fits the convert-then-tile model.

**Design notes for the in-progress kernel**, beyond what is already planned:
1. **Also cover n=1** (plain decode and every MTP draft step). It replaces VEC's 6× re-read, worth −3.6 ms @32k per target n=1 call.
2. **Also cover the draft context (MTP layer blk.64)**:
   - Its KV is f16 by default, so it goes to the TILE path with `ncols2=2` and KV is read 3×.
   - Taking f16 KV as input as well removes about 2 × 0.4 ms per pass @94k.
3. **Split-K so that ≥2×96 blocks run.** There are only 4 KV heads, so use about 48-96 KV splits per head at ≥32k. The existing `parallel_blocks` and `flash_attn_combine_results` machinery can be reused (fattn-common.cuh:1191-1224, 1304-1312).
   - Combine traffic is negligible: 24 heads × 5 tok × 96 splits × 256 × 4 B ≈ 12 MB.
4. **Load whole K/V rows.**
   - One token × one KV head of q4_0 = 8 blocks × 18 B = 144 B = 9 × 16 B.
   - The token stride in the cache is 4 heads × 144 = 576 B, which is 16-B aligned.
   - So per-row 128-bit loads work even though a single 18-B block is misaligned. No KV layout change is needed.
5. **Launch order and cache reuse.**
   - Per-layer q4_0 KV at 94k is 108 MB, larger than the 96 MB Infinity Cache. One KV head is 27 MB.
   - Make the split index the fastest-varying grid dimension within one KV head, so all Q heads and tokens of the group consume a KV chunk while it is in L2/IC [INFERENCE].
6. **VRAM.**
   - The f16 scratch is reserved inside the FA dst allocation (fattn.cu:722-756 via ggml-cuda.cu:907-912). At 204800 ctx it is 2 × 256·4·204800·2 B ≈ **839 MB**, assuming the reserve uses n_kv = kv_size [INFERENCE].
   - It goes away only if prefill (MMA_F16) also stops converting; see F6.

### F2. Prompt caching for a hybrid recurrent model: exact behavior and recommended flags

**How it works in this tree:**
- **Prefix reuse:**
  - The slot keeps its KV and recurrent state, and `n_past = LCP(old, new)` (server-context.cpp:3589-3591).
  - Hybrid `seq_pos_min` = max(attention, recurrent) (llama-memory-hybrid.cpp:172-175). For the recurrent part it is the last position, so any n_past behind the end needs a **context checkpoint**.
  - Restore: newest checkpoint with pos ≤ n_past (server-context.cpp:3726-3764). If none exists: "forcing full prompt re-processing" (3766-3771).
- **Checkpoints** are created only (server-context.cpp:3865-4062):
  - at the start of the **last user message**;
  - at user-message starts spaced at least `-cms` apart (default 8192, common.h:643);
  - near the prompt end, at n−4−n_ubatch and n−4 (3986-4005, ref PR #20288).
  - Only `COMMON_CHAT_ROLE_USER` spans count (common/chat.h:173-187). Tool-result messages do not create checkpoints.
  - The maximum count is `--ctx-checkpoints` (default 32, common.h:641). When the limit is reached, ones closer than -cms are thinned (2528-2550).
  - They are host-RAM `std::vector`s. Size ≈ the recurrent state: 48 × (128·128·48·4 B + 3·10240·4 B) ≈ **150 MB** (possibly ×(1+n_rs_seq) if rollback rows are serialized [INFERENCE]; the `created context checkpoint … size =` trace at 2581 shows the real figure).
- **Speculative rollback does not use these checkpoints.** It uses `slot.spec_ckpt` plus n_rs_seq snapshots (server-context.cpp:3351-3434, 4434-4438). So the "--ctx-checkpoints 2 for spec rollback" advice in [QingYis/llama-7900xtx-qwen3.8-27b docs/rocmfp4.md](https://github.com/QingYis/llama-7900xtx-qwen3.8-27b/blob/main/docs/rocmfp4.md) does not apply to this tree. Lowering it only removes fallbacks.
- **Host prompt cache (`--cache-ram`, default 8192 MiB, common.h:644; `--cache-idle-slots` default on, :640):**
  - On a new task with a different prefix, the current slot state (full KV + recurrent + checkpoints) is saved to RAM (server-context.cpp:1769-1789).
  - The best entry is restored when f_keep ≥ 0.25 and both f_keep and f_sim improve (server-task.cpp:1804-1861).
  - Entry size per token ≈ 18,432 B (q4_0 target) + 4,096 B (f16 MTP KV, 1 layer), plus 150 MB recurrent, plus checkpoints.
    - 30k conversation ≈ 0.68 GB + ckpts.
    - 94k conversation ≈ 2.3 GB + ckpts (1-2 GB) → **the default 8 GiB holds ~2 long conversations.**
  - Restore ≈ size / ~10-25 GB/s ≈ 0.05-0.3 s, versus 34 s (30k) or 142 s (94k) of re-prefill.
- **`--cache-reuse N` is NOT lossless for qwen35** [INFERENCE from code]:
  - `llama_memory_hybrid::get_can_shift()` returns the attention cache's answer, i.e. true (llama-memory-hybrid.cpp:133-136), so the server enables chunk shifting (server-context.cpp:3606-3659).
  - `seq_rm(head_p, head_c)` on the recurrent cache cannot remove a middle span. The partial branch requires p1 > cell.pos (llama-memory-recurrent.cpp:200-224), so the tail cell survives unchanged and its state still contains the removed tokens.
  - Attention KV gets shifted, but the GDN state is wrong, so outputs differ from a fresh prefill. **Keep `--cache-reuse 0` (the default).**
- **Thinking blocks:**
  - The Qwen3.8 template supports `preserve_reasoning`, which is on by default (server-context.cpp:1627-1645; arg.cpp:3755-3759). With it the re-rendered history is identical to what was generated, and the LCP covers the whole previous turn.
  - If the client drops `reasoning_content` (many OpenAI clients do), or the template re-renders tool calls differently, the prefix diverges at the previous assistant message. The server then restores the previous request's n−4 checkpoint and re-prefills only the previous answer plus the new message: hundreds to a few thousand tokens, 0.3-3 s. That is not a full re-prefill.
  - Editing an earlier message re-prefills from the nearest user-start checkpoint, which with -cms 8192 can lose up to ~8k tokens (≈ 9 s at 900 t/s).
- **`--swa-full`:** N/A; n_swa = 0, so the server disables it (server-context.cpp:1330-1335).
- **kv_unified:** off with explicit `-np 1` (arg.cpp:1727-1733).

**Recommended for single-user chat + agent** (add to run-llm.sh):

```
--cache-ram 32768            # 62 GB host RAM; fits ~6-10 long conversations instead of ~2
--ctx-checkpoints 96 -cms 2048   # finer fallbacks for history edits / agent compaction; 96×150 MB ≈ 14 GB worst case, host RAM only
--slot-save-path ~/qwen-opt/slots   # then POST /slots/0?action=save after building a long agent system prompt; restore after server restart
# keep: --cache-reuse 0 (default), reasoning-preserve (default) and make the client send reasoning_content back
```

Expected effect:
- Conversation switch or return: 34 s → ~0.1 s at 30k, and 142 s → ~0.3 s at 94k.
- Agent history edit: average loss ~cms/2 tokens, from ~4.1k tokens (4.5 s) down to ~1k (1.1 s).
- Cost: each extra checkpoint is ~150 MB D2H (~10-20 ms) plus one forced batch break at that user message.

### F3. Fixed prompt cost per request (TTFT floor for chat turns)

**Evidence** (`~/qwen-opt/logs`):

| prompt tokens | no MTP | MTP |
|---|---|---|
| 30 | 150 ms | 230 ms |
| 70 | 200 ms | 283 ms |

Sources: master-nomtp-q4kv-131k.log vs master-mtp3-q4kv-131k.log; pl-plain.log vs pl-mtp4.log. The ROCm runs `ctx200k-hipopt-mtp4-vocab.log` average 260 ms at 54 tokens.

A 30-token prompt is only ~1.5 TFLOP. The cost is fixed overhead.

**Causes:**
1. **The near-end checkpoint split** (server-context.cpp:3986-4005) always processes the last 4 tokens as a separate decode. That is a full weight-bound forward of ~35-40 ms.
   - Prompts longer than 516 tokens additionally get a ragged split at n−516.
   - Fix: after one combined ubatch, take the n−4 state from the **GDN rollback snapshots**. The kernel already writes the last K states (gated_delta_net.cu:154-166, `keep_rs_t`), and conv snapshots exist as well.
   - Serialize "attention truncated at n−4 + rs slot 4" as the checkpoint. This needs n_rs_seq ≥ 4, which the MTP n=4 config already has (common.cpp:1697).
   - Saves ~40 ms per request. Lossless (bit-identical state).
   - Code: server-context.cpp:3986-4005 and `create_checkpoint` (~2520-2584); a state-export variant in llama-memory-recurrent.cpp (the rs_idx slot).
2. **MTP prompt hook** (common/speculative.cpp:1557-1643): after every prompt batch, a D2H of h_nextn for all tokens (20 KB/token), then a separate ctx_dft decode of the same tokens, serialized. This accounts for about +80 ms on tiny prompts.
   - Profile it for graph re-reserve/capture on new shapes, the sync, and the f16 MTP KV.
   - Likely fixes: fold it into the target graph, or overlap it with the next target batch.
   - Gain −40…80 ms TTFT [INFERENCE].
3. Checkpoint D2H of ~150 MB per created checkpoint (~10-20 ms).

### F4. MTP draft context KV type

- `params.speculative.draft.cache_type_k/v` default to F16 (common/common.h:350-351; flags `-ctkd/-ctvd`, arg.cpp:4109-4133). They are passed to the draft context (speculative.cpp:2577-2578).
- run-llm.sh does not set them, so the blk.64 KV is f16: 4096 B/token → **839 MB VRAM at 204800**, and 386 MB read per draft pass at 94k (×3 for TILE's ncols2=2).
- With `-ctkd q4_0 -ctvd q4_0`: 236 MB VRAM (−0.6 GB) and 108 MB per pass. This pays off once F1 covers n=1; before that, q4_0 at n=1 goes to the VEC 6× re-read path, so compare both.
- Output stays lossless; only acceptance can move. Re-measure with spec_sweep.

### F5. KQ mask construction on the CPU at long context

- `llama_kv_cache::set_input_kq_mask` (llama-kv-cache.cpp:1569-1718) scans all n_kv cells (`is_empty`, `seq_has`, `pos_get`) for the first row of each sequence, then copies n_kv halves per extra row. The result is uploaded H2D.
- Per spec step that is the target verify plus about 5 ctx_dft evals, each with its own mask, so roughly 6 × O(94k) CPU work and ~1 MB H2D at 94k.
- At step boundaries the GPU is waiting, so this is on the critical path [INFERENCE].
- Estimated 1-3 ms per step @94k: 2-4% of the step.
- Measure with the commented timer at llama-kv-cache.cpp:1798.
- Fixes (lossless):
  - cache the mask per context and rewrite only the tail when n_kv grows by a few tokens;
  - or, for one sequence without SWA, build the causal mask on the GPU from `pos` (tiny kernel), or rely on `KV_max` plus an implicit causal check inside the FA kernel.

### F6. Prefill attention at long context

**Kernel path:**
- Prefill with q4_0 goes to MMA_F16 (WMMA f16, mma.cuh:1547-1553 RDNA3) with ncols2 = 2 and ncols1 = 32 (fattn.cu:249-263, 184-190).
- RDNA config: (256,256,64): 256 threads, occupancy 2, nbatch_fa 64 (fattn-mma-f16.cuh:164).
- The whole K/V is converted to f16 on each call (fattn-common.cuh:1031-1090).

**Arithmetic:**
- Attention FLOPs per token = 4 × 24 × 256 × n_kv × 16 = **393,216 · n_kv**.
- 94k prompt: Σ ≈ 393,216 × 94,181²/2 = **1.74 PFLOP**, against matmul 94,181 × 48.6 G = 4.58 PFLOP.
- The 94k run took 141.5 s vs 104.6 s at 900 t/s, so the extra ≈ 37 s, i.e. **~47 TFLOPS effective FA, 26% of the 94k time**.
- 30k: 0.171 PFLOP ≈ 3.6 s of 34.2 s (10.6%).

**The f16 conversion is not the bottleneck:**
- Per 512-ubatch per layer it reads n_kv × 1152 B and writes n_kv × 4096 B. Summed over a 94k prompt: 184 ubatches × avg 47k × 5.2 KB × 16 ≈ 0.73 TB → 0.76 s (0.5%).
- Upstream [PR #29846](https://github.com/ggml-org/llama.cpp/pull/29846) (fused q4_0 dequant into fattn-mma, closed) measured **qwen35 27B pp1024@d32768 q4_0: ub512 ×1.02, ub8 ×1.13, ub2 ×1.21** on RTX 3090. It helps small ubatches (the F1 territory) and barely helps prefill.

**Options:**
- (a) **Profile first:** `rocprofv3 --pmc` TCC hit / FETCH_SIZE on `flash_attn_ext_f16<256,256,32,2>` at d=65536.
  - KV f16 per KV head at 94k = 96 MB, and 3 head-pairs × 16 token tiles re-read it.
  - If the kernel is DRAM/IC-bound, a GQA-6 tile (all 6 Q heads × 8-16 tokens; ncols = 48/96, which needs new configs at fattn-mma-f16.cuh:161-164 and instances) cuts KV traffic 3×.
  - If it is WMMA-bound at ~47 TFLOPS (≈ the MMQ level), the gain is small.
- (b) Port in-kernel q4_0 dequant to LDS (no cp.async on HIP). It removes the 839 MB scratch (F1.6) more than it gains speed.
- Expected: 1.3-1.5× FA → −9…12 s at 94k (−6…8%), −1.1 s at 30k (−3%).
- Code: fattn.cu:541-720 (dispatch), fattn-mma-f16.cuh:130-216 (RDNA configs), fattn-common.cuh:982-1314.
- `GGML_HIP_ROCWMMA_FATTN` no longer exists ([PR #26046](https://github.com/ggml-org/llama.cpp/pull/26046) removed it; the tree has no fattn-wmma-f16.cu).

### F7. Matmul path on gfx1100 (dominant prefill cost)

**Dispatch** (ggml-cuda.cu:1909-1961 → mmq.cu:356-473):
- On RDNA3 (`amd_wmma_available`, common.cuh:356-358), MMQ is used for everything except Q2_K above 128 columns, **Q6_K above 128 columns on RDNA3_0** (mmq.cu:460-461), and IQ2_XS/S above 128.
- Those types fall to `ggml_cuda_mul_mat_cublas`, which dequantizes to f16 and runs a hipBLAS f16 GEMM with f16 output, then converts back (ggml-cuda.cu:1625-1704).
- MMQ uses **int8 WMMA** `__builtin_amdgcn_wmma_i32_16x16x16_iu8_w32` (mma.cuh:1464-1469, 1581-1585). Tiles come from mmq-config-rdna3.cuh: Q4_K/Q5_K/IQ4_XS use I=64, J≤128, 128 threads, `stream_k=false` everywhere, so the AMD stream-k path is unused (mmq.cuh:1430-1475).

**Upstream gfx1100 data** ([PR #17576](https://github.com/ggml-org/llama.cpp/pull/17576), W7900 = same die at 295 W, llama 8B pp2048):

| quant | MMQ, ub512 → ub2048 | hipBLAS | MMQ vs hipBLAS |
|---|---|---|---|
| Q4_K_S | 2109-2142 | 1932-1978 | +6-11% |
| IQ4_XS | 2201-2259 | ~1960 | +12-17% |
| Q6_K | 1450-1488 | 1930-1973 | −25%, so the hipBLAS choice for Q6_K is right |

- Throughput is **flat from ub512 to ub2048** on dense MMQ.

**Achieved rate:**
- 924 t/s × 48.6 GFLOP ≈ 45 TFLOPS overall. With the split below, matmul ≈ 50 TFLOPS (~40% of 123). A cross-check is llama 7B Q4_0 pp512 ≈ 3800 t/s on a 7900 XTX ([1337hero bench](https://github.com/1337hero/rx7900xtx-llama-bench-rocm/blob/main/README.md)), i.e. ≈ 49 TFLOPS.
- int8 WMMA has no rate advantage over f16 on RDNA3, so the headroom is in MMQ tiling and decode overhead, not the instruction rate.

**Cheap options:**
- (a) `ROCBLAS_USE_HIPBLASLT=1` (env only; mmq.cu:428-429 says it only crashes on CDNA3) for the Q6_K GEMMs.
- (b) The Q6_K dequant costs 4.25 G × (0.82 + 2) B ≈ 12 GB per ubatch, i.e. ~12.5 ms per 554-ms 512-ubatch: 2.3% for Q4_K_M, 1.2% for UD. A larger ubatch amortizes it (F8).
- (c) Tune Q6_K MMQ (mmq-config-rdna3.cuh:137-147, SRAM layout Q6_K) up to Q4_K-level and flip mmq.cu:461. Gain ≈ (2106/1973 − 1) × 17.5% + 2.3% ≈ **3.5% (Q4_K_M), ~1.8% (UD)**.
- (d) Deep MMQ work for 50 → 60 TFLOPS: LDS double-buffering, I=128 tiles at occupancy 2, stream-k for 5120-row outputs. That would be −15% prefill at ≤30k, but upstream already tuned these tables. High effort, uncertain.
- First measure kernel TFLOPS with `test-backend-ops perf -o MUL_MAT` at the model shapes (k=5120/6144/17408, n=512).

**Prefill time split, one 512-ubatch at ~6.6k context (554 ms measured):**
- matmul 24.9 TFLOP / ~50 TFLOPS ≈ **500 ms (90%)**
- GDN recurrence 12-18 ms (2-3%, F9)
- FA 0.66 TFLOP ≈ 14 ms (2.5%)
- small elementwise and quantize ops ≈ 20-30 ms (4-5%) [INFERENCE from bytes: ~200 MB per GDN layer, ~160 MB per FFN]
- Q6_K dequant 6-12 ms

At 94k context the FA term grows to ~9.5 TFLOP ≈ 200 ms per ubatch, giving ~750 ms per ubatch → 682 t/s predicted vs 666 measured.

### F8. ubatch size for the hybrid model

- The recurrent split constraint is `split_equal(n_ubatch, …, n_rs_seq+1)`, which keeps the last 1+n_rs_seq tokens in one ubatch (llama-memory-hybrid.cpp:84-89). With one sequence this does not depend on ub size, so correctness and recurrent state are unaffected.
- Dense MMQ is flat from ub512 to 2048 (F7). The hybrid-specific costs per ubatch shrink 4× at ub2048: the Q6_K dequant (≤2.3%), the f16 KV conversion (~1% at deep context), and per-ubatch kernel and launch overhead.
- **Expected 0-3%.**
- VRAM is tight. Estimate: weights 16.4 GiB + q4_0 KV 3.77 GB + f16 MTP KV 0.84 GB + recurrent with snapshots ~0.9 GB + FA scratch 0.84 GB + compute.
- ub2048 adds roughly 0.5-1 GB of compute buffer (FFN intermediates 3 × 2048·17408·4 B ≈ 430 MB) [INFERENCE].
- Pair it with F4 (−0.6 GB), then try `-ub 1024`, then 2048.

### F9. GDN prefill kernel

- **Implementation:**
  - `gated_delta_net_cuda` (gated_delta_net.cu:6-176) loops serially over tokens (`for t < n_tokens`, :72).
  - Grid = 48 V heads × 8 column blocks, 4 warps, state kept in registers (`s_shard`).
  - `//TODO: Add chunked kernel` at :189.
  - Prefill reaches it via the fused path: `cparams.fused_gdn_ch = true` (llama-context.cpp:236-237, 572-574; delta-net-base.cpp:425-447). The ggml-op chunked graph (`build_delta_net_chunking`, CS = 64, delta-net-base.cpp:16-61) is not used on HIP.
- **Measured cost** (rocprof trace above, 7,632 GDN calls): n=1 ≈ 3.7 µs, n=5 ≈ 10.7 µs, n=30 ≈ 23.6 µs, n=38 ≈ 29.4 µs. That is **≈ 0.5-0.75 µs per token per layer**.
  - Per 512-ubatch: 48 × 512 × 0.6 µs ≈ 15 ms = **2.7% of prefill**.
- **Options:**
  - (a) Software-pipeline the per-token loads: issue the loads of k/q/v/g/β for t+1 before computing t. The per-token chain is latency-bound at ~1500 cycles. Low effort; saves ~1-1.5% prefill and a little verify time [INFERENCE].
  - (b) Chunked WY/UT form ([Gated DeltaNet, arXiv 2412.06464](https://arxiv.org/abs/2412.06464); FLA) on WMMA. Ceiling ≈ 2% prefill; high effort. Upstream maintainers warn about the code size and performance tuning involved ([issue #22967](https://github.com/ggml-org/llama.cpp/issues/22967); am17an's TF32 branch beats the AR kernel only at larger batches). **Low priority.**

## 2. Avoid / does not apply

- **`--cache-reuse N`:** silently non-lossless for qwen35. The recurrent state is not edited when attention KV is shifted (F2).
- **`--ctx-checkpoints 2`** (QingYis recipe): in this tree spec rollback uses `spec_ckpt` and n_rs_seq, not these checkpoints. Lowering them only increases full re-prefills.
- **`GGML_CUDA_FORCE_MMQ`:** routes Q6_K to MMQ, which is 25% slower than hipBLAS at ≥256 columns on gfx1100 (PR #17576).
- **`GGML_CUDA_FORCE_CUBLAS`:** MMQ beats dequant+hipBLAS by 6-17% for Q4_K/IQ4_XS (PR #17576).
- **`GGML_HIP_MMQ_MFMA` / `NO_MMQ_MFMA`:** CDNA only (mmq.cu:427-444), no effect on gfx1100.
- **`GGML_HIP_ROCWMMA_FATTN`:** removed upstream (PR #26046).
- **`--swa-full`:** n_swa = 0, so it is auto-disabled.
- **kv-unified:** not relevant with `-np 1`.
- **f16 KV:** 16 × 204800 × 4096 B = 13.4 GB plus 16.4 GiB of weights does not fit in 24 GB.
- **Persistent f16 shadow of KV for prefill:** same VRAM problem, and conversion is only ~0.5-1% of prefill.
- **q8_0 KV:** 1.89× the KV bytes, so long-context decode floors are 1.89× higher. q4_0 already gets Hadamard rotation (llama-kv-cache.cpp:315-352).
- **INT4 WMMA (245 TOPs):** needs 4-bit activations, which is lossy.
- **KV eviction or sparse attention** (StreamingLLM, H2O, SnapKV, Quest): lossy.
- **`-b` > 2048:** no effect; the ubatch governs.
- **Chunked GDN as a big project:** ≤2-3% upside (F9); do it last.

## 3. Cheap measurements for the main agent (in order)

1. `ROCBLAS_USE_HIPBLASLT=1` with llama-bench pp512 (zero code; the Q6_K-heavy Q4_K_M model shows the effect best).
2. `-ctkd q4_0 -ctvd q4_0`: spec_sweep acceptance and ms per step at 1.7k/30k/94k, plus the VRAM line in the server log.
3. `-ub 1024`, then `-ub 2048`, on pp at 6.6k/30k/94k (watch VRAM).
4. Server `-lv 4`: read the `created context checkpoint … size = X MiB` line to get the real checkpoint size, then set `--cache-ram`, `--ctx-checkpoints` and `-cms`.
5. A timer around `set_input_kq_mask` (llama-kv-cache.cpp:1798) at 94k context (F5).
6. rocprof on a 30-token prompt with MTP vs without, to split the 80 ms MTP prompt overhead (F3).
7. `test-backend-ops perf -o MUL_MAT` and `-o FLASH_ATTN_EXT` at the model shapes (KV 32k/64k) to settle F6 and F7.
