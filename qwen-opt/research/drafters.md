# Existing drafters for Qwen3.8-27B (UD-Q4_K_XL) in llama.cpp: survey

Scope: drafters that already exist (HF, GitHub, papers) for Qwen3.8-27B, checked against our llama.cpp tree (`~/llama-master`, e60eff95f + local patches). Nothing over 200 MB was downloaded. Model cards and configs are cached in `/tmp/hfcards/`.

AL (acceptance length) below means **tokens per verify step, bonus token included**. That is the convention SGLang and vLLM use (`1 + accepted/draft_calls`), and it is also what the parent calls "accepted tokens per step". The local baseline is MTP n=5, AL ≈ 3.0 on EN chat at T=1, 44–46 ms per step, measured 60–64 t/s.

## TL;DR

1. **No existing drafter gives a big jump on chat-style T=1 text by itself.** Every published chat AL for Qwen3.8-27B (MT-Bench, Alpaca, Arena-Hard, "writing", "question") is between 2.8 and 4.1 at a 7–8 token draft. The 4.1 is DFlash2 in thinking mode with probabilistic drafting. Our MTP already gets ~3.0.
2. **Best candidate: the DFlash2 drafter we already have (z-lab/incoai), with probabilistic path sampling plus rejection added to llama.cpp, at n=7.** Upstream DFlash2 samples its path from the selector scores and verifies by rejection at T>0. llama.cpp only takes the argmax path and verifies by sample-and-match. llama.cpp already has the rejection verifier and the `result_q` plumbing (draft-simple and MTP use it), so this is about 40 lines in `common/speculative.cpp`. Expected result on EN chat at T=1: about +15–25% over MTP (arithmetic in §3). Polish prose: about equal to MTP.
3. DSpark drafters (RadixArk v2, RedHat, DimInfer, multilingual/zh/agentic finetunes) load in llama.cpp today (`draft-dspark`). On Qwen3.8-27B chat they are **no better than MTP**: z-lab's head-to-head gives MT-Bench MTP 3.74, DSpark 3.01, DFlash2 4.10. In llama.cpp they also draft greedily (the in-graph Markov chain is argmax), which a vLLM user measured at −23% t/s versus probabilistic at T>0. Second-tier.
4. **There is no EAGLE-3, Medusa/Hydra, or retrained MTP head for Qwen3.8-27B anywhere on HF.** The searches covered `eagle`, `eagle3`, `EAGLE-3`, `medusa`, `hydra`, `speculator`, `-draft` and `MTP` with Qwen3.8 in the name, about 1000 hits each. The only "MTP drafters" are re-packagings of the stock head for MLX. Same-vocab small models (Qwen3.5-0.8B/2B/4B, vocab 248320) work with `draft-simple`, but they cost as much per step as MTP and should accept fewer tokens.
5. There is **no drafter trained on Polish**. The multilingual DSpark covers EN/FR/DE/ES/ZH/IT/PT/JA/RU/NL. Polish needs training, which is the DrafterTraining peer's job. Useful public data with Polish: aya, WildChat. DaoCloud also released a Qwen3.8-27B drafter SFT set.

## 1. Ranked table (chat-style traffic, T=1, this GPU)

The cost model behind the "est. step" column is calibrated on NOTES.md:

- A 6-token verify takes 33.6 ms (Vulkan perf logger).
- mmvq Q4_K runs at 694 GB/s with 4 columns and 573 GB/s with 8. The 6-column rate is assumed at about 630 GB/s, so an 8-token verify comes to about 33.6 × 630/573 ≈ 37 ms.
- MTP drafting is 45 − 33.6 ≈ 11 ms (5 passes).
- A DFlash-family draft is one pass over the ~1.1 GB Q4_K_M backbone plus the 248k LM head (~1.04 GB Q6_K target head) at 8 columns. That gives ≈ 2 + 1.7 ms plus injection and launches, so **≈ 4–5 ms** [INFERENCE].
- DSpark adds a sequential in-graph Markov chain (w2 is 256×248320, read once per position) and CPU sampling over 7×248k logits, so ≈ +2–3 ms [INFERENCE].
- t/s = AL / step. MTP check: 3.0 / 45 ms = 66.7 t/s, against 60–64 measured (the rest is server overhead).

| # | Drafter | Published chat AL (benchmark, setting) | Expected AL here, EN chat T=1 | Est. step (n) | Est. t/s vs MTP 66.7 | llama.cpp status | Download |
|---|---|---|---|---|---|---|---|
| **1** | **z-lab / incoai Qwen3.8-27B-DFlash2** (already at `~/models/draft/…DFlash2-Q4_K_M.gguf`) + **probabilistic path sampling (to implement)** | MT-Bench 4.10 vs MTP-7 3.74 (SGLang, H200, T=1, top-p .95, top-k 20, thinking xhigh, with rejection sampling) [inco.ai/blog/dflash2] | ≈ 3.0 × 1.03 (n 5→7) × 1.10 (DFlash2/MTP ratio) ≈ **3.3–3.4** [INFERENCE] | 37 + 4.5 ≈ 41.5 ms (n=7) | ≈ **80–82 (+20–24%)** | Loads now (`draft-dflash`, auto-detected). Draft path is argmax only: `common/speculative.cpp:1297-1325`. Rejection verifier exists: `common/sampling.cpp:735-839` | have it (1.14 GB) |
| 2 | Same DFlash2, current greedy path | as above | measured locally: en-chat 58.0 t/s at T=1 vs MTP 60.4, so AL ≈ 58 × 0.040 ≈ **2.3–2.4** [INFERENCE from t/s] | ≈ 40 ms (n=6) | ≈ −4% (measured) | works | have it |
| 3 | **RedHatAI/Qwen3.8-27B-speculator.dspark** (5 layers, 8 aux taps, SWA 2048, Markov + confidence heads, trained on 1.74M × 8k-token on-policy examples ≈ 14B tokens) | writing 3.77, question 3.80, qa 4.22, translation 4.55, tool_call 3.76 (vLLM 0.29, 8 drafts, temperature not stated). Card's plot: DSpark8 > MTP8 on HumanEval/math/RAG | ≈ MTP-7 level with greedy chain, ≈ 3.0–3.2 [INFERENCE] | 37 + 7 ≈ 44 ms (n=7; n=8 means a 9-col verify, which is off the mmvq fast path) | ≈ 68–73 (0 to +10%) | Converter handles the speculators schema (`conversion/qwen.py:949-972`); SWA and M-RoPE handled (`:816-835`). Markov chain is greedy (`src/models/dflash.cpp:344-345` TODO) | 3.98 GB BF16, needs conversion (no GGUF) |
| 4 | RadixArk/Qwen3.8-27B-DSpark (v2, 1.86B, 5 full-attn layers) | MT-Bench 3.29, Alpaca 3.23, Arena-Hard 3.25 (SGLang, T=1, thinking). z-lab's own run: MT-Bench 3.01 | ≈ 2.6–2.9 [INFERENCE] | ≈ 44 ms + full-attention draft KV at 200k ctx (≈1.2 GB at q4_0) | ≈ 60–66 (≤ 0%) | `draft-dspark` works | GGUF: Anbeeld Q4_K_M 1.1 GB (BeeLlama fork; plain GGUF) |
| 5 | DimInfer/Qwen3.8-27B-Dspark-v1 (trained on **Q4_K_M GGUF** hidden states, 40k samples) | **llama.cpp**, UD-Q4_K_XL target, **T=0**, n=4: MT-Bench 2.77, Alpaca 3.10, Arena-Hard-v2 2.77. 2.14× over no-spec on a 4090D | ≤ 2.8 at T=1 [INFERENCE] | ≈ 40 ms (best n=4 on CUDA) | ≈ 60–70 | works upstream (the card states so) | Q8_0 GGUF 2.0 GB |
| 6 | ysober/qwen3.8-27b-dspark-zh (RadixArk-v1 1.36B finetune, 76% ZH) | MT-Bench 3.39, Alpaca 3.26, Arena-Hard 2.92 (SGLang, T=0.6, thinking): +5.4% EN over RadixArk v1 | ≈ 2.6–2.8 | ≈ 43 ms | ≤ MTP | `draft-dspark` (needs conversion) | 2.7 GB BF16 |
| 7 | hasanbasbunar/Qwen3.8-27B-DSpark-Multilingual (v1 finetune; 10 languages, **no Polish**; two revisions) | t/s on a DGX Spark, greedy: FR/DE free prose +8–25% over stock v1. Stock v1 free prose sits at only **1.5–1.9 accepted/step** | PL unknown; EN chat ≤ MTP [INFERENCE] | ≈ 43 ms | ≤ MTP | `draft-dspark` (needs conversion) | 2.7 GB BF16 |
| 8 | tiyuvta/Qwen3.8-27B-DSpark-Agentic (1.36B, from scratch) | short chat 2.88 (SGLang T=0.6); 2.23–2.42 greedy on a GGUF engine | ≈ 2.3–2.6 | — | < MTP | `draft-dspark` (needs conversion) | 2.7 GB |
| 9 | DaoCloud/Qwen3.8-27B-DFlash2-Exp (anchor-first DFlash2, 7 queries) | MT-Bench 2.83 thinking / 3.52 non-thinking (vLLM, T=1 / T=0.7) | unknown | — | — | **Not loadable as-is**: the DFlash2 path has no `sample_from_anchor` layout (`speculative.cpp:1265` handles it only for DSpark), and `DFlashModel` doesn't write that key | 3.85 GB |
| 10 | JonasLoos/Qwen3.8-27B-DFlash2-b32 (block 32 finetune) | chat (thinking) 3.9 → 4.2, but only with a **32-token draft tree** on MLX; positions 1–8 unchanged | no gain at n ≤ 7 | — | 0 | loads as DFlash2 | 3.85 GB |
| 11 | RedHat WIP DFlash2 runs (`nm-research/…dflash2.updatedparams.epoch1_end`, 2026-10-09; `inference-optimization/…dflash2.comparisonrecipe*`) | no eval published | unknown | — | — | Speculators schema (`aux_hidden_state_layer_ids`, `transformer_layer_config`) is **not** normalized for `DFlash2DraftModel` (only `DSparkModel` does it, `conversion/qwen.py:963-972`), so the converter needs a small patch | ~4 GB each |
| 12 | Qwen/Qwen3.5-0.8B / 2B, empero-ai/Qwen3.8-2B-Distill (same 248320 vocab) as `draft-simple` | none for this target | < MTP (no target features; not distilled from 27B) [INFERENCE] | 5 × (24-layer hybrid pass ≈ 1.5–2.5 ms) ≈ 8–12 ms draft, same as MTP | ≤ MTP | `draft-simple` | 0.9–4.5 GB |
| — | EAGLE-3 / Medusa / Hydra / retrained MTP for Qwen3.8-27B | **none exist** | — | — | — | `draft-eagle3` would load one (`speculative.cpp:515-563`, needs 3 extract layers; qwen35 supports layer-input extraction, `src/models/qwen35.cpp`) | — |

## 2. Per-drafter evidence and details

### DFlash2: incoai/Qwen3.8-27B-DFlash2 (mirror z-lab/Qwen3.8-27B-DFlash2; GGUF z-lab/…-GGUF)
- Sources: https://huggingface.co/z-lab/Qwen3.8-27B-DFlash2, https://inco.ai/blog/dflash2/ (2026-08-18).
- Architecture: 5 layers, hidden 5120, FFN 17408, SWA 2048 (small draft KV), two-tap dynamic convolution, top-16 candidate selector (rank 256), block 8 (7 drafts). Taps on target layers 5/19/33/47/61. Full 248320 vocab through the target LM head, then top-16.
- Published AL at T=1, thinking xhigh, Qwen3.8-27B, 7 drafts, MTP / DSpark / DFlash2:

  | Benchmark | MTP | DSpark | DFlash2 |
  |---|---|---|---|
  | GSM8K | 5.02 | 4.36 | 5.46 |
  | MATH-500 | 4.72 | 3.92 | 5.28 |
  | HumanEval | 3.91 | 3.30 | 4.39 |
  | MBPP | 3.99 | 3.51 | 4.79 |
  | MT-Bench | 3.74 | 3.01 | 4.10 |

  Throughput at concurrency 1 on H200, MT-Bench: MTP 134.9, DFlash2 184.0 (+36%). Much of that is the cheaper single-pass draft on H200.
- **Sampling, question (4) of the task.** The blog says: "greedy follows the best successor at each step, *sampling draws from the same scores*, and rejection sampling restores the exact target distribution". Upstream therefore drafts probabilistically at T>0. llama.cpp (`common/speculative.cpp:1297-1325`) always takes `max_element` of the selector scores and never fills `dp.result_q`, so the server falls back to sample-and-match (`tools/server/server-context.cpp:4409-4426`).
- With a deterministic draft, rejection sampling is mathematically identical to exact match. With q = δ_x the acceptance is min(1, p(x)) = p(x), and the residual is p restricted to y ≠ x. "Adding rejection sampling" alone therefore gains nothing. The gain needs a **sampled draft with a known q**, which DFlash2 provides: q_t(b | a) = softmax over the 16 pairwise scores `S_t(a,b)`, conditioned on the sampled predecessor a. That is why the objection in PR #27694 ("DFlash positions are not conditioned on each other, so sampling one breaks the rest") applies to plain DFlash and only partially to DFlash2.
- The PR #27342 benchmark (llama.cpp, M5 Pro, T=1, GSM8K) shows the drafter quant doesn't matter: Q4_K_M AL 5.03 vs BF16 4.92. https://github.com/ggml-org/llama.cpp/pull/27342
- Open upstream perf PR: #30197 "batch DFlash target feature reads", +1.9% on Qwen3.8-27B+DFlash2. https://github.com/ggml-org/llama.cpp/pull/30197
- Our tree already has #30111 (the DFlash output-head sharing fix, which had caused 0% acceptance on some drafts); it is commit a11f57ba9 in `git log`.

### DSpark family (DFlash backbone + Markov head ± confidence head; paper arXiv:2607.05147)
- Paper (DeepSeek/PKU): https://arxiv.org/abs/2607.05147. DSpark-on-Qwen3 beats EAGLE-3 by 27–31% and DFlash by 16–18% in macro AL. The Markov head adds bias B(x_{k−1}, ·) = W1[x_{k−1}] W2 (rank 256), sampled left to right.
- llama.cpp: PR #25173 (merged 2026-07-28), https://github.com/ggml-org/llama.cpp/pull/25173. The chain is computed in-graph with `ggml_argmax` (`src/models/dflash.cpp:344-383`, "TODO: the in-graph chain is greedy"), so it is **greedy-only at T>0**. The confidence head is used only for `p_min` truncation (`speculative.cpp:1059-1067, 1327-1337`).
- Evidence that probabilistic drafting matters for DSpark at T>0: Doopeworld/Qwen3.8-27B-DSpark-vLLM (vLLM, Arc B70) measured greedy 42 t/s with AL 1.94–2.67, against probabilistic 52 t/s (+23%) with AL 2.45–2.79. https://huggingface.co/Doopeworld/Qwen3.8-27B-DSpark-vLLM
- Making it probabilistic in llama.cpp needs Gumbel-max inside the graph: add a noise input and take `argmax(col/T + g)` instead of `argmax(col)`. Then expose softmax(col) per position as q [INFERENCE: design only].
- RadixArk v2: https://huggingface.co/RadixArk/Qwen3.8-27B-DSpark. Draft vocab 248320, block 7, 5 **full-attention** layers (draft KV grows with context; at 204800 ctx that is ≈ 5·8·128·2·204800·0.56 B ≈ 1.2 GB at q4_0 [INFERENCE]). AL at T=1: chat 3.23–3.29, code 3.35–4.06, math 3.9–4.5. Note that the current repo config is the 1.86B v2. The finetunes (ysober, hasanbasbunar, tiyuvta) derive from the 1.36B v1 layout (FFN 10240, taps 4/16/28/40/52).
- RedHat: https://huggingface.co/RedHatAI/Qwen3.8-27B-speculator.dspark. Draft vocab 248320, block 8 with `sample_from_anchor` (8 drafts), SWA 2048, 8 aux taps (input to the fc is 8×5120). Loss is 0.1 CE + 0.9 TV, which targets acceptance under sampling. It is the most heavily trained DSpark found: ≈1.74M × 8k tokens on Qwen3.8-27B regenerations of Open-PerfectBlend, stopped at 75% of one epoch. Long-context AL holds at 4.3–4.8 up to 1M tokens. Converter support: `conversion/qwen.py:937-1025` (speculators schema, d2t).
- orestis-z/Qwen3.8-27B-speculator.dspark is a RedHat-style DSpark with **draft vocab 64000 (d2t)**. No card or eval. A 64k head would cut DSpark's LM-head and Markov costs about 4× (same idea as our `--spec-draft-vocab`).
- DimInfer: https://huggingface.co/DimInfer/Qwen3.8-27B-Dspark-v1. It is the only drafter with **llama.cpp numbers on UD-Q4_K_XL**. On a 4090D at T=0, the n_max sweep gives AL 2.49 (n=2), 2.94 (n=3), 3.27 (n=4), 3.53 (n=5), 3.81 (n=6), 3.74 (n=8). t/s peaks at n=4 because llama.cpp DSpark's draft cost grows with n (sequential chain plus CPU sampling). Per-dataset at UD-Q4_K_XL: MT-Bench 2.77, Alpaca 3.10, Arena-Hard 2.77, MATH 4.06. That is worse than our MTP on chat.

### EAGLE-3
- No Qwen3.8-27B head on HF. EAGLE-3 heads exist for Qwen3.6-27B (`Dogacel/specdrift-qwen3.6-27b-eagle3`, `gelim/Qwen3.6-27B-PRISM-EAGLE3-GGUF`). Qwen3.6 and 3.8 share config and tokenizer (DimInfer's card: "same config … same vocab.json/merges.txt"), but the weights differ, so the hidden-state distributions differ. Zero-shot use would accept poorly [INFERENCE]. At most it could serve as a warm start for training.
- The ecosystem has moved to DFlash/DSpark for this model: RadixArk's card compares against MTP ("EAGLE" there = the built-in MTP head), not against an external EAGLE-3.
- Even with a head, EAGLE-3 drafts autoregressively: n sequential passes, like MTP. The DSpark paper reports EAGLE-3 27–31% below DSpark on Qwen3-4B/8B/14B.

### Retrained MTP heads
- None found. `seabit-ai/Qwen3.8-27B-MTP-draft`, `caslca/…-mtp-drafter` and the `Youssofal/…MTPLX` packs are the stock `mtp.*` tensors re-packed for MLX; caslca only re-adds +1.0 norm offsets. Perplexity's "dspark2 MTP" in pplx-qwen-3-8-27b-dflash2 is 849 MB and is described as reaching "similar acceptance" to DFlash2 at about 2× slower decode. It looks like the stock head [INFERENCE].
- Open llama.cpp PRs relevant to MTP: #27210 adaptive MTP depth, #29143 d2t vocab trim (equivalent to our local `--spec-draft-vocab`).

### Small same-tokenizer models
- Qwen/Qwen3.5-0.8B, 2B and 4B have vocab 248320, the same as Qwen3.8-27B (config.json checked). empero-ai/Qwen3.8-{2B,4B,9B}-Distill are Qwen3.5 bases fine-tuned on Qwen3.8-**2.4T** traces, not the 27B. `inference-optimization/Qwen3.8-1.0B-A0.6B` is a toy random test model.
- `draft-simple` cost = n × a full 24-layer DeltaNet-hybrid pass per draft token, about the same as or more than MTP's 5 one-layer passes. With no access to target features, AL on chat should be below MTP's [INFERENCE]. Not worth testing first.

## 3. Arithmetic for the top recommendation

Baseline: MTP n=5, AL 3.0, step 45 ms, so 66.7 t/s (60–64 measured).

DFlash2 n=7 step: verify of 8 tokens ≈ 37 ms, plus a one-pass draft ≈ 4.5 ms, so ≈ 41.5 ms [INFERENCE].
- Break-even against MTP: AL ≥ 66.7 × 0.0415 = **2.77**.
- Current greedy DFlash2 at T=1 sits around 2.3–2.4 (from the measured 58 t/s × ≈ 0.040 s), which is below break-even. That matches the measurements.
- Published T=1 ratio DFlash2/MTP-7 on MT-Bench: 4.10 / 3.74 = 1.10. Our MTP at n=7 would be about 3.0 × 1.03 ≈ 3.1, so DFlash2 with probabilistic path ≈ 3.1 × 1.10 ≈ **3.4**, giving 3.4 / 0.0415 ≈ **82 t/s (+23% over MTP)** on EN chat.
- For a "big jump" of +50% (≈ 100 t/s), chat AL would need ≥ 4.15 at T=1 non-thinking. No published 7-token linear drafter reaches that on chat. Only longer drafts with tree verification do (JonasLoos: 4.2 with a 32-token tree on MLX), and a 32-token verify is far off our 8-column mmvq fast path.
- Polish prose: local DFlash greedy PL prose was 54.9 vs MTP 63.9 t/s, so even with sampling PL is expected around MTP parity. A Polish-aware drafter needs training.
- Uncertainty: the 1.10 ratio comes from thinking-mode traces on an H200 harness. Our en-chat is non-thinking. DaoCloud's DFlash2-Exp got *higher* AL in non-thinking mode (MT-Bench 3.52 vs 2.83), so the direction of the mode effect is unclear.

## 4. Concrete actions for the parent (in order)

1. **Measure before coding.** Run DFlash2 n=6 and n=7 against MTP n=5 at T=0 and T=1 on en-chat and pl-prose, and log `draft acceptance` (accepted/proposed) as well as t/s. That separates the AL drop at T=1 from per-step overhead. The T=1 penalty locally is −21% for DFlash and only −6% for MTP (NOTES table, 90.6 → 71.9 vs 86.3 → 81.1), which is suspicious.
2. **Implement probabilistic DFlash2 drafting** in `common_speculative_impl_draft_dflash::draft()` (`common/speculative.cpp:1297-1325`):
   - When `params.probabilistic && dp.result_q`, sample `predecessor` from softmax(scores / T_target) instead of argmax.
   - Push `{id = row[k], p = softmax_k}` for all 16 candidates into `(*dp.result_q)[i]`.
   - Clear `result_q` on the `p_min` and `n_min` early exits, as MTP does at lines 1684-1697.
   - Use an RNG seeded from `dp.seed`.
   - The verifier (`common_sampler_sample_and_accept_n_rejection`, `common/sampling.cpp:735`) already handles a partial-support q: tokens outside q keep all of p.
   - Effort: about 40–60 lines, no graph changes, lossless by construction.
3. Try **n=7** with DFlash2 (an 8-column verify, still inside the RDNA3 mmvq 2–8 kernels; n=8 drops to the slow path per NOTES).
4. Optional, for cost: a reduced-vocab LM head for the DFlash2 draft. The selector only needs top-16, so the 64k ranking from `--spec-draft-vocab` would cut the ≈ 1.0 GB head read to ≈ 0.27 GB, saving about 1.2 ms per step (≈ 3%) [INFERENCE].
5. Second experiment: **RedHat DSpark** (4 GB BF16, convert with `--target-model-dir`, quantize to Q4_K_M, n=7). Only worth it after adding Gumbel-max sampling to the Markov chain (`src/models/dflash.cpp:381-383`). Expect at most +10% over MTP on chat.
6. Do not bother with: RadixArk v1/v2 DSpark and its finetunes (≤ MTP on chat per the z-lab head-to-head), DFlash2-b32 (needs tree verify), Qwen3.5 small models (`draft-simple`), Qwen3.6 EAGLE-3 heads (target mismatch).

## 5. Draft vocab sizes (from config.json)

| Drafter | draft vocab |
|---|---|
| z-lab/incoai DFlash2, JonasLoos b32, DaoCloud Exp, RedHat DFlash2 WIP | 248320 (target LM head) → top-16 selector |
| RadixArk DSpark, RedHat DSpark, ysober, hasanbasbunar, tiyuvta, DimInfer | 248320 |
| orestis-z/Qwen3.8-27B-speculator.dspark | **64000** (d2t; supported by the converter, `conversion/qwen.py:977-1025`, and the graph, `src/models/dflash.cpp:349-357`) |
| Stock MTP head (current) | 248320; locally trimmed to 64k with `--spec-draft-vocab` |
