# Cost of one MTP speculative step (Qwen3.8-27B UD-Q4_K_XL, Vulkan/RADV, RX 7900 XTX)

Scope: code reading only, no GPU runs. Code refs are to `~/llama-master` (HEAD `8af9de8f8`). Measured inputs:

- `/tmp/vkperf6.txt`: a Vulkan perf-logger dump of a 6-token forward. **It is not a real verify step.** The lm_head line is `q6_K m=248320 n=1`, so only one output row was produced, and there are 96 CPY ops (2 per GDN layer), which means `n_rs_seq = 0` and no rollback snapshots. It looks like a pp6/one-output run. The warm second block totals 34.76 ms.
- `~/qwen-opt/prof/mtp4/run_kernel_trace.csv`: a rocprofv3 trace of the ROCm build, MTP n=4, full 248k draft head. It shows real step structure and host gaps (re-analysed below).
- `~/qwen-opt/logs/*.log`, `NOTES.md`.

Labels: values marked [INFERENCE] are estimates; everything else is read from code or the files above.

---

## 0. What one step consists of (server, `draft-mtp`, n_max = 5)

Order of work per step, from `tools/server/server-context.cpp` and `common/speculative.cpp`:

1. **Verify.** `llama_process(ctx_tgt, 6 tokens)`, then `llama_synchronize` (server-context.cpp:4166-4170). One graph: 64 layers at 6 tokens, 6 output rows (lm_head 248320 × 6), h_nextn for all rows. With MTP, `n_rs_seq = n_max = 5` (common.h:403-408). Each GDN layer keeps K = 6 recurrent snapshots.
2. **MTP catch-up.** `common_speculative_process`, then `llama_process(ctx_dft, same 6 tokens, no outputs)` (speculative.cpp:1601-1635). The MTP layer runs at n=6 to fill its KV. All 6 tokens are re-evaluated, including tokens that will be rejected. Upstream marks this with `TAG_SPEC_AVOID_DRAFT_REEVAL` (server-context.cpp:4226).
3. **Target sampling on the CPU.** `common_sampler_sample_and_accept_n` (server-context.cpp:4423-4425) runs over 248320-entry logits rows and copies 6 × 248320 × 4 B = 6 MB of logits off the GPU. This overlaps with step 2 on the GPU.
4. **Five draft passes.** Serial `llama_process(ctx_dft, 1 token)` calls (speculative.cpp:1711-1814). Each pass waits for its result through `common_sampler_sample` (sync), then reads the 20 KB h row (`llama_get_embeddings_nextn_ith`). Draft sampling already runs on the GPU: `backend_sampling = true` is the default (common.h:335), and the chain is `top_k(10)` via `ggml_top_k` (speculative.cpp:1465-1477, llama-sampler.cpp:1483).
5. The server builds the next batch, then goes back to 1.

The `graphs reused` counter in the server log is per target context, about 1 per step (e.g. 148 over 400 tokens, sweep-server.log). The verify graph is therefore reused. The draft context alternates between n=6 (catch-up) and n=1 (draft) graphs, so its graph is rebuilt at least twice per step [INFERENCE: `gf_res_prev` holds only one graph, llama-context.cpp:1421-1465; ctx_dft reuse is not counted in the log].

---

## 1. Verify (6 tokens): what scales with token count, and why it is not 18 ms

### 1.1 How Vulkan executes n=6 matmuls
- `ggml_vk_mul_mat` (ggml-vulkan.cpp:7302) sends anything with `ne[1] <= mul_mat_vec_max_cols` to `ggml_vk_mul_mat_vec_q_f16`. That limit is 8 (ggml-vulkan-types.h:383). So 6 columns use one mul_mat_vec dispatch with a NUM_COLS=6 pipeline variant, and weights are read once. n=9 falls back to `mul_mm` tiles; this is the n=8 cliff in NOTES.
- `ggml_vk_should_use_mmvq` (6560-6642) returns `true` for every n>1 except Q6_K on non-Intel. That case is the "2-byte alignment" exclusion at 6567-6572. Result:
  - IQ4_XS, Q4_K, Q5_K, Q3_K, Q8_0, IQ4_NL: q8_1-quantized activations and the integer-dot MMVQ shader. The quantized y is cached across consecutive matmuls with the same src1 (`prealloc_y_last_tensor_used`, 14271-14273).
  - Q6_K (2.52 GB including `output.weight`): the float dequant shader.
- Rows per workgroup (2876-2897): RDNA3 MMVQ uses `rm_int_n = 4` rows/WG once the column count is ≥5 (line 2894). The float path uses `rm_kq = 2`.
- Workgroup size: AMD always gets `DMMV_WG_SIZE_SUBGROUP` (64 threads). The `LARGE` (256-thread) variant is chosen only for NVIDIA and Intel when M is small (5583-5597).
- Matvec has no split-K (split-K exists only for `mul_mm` and FA).

### 1.2 Measured matvec efficiency at 6 columns (`/tmp/vkperf6.txt`, warm block)
Weight bytes read per forward, excluding `token_embd` (gather only) and `blk.64`: **16.47 GB**. By type: Q5_K 7.93, IQ4_XS 3.13, Q6_K 2.52, Q4_K 2.35, IQ4_NL 0.28, Q8_0 0.12, Q3_K 0.12, IQ3_S 0.04 (from the GGUF). At 960 GB/s the floor is **17.2 ms**, not 18.3: `token_embd` (0.72 GB) is never streamed, and `blk.64` belongs to the drafts.

Matvec total is 27.84 ms, i.e. **592 GB/s on average (62 % of peak)**. Loss against a realistic 680 GB/s target is **3.6 ms**:

| shape | time | effective rate | loss vs 680 GB/s |
|---|---|---|---|
| `q8_0 m=48 k=5120` (ssm_alpha + ssm_beta, 96 calls) | 1.31 ms | **19 GB/s** | **1.27 ms** |
| `iq4_xs m=17408 k=5120` (46 calls) | 3.87 ms | 564 GB/s | 0.66 ms |
| `q5_K m=5120 k=6144` (ssm_out, 40 calls) | 1.60 ms | 542 GB/s | 0.32 ms |
| `q4_K m=10240 k=5120` | 1.25 ms | 542 GB/s | 0.25 ms |
| `iq4_xs m=5120 k=17408` | 1.35 ms | 561 GB/s | 0.24 ms |
| `q6_K m=5120 k=6144` (float path) | 0.98 ms | 555 GB/s | 0.18 ms |
| best cases: `q5_K 17408×5120` / `q6_K m=17408 n=6` / lm_head `q6_K n=1` | | 687 / 696 / 894 GB/s | |

Why m=48 is so slow: 6 columns means 4 rows/WG, so m=48 gives **12 workgroups of 64 threads on a 96-CU GPU**. The run is latency-bound at 13.6 µs per call.

### 1.3 Ops that scale with token count, and the GDN state path
- **GDN recurrence** (`gated_delta_net.comp`). There is one workgroup per (head, column-block), and the token loop runs serially inside the kernel (`for t < n_tokens`, line 121). Work grows with n_tokens, but the state stays in registers, so per-token cost is small. Measured: 8.5 µs per layer with no snapshots.
- **Rollback snapshots** (`n_rs_seq = 5`, so K = 6):
  - GDN writes K full states into its own dst tail (shader 173-181): 6 × 128×128×48×4 B = **18.9 MB per layer**.
  - `build_recurrent_attn` then `ggml_cpy`s that tail into `ssm_states_all` (delta-net-base.cpp:591-603): another **18.9 MB read + 18.9 MB written** per layer.
  - Before GDN, `build_rs` gathers the state with `ggml_get_rows` (llama-graph.cpp:3661): 3.15 MB read + 3.15 MB written per layer, then GDN reads it again.
  - Total state traffic per verify: about 66 MB × 48 = **3.2 GB**. With K = 1 (plain decode) it is about 0.9 GB.
  - The 96 MB Infinity Cache absorbs part of this. The HIP GDN kernel, which writes 5 snapshots straight into the cache because of CUDA fusion, takes 10.6 µs/layer.
  - [INFERENCE] On Vulkan without fusion, the snapshot path costs about **1.5–3 ms per verify**.
  - CUDA already fuses GDN → cache CPY (`ggml_cuda_try_gdn_cache_fusion`, ggml-cuda.cu:2843; PR [#23940](https://github.com/ggml-org/llama.cpp/commits/master?search=23940), commit `5a460dea9`). Vulkan does not; issue [#27193](https://github.com/ggml-org/llama.cpp/issues/27193) gives a full design and was closed as stale with no PR.
- **Conv-state snapshots.** `build_conv_state` issues **K = 6 separate `ggml_cpy`** per GDN layer (delta-net-base.cpp:504-521), which is **288 tiny dispatches per verify** (48 with n_rs_seq = 0). The HIP verify trace shows 253 `cpy` kernels with K = 5.
- **Flash attention.** 16 layers, 6 query rows; GQA 6 × 6 = 36 rows share K/V reads. 0.25 ms at n_kv = 256. Cost grows with context: q4_0 K+V is 1152 B/token/layer, i.e. about 18.4 KB/token per verify. That is ~0.5 ms at 20k context and ~2.3 ms at 100k [INFERENCE: bandwidth-bound].
- **Small ops** (non-matvec) in vkperf6: 6.9 ms of 34.8. The largest are:

  | op | count × time | notes |
  |---|---|---|
  | RMS_NORM_MUL(5120) | 127 × 10.3 µs = 1.31 ms | |
  | SCALE | 192 × 4.5 µs = 0.86 ms | 2 per layer are the `build_gdn_l2_norm` scale, models.h:14-17; the other 2 are build_rs `state_zero` and should be empty in steady server state [INFERENCE] |
  | GET_ROWS | 98 × 6.5 µs = 0.63 ms | state gathers |
  | CPY | 96 × 5.1 µs | |
  | ADD | 175 × 2.5 µs | |
  | RMS_NORM(128,16,6) | 96 × 3.3 µs | l2-norm of q and k |
  | SIGMOID / SOFTPLUS_MUL / SSM_CONV_SILU / CONCAT | each 0.17–0.27 ms | |

  The non-concurrent perf logger puts a timestamp and full barrier after every node (14622-14629), so these figures are inflated by roughly 1–2 µs/op.

### 1.4 Estimated real verify (server, short context)

| component | ms |
|---|---|
| matvec, 64 layers @ n=6 (incl. alpha/beta 1.3 ms) | 26.5 |
| lm_head 248320 × 6, Q6_K float path, ~1.04 GB at ~700 GB/s | 1.5 |
| small ops (≈1800 dispatches) | 4.5–5.5 |
| +240 extra conv-snapshot CPY dispatches | 0.5–0.8 |
| GDN K=6 snapshot write + snapshot CPY + state gather | 1.5–3 |
| **total GPU** [INFERENCE] | **≈33–36** (user's logger measurement: 33.6) |

Weight floor for the same work: 17.2 ms + 1.04 GB lm_head ≈ 18.3 ms. Gap ≈ 15 ms:

- matvec below peak: 26.5 + 1.5 − 18.3 ≈ 9.7 ms, of which 3.6 ms is recoverable at a realistic 680 GB/s and 1.3 ms of that is m=48
- small-op dispatch overhead: ~5 ms
- recurrent-state traffic: ~2 ms

---

## 2. Draft side

### 2.1 One draft pass (1 token, 64k head)
- MTP block `blk.64`: **351 MB**. Q6_K for eh_proj, q, o, ffn_up/gate/down; Q8_0 for k and v.
- Draft head: 65536 rows of `output.weight`, copied at load as **Q6_K, 275 MB** (llama-model.cpp:3045-3061).
- Read rate: both run on the n=1 float/Q6_K path, measured at 865–894 GB/s. **626 MB → ~0.72 ms.**
- Extra graph work (qwen35.cpp:654-665):
  - `ggml_fill(248320, −inf)` + `set_rows`
  - backend `top_k(10)` over all 248320 entries: Vulkan's tournament top-k, several passes (ggml-vulkan.cpp:11326-11457)
  - ~45 small dispatches (rms_norm ×5, rope ×2, FA over the MTP KV, sigmoid-mul, swiglu, adds)
- **GPU per pass ≈ 0.85–1.0 ms** [INFERENCE].
- **Host per pass, all serialized:**
  - `set_inputs` (token, pos, 20 KB h row, KV mask)
  - Vulkan re-records about 50 nodes, with several submits because `flops_per_submit` comes from the previous graph and the `almost_ready` fence fires at 80 % (14613-14618)
  - fence wait, then read back the 10 candidates and 20 KB of h
  - CPU sampler bookkeeping
  - Estimate: **~0.2–0.5 ms** [INFERENCE]. On ROCm the same sequence measured 30–70 µs of gap plus ~100 µs of input-upload copies per draft graph (trace below).
- For comparison, the ROCm trace with the full 248k head: draft graph wall 1.87 ms (busy 1.70; the 248k Q6_K head alone is 1.54 ms).

### 2.2 Catch-up pass (6 tokens, no lm_head)
351 MB at n=6 plus ~40 dispatches ≈ **0.6–0.8 ms**. The ROCm trace shows 0.67 ms wall.

### 2.3 Answers to the specific questions
- **Smaller draft vocab (32k).** It halves the head (275 → 137 MB), saving ~0.16 ms/pass, or ~0.8 ms/step. NOTES already measured it: 32k gave +7 % vs +7.5 % at 48–64k, so lost acceptance cancels the saving. **No.**
- **Cheaper head/MTP bytes without vocab loss.** Requantize the 64k draft head and `blk.64` from Q6_K to Q4_K or IQ4_XS: 626 → ~430 MB per pass, **−0.2 ms/pass → −1.0 ms/step**, plus −0.1 ms on catch-up. See item 5 in §5.
- **Draft sampling on the GPU.** Already on: `common.h:335` default true, and the `--spec-draft-backend-sampling` flag exists. With it on, `needs_raw_logits` is false, so the 1 MB logits row is not copied (llama-context.cpp:1954). Nothing more to gain except skipping the 248k fill + set_rows + top_k (item 10).
- **Graph rebuilds on ctx_dft.** About 2 per step (catch-up n=6 ↔ draft n=1). Each costs `build_graph` + `ggml_backend_sched_alloc_graph` + Vulkan `graph_optimize` on a ~60-node graph. That is small: ~0.1–0.3 ms per step [INFERENCE].
- **Fusing passes.** Two options:
  - (a) Merge catch-up with draft 1 (item 6).
  - (b) Unroll all 5 MTP steps into one graph with argmax/top-k and in-graph token-embedding `get_rows` (item 9). This removes 4 host round-trips.

---

## 3. Host/CPU overhead between graphs

### 3.1 Evidence from the ROCm trace
`~/qwen-opt/prof/mtp4/run_kernel_trace.csv`, re-analysed; median of 148 steps with 4 drafts, ROCm build, n=4, full head:

| item | value |
|---|---|
| step wall | **48.8 ms** |
| GPU busy | 37.6 ms |
| verify graph wall | 38.0 ms (busy 30.1; ~2428 kernels, HIP launch gaps) |
| gaps **between graphs** | **2.08 ms per step** (p90 2.5) |
| — after verify | 0.41 ms (sync, output extraction, launch of catch-up) |
| — after catch-up | **0.71 ms** (p90 1.0) |
| tiny H2D input-upload segments (`__amd_rocclr_copyBuffer`, 1–5 copies each) | 10 per step, **0.70 ms** wall |
| intra-draft-graph gaps | 4 × 0.17 ms |

The gap after catch-up is CPU target sampling over 248k-vocab rows that the 0.67 ms catch-up does not hide. Implied CPU sampling ≈ 1.4 ms per step [INFERENCE].

The same CPU-side code runs on Vulkan (inputs, sampling, speculative loop). Expect **~2–3.5 ms per step of GPU-idle host time** on Vulkan as well [INFERENCE; measure with §6].

### 3.2 Vulkan-specific behaviour
- Every `graph_compute` re-records every node (`ggml_backend_vk_graph_compute`, 14205-14707 → `ggml_vk_build_graph`). Command buffers come from a pool and are recycled (1124-1137), but are **never replayed**.
- Descriptor writes are skipped when the bindings are identical (`GGML_VK_DISABLE_DESCRIPTOR_REUSE`, ggml-vulkan-common.h:292). That is the only cross-call caching.
- For the 1800-node verify, recording overlaps GPU execution. The first submit goes out after about `last_total_flops/40` (doubling for the first 3 submits) or 100 nodes (`GGML_VK_MAX_NODES_PER_SUBMIT`, 4265-4270), so recording is hidden. For the ~50-node draft graphs it sits on the critical path.
- Input uploads: device buffers prefer ReBAR host-visible VRAM (ggml-vulkan-buffers.cpp:214-223), so `set_tensor` is a plain memcpy when ReBAR is on (buffers.cpp:502-511). Without ReBAR, every input upload is a separate submit and **fence wait** (buffers.cpp:512-533). Check that ReBAR is active.
- Reads go through a GPU copy into host-cached staging (buffers.cpp:620-629).

### 3.3 Graph-level command-buffer reuse (question 4)
**Not supported** in this tree; I found no graph-keyed cache. Upstream's closest work is async `graph_compute` + `get_tensor_async` (PR #17158, commit `38eaf32af`).

---

## 4. Estimated breakdown of one step (Vulkan, prose, short context) [INFERENCE except where noted]

| part | ms | basis |
|---|---|---|
| verify GPU: matvec 26.5 + lm_head 1.5 | 28.0 | vkperf6 + lm_head scaling |
| verify GPU: small ops + conv-snapshot CPYs | 5.0–6.3 | vkperf6 + 240 extra CPYs |
| verify GPU: GDN snapshots + state copy/gather | 1.5–3.0 | byte count §1.3 |
| verify host (sync, 6 MB logits D2H, h copy) | 0.4–0.8 | ROCm gap after verify 0.41 |
| catch-up MTP pass (GPU) | 0.6–0.8 | 351 MB @ n=6; ROCm 0.67 |
| CPU target sampling not hidden by catch-up | 0.5–1.0 | ROCm gap 0.71 |
| 5 draft passes, GPU (626 MB + ~50 dispatches + top-k) | 4.3–5.0 | 0.72 ms weights + small ops |
| 5 draft passes, host (inputs, record, submit, fence, readback) | 1.0–2.5 | ROCm 0.1–0.25 per pass; Vulkan [INFERENCE] |
| **sum** | **≈41–47** | measured 44–46 |

Summary: verify ≈ 75 %, drafts ≈ 13–16 %, host idle ≈ 6–10 %.

The arithmetic limit is plain. At ~2.9 tokens/step on prose, t/s = 2.9 / step. A 45 → 36 ms step gives 64 → 80 t/s. A 2× jump needs higher acceptance, not cheaper steps.

---

## 5. Ranked optimizations (ms per ~45 ms step; prose t/s at 2.9 tokens/step)

| # | change | where | saves/step | effort | notes |
|---|---|---|---|---|---|
| 1 | **Fix small-M matvec on AMD** (ssm_alpha/ssm_beta m=48): use 1 row/WG + 256-thread WG when m is small, or route m < ~512 to the float path. Also concat alpha+beta into one m=96 weight at load. | `ggml_vk_should_use_mmvq` (6560), `rm_int_n` (2894), WG heuristic in `ggml_vk_get_dequantize_mul_mat_vec` (5583); model side qwen35.cpp:372-380 | **−0.9…−1.1 ms** verify; also −0.3…−0.5 ms in plain decode (96 × q8_0 m=48 at n=1) | low | Matches NOTES ("za mało grup roboczych przy 48 wierszach"). Diagnostic: `GGML_VK_DISABLE_MMVQ=1` moves q8_0 to the float path at 1 row/WG (other types will regress). |
| 2 | **One strided CPY for the K conv-state snapshots** instead of K = 6 (src: overlapping-window 4D view of `conv_input`, slot stride = 1 element; dst stride = `mem_size*row_size`), or write them in SSM_CONV. | delta-net-base.cpp:502-521 | **−0.5…−0.9 ms** (−240 dispatches) | low–med | Graph-only change; helps every backend. Check that the Vulkan generic CPY accepts the overlapping-stride src view. |
| 3 | **GDN → recurrent-cache fusion on Vulkan** (port of CUDA `ggml_cuda_try_gdn_cache_fusion`): GDN writes the K snapshots straight into `ssm_states_all` and the CPY is skipped. Optionally read s0 from the cache row (`s_copy`) instead of the `build_rs` `get_rows` gather. | `gated_delta_net.comp` (extra binding + slot stride), `ggml_vk_gated_delta_net` (10219), fusion matcher in `ggml_backend_vk_graph_compute` | **−1.2…−2.2 ms** verify (−1.8 GB copy traffic, −48 dispatches); −0.3…−0.5 ms in plain decode | medium | Design in [#27193](https://github.com/ggml-org/llama.cpp/issues/27193); Vulkan `graph_optimize` may put nodes between GDN and CPY, so scan forward. Snapshot-free rollback (keep per-token k/v/g/β, replay on reject) would also remove most of the 18.9 MB/layer writes; that is SpecAlgorithms' topic. |
| 4 | **Fuse GDN elementwise prologue into the GDN shader**: l2-norm of q/k (`rms_norm` + `scale`, models.h:14-17), `sigmoid(beta)`, `softplus(alpha+dt)*A`. About 7 fewer dispatches per layer. | gated_delta_net.comp + matcher; or a new fused op | **−0.8…−1.3 ms** verify; −0.6…−1.0 ms plain decode | medium | Lanes already hold the full q/k row (`k_reg`/`q_reg`), so the norm is one more `reduce_partial`. |
| 5 | **Requantize the draft head (64k) and the `blk.64` MTP layer Q6_K → Q4_K/IQ4_XS**: 626 → ~430 MB per pass. | head: requantize in `llama_model::set_draft_head_vocab` (llama-model.cpp:3045-3061); MTP layer: `llama-quantize --tensor-type 'blk\.64\..*=q4_k'` leaves the main 64 layers byte-identical | **−1.0…−1.2 ms** (5 × 0.2 + catch-up 0.1) | low | Changes the drafter only, which is allowed. Acceptance must be re-measured. |
| 6 | **Merge catch-up with draft #1**: process only accepted tokens + the new token in one ctx_dft pass and take the draft-1 logits from it. | speculative.cpp `process()`/`draft()` (1557-1830), server-context.cpp:4226 TODO | **−0.8…−1.3 ms** (one MTP pass + one sync) | medium | Loses the catch-up/CPU-sampling overlap unless #7 is done too. |
| 7 | **Target-side GPU sampling** (`-bs` / `--backend-sampling`): no 6 MB logits D2H, no CPU sorting of 248k rows. | flag; `n_outputs_max_per_seq` is already set to n_max+1 for ctx_tgt (server-context.cpp:48, 1117) | **−0.5…−1.5 ms** | zero to test | Disabled when grammar or a reasoning budget is set (sampling.cpp:422-431). Samplers without `backend_apply` (dry, xtc, typical, top-n-sigma) cannot be offloaded, so check the request sampler chain. Only valid for greedy-match verify, not the probabilistic rejection path. |
| 8 | **6-column MMVQ tuning** for IQ4_XS (3.1 GB at ~560 GB/s), Q4_K 10240-row, Q5_K k=6144 (ssm_out at 542), Q6_K float path: target ~680 GB/s. | `mul_mat_vecq*.comp`, row/WG tables 2876-2897 | **−2.0…−2.4 ms** (3.6 ms total loss minus #1) | high | Same direction as the HIP mmvq work in NOTES. |
| 9 | **Single-graph 5-step MTP draft** (unrolled MTP layer, argmax/top-k on GPU, in-graph token-embedding gather, KV writes at pos0+i) | new graph type in qwen35.cpp `graph_mtp` + speculative.cpp | **−1.0…−2.0 ms** (4 fewer host round-trips + 4 fewer rebuilds/records) | high | Greedy drafts only; greedy is the current default. |
| 10 | **Top-k on the 64k sub-logits**, then map ids through `draft_head_ids`, instead of `fill(-inf, 248k)` + `set_rows` + top-k over 248k | qwen35.cpp:654-665 + sampler id remap | −0.1…−0.2 ms | low–med | |
| 11 | **Vulkan env A/B**: `GGML_VK_MAX_NODES_PER_SUBMIT` (default 100), `GGML_VK_ALLOW_GRAPHICS_QUEUE` (comment: "can increase performance on RADV", 4289-4291), `GGML_VK_DISABLE_GRAPH_OPTIMIZE`, `GGML_VK_FA_SPARSE_DISABLE` (long context) | env only | ±0–0.5 ms | zero | |
| 12 | **Command-buffer replay** for reused graphs | ggml-vulkan.cpp graph_compute | −0.3…−0.8 ms (draft side) | high | Not present; low priority. |

**Cumulative estimates:**
- Low/medium-effort items #1–#7: −5.7…−9.5 ms per step. 45 → ~36–39 ms means **prose ~74–80 t/s, code (4.1 tokens/step) ~105–114 t/s**.
- Plus #8 + #9: 45 → ~32–34 ms, prose **≈85–90 t/s**.
- Plain decode also gains about 1.5–2.5 ms/token from #1, #3 and #4.

---

## 6. Profiling commands for the parent

### 6.1 Per-graph GPU op breakdown of a real step (verify, catch-up, draft)
The perf logger prints one block per `graph_compute` to **stderr**, not to `--log-file` (ggml-vulkan.cpp:5261-5273, 16424-16466). It also forces a fence wait per graph and adds a timestamp + barrier per node, so small-op times are inflated and CPU/GPU overlap is lost.

```bash
cd ~/qwen-opt
GGML_VK_PERF_LOGGER=1 GGML_VK_PERF_LOGGER_FREQUENCY=1 PORT=8090 LOG=/tmp/vkperf-srv.log \
  ./run-llm.sh qwen mtp vulkan 2> /tmp/vkperf-steps.txt &
until curl -sf http://127.0.0.1:8090/health >/dev/null; do sleep 1; done
curl -s http://127.0.0.1:8090/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"Napisz krótkie opowiadanie o kocie."}],"max_tokens":128,"temperature":1.0}' >/dev/null
pkill -f 'llama-server.*--port 8090'
python3 - /tmp/vkperf-steps.txt <<'EOF'
import re, sys, statistics as S, collections
blocks = open(sys.argv[1]).read().split('Vulkan Timings:')[1:]
kind = collections.defaultdict(list); ops = collections.defaultdict(lambda: collections.defaultdict(list))
for b in blocks:
    m = re.search(r'Total time: ([\d.]+) us', b)
    if not m: continue
    if 'GATED_DELTA_NET' in b and 'MUL_MAT_VEC' in b and ' n=6 ' in b: k = 'verify'
    elif 'GATED_DELTA_NET' in b: k = 'prefill/other-target'
    elif 'm=65536 n=1' in b: k = 'draft'
    elif ' n=6 ' in b: k = 'mtp-catchup'
    else: k = 'other'
    kind[k].append(float(m.group(1)))
    for o in re.finditer(r'^(.*?): (\d+) x [\d.]+ us = ([\d.]+) us', b, re.M):
        ops[k][o.group(1)].append(float(o.group(3)))
for k, v in kind.items():
    print(f'== {k}: {len(v)} graphs, median total {S.median(v)/1e3:.2f} ms')
    for name, vals in sorted(ops[k].items(), key=lambda x: -S.median(x[1]))[:20]:
        print(f'   {S.median(vals)/1e3:7.3f} ms  {name[:100]}')
EOF
```
What to check:
- `CPY` count and time in **verify**: expect ~336 CPYs (288 conv + 48 ssm) and multi-µs ssm CPYs. This confirms items #2 and #3.
- `GATED_DELTA_NET` µs per layer with K = 6 vs 8.5 µs in vkperf6.
- `MUL_MAT_VEC q8_0 m=48`.
- Draft-graph total vs the ~0.9 ms estimate.

Second run with less distortion (timestamps only at real sync points; nodes grouped): add `GGML_VK_PERF_LOGGER_CONCURRENT=1`.

### 6.2 Wall time spent in drafting (host + GPU) per step
`-lv 4` (trace) makes the server print, per request, `spec ... statistics draft-mtp: #calls(b,g,a) = … dur(b,g,a) = <begin>, <draft>, <accept> ms` (speculative.cpp:3040-3083, called from server-context.cpp:721). It also prints `backend_sampling=1` for the draft at init (speculative.cpp:1443).

Run `run-llm.sh` with the extra arg `-lv 4`, e.g. by temporarily appending it to the final `"$bin" …` line, or start `llama-server` by hand with the same flags. Then:

```bash
grep -E 'statistics|backend_sampling' ~/qwen-opt/logs/latest.log
```
- `t_draft / #calls(g)` = wall ms for the 5 draft passes per step.
- Compare it with 5 × the draft-graph GPU total from §6.1; the difference is host overhead.

### 6.3 CPU hotspots during a bench
Not GPU-heavy; profiles the CPU while `serve_bench.py` or `spec_sweep.py` runs:

```bash
perf record -F 999 -g -p "$(pgrep -f 'llama-server.*--port 8080')" -- sleep 15
perf report --no-children --sort symbol | head -60
```
Look for: `llama_sampler_*`, `std::__introselect` / `partial_sort` (target sampling), `common_sampler::set_logits`, `ggml_vk_build_graph`, `ggml_backend_sched_*`, `memcpy`, `vkQueueSubmit` / `ioctl`.

### 6.4 Sync, submission and memory facts
- `GGML_VK_SYNC_LOGGER=1`: prints every barrier and node (ggml-vulkan.cpp:12299-12339). Use it to count barriers in the draft graph.
- `GGML_VK_MEMORY_LOGGER=1`: shows whether buffers land in DEVICE_LOCAL|HOST_VISIBLE, i.e. whether ReBAR is active. `vulkaninfo --summary` / `vulkaninfo | grep -A4 memoryHeaps` should show a ~24 GB HOST_VISIBLE device-local heap.

### 6.5 A/B knobs (one env at a time with `spec_sweep.sh`)
```
GGML_VK_MAX_NODES_PER_SUBMIT=400   (and 2000)
GGML_VK_ALLOW_GRAPHICS_QUEUE=1
GGML_VK_DISABLE_GRAPH_OPTIMIZE=1   (expect worse; sanity check)
GGML_VK_DISABLE_FUSION=1           (expect worse; sanity check)
GGML_VK_DISABLE_MMVQ=1             (diagnostic for the m=48 issue only)
GGML_VK_FA_SPARSE_DISABLE=1        (only matters at long context)
--no-spec-draft-backend-sampling   (should be slower; confirms GPU draft sampling helps)
-bs / --backend-sampling           (target-side GPU sampling, item #7)
```

### 6.6 Optional timeline
[INFERENCE: not verified on this Mesa build] RADV can write Radeon GPU Profiler captures with `MESA_VK_TRACE=rgp` (plus `MESA_VK_TRACE_PER_SUBMIT=1` for compute-only apps on recent Mesa). Use it to see GPU-idle gaps between submits.

---

## 7. Files and evidence index
- Step loop:
  - server-context.cpp:4166-4241 (verify + process), 4423-4471 (accept), 3404 (draft)
  - speculative.cpp:1557-1663 (catch-up), 1666-1830 (draft loop), 1832-1845 (accept)
- Rollback snapshots: common.h:403-408 (`n_rs_seq = n_max`); delta-net-base.cpp:479-522 (conv), 546-605 (GDN + CPY); llama-graph.cpp:3635-3676 (`build_rs` get_rows gather); llama-memory-recurrent.cpp:1368-1386.
- Vulkan:
  - graph_compute 14205-14707
  - build_graph sync logic 12205-12326
  - graph_optimize 14709-15094
  - mmvq choice 6560-6642
  - rows/WG 2876-2897
  - WG-size heuristic 5583-5606
  - GDN dispatch 10219-10274; shader `vulkan-shaders/gated_delta_net.comp`
  - top-k 11326-11457
  - env knobs 4016-4026, 4063-4101, 4187, 4193-4216, 4265-4270, 4290, 4889-4922, 5212, 5261-5272, 8152
- CUDA GDN cache fusion: ggml-cuda.cu:2841-2903, 3577-3581.
- Draft head construction: llama-model.cpp:3029-3075; MTP graph qwen35.cpp:500-673.
- Data: `/tmp/vkperf6.txt` (6-token, 1-output, no-snapshot forward); `~/qwen-opt/prof/mtp4/run_kernel_trace.csv` (ROCm step timeline).
