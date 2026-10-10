# Speculative-decoding algorithm improvements for Qwen3.8-27B (qwen35 hybrid) on 1× RX 7900 XTX

Author: SpecAlgorithms (research only, no GPU runs). Local code = `~/llama-master` (e60eff95f + amd-opt patches).
All "measured" numbers are from `~/qwen-opt/NOTES.md` / `spec_sweep.jsonl`; everything derived by me is marked [INFERENCE].

## TL;DR ranking

| # | Idea | Chat/prose gain (en-chat 60, pl-prose 64 t/s) | Code gain | Effort | Already in llama.cpp? |
|---|---|---|---|---|---|
| 1 | **Adaptive draft length**: stop on *cumulative* (path) draft confidence + per-request controller | **+10–15 %** (en-chat ≈ 67–69) | 0 … +3 % | Low (≈100 LOC in `common/speculative.cpp`) | No. Only per-token `p_min` (speculative.cpp:1760-1766) |
| 2 | **Cheaper drafting**: run the k MTP passes + catch-up pass with no host round-trip (one graph / one submit) | **+12–17 %** (≈ 68–70) | **+20–30 %** (≈115–123) | Medium-high (new graph path in `src/models/qwen35.cpp` graph_mtp + context API) | No (Gemma4 `is_mem_shared` path runs all heads in one graph, not qwen35) |
| 1+2 | combined | **≈ +20–25 %** (≈ 72–75) | ≈ +25–30 % | | |
| 3 | n-gram / suffix hybrid (n-gram first, MTP fallback), capped at ≤7 drafts | ≈ 0 … +5 % | large on edits/quotes | Config now; score-gated selection = low | Yes, comma list in `--spec-type`; n-gram has precedence (speculative.cpp:2716-2728) |
| 4 | Lossless verification tweaks at T=1 (block verification; multi-draft at first position) | +3–6 % | +2–4 % | Low-medium (`common/sampling.cpp`) | No |
| 5 | Tree / multi-candidate verification | **≈ −5 … +5 %** (likely negative inside an 8-token verify budget) | ≈ 0 | Very high (new GDN op, conv, mask, server) | No; recurrent rollback is chain-only |
| 6 | Multi-head MTP chaining (`chain_heads`) | n/a | n/a | — | Code exists, but Qwen3.8 ships **1** nextn layer |
| 7 | Lossy acceptance (Medusa "typical acceptance", Judge decoding) | potentially large | — | Low | No; changes output distribution — user decision |

Hard ceiling for chat (section 0): with the current MTP head's ≈0.64 per-position acceptance, an infinitely long and free draft yields at most 2.78 tokens/step versus 2.6 today. **A "big jump" on chat cannot come from drafting/verification algorithms alone.** Ideas 1+2 reach ≈72–75 t/s. Anything beyond that needs a drafter with higher per-token acceptance (DrafterTraining / DrafterSurvey scope) or a cheaper base forward.

---

## 0. Cost model calibrated on this machine (used for every estimate below)

Measured anchors: plain decode 26 ms/token. Verify forward of 6 tokens (Vulkan perf logger) 33.6 ms. One full MTP n=5 step is 44–46 ms.
- Extra verify column: (33.6 − 26)/5 = **1.52 ms/token** (holds for 2–8 columns thanks to the multi-col mmvq kernels).
- One MTP draft pass ≈ (45 − 33.6)/5 ≈ **2.3 ms** [INFERENCE]. Its bandwidth floor is MTP block 351 MB (`blk.64.*`, measured from the GGUF) + 64k-row Q6_K head ≈ 275 MB ≈ 626 MB, i.e. **0.65–0.8 ms**. So about 1.5 ms of each pass is launch, sync and readback overhead [INFERENCE].
- Step model: **T(k) ≈ 26 + 3.8·k ms** for k drafts (k ≤ 7). E[tokens] = 1 + Σ_{i≤k} Π_{j≤i} a_j.

Validation against `spec_sweep` (T=1). Acceptance → tokens/step → predicted vs measured t/s:

| prompt | n | acc | tok/step | T(k) | predicted | measured |
|---|---|---|---|---|---|---|
| en-chat | 3 | 0.51 | 2.53 | 37.4 | 67.7 | **68.6** |
| en-chat | 5 | 0.32 | 2.60 | 45.0 | 57.8 | 59.3 |
| pl-proza | 3 | 0.49 | 2.47 | 37.4 | 66.0 | 67.1 |
| pl-proza | 5 | 0.36 | 2.80 | 45.0 | 62.2 | 64.2 |
| pl-kod | 3 | 0.72 | 3.16 | 37.4 | 84.5 | 84.6 |
| pl-kod | 5 | 0.655 | 4.28 | 45.0 | 95.1 | 96.0 |

The model is within ~3 %. Implied per-position acceptance: chat p ≈ 0.64 (0.64+0.41+0.26+0.17+0.11 = 1.59 ≈ 0.32·5); code p ≈ 0.87.

Verify ≥ 9 tokens falls to MMQ. From n=6 p_min .5 → 77 t/s and n=8 p_min .5 → 47 t/s, verify(9) ≈ 60 ms (≈2.3× a single decode) [INFERENCE]. **Every algorithm below must keep the verify batch at ≤ 8 tokens (root + ≤7 drafts).**

Chat ceiling at p = 0.64: E[tokens] ≤ 1/(1−p) = 2.78 even for infinite free drafting. Today we get 2.60, i.e. 94 % of that limit. The only remaining chat levers are (a) the cost per step (ideas 1, 2) and (b) p itself (drafter quality). Sensitivity with the idea-2 cost model, n=5: p=0.75 → 3.29 tok/step → ≈87 t/s; p=0.80 → 3.69 → ≈98 t/s [INFERENCE].

---

## 1. Adaptive draft length (EAGLE-2 "value" / SpecDec++ threshold policy) — rank 1

**What.** Stop drafting when the *cumulative* product of draft confidences (the estimated probability that the whole draft prefix is accepted) drops below a threshold τ. Optionally add a per-request controller that picks k by maximising E[tokens]/T(k) using the cost model and an EMA of per-position acceptance.

**Why it should work here (evidence).**
- Your own sweep already shows the per-category optimum differs: en-chat n=3 **68.6** vs n=5 **59.3** t/s (+16 %), pl-proza 67.1 vs 64.2 (+4.5 %), code n=5 96.0 vs n=3 84.6. The "no gain" verdict in NOTES compared *medians across all prompts*. A per-step or per-request choice gets the best of both (`~/qwen-opt/NOTES.md:147-157`).
- The marginal-cost rule follows from the cost model. Draft token i adds 3.8 ms and is worth it only if P(prefix through i accepted) > 3.8 ms / (ms per output token). That is ≈ 3.8/16.7 = **0.23** at 60 t/s and ≈0.36 at 95 t/s. This is a cumulative-probability threshold, not a per-token one.
- EAGLE-2 ablation (MT-bench, Vicuna-7B): using the path product ("value") instead of raw per-token confidence gives τ 4.39 → 4.98 and speedup 3.21× → 3.62×. Draft confidence is well calibrated: conf < 0.05 → acceptance ≈ 0.04; conf > 0.95 → ≈ 0.98. Sources: https://arxiv.org/abs/2406.16858 (Table 3, Fig. 6).
- SpecDec++ proves the optimal stopping policy is a threshold on the predicted rejection probability (MDP). It reports +7.2 % / +9.4 % / +11.1 % over the best *fixed* K (Alpaca / GSM8K / HumanEval). Source: https://arxiv.org/abs/2405.19715.
- Upstream practice: llama.cpp discussion #25198 (`--spec-draft-n-max 8..16 --spec-draft-p-min 0.8`): +15–20 % on Qwen3.6-27B / Gemma-4 for code. https://github.com/ggml-org/llama.cpp/discussions/25198. That is a per-token threshold, which is why it needed high n_max. On this GPU n_max must stay ≤ 7 (MMQ cliff).
- Why your `p_min` test showed nothing: `p_min` is per-token (speculative.cpp:1760-1766). Its `p` is renormalised over the backend top-10 candidates: the backend top-k returns logits only (llama-sampler.cpp:1483), and the CPU top_k(10) softmaxes over the 10 (common/sampling.cpp:134-155). So it is over-confident and never fires on "three 0.8 tokens in a row = 0.51".

**Expected gain** [INFERENCE from the cost model]: en-chat → ≈67–69 t/s (+12–15 %), pl-prose → ≈67–69 (+5–8 %), code unchanged; with n_max 7 when confident, code gets ≈+3 %.

**Code locations.**
- `common/common.h:328-341` `common_params_speculative_draft`: add `float p_cum = 0.0f;` (+ arg in `common/arg.cpp` next to `--spec-draft-p-min`).
- `common/speculative.cpp:1666-1830` `common_speculative_impl_draft_mtp::draft()`: keep a per-seq `float cum = 1.0f`. At line 1760: `cum *= cur_p->data[0].p; if (cum < params.p_cum) { stop }`. Keep at least `n_min` drafts.
- Controller (optional): in `accept()` (speculative.cpp:1832) update an EMA of per-position acceptance; `n_acc_tokens_per_pos` already exists (speculative.cpp:2990-2996). In `draft()` choose `k* = argmax_k (1+Σ_{i≤k}Π a_j)/(T0 + c·k)` with T0 = 26, c = 3.8 (or measured).
- Keep `n_rs_seq` = n_max (common.h:403-409). Snapshot writes scale with the actual tokens (delta-net-base.cpp:588), so short drafts are cheaper automatically.

**Risk.** Calibration of the reduced-vocab, top-10-renormalised MTP p; τ needs tuning per T (0.2–0.35). Lossless (verification unchanged).

---

## 2. Cut the per-pass draft overhead: device-side MTP draft chain — rank 2 (cost side)

**What.** Today each step runs 1 catch-up MTP decode (`process()`, speculative.cpp:1590-1635, called at server-context.cpp:4232 on the full verify batch including rejected rows) plus k separate `llama_process` draft calls (speculative.cpp:1711-1814). Each call does build/reuse, submit, sync, top-k readback and host batch rebuild.

Proposal:
- (a) Build one MTP graph that unrolls k steps. Token i+1 = argmax(logits_i) via `ggml_argmax` + `ggml_get_rows(tok_embd)`, h_{i+1} = `h_nextn` of step i, and KV for positions pos0..pos0+k−1 is written in-graph (positions are known up front). Only the k token ids and top-p values are read back once.
- (b) Fold the catch-up pass into the first draft pass: run catch-up after acceptance with only accepted rows + id_last in one ubatch. This saves one pass per step and stops computing MTP KV for rejected rows, which are deleted later at server-context.cpp:3423.

**Evidence.**
- Inferred ≈2.3 ms/pass vs 0.65–0.8 ms bandwidth floor (section 0).
- PR #23287 moved only MTP draft *sampling* to the backend: +7–8 % on CUDA, +4 % on Vulkan, "draft sampling can dominate the draft execution time" (https://github.com/ggml-org/llama.cpp/pull/23287).
- ik_llama.cpp measurements for the MTP DRAFT_GEN graph: 50 nodes, still 5–9 ms on GLM (https://github.com/ikawrakow/ik_llama.cpp/issues/1630). This shows the pass is overhead-dominated.
- Lumo/GDN Tree-Scan campaign: "whole-spine drafter graph capture (~−40 ms)" was among their wins (https://macoredroid.github.io/Lumo_FlyWheel/every-lever.html).

**Expected gain** [INFERENCE]. Pass cost 2.3 → ~0.9 ms gives T(k) ≈ 26 + 2.4k. Chat at the best k (4–5): 2.48/35.6 ≈ 70 t/s (+17 %). Code at k=7 (p=.87, E=5.17 tok): 5.17/42.8 ≈ 120 t/s (+25 %). Saving the catch-up pass alone (b): ≈2 ms/step ≈ +4–5 % everywhere. Cheaper drafts also move the optimal k up, so ideas 1 and 2 compound.

**Code locations.**
- `src/models/qwen35.cpp:499-660` (`graph_mtp`): add an unrolled-k variant (loop the block with in-graph argmax/get_rows). The reduced-vocab head path (lines ~654+) must produce the argmax over the 64k subset.
- Context side: new `LLAMA_PROCESS_TYPE`/API to run "draft k steps" on ctx_dft. The MTP KV cache is a plain attention cache (llama-model.cpp:2700-2707 `mtp_on_hybrid_qwen`), so reserving k cells in one ubatch is standard.
- `common/speculative.cpp:1666-1830` replaces the while-loop with one call. `process()` / `accept()` reorder for (b): the server must call process after acceptance (server-context.cpp:4232 vs 4392-4471).
- Vulkan backend: whatever ops the unrolled graph uses (argmax and get_rows with a device-side index already exist).

**Risks.** Breaks `p_min` per-step early exit unless computed in-graph (cumulative-p cut can be applied post-hoc: draft 7, then truncate). Wasted MTP compute on cut drafts is cheap (0.8 ms/pass). Sampling at T>0 for the draft (probabilistic mode) needs an in-graph sampler. Coordinate with StepCostAnalysis, who measures the actual per-pass time.

---

## 3. Hybrid n-gram / suffix drafting + MTP — rank 3 (cheap, workload-dependent)

**Status in llama.cpp.** Supported: `--spec-type ngram-map-k,draft-mtp` (comma list; docs/speculative.md:207, 227-228). N-gram impls are tried first and MTP is the fallback (speculative.cpp:2716-2728, 2912-2967). The MTP impl stays in sync via `accept(..., is_other=true)` (speculative.cpp:3007-3012; MTP `accept` updates `pending_h`, 1832-1845).

**Evidence for chat.** SuffixDecoding (https://arxiv.org/abs/2411.04975):
- Spec-Bench (open-ended + MT-bench): hybrid suffix+EAGLE-3 gives 4.68 mean accepted tokens/step vs EAGLE-3 4.65 (+0.7 %), speedup 2.50× vs 2.37× (+5.6 %, App. A tables).
- Suffix alone loses on open chat (Spec-Bench acceptance 0.19). WildChat speedup is only 1.1–1.6× even with a 10k-example global tree (Fig. 8).
- Agentic/code reuse: 5.3× (AgenticSQL), 2.5× (SWE-Bench).
- Their threshold recommendation: τ ≈ MAT of the model drafter (App. B.1).

**Pitfalls on this setup (must fix for any gain).**
1. N-gram drafts are not capped by the spec n_max. The server passes `n_max = n_ctx - n_tokens - 2` (server-context.cpp:517-535, 3385). `ngram-mod` defaults to n_min 48 / n_max 64 (common.h:361-366). That means a 49–65-token verify (MMQ cliff) and, beyond `n_rs_seq`, a **full recurrent checkpoint save/restore** (server-context.cpp:3429-3447, 4433-4463). Cap n-gram drafts at ≤7, e.g. `--spec-ngram-map-k-size-m 7`, or clamp in `common_speculative_draft` (speculative.cpp:2934-2944) to the MTP n_max.
2. A wrong n-gram hit pre-empts a good MTP draft. Gate by match quality (SuffixDecoding score / ngram-map `min_hits`) or by comparing with τ ≈ current MTP mean acceptance.

**Expected gain** [INFERENCE]: casual EN/PL chat ≈ 0 … +5 % (names, phrases echoed from the prompt; the n-gram draft costs ~0 ms vs 2.3 ms/MTP pass). Large on "rewrite/quote/edit this" requests. Effort: config + ≈30 LOC clamp; a score-based selector is ≈100 LOC in `common_speculative_draft`.

---

## 4. Lossless verification improvements at T=1 — rank 4 (small)

Background: at T=1 with greedy (argmax) drafts, verification is sample-and-match. Acceptance at a position equals p_target(draft), bounded by E[max p_target] even for a perfect drafter. Your T=0 vs T=1 gap is ≈ +7–12 % (MTP pl-prose 71.5 vs 63.9, en-chat 64.5 vs 60.4; NOTES:164-172). That gap is the most a T=1-specific verifier trick can recover.
- **Block verification** (Sun et al., ICLR 2025, https://arxiv.org/abs/2403.10444): optimal joint acceptance over the draft block, provably lossless. +7–10 % block efficiency and +5–8 % wall-clock at γ=8. It needs probabilistic drafts (q). Your `--spec-draft-sampling probabilistic` path supplies q as top-10 candidates (speculative.cpp:1775-1777). Where: `common_sampler_sample_and_accept_n_rejection` (common/sampling.cpp:~740-800). Expected +3–5 % at γ=5 [INFERENCE: gains grow with γ].
- **Multi-draft at the first position** (SpecInfer-style recursive rejection over the top-2 MTP candidates): this is the "root sibling" of section 5 and carries the same recurrent-state problem. See there.

---

## 5. Tree / multi-candidate drafting with recurrent (GDN) state — rank 5 (not worth it here)

### How llama.cpp rolls back qwen35 state today (chain only)
- The number of rollback snapshots is `n_rs_seq = draft.n_max` for MTP/EAGLE3/DFlash (common.h:403-409 → common.cpp:1697). It is allowed only for archs in `llm_arch_supports_rs_rollback` (llama-arch.cpp:1171-1174 includes QWEN35; clamp in llama-context.cpp:108-113).
- Recurrent tensors are widened to (1+n_rs_seq) row groups (llama-memory-recurrent.cpp:101). Per seq that is 48 layers × (3.15 MB SSM + 0.12 MB conv) ≈ 157 MB × 6 ≈ **0.94 GB** at n_rs_seq=5 [INFERENCE from GGUF dims: S_v=128, H_v=48, conv 3×10240].
- Each GDN layer writes the state after each of the last K=n_rs_seq+1 tokens (delta-net-base.cpp:546-603; conv snapshots 497-522).
- `seq_rm(p0)` moves back ≤ n_rs_seq tokens by setting a single-use `rs_idx` (llama-memory-recurrent.cpp:200-218). A cell shared by several seqs cannot roll back (same function, ~202-210; abort at :819).
- Server: if the draft or rollback exceeds n_rs_seq it falls back to full state checkpoints (server-context.cpp:3429-3447, 4433-4463).

### Can multiple branches be verified?
- **True tree in one sequence: no.** The KQ mask is "same seq_id && pos ≤" (llama-kv-cache.cpp:1663-1683), so siblings at equal positions would see each other. GDN and conv kernels scan tokens linearly with no parent index (delta-net-base.cpp:567; `ggml_gated_delta_net`). Acceptance is chain-only (`common_sampler_sample_and_accept_n*`, server-context.cpp:4414-4426).
- **Branches as separate seq_ids: technically possible, impractical.**
  - The attention side supports multi-seq tokens (mask uses `cells.seq_has`); recurrent `seq_cp` shares the tail cell and diverges on write (llama-memory-recurrent.cpp:265-299).
  - But recurrent ubatches require **equal tokens per seq** (`assert(n_tokens % n_seqs == 0)`, llama-batch.cpp:850; `split_equal` with n_keep_tail, :603-745). The branch root x0 must be duplicated per branch.
  - It needs `n_seq_max ≥ branches` (+≈0.6–0.94 GB recurrent state each, VRAM is at 22.3/24 GB) and `-kvu`; otherwise the 204800-token q4_0 KV (~3.8 GB) is duplicated per stream.
  - Server plumbing for a single slot using extra seq ids is non-trivial.

### Expected value on this GPU (8-token verify budget)
- 2 branches × 4 tokens (= 8 cols: shared root duplicated, top-1 / top-2 at depth 1, depth 3 each). Draft 3 batched passes ≈ 7 ms + verify(8) ≈ 36.6 ms → **≈ 44 ms**. Tokens: chain-3 gives 2.53, and branch B adds P(rej a1)·P(hit b1|rej)·(1+p+p²) ≈ 0.36·0.3·1.97 ≈ 0.21 → 2.74 tokens → **62 t/s, worse than chain-3's 67.6** [INFERENCE; the 0.3 top-2 conditional hit rate is a guess].
- External evidence:
  - EAGLE tree vs chain: +0.6–0.75 τ, but with 10+-node trees (EAGLE Table 5, https://arxiv.org/abs/2401.15077), i.e. outside the 8-col mmvq budget here.
  - vLLM TreeWY RFC on Qwen3.5 GDN: acceptance 3.23 → 3.44 with width, "throughput falls at every width" (https://github.com/vllm-project/vllm/issues/54080).
  - GDN Tree-Scan (vLLM, Qwen3.6-27B): paper claims +17 % committed tokens with one root sibling (https://arxiv.org/abs/2609.23900). That looks implausible: one depth-0 leaf with no children can add at most P(first spine token rejected) tokens per step, and with accept/event 3.11 of 5 that probability is likely ≲0.2–0.3, not the reported +0.71 [INFERENCE]. The authors' own later write-up reports a "squared temperature" sampling bug and **"Tree ~0.92× native at the operating point"** (https://macoredroid.github.io/Lumo_FlyWheel/every-lever.html).
  - SGLang supports topk>1 on Mamba/GDN with one private state slot per draft token + parent indices. Reported Qwen3-Next acceptance length: 3.41 (3 steps, topk=1) → 4.23 (4 steps, topk=4, 8 draft tokens). Depth also changed, so this is not a clean tree-vs-chain comparison (https://pytorch.org/blog/hybrid-models-meet-sglang-more-than-full-attention/). Measured on H100 multi-GPU with spare compute, not on bandwidth-bound RDNA3 with an MMQ cliff.
- STree (https://arxiv.org/abs/2505.14969) gives the algebra for state sharing in trees but no llama.cpp path.

**Effort if attempted anyway** (very high):
- a parent-indexed `ggml_gated_delta_net` variant (CUDA + Vulkan shaders) that writes per-node snapshots — the K-snapshot output already exists, so add a `parent[]` input and load S_parent from the snapshot slot;
- parent-indexed conv1d history;
- an ancestor KQ mask in `llama_kv_cache::set_input_kq_mask` (llama-kv-cache.cpp:1759+);
- tree acceptance in `common/sampling.cpp`;
- tree drafting in the MTP impl;
- promotion of the accepted path's snapshot (rs_idx semantics) in llama-memory-recurrent.

Verdict: skip unless verify(9..16) becomes cheap (multi-col mmvq to 16 columns), and even then the chat gain is ≤ ~+5 %.

---

## 6. Multi-head MTP chaining (`chain_heads`) — not applicable

- GGUF metadata: `qwen35.nextn_predict_layers = 1`, `block_count = 65`. The only nextn tensors are `blk.64.nextn.{eh_proj,enorm,hnorm,shared_head_norm}` (read with gguf-py from `~/models/Qwen3.8-27B-UD-Q4_K_XL.gguf`).
- `chain_heads = n_mtp_layers > 1 && !is_mem_shared` (speculative.cpp:1440, 1500), so it is false here. The graph asserts `n_layer_nextn == 1` (qwen35.cpp:503).
- The single head is reused recursively, so per-position acceptance decays (p ≈ 0.64 chat). Extra trained heads (Step-3.5 style) would be a drafter-training project (DrafterTraining scope).

---

## 7. Lossy acceptance — only if the user accepts distribution change

Medusa "typical acceptance" accepts draft x if p_target(x) > min(ε, δ·exp(−H(p_target))). It reports MT-bench quality on par with random sampling and higher acceleration for creative tasks (https://arxiv.org/abs/2401.10774 §2.3.1, §3.3.2). Judge Decoding / FLy are similar (https://arxiv.org/abs/2501.19309, https://arxiv.org/abs/2511.22972).

On high-entropy PL/EN prose this attacks exactly the T=1 ceiling of section 4, so it could be the largest chat lever. **Not lossless**: the outputs are no longer samples of the Q4 target.
- Where: `common_sampler_sample_and_accept_n` (common/sampling.cpp).
- Effort: low.
- Gain: unknown on this model. Needs a quality A/B.

---

## 8. Considered and rejected

- **Lookahead/Jacobi decoding**: τ 1.69 vs EAGLE 3.94 on MT-bench (EAGLE-2 Table 1, https://arxiv.org/abs/2406.16858). Each Jacobi window token costs a full verify column.
- **Self-speculative layer/SSM-skip drafts** (https://arxiv.org/abs/2605.01106): any draft that runs a fraction of the 27B trunk costs ≥ several ms per token vs 0.8–2.3 ms for MTP [INFERENCE: bandwidth arithmetic].
- **Draft/verify overlap (PEARL-style)**: single memory-bound GPU, no idle units. The Lumo campaign also found the overlap class "dead because the GPU is already 97 % busy".
- **ReplaySSM** (input-cache instead of state snapshots, https://github.com/vllm-project/vllm/issues/47572): helps at large batch; bs=1 c/std = 0.99 for Qwen3.5-122B. It is relevant to *snapshot traffic* only (see note below).

---

## Cost-side notes for StepCostAnalysis (shared)

- With n_rs_seq=5, each GDN layer emits up to 6 f32 state snapshots (6 × 3.15 MB) and copies them into `ssm_states_all` (delta-net-base.cpp:563-603). That is ≈ 2.7 GB of traffic per 6-token verify vs ≈ 0.45 GB for 1-token decode [INFERENCE], i.e. a candidate for a large share of the 26 → 33.6 ms verify growth.
- CUDA fuses GDN→cpy (`ggml_cuda_try_gdn_cache_fusion`, per StepCostAnalysis); Vulkan does not.
- Lowering n_max (idea 1) reduces snapshot writes proportionally.
- The ≥9-token MMQ cliff caps every algorithm here at 8 verified tokens.

## Upstream / other engines status (2025–2026)

- **llama.cpp**:
  - No tree verification and no adaptive/cumulative draft-length policy.
  - `p_min` per-token (PR #23269 era) and backend top-k for MTP drafts (PR #23287).
  - FR-Spec draft-vocab issue #25187 (you already have the local equivalent).
  - Combined `draft-mtp` + external `-md` drafter crashes at init (issue #27850), so MTP+DFlash per-step switching is not available yet.
  - `examples/speculative` has old multi-branch drafting (`p_split`, seq_cp) for attention-only models only (examples/speculative/speculative.cpp:59-67, 532-538).
- **ik_llama.cpp**: Qwen3.5 MTP was only a discussion; the spec-backend issue #1630 documents the MTP pass overhead. No tree or adaptive MTP found (search not exhaustive).
- **vLLM**: chain MTP; tree on GDN only as RFC/out-of-tree (TreeWY #54080, GDN Tree-Scan); ReplaySSM #47572 for state traffic.
- **SGLang**: EAGLE topk>1 supported on hybrid GDN/Mamba via per-draft-token state slots + parent tracing (PyTorch blog above).

## Suggested experiment order for Main

1. Idea 1 (cumulative p stop, τ ∈ {0.2, 0.25, 0.3, 0.35}, n_max 7). Bench with `spec_sweep.sh` per category; expect en-chat ≈ 67+, code ≥ 96.
2. Idea 2(b) (fold catch-up pass, low risk), then 2(a) (unrolled draft graph). Re-tune τ afterwards (optimal k rises).
3. Idea 3 only as `ngram-map-k` with size-m ≤ 7 and a match-length gate; measure on prompts that quote/edit user text.
4. Skip trees.
