# Alternative engines and the speculative-decoding frontier for Qwen3.8-27B on one RX 7900 XTX

Slice: RoadmapResearch.EnginesDrafters. Date: 2026-10-12. Research only: nothing was built, nothing ran on the GPU, nothing over 50 MB was downloaded.
Baseline used throughout (from the task and `~/qwen-opt/NOTES.md:188-199`):
- ROCm, MTP n=4: step 41.8 ms, 74.5 t/s mixed at T=1. Chat is about 60 t/s and code about 80-90.
- At T=0 with ctx 1.7k: 78.6 t/s.
- Prefill: 750-924 t/s up to 30k, then 666 t/s at 94k (142 s).

## How the gain numbers are computed

ROCm step model, fitted to the NOTES measurements:

| MTP n | step (ms) | t/s |
|---|---|---|
| 3 | 38.4 | 74.4 |
| 4 | 41.8 | 74.5 |
| 5 | 44.5 | 73.8 |

From this:
- T(k) ≈ 29.3 + 3.05·k ms for k MTP drafts.
- 3.05 ms is one verify column (c_v) plus one MTP pass.
- c_v on ROCm has not been measured. Vulkan gave 1.52 ms/column (`research/algorithms.md:26`). I use **c_v ≈ 1.4 ms** [INFERENCE].
- An n-gram draft costs no MTP passes, so T_ng(k) ≈ 29.3 + 1.4·k ms [INFERENCE]: T_ng(4) ≈ 34.9 ms and T_ng(7) ≈ 39.1 ms.
- Verifies of 9 or more tokens fall off the 2-8-column MMVQ fast path (`research/algorithms.md:43`).

---

## 0. Ranked findings (expected impact on this setup)

| # | Finding | Workload hit | Expected gain vs MTP n=4 | Effort | Risk | Lossless? |
|---|---|---|---|---|---|---|
| 1 | **Hybrid `ngram-mod`/`ngram-map-k` + `draft-mtp`**, n-gram drafts capped at ≤7 tokens and `n_rs_seq` decoupled from the MTP n_max (§3) | code edits, verbatim rewrites, quotes | code edit with 50-80% copied tokens: **+23 … +75%** (≈104-149 t/s vs 85). Agentic: +5-20%. Chat: ≈0 | config + ≈10-30 LOC | low (wrong n-gram drafts pre-empt MTP; needs a min-length gate) | yes (deterministic drafts, sample-and-match verify) |
| 2 | **Exact prefix/state reuse** for long documents and agent loops: checkpoints, `--cache-ram`, slot save/restore (§4) | long-doc follow-ups, agent turns | 94k-doc follow-up: **165 s → ≈23-25 s E2E** (prefill 142 s skipped; restore ≈0.1-0.5 s) [INFERENCE] | config + verification | low (template must keep the prefix byte-stable) | yes, up to ubatch-split kernel noise |
| 3 | **Per-language MTP head self-distillation.** New evidence: KaedeTai zh head, +5.8 pp acceptance on zh with EN/code flat (§2) | PL prose and chat | PL: **≈ +6-9%** [INFERENCE: +0.058×4 drafts ≈ +0.23 tok/step on ≈2.8] | high (already planned) | medium | yes |
| 4 | **Deeper drafts for code/recall**, only if ROCm verify(9-16) is cheap. rdna-boosts adaptive MTP at ceiling 12: code +28%, recall +61%, prose +13% vs fixed n3 (RDNA4) (§3.5) | code, recall | 0 … +30% on code. Unknown until ROCm verify(9-16) is measured | measurement first; then multi-column MMVQ to 16 (high) | medium (bit-exactness changes across kernel families) | yes, within kernel noise |
| 5 | **Upstream cherry-picks** (§1.3): #30103 FA race fix (correctness), #30139 in-place recurrent state read (−48 kernels per graph, ≈0.2-0.35 ms/step), #30329 realloc counter (diagnostic), #29353 GDN chunked prefill (+7% prefill on RDNA3.5), and a `ggml_cont` removal like #30198 for `qwen35.cpp` | all | decode ≈ +0.5-1.5%; long-prompt prefill ≈ +5-7% [INFERENCE] | low-medium | low (#29353: a fork using a chunked GDN was found non-deterministic, §1.1) | yes, within noise |
| 6 | Sliding-window (SWA) KV for the MTP layer: draft context only | long ctx | prefill ≈ +2-5% at ≥30k, decode ≈ +1-2% at 94k [INFERENCE] | medium | acceptance on long-doc quoting may drop; measure | yes (drafts only) |
| 7 | Polish-aware 64k draft-vocab ranking (KoDraft idea, §2) | PL | ≤ +1-2% (only 3.5% of PL tokens fall outside the 64k list, `NOTES.md:161`) | low | none | yes |

**Engine verdict: do not switch.** No alternative engine has published or reproduced numbers on a 7900 XTX that come near 74.5 t/s at T=1 for this model (§1.1). The best external number is 63.5 t/s greedy (hipEngine), and its MTP mode loses to its own autoregressive (AR) decode on 128-token outputs.

---

## 1. Alternative engines (question 1)

### 1.1 Measured on a 7900 XTX / gfx1100 with Qwen3.8-27B

The only head-to-head on this exact GPU and model is hipEngine's comparison artifact: https://github.com/shisa-ai/hipEngine/blob/main/benchmarks/results/2026-09-08-rx7900xtx-engine-comparison.json (fetched and parsed).

Setup: Q4_K_M 17.1 GB, BF16 KV, greedy, 10 prompts covering code, EN and JA.

| Engine (same host, gfx1100) | pp512 t/s | tg t/s @512 / @8192 | MTP K3, 24-token outputs | MTP K3, 128-token outputs |
|---|---|---|---|---|
| hipEngine (shisa-ai, HIP-native, AGPL) | 985 | 34.3 / 29.8 | **63.5** (1.77× AR) | **30.4 (0.86× AR, a regression)** |
| nasone32 `llama.cpp-RDNA3-7900xtx-opt` | 912 | 36.7 / 35.7 | 58.6 | 44.5 |
| llama.cpp "strix" fork head `5f851647` | 847 | 32.6 / 29.5 | 47.7 | 50.2 |
| **ours** (UD-Q4_K_XL, KV q4_0, MTP n=4, 64k head) | 750-924 (server) | — | 78.6 at T=0, 74.5 at T=1 | same |

Other gfx1100 data points:
- hipEngine README (W7900 = gfx1100 at 864 GB/s): Qwen3.8-27B Q4_K_M reaches 30.8 t/s AR and 39.7 t/s MTP. https://github.com/shisa-ai/hipEngine (README "Performance").
- hipEngine has a trained KV-eviction route (DMS, which is lossy) that reaches 232k context on 24 GB.

### 1.2 Status by engine

**hipEngine** (shisa-ai, v0.7.0 alpha, 2026-10-06)
- qwen35/GDN: yes, Qwen3.5/3.6/3.8 GGUF.
- MTP/spec: MTP, but production defaults to AR. Strict C1/K3 MTP is "qualified" only for ≤1,024-token context.
- Measured on gfx1100: see §1.1. Slower than ours.
- Verdict: **avoid** (slower). Ideas worth noting: radix prefix cache over the hybrid state, and an n-gram replay off by default because it was not worth it on novel text.

**ik_llama.cpp**
- qwen35/GDN: Qwen3.5/3.6/3.8 MTP (PR 1698/1745/2369), fused delta-net, DFlash/DSpark, `suffix` decoding (PR 1646). Low-perplexity Q4_0 KV (PR 1547/1556) changes numerics.
- Measured: none on ROCm.
- Source: README says "The only fully functional and performant compute backends are CPU … and CUDA … Please do not enter issues related to ROCm" (https://github.com/ikawrakow/ik_llama.cpp). Also "Do not use … Unsloth `_XL`" models, and ours is UD-Q4_K_XL.
- Verdict: **avoid** (no ROCm). The suffix-decoding results are used in §3.

**vLLM ROCm**
- qwen35/GDN: the Triton FLA kernels run on gfx1100 (per AMD-AIM's SGLang doc, which uses the same `fla/` kernels).
- Spec: MTP exists. A GDN+MTP engine bug is reported in vLLM 0.27.x (https://huggingface.co/Avuja/Qwen3.8-27B-int4-AutoRound). "vLLM MTP collapses on chunked prefill" (https://github.com/tsarihan/qwen3.8-27b-rtx5090-playbook).
- Measured: an RDNA3 W4A16 kernel is merged (#41394). Its only numbers are TP=2 on two 7900 XTX at concurrency 100: TPOT 28 ms at 8 seqs. **No batch-1, single-GPU number exists.** https://github.com/vllm-project/vllm/pull/41394
- Fit: GPTQ int4 27B uses ≈19 GB (SGLang on W7900, below), so 200k context does not fit. RDNA3 has no FP8 hardware for a cheaper KV cache.
- Verdict: **avoid**.

**SGLang ROCm (AMD-AIM `sglang-radeon`)**
- qwen35/GDN: works on gfx1100. HIP graph capture hangs (sglang#30245), so it must run with `--disable-cuda-graph`.
- Measured: 1× W7900 GPTQ-Int4 at concurrency 4 gives **TPOT 54.3 ms** and 47.3 t/s aggregate. https://github.com/AMD-AIM/sglang-radeon/blob/main/docs/qwen3.8-27b.md
- Verdict: **avoid** (no graphs, so batch-1 overhead is high).

**ExLlamaV3**
- qwen35: Qwen3.5 is supported on CUDA.
- ROCm port: PRs #441/#442/#443 were **closed unmerged** (2026-10-03). DFlash2 is excluded under HIP (`dflash2.cu` is CUDA-only).
- Measured: the old ROCm PR #283 reports Qwen3.8-27B 4.0 bpw at **≈15 t/s decode and ≈500 t/s prefill** on gfx1100. https://github.com/turboderp-org/exllamav3/pull/283, https://github.com/turboderp-org/exllamav3/pull/441
- Verdict: **avoid**.

**BeeLlama.cpp (Anbeeld)**
- qwen35: inherits upstream.
- Spec: adds KVarN KV quantization, a precision tail (recent tokens kept in F16), and an adaptive depth "profit controller" for **DFlash1 only**. DFlash2 depth is fixed.
- Measured: none on HIP. Its docs say HIP routes are "source-policy verified pending … AMD hardware reports; no ROCm performance claim". https://raw.githubusercontent.com/Anbeeld/beellama.cpp/main/docs/beellama-features.md
- Verdict: **avoid** as an engine. The precision-tail idea is in §4.

**nasone32 RDNA3 fork**
- Spec: `draft-mtp-adaptive`, plus a chunked BF16/WMMA GDN prefill.
- Measured: §1.1. hipEngine found two defects in it:
  - its default chunked GDN path is **non-deterministic under greedy decoding**;
  - adaptive mode is silently disabled by default (minimum 3 = maximum 3).
- Sources: https://github.com/nasone32/llama.cpp-RDNA3-7900xtx-opt, https://raw.githubusercontent.com/shisa-ai/hipEngine/main/docs/campaigns/QWEN38-STRIX-HALO-EXTERNAL-SURVEY.md
- Verdict: **avoid** as an engine. Mine it for ideas only, and verify bit-exactness before taking any of them.

**stew675 `llama-cpp-rdna-boosts`** (16 `git am` patches on upstream `a55e952b8`, 2026-10-03)
- What it contains: adaptive MTP (§3.5); a gfx11 chunked GDN prefill; native q8_0/bf16 K/V in FlashAttention (FA) (block 15 V4/V5, opt-in); q8_1 quantize-cache fusions. Most patches were measured on RDNA4.
- Source: https://github.com/stew675/llama-cpp-rdna-boosts
- Verdict: a **source of patches**, not a replacement engine. Block 15 V4 (native quantized K/V in FA) is directly relevant to the in-progress GQA FA work.

**PurHur `llama.cpp-qwen35-rocm`** (gfx1151)
- What it contains: GDN occupancy tuning; the q/k L2-norm fused into the GDN kernel (one kernel fewer per GDN layer).
- Source: https://github.com/PurHur/llama.cpp-qwen35-rocm/blob/master/docs/GDN_TUNING.md
- Verdict: an idea for the kernel-fusion work (HipLevers' slice).

**Lemonade**
- Ships upstream llama.cpp ROCm nightlies built with TheRock; no qwen35-specific changes. https://github.com/lemonade-sdk/llamacpp-rocm
- Verdict: **no delta** over our fork.

**Ollama**
- qwen35 arch is supported (https://ollama.com/library/qwen3.6:27b shows `arch qwen35`). No MTP or speculative decoding was found in searches.
- Verdict: **avoid**.

**MLC-LLM, tinygrad**
- No evidence of qwen3_5/GDN support was found in searches.
- Verdict: **avoid** (no evidence).

### 1.3 Upstream llama.cpp after our base

Our base `e60eff95f` is #30217, dated 2026-10-09. I listed all 60 PRs merged since then (GitHub search API, `merged:>=2026-10-09`) and checked each one with `git log --grep`.

**Merged after the base and not in our tree:**

| PR | Title | Relevance | Expected gain | Action |
|---|---|---|---|---|
| **#30103** (2026-10-10) | CUDA/HIP: fix race in `flash_attn_ext_f16_process_tile` when `nbatch_combine != DKQ/2` | One-line `__syncthreads` fix. It was found on gfx1201 (issue #29314). On gfx1100 the MMA FA kernel is chosen whenever `Q->ne[1]·gqa_ratio_eff > 16` at D=256 (`fattn.cu:700-703`). For qwen35, gqa_ratio_eff = 2 (`fattn.cu:667-671`), so this covers **prefill and any verify of ≥9 tokens**. Our tree still has `if (np > 1)` at `fattn-mma-f16.cuh:1775`. | correctness (possible nondeterminism in prefill); ≈0 perf | **cherry-pick** |
| #30223 (2026-10-09) | keep the backend sampling graph static across ubatches | With spec decoding `n_outputs_max_per_seq > 1`. Without it, the sampling graph is rebuilt smaller and then reallocated when the output count changes. | Removes graph re-reservations when the verify width varies [INFERENCE: size unknown] | cherry-pick together with #30329 and measure |
| #30329 (2026-10-12) | report compute graph reallocations during inference | Adds `graph reallocs = same/changed` to the perf print. Shows directly whether the spec loop (verify widths 1..5, draft passes) re-reserves buffers. That would be a candidate source of the 2.08 ms host gaps between graphs. | diagnostic | **cherry-pick first** |
| #30160 | graph: reorder get_rows for embeddings | Mainly affects mixed or multimodal batches | ≈0 for text | skip |
| #29807 | Remove redundant copies after SSM_SCAN | Mamba only; GDN got the same fix in #23940 (already in tree, `5a460dea9`) | 0 | skip |
| #30257, #30095 | mtmd MTP; `examples/speculative` | n/a | 0 | skip |

**Open upstream PRs worth taking or watching** (updated after 2026-10-01):

| PR | What | Gain for us | Note |
|---|---|---|---|
| **#30139** | graph: read recurrent states in place (a view instead of `ggml_get_rows` copy) | "removes a 3MB read and a 3MB write per linear attention layer per token … 209 µs on a 27B". That is −48 copy kernels per graph, so ≈0.2-0.35 ms per spec step (+0.5-0.8%). | Our tree still copies at `src/llama-graph.cpp:3661`. Graph-only change, +58/−7. |
| **#29353** | cuda, hip: GDN chunked kernel (prefill) | Qwen3.8-27B: +11% on Blackwell, **+6.8-7.0% on Strix Halo (RDNA3.5)**. On a 94k prompt, GDN is the non-attention part, so long-doc E2E gains ≈ +3-6% [INFERENCE]. | Check bit-exactness first; the nasone32 chunked GDN was non-deterministic (§1.2). |
| #30198 | remove redundant `ggml_cont` before sigmoid (qwen3next) | Our `src/models/qwen35.cpp:307` and `:592` still do `ggml_cont_2d(gate)`. Sigmoid on the strided view, then a free reshape, removes 16 kernels per verify and 1 per MTP pass (≈21 per step, ≈0.1-0.2 ms) [INFERENCE]. | #29781 (non-contiguous unary) is already in tree (`08246a28f`). |
| #29720 | rms_norm float4 variants (CUDA/HIP) | "RDNA more neutral" | low |
| #29187 | fuse GDN alpha/beta projections (draft, CUDA) | kernel-count reduction | port idea only |
| #30141 / #30345 / #30311 | MTP hidden-state save/restore; MTP masked-mode output-row selection; guard recurrent rollbacks | **Correctness prerequisites.** #30141 matters when n-gram drafts exceed `n_rs_seq` and take the checkpoint path (§3). #30345 is a latent bug that bites any "MTP chain in one graph" design that decodes unflagged rows. | take before the planned one-graph MTP chain |
| #27210 | adaptive MTP depth | see §3.5 | — |
| #29918 | `--cache-reuse-hybrid` (mid-prompt edit reuse, forks the recurrent state) | — | **lossy**, goes to the avoid list |

---

## 2. New drafters and evals after about 2026-10-05 (question 2)

### How I searched
- HF API queries `Qwen3.8-27B`, `dflash`, `dspark`, `eagle3`, `eagle`, `speculator`, `mtp-head`, `nextn`, `pard`, `drafter`, sorted by `createdAt`. That gave 841 repos; 109 had drafter-like names since 2026-10-04.
- The bulk are quant repackages (`-oQ4e-mtp`, `-MTP-GGUF`) or finetuned targets that bring their own heads. Those finetunes, for example `nerkyor/…Coder390…-MTP-DFlash2`, target different weights and do not apply to our trunks.
- No upstream drafter in `drafters.md` (z-lab/incoai DFlash2, RedHat/RadixArk/DimInfer DSpark, DaoCloud, JonasLoos, orestis-z) has been modified since 2026-09-28 (HF `lastModified`).
- **Still no EAGLE-3, PARD or Medusa for Qwen3.8-27B.**

### New items

| Item | What | Evidence | Relevance here |
|---|---|---|---|
| **KaedeTai/Qwen3.8-27B-MTP-zh** (2026-10-10) | Stock MTP head, **hard self-distilled** on the frozen 4-bit trunk's argmax using Chinese text. 512-token blocks, grad-accum 4, lr 1e-5. Trunk: `orcarouter/Qwen3.8-27B-Uncensored-MLX`. | Acceptance (accepted/drafted), stock → tuned: zh_web 56.8 → **62.6%**, zh_news 56.5 → **62.4%**, english 70.0 → 69.6%, code 81.5 → 81.8%. https://huggingface.co/KaedeTai/Qwen3.8-27B-MTP-zh | **First public proof** that a language-specific MTP self-distillation (planned item) lifts one language by about 6 pp without hurting EN/code. Same trunk family as our orca model. PL estimate ≈ +6-9% t/s [INFERENCE]. Format is MLX: retrain, do not convert. |
| shinhipc/…-NInfer-**KoDraft** (2026-10-06) | Language-aware **reduced draft vocab**: 65,536 Korean-Wikipedia tokens plus the default ranking, 131,072 in total, for the MTP draft head | Korean: acceptance 0.18 → 0.31, **+23-28% t/s**; EN/code flat (RTX 5090, T=0.7). https://huggingface.co/shinhipc/Qwen3.8-27B-Huihui-NVFP4-NInfer-KoDraft | Their default list covered only 58-71% of Korean tokens. **Ours already leaves only 3.5% of PL prose outside the 64k list** (`NOTES.md:161`), so the remaining upside is ≤1-2%. A cheap rebuild with `build_draft_vocab.py` and a PL corpus mix. |
| nm-research `qwen3.8-27B-speculator.dflash2.updatedparams.strict.ckpt0` (2026-10-12) | Red Hat WIP DFlash2 checkpoint (raw training state) | No card, no eval | Same converter gap as the 10-09 runs (`drafters.md` row 11). Wait for a release. |
| Plaguekind FrostDFlash-MixedLow-GGUF (2026-10-10) | z-lab DFlash2 re-quantized to mixed IQ3_S/Q5_K/Q6_K, 999 MiB | No acceptance eval | Draft quant barely matters (PR #27342: Q4_K_M AL 5.03 vs BF16 4.92), and DFlash2 is greedy-only in llama.cpp. Skip. |
| magnitudedev DFlash2-GGUF, AEON-7 DFlash2 (gated), Arkane/ai-server-mgr W4A16 DFlash2, LithosAI DSpark-NVFP4 | Repackages or quants of existing drafters (NVFP4 needs Blackwell or lithos-metal) | — | Nothing new |
| localweights `…-IQ4_XS-Q8nextn-GGUF` | Trunk IQ4_XS, MTP head Q8_0 | No MTP acceptance numbers | Our UD-Q4_K_XL head is already Q6_K/Q8_0 (parsed from the GGUF: `blk.64.attn_q` Q6_K, `attn_k/v` Q8_0, `ffn_*` Q6_K, `nextn.eh_proj` Q6_K). |

**New fact about the orca model** (parsed from our GGUF): `orca/Qwen3.8-27B-Uncensored-Q4_K_M.gguf` has its MTP head at **Q4_K** (`attn_q`, `attn_k`, `attn_output`, `ffn_gate/up`, `nextn.eh_proj`). The UD file has it at Q6_K/Q8_0.
- Requantizing the orca head to Q6_K from its source weights is lossless (it only changes drafts).
- Cost: +109 MB per pass × 5 passes ≈ +0.6 ms per step (−1.4%) [INFERENCE: 425M params × (6.56−4.5)/8 B].
- Gain is probably small (draft quant rarely matters, PR #27342).
- A head self-distilled on the orca trunk (KaedeTai recipe) is the better lever.

### Evals of known methods published since 2026-10-10
- hipEngine survey (2026-09-12, still current):
  - Laurent adaptive DFlash2, fresh process: 34.5 t/s;
  - q38rocm MTP K4: 33.0 t/s on the same FP4 target;
  - so DFlash2 ≈ MTP on mixed prompts (Strix Halo).
  - The adaptive DFlash2 fork **leaks speculative state across requests** (invalid outputs).
  - This confirms `drafters.md`: DFlash2 is no better than MTP on chat. https://raw.githubusercontent.com/shisa-ai/hipEngine/main/docs/campaigns/QWEN38-STRIX-HALO-EXTERNAL-SURVEY.md
- rdna-boosts adaptive MTP numbers: §3.5.

---

## 3. Speculative methods for agentic, code and long-doc workloads (question 3)

### 3.1 What our llama.cpp already does (read from code)

**Types**
- `--spec-type` takes a comma list. The priority order is fixed: `ngram-simple` > `ngram-map-k` > `ngram-map-k4v` > `ngram-mod` > `ngram-cache` > `draft-simple` > `draft-eagle3` > `draft-mtp` > … (`common/speculative.cpp:2716-2728`).
- `common_speculative_draft` asks each implementation in order and stops at the first non-empty draft (`speculative.cpp:2912-2967`). So **an n-gram hit pre-empts MTP for that step**; MTP is the fallback.
- MTP stays in sync because its `process()` runs the catch-up pass on every verify batch (`speculative.cpp:1557-1664`) and `accept(...is_other=true)` copies the right hidden row (`:1832-1845`, called at `:3007-3012`).

**Draft length is not capped by `--spec-draft-n-max` for n-gram types**
- The server passes `n_max = n_ctx − n_tokens − 2` (`tools/server/server-context.cpp:517-535`, used at `:3383-3393`).
- `common_speculative_draft` truncates only to that `dp.n_max` (`speculative.cpp:2934-2944`).
- So n-gram drafts are bounded only by their own size:

| Type | Size flag(s) | Default | Code |
|---|---|---|---|
| `ngram-mod` | `--spec-ngram-mod-n-max` | 64 | `common.h:361-366`; `--spec-default` sets 24/48/64 at `arg.cpp:4776-4779` |
| `ngram-map-k`, `ngram-simple` | `--spec-ngram-*-size-m` | 48 | `common.h:368-372` |
| `ngram-cache` | fixed | 8 | `speculative.cpp:2439` |

**Recurrent rollback window**
- `need_n_rs_seq()` returns `draft.n_max` only if a model drafter (MTP/EAGLE3/DFlash/DSpark) is in the list, and 0 otherwise (`common/common.h:403-409`).
- An n-gram-only config therefore has `n_rs_seq = 0`.
- Any draft longer than `n_rs_seq` makes the server take a **full recurrent checkpoint** before the verify (`server-context.cpp:3429-3447`) and restore it on partial acceptance (`:4433-4463`).
- That checkpoint is a host copy: `llama_state_seq_get_data_ext` into a `std::vector` (`common/common.cpp:2355-2421`).
- Size is ≈48 × (128×128×48×4 B) ≈ 151 MB of GDN state plus conv state, so ≈7-8 ms each way over PCIe 4.0 [INFERENCE].
- **With MTP n=4, any n-gram draft of more than 4 tokens pays this.**

**Adaptive behaviour already built in**
- `ngram-map-k` shrinks each key's draft to its last accepted count: `n_draft = min(m, values[].n_accepted)` (`common/ngram-map.cpp:386, 503, 535`).
- `ngram-mod` drafts only if it can chain at least `n_min` tokens (`speculative.cpp:2053-2059`).
- `ngram-mod` resets its pool after 5 rounds below 25% acceptance (`:2095-2120`).
- The `ngram-mod` hash pool (4M entries) is **shared across slots and kept across requests** (docs/speculative.md:203). In effect it is a cross-request suffix cache, which is what helps agent loops.

**T=1**
- N-gram drafts carry no q. The server falls back to sample-and-match (`server-context.cpp:4411-4426`), which is lossless.
- #29924 (n-gram drafts rejected at T>0 after truncation) is in tree (`8330e9696`).

### 3.2 Recommended configuration (no code change)
```
--spec-type ngram-mod,draft-mtp --spec-draft-n-max 4 \
--spec-ngram-mod-n-match 16 --spec-ngram-mod-n-min 3 --spec-ngram-mod-n-max 4
```
(or `ngram-map-k` with `--spec-ngram-map-k-size-n 12 --spec-ngram-map-k-size-m 4 --spec-ngram-map-k-min-hits 1`)

Why these values:
- `n-max 4` equals `n_rs_seq`, so there are no host checkpoints, and the verify stays at 5 columns.
- `n-min 3` makes n-gram take over only when it can beat MTP's ≈3.1 tokens per step.
- `n-match 16` follows rdna-boosts, which found the default 24/48/64 "never drafted" on dense Qwen3.8 and 16/2/96 worked (https://github.com/stew675/llama-cpp-rdna-boosts/blob/main/benchmarks/2026-09-13-qwen38-unc-ngram-mod.md). Below 16 the code warns (`speculative.cpp:1985-1988`).

### 3.3 Small code change (≈10-30 LOC) for the larger win
1. `common/common.h:403-409`: when an n-gram type is combined with MTP, return `n_rs_seq = max(draft.n_max, ngram caps)` and cap the n-gram caps at 7. Then 8-column verifies stay on the MMVQ fast path with no host checkpoint.
   - VRAM cost: about +3 snapshots × ≈0.16 GB ≈ +0.5 GB (sizes from `research/algorithms.md:129`).
   - Snapshot writes scale with the actual tokens, so short MTP steps pay nothing extra.
2. `common/speculative.cpp:2934-2944`: optionally clamp every non-model draft to a configurable ceiling (for example `--spec-ngram-cap 7`). Users then cannot hit the 49-65-token MMQ plus checkpoint path by accident.
3. Optional gate in the same loop: drop an n-gram draft when that implementation's recent acceptance per draft token is below the MTP mean. The counters already exist (`n_acc_tokens`, `n_gen_tokens`).

### 3.4 Expected gains (arithmetic; c_v ≈ 1.4 ms [INFERENCE])

**Code editing** (re-emit a file with small changes). Let f be the share of output tokens inside verbatim spans, and p ≈ 0.97 the n-gram per-token acceptance inside spans [INFERENCE]. Novel regions run at MTP code speed, 85 t/s.

| Cap k | Tokens per step | Step | Copy-region speed | f = 0.8 | f = 0.5 |
|---|---|---|---|---|---|
| 4 (config only) | 1 + Σ0.97^i (i ≤ 4) = 4.71 | 34.9 ms | 135 t/s | **121 t/s (+42%)** | 104 (+23%) |
| 7 (§3.3 patch) | 7.21 | 39.1 ms | 184 t/s | **149 t/s (+75%)** | 116 (+37%) |

External sanity checks:
- ik_llama PR 1646 (GLM-4.5-Air, CUDA), "refactor" follow-up: ngram_mod 65.3 t/s vs ≈38-40 for weak drafters, i.e. **+65%**. Suffix decoding with a corpus: 71.3. https://github.com/ikawrakow/ik_llama.cpp/pull/1646
- KyaniteLabs MTP+ngram on Qwen3.8-27B UD-Q4_K_XL (Strix Halo): warm verbatim replay 164-168 t/s vs 59-61 MTP-only. **Novel prompts: +1.96%.** (hipEngine survey link in §2.)
- rdna-boosts: ngram-mod gave code 343 t/s, but unique prose median: MTP still wins (2× R9700, Q8).

**Agentic tool loops**
- Decode: tool-call JSON reuses paths, identifiers and arguments from the context. SuffixDecoding reports 5.3× on AgenticSQL and 2.5× on SWE-Bench vs AR with its hybrid (https://arxiv.org/abs/2411.04975; already in `research/algorithms.md:103-107`). Against our MTP baseline I estimate **+5-20% on the decode part** [INFERENCE].
- E2E for agents is dominated by prefill and prefix reuse (§4). A 2k-token tool result costs ≈2.5 s of prefill; a 300-token answer costs ≈4 s of decode.

**Long-document QA with quotes**
- If ≈30% of answer tokens are verbatim quotes, the 94k decode of 1,000 tokens (23 s at 43 t/s) shrinks by ≈3-5 s. That is only **≈ −2-3% of the 165 s E2E** [INFERENCE].
- The real lever is not re-prefilling the document (§4).

**Plain chat / PL prose:** ≈0. The n-min gate keeps MTP in charge; without the gate the change could be negative.

**REST / `ngram-cache` with a static corpus cache** (`-lcs FILE`, built by `llama-lookup-create`; `arg.cpp:1627-1640`)
- This is llama.cpp's REST equivalent.
- REST reports 1.62×-2.36× over AR on code and text (https://arxiv.org/abs/2311.08252). Against MTP the gain is mostly limited to boilerplate code [INFERENCE].
- Its draft is fixed at 8 tokens (`speculative.cpp:2439`), so 9 columns: off the fast path and over `n_rs_seq`. Fix that first.
- Low priority.

### 3.5 Deeper drafts (only for code and recall)

rdna-boosts `draft-mtp-adaptive` (a table controller, not a confidence threshold) on 1× R9700 (gfx1201), UD-Q4_K_XL, T=0, `-n 3000`:

| Workload | n3 t/s | adaptive, ceiling 12 | change | mean accepted length |
|---|---|---|---|---|
| prose | 56.3 | 63.4 | +13% | 5.10 |
| code | 62.9 | 81.8 | +28% | 7.02 |
| recall | 68.0 | 109.6 | +61% | 8.95 |
| reasoning | 47.3 | 46.0 | −1% | 2.74 |

- Ceiling 7 lost to n3 on prose and code.
- Outputs diverge from plain decoding once the verify exceeds 8 rows, because that switches kernel families. Source: https://github.com/stew675/llama-cpp-rdna-boosts/blob/main/benchmarks/2026-09-13-adaptive-mtp-4-axis-n12.md

Why this matters here:
- Our earlier negative result was a cumulative-confidence stop with n_max ≤7.
- Their gain comes from **depth >8**, which on our GPU hits the ≥9-token cliff. On Vulkan, 9-16 tokens cost 108-110 ms (`research/PLAN.md:19`). **ROCm verify(9-16) has not been measured.**
- Action: measure ROCm step time at verify widths 9, 12 and 16. If ≲ 29.3 + 1.4·k holds, extending multi-column MMVQ to 16 columns plus an adaptive ceiling of 12 is worth ≈ +20-30% on code at T=0.
- At T=1, chat acceptance (p ≈ 0.64) caps the gain near 0 (`research/algorithms.md:45`).

**Lookahead / Jacobi:** see the avoid list.

---

## 4. Lossless context and KV handling for long context (question 4)

**Lossless: same tokens, up to kernel-order noise from different ubatch splits.**

1. **Exact prefix reuse inside a conversation.**
   - The server checkpoints recurrent and KV state at user-message starts and near the prompt end (`server-context.cpp:3865-4061`, `-ctxcp`, `-cms`; `arg.cpp:1700-1716`).
   - A follow-up question on the same 94k document then only processes the new turn: **≈142 s of prefill saved** (165 s → ≈23-25 s E2E) [INFERENCE].
   - Requirement: the chat template must re-render earlier turns byte-identically. The Qwen3.8 template defaults to `preserve_thinking=true` (https://huggingface.co/localweights/Qwen3.8-27B-MTP-IMAT-IQ4_XS-Q8nextn-GGUF), which helps.
   - Verify with server logs ("restored context checkpoint …").
2. **Across conversations or restarts:** `--cache-ram N` (host-RAM prompt cache, `arg.cpp:1718-1722`) and `--slot-save-path` (our tree appends checkpoints to the slot file, `server-context.cpp:2586-2714`).
   - Size: KV q4_0 = 16 layers × 2 × 4 heads × 256 × 0.5625 B ≈ **18.4 KB/token**, so 94k tokens ≈ 1.73 GB plus ≈0.15 GB recurrent state.
   - 62 GB of RAM holds ≈30 such documents.
   - Restore ≈0.1 s at about 20 GB/s versus 142 s of prefill [INFERENCE].
3. **Agent loops:** the same mechanism. hipEngine measured a coding-agent replay at 2.79× E2E with prefix reuse (radix cache, 16 snapshots). Without it every turn re-prefills the transcript (https://github.com/shisa-ai/hipEngine, "Coding-Agent Session Replay").
4. **Prefill cost of MTP itself**
   - MTP's `process()` runs the MTP layer over every prompt token (`speculative.cpp:1599-1635`) and round-trips hidden rows through the host (`llama_get_embeddings_nextn` → `set_embd`).
   - rdna-boosts reports MTP prefill at **−23-28%** vs no-spec (1785 → 1283 t/s on 2× R9700 with tensor split).
   - Our hint: llama-bench pp4096 1044 t/s (no MTP) vs server 924 t/s at 6.6k (with MTP) (`NOTES.md:16, 192`). That is consistent with ≈5-12% [INFERENCE].
   - **Measure server prefill with and without `draft-mtp` at 30k and 94k.** Fixes, both lossless because only draft quality changes:
    - (a) an MTP-layer SWA window (finding 6). Note that hipEngine does not window: its gfx1151 MTP route simply falls back to AR above the head's 1,023-token context, so there is no public windowed-MTP acceptance data;
     - (b) skip MTP catch-up for all but the last W prompt tokens.
   - Where: the MTP KV creation, `mtp_on_hybrid_qwen` in `src/llama-model.cpp` (≈2700-2707 per `research/algorithms.md:91`), and the `process()` loop above.

**Not lossless (avoid list):** StreamingLLM, SnapKV, H2O, DMS (hipEngine's trained eviction), `--cache-reuse-hybrid` (#29918, forks recurrent state after mid-prompt edits), KV below q4 (q3/q2/KVarN ≤3 bit, TurboQuant).

BeeLlama's **precision tail**:
- What it does: keeps the newest 1024 tokens in F16 on top of a q4_0 body.
- Effect: q4_0/q4_0 median KLD drops from 0.001846 to 0.001057 (Qwen3.6-27B, Wikitext).
- It is a fidelity *improvement*, but it changes outputs relative to the current q4_0 baseline. Treat it as a quality option, not a speed option.
- Source: https://raw.githubusercontent.com/Anbeeld/beellama.cpp/main/README.md

---

## 5. Avoid or does not apply

- **Switching engines.**
  - hipEngine, the nasone32 fork and llama.cpp forks are all ≤63.5 t/s greedy on a 7900 XTX, and hipEngine's MTP is a regression on 128-token outputs (§1.1).
  - vLLM, SGLang, ExLlamaV3 and ik_llama lack batch-1 ROCm evidence or ROCm support altogether (§1.2).
- **ik_llama.cpp:** ROCm is explicitly unsupported and `_XL` Unsloth quants are discouraged.
- **ExLlamaV3 ROCm:** not merged, DFlash2 is CUDA-only, ≈15 t/s.
- **Lookahead / Jacobi decoding:** τ 1.69 vs EAGLE 3.94 (EAGLE-2 Table 1, https://arxiv.org/abs/2406.16858). Each window token costs a verify column, and the 2D n-gram window needs far more than 8 columns.
- **Tree / multi-branch drafts, SpecInfer-style:** GDN rollback is chain-only (`research/algorithms.md:127-159`).
- **ngram-only `--spec-default`** (24/48/64): it never drafts on dense Qwen3.8 (rdna-boosts). When it does, the 49-65-token verify falls off MMVQ and the `n_rs_seq = 0` checkpoint path runs (§3.1).
- **`ngram-cache` with its fixed 8-token draft:** 9 columns, so off the fast path and over `n_rs_seq` unless capped.
- **DFlash2 re-quants (FrostDFlash), DFlash2-b32, DSpark NVFP4 heads, finetuned-target heads (Coder390 …):** no gain, a different target, or different hardware.
- **Qwen3.6 EAGLE-3 heads:** target mismatch (`drafters.md`).
- **Lossy KV and context methods:** StreamingLLM, SnapKV, H2O, DMS, q3/q2/KVarN-2/3 KV, `--cache-reuse-hybrid`.
- **Changing trunk quant for speed** (IQ4_XS, NVFP4): this changes the output model; it is outside the lossless constraint.
- **Chunked-GDN prefill kernels from forks** (nasone32, rdna-boosts block 02, #29353): adopt only after a greedy repeat-stability check. hipEngine found the nasone32 default non-deterministic.

## 6. Checks Main should run, in order
1. Cherry-pick #30329 and #30103, then run one spec session and read `graph reallocs`.
2. Server prefill at 30k and 94k with and without `--spec-type draft-mtp`, to quantify MTP prefill overhead.
3. ROCm step time at verify widths 6, 8, 9, 12 and 16 (`llama-batched-bench` or the perf logger), to decide on finding 4.
4. The §3.2 config on a code-rewrite prompt and a quote-heavy long-doc prompt against MTP-only, with `greedy_check.sh` for losslessness. Then the §3.3 `n_rs_seq` patch with cap 7.
5. A follow-up question on a 94k document to confirm checkpoint restore (log line) and E2E time.
