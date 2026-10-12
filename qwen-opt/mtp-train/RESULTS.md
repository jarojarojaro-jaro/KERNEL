# MTP head self-distillation — phase 1 (feasibility, go/no-go)

Target: Qwen3.8-27B-UD-Q4_K_XL, built-in MTP head `blk.64`, served as in `run-llm.sh qwen mtp rocm`
(KV q4_0, MTP n=4 greedy draft chain, 64k draft vocab, reasoning effort low, GGUF sampler T=1 top-k 20 top-p 0.95, min-p 0.05).
Date 2026-10-12, fork amd-opt @c90db29c6.

## 1. Torch on gfx1100 (`smoke_torch.py`)

torch 2.14.1+rocm7.14, RX 7900 XTX gfx1100, 24 GiB. 4096² matmul: bf16 71 TFLOP/s (rel err 2.9e-3), fp16 74 TFLOP/s.

## 2. Data + extractor

- `gen.py` / `gen_block.sh`: 57 prompts (27 PL, 30 EN; chat/prose/code/tech) answered by the Q4 target through
  `llama-server -np 4` with MTP, server default sampler, thinking low. Exact token ids via `/completion` `return_tokens`.
  **69,207 response tokens** (PL 33.8k, EN 35.4k), max 1400 tokens/answer (31 truncated). Aggregate 107–127 t/s.
  Reasoning is English even for PL prompts, so PL rows are split into `think` and `answer`.
- `mtp_extract.cpp` (libllama, `src/llama-ext.h`), per sequence:
  - target teacher-forced pass (KV q4_0 as served): `h.f16` = h_nextn at every position, and `top.bin` = top-32 full-vocab log-probs per response position;
  - MTP teacher-forced pass (draft ctx KV f16 as served), with depth-1 draft logits + h_nextn on parity sequences;
  - for **every** response position t, the server's greedy draft chain (`llama_set_mtp_draft_chain`, row 0 = (x_t, h_{t-1}), prefix KV from teacher-forced pairs). Output: `chain.bin`.
  - Speed: 2.3 ms/token for the target pass (incl. top-k on the CPU) + 3.7 ms per draft chain. The whole sample took 7.4 min.
- Fork quirk found: with `llama_set_embeddings_nextn(ctx_mtp, true, masked=true)` and a multi-row batch where only some
  rows are outputs, the context keeps the first n_outputs rows of `t_h_nextn` (taken before the output gather). So
  `llama_get_embeddings_nextn_ith(i)` returns the wrong row. Serving is unaffected: draft batches have one row, or use the chain.
  The extractor works around it by marking every row as an output in parity batches.

## 3. PyTorch mirror (`mtp_torch.py`) vs llama.cpp

blk.64 is dequantized with the fork's gguf-py (Q6_K/Q8_0/F32), along with token_embd (Q4_K, 248k rows, fp16 cache) and output rows for the 64k draft vocab (Q6_K).
The data flow mirrors qwen35.cpp graph_mtp. With equal text positions, IMRoPE reduces to NeoX rope on 64 dims, base 1e7.
`forward_chain_step` rebuilds the server's draft KV layout: the prefix comes from teacher-forced K/V up to t, plus this chain's own K/V.

| check (1536 depth-1 positions, 3 seqs; chain: all 69,207 starts) | fp32 | bf16 |
|---|---|---|
| depth-1 top-1 agreement | 98.4 % | 98.4 % |
| logit rel-L2 (mean / p99) | 1.54 % / 2.34 % | 1.69 % / 2.51 % |
| TV(softmax llama, softmax torch) | 0.015 | 0.016 |
| h_nextn rel-L2 | 1.6 % | – |
| llama.cpp margin at top-1 disagreements (median) | 0.06 logits (overall median 3.1) | same |
| draft-chain token agreement d1/d2/d3/d4 | 99.6 / 99.0 / 98.2 / 97.3 % | – |
| acceptance table (all) | identical to llama.cpp to 3 decimals | – |

Every top-1 disagreement is a near-tie. The ~1.5 % residual is consistent with llama.cpp's q8_1 activation quantization in the quantized matmuls plus the f16 FA. The mirror is accurate enough for training and offline evaluation.

## 4. Offline per-depth acceptance of the shipped head (go/no-go measurement)

Start positions: every response token (n). `cum@k` = P(the first k drafts are accepted) when greedy drafts are verified against the tokens the target actually sampled.
The `expected` estimator, prod 1[match] · p'(d_k), agrees with `realized` to ±0.003 (see `results_llama.md`). tok/step = 1 + Σ cum (n_draft = 4).
`oracle` = greedy drafting with the target's own argmax (ceiling for any greedy drafter).
`Σmin(p',q10)` = per-depth rejection-sampling acceptance of the head's top-10 T=1 distribution (PyTorch mirror).

| group | n | OOV% | shipped cum@1..4 (realized) | shipped cond@1..4 | tok/step | T=0 agree tok/step | Σmin(p',q10) cond@1..4 | oracle cond@1..4 | oracle tok/step |
|---|---|---|---|---|---|---|---|---|---|
| en | 35279 | 2.0 | 0.785 / 0.581 / 0.427 / 0.315 | 0.785 / 0.741 / 0.734 / 0.739 | 3.11 | 3.18 | 0.825 / 0.726 / 0.728 / 0.734 | 0.870 / 0.882 / 0.890 / 0.895 | 3.93 |
| pl | 33757 | 3.7 | 0.773 / 0.548 / 0.382 / 0.270 | 0.773 / 0.710 / 0.696 / 0.709 | 2.97 | 3.04 | 0.804 / 0.698 / 0.693 / 0.706 | 0.872 / 0.880 / 0.883 / 0.887 | 3.92 |
| en-think | 11700 | 1.9 | 0.779 / 0.568 / 0.408 / 0.291 | 0.779 / 0.729 / 0.719 / 0.712 | 3.05 | 3.13 | 0.819 / 0.717 / 0.713 / 0.711 | 0.861 / 0.877 / 0.881 / 0.882 | 3.87 |
| en-answer | 23579 | 2.1 | 0.787 / 0.588 / 0.436 / 0.327 | 0.787 / 0.746 / 0.741 / 0.751 | 3.14 | 3.21 | 0.828 / 0.730 / 0.735 / 0.744 | 0.875 / 0.884 / 0.894 / 0.901 | 3.96 |
| pl-think | 9990 | 2.1 | 0.807 / 0.614 / 0.462 / 0.342 | 0.807 / 0.761 / 0.753 / 0.741 | 3.23 | 3.29 | 0.842 / 0.751 / 0.744 / 0.741 | 0.878 / 0.893 / 0.896 / 0.899 | 4.00 |
| pl-answer | 23767 | 4.3 | 0.758 / 0.521 / 0.348 / 0.240 | 0.758 / 0.687 / 0.667 / 0.691 | 2.87 | 2.93 | 0.788 / 0.674 / 0.667 / 0.686 | 0.870 / 0.875 / 0.877 / 0.882 | 3.89 |
| en-chat | 8736 | 2.3 | 0.716 / 0.473 / 0.305 / 0.191 | 0.716 / 0.661 / 0.645 / 0.626 | 2.68 | 2.79 | 0.772 / 0.647 / 0.639 / 0.630 | 0.823 / 0.831 / 0.836 / 0.837 | 3.56 |
| en-prose | 7766 | 2.9 | 0.686 / 0.415 / 0.244 / 0.145 | 0.686 / 0.606 / 0.588 / 0.594 | 2.49 | 2.58 | 0.745 / 0.593 / 0.579 / 0.584 | 0.811 / 0.822 / 0.826 / 0.831 | 3.49 |
| en-tech | 8275 | 1.6 | 0.822 / 0.634 / 0.482 / 0.363 | 0.822 / 0.771 / 0.760 / 0.753 | 3.30 | 3.36 | 0.857 / 0.760 / 0.753 / 0.751 | 0.894 / 0.900 / 0.907 / 0.910 | 4.09 |
| en-code | 10502 | 1.5 | 0.885 / 0.752 / 0.619 / 0.507 | 0.885 / 0.850 / 0.823 / 0.819 | 3.76 | 3.81 | 0.904 / 0.838 / 0.824 / 0.813 | 0.935 / 0.944 / 0.947 / 0.949 | 4.45 |
| pl-chat | 11255 | 3.5 | 0.771 / 0.543 / 0.375 / 0.264 | 0.771 / 0.705 / 0.691 / 0.703 | 2.95 | 3.02 | 0.804 / 0.695 / 0.692 / 0.696 | 0.867 / 0.874 / 0.875 / 0.878 | 3.87 |
| pl-prose | 9943 | 5.0 | 0.693 / 0.418 / 0.236 / 0.132 | 0.693 / 0.603 / 0.564 / 0.558 | 2.48 | 2.54 | 0.733 / 0.588 / 0.560 / 0.563 | 0.828 / 0.833 / 0.832 / 0.833 | 3.57 |
| pl-tech | 5574 | 3.0 | 0.816 / 0.609 / 0.431 / 0.306 | 0.816 / 0.746 / 0.709 / 0.710 | 3.16 | 3.23 | 0.836 / 0.735 / 0.713 / 0.707 | 0.900 / 0.908 / 0.910 / 0.913 | 4.14 |
| pl-code | 6985 | 2.7 | 0.855 / 0.694 / 0.560 / 0.450 | 0.855 / 0.812 / 0.806 / 0.804 | 3.56 | 3.62 | 0.880 / 0.803 / 0.797 / 0.803 | 0.922 / 0.929 / 0.932 / 0.935 | 4.32 |
| all | 69036 | 2.8 | 0.779 / 0.565 / 0.405 / 0.293 | 0.779 / 0.726 / 0.716 / 0.725 | 3.04 | 3.11 | 0.815 / 0.712 / 0.711 / 0.721 | 0.871 / 0.881 / 0.886 / 0.891 | 3.93 |

Sanity check against the live server (different prompts; n=4, 6 prompts × 3 seeds): pl-proza 2.65, en-chat 2.43, pl-kod 3.64, en-tech 3.53 tok/step.
Offline: pl-prose 2.48, en-chat 2.68, pl-code 3.56, en-tech 3.30. Same ballpark.

What the numbers say:
- **No language gap to fix.** Shipped/oracle conditional ratio:
  - PL prose: d1 0.84, d2–4 0.72 / 0.68 / 0.67.
  - EN prose: d1 0.85, d2–4 0.74 / 0.71 / 0.71.
  - PL-answer 2.87 vs EN-answer 3.14 tok/step, but the oracle is equal (3.89 vs 3.96).
  - So PL prose is slow mainly because the target itself is less predictable. The head is not specifically weak at Polish.
  - KaedeTai's lever (zh 56.8→62.6 %, EN flat) was a *language* deficit: their stock head was 13 pp worse on zh than on EN. We don't have that deficit.
- **There is a generic depth/recursion gap.** The shipped conditional acceptance falls from d1 to d2+ (all: 0.78 → 0.72), while the oracle stays flat at 0.87–0.89.
  The shipped/oracle ratio drops from 0.90 (d1) to 0.83 (d2–4). This is what recursive multi-step self-distillation targets: FastMTP, and Red Hat's +0.015/+0.05/+0.13 per-depth gains on a natively multi-step head.
- **The shipped head is overconfident for rejection sampling.** Σmin(p', q10) ≈ the T=0 agreement (all: 3.11 vs 3.11 tok/step) and only slightly above greedy (3.04).
  This explains why `--spec-draft-sampling probabilistic` didn't help. A KL/TV-distilled head is the only route to the larger probabilistic upside; its ceiling is 1.0 per depth, not the 0.87–0.89 greedy oracle.
- The q4 trunk vs the bf16 training trunk can't be separated here, because there is no bf16 reference on this box.

Projected greedy tok/step (`results_projection.txt`, applied to the per-group conditional acceptances):

| scenario | all | en | pl | en-chat | pl-prose | en-code | pl-code |
|---|---|---|---|---|---|---|---|
| shipped | 3.04 | 3.11 | 2.97 | 2.69 | 2.48 | 3.76 | 3.56 |
| close 25 % of gap to oracle per depth | +6 % | +6 % | +7 % | +7 % | +9 % | +4 % | +5 % |
| Red Hat-like Δcond (+.015/+.05/+.13/+.13, capped at oracle) | +11 % | +11 % | +11 % | +10 % | +9 % | +12 % | +12 % |
| close 50 % of gap | +13 % | +12 % | +15 % | +15 % | +19 % | +9 % | +10 % |

## 5. Phase 2 plan and estimates (measured rates)

- **Data (pilot):**
  - ~1.7 k prompts → 2 M response tokens. Mix 40 % PL chat/prose, 35 % EN chat/prose, 25 % code/tech.
  - Prompt sources: the user's logs if any; WildChat PL/EN, oasst2 pl, aya pl, ultrachat.
  - Thinking low as served; max 2048 tokens.
  - Hold out 5 % of prompts for evaluation.
- **Generation:** measured 107–127 t/s aggregate with `-np 4` + MTP. Try `-np 8` first. At ~120 t/s, 2 M tokens ≈ 4.6 h of GPU time, ≈ 5.3 h wall in 8-min blocks with 60 s pauses. Full run (10 M): ~1 day.
- **Extraction (target pass only for training data):**
  - 2.3 ms/token → 2 M tokens ≈ 77 min.
  - Chain evaluation only on the held-out split: 3.7 ms/token.
  - Disk: h 10 KB/token + top-32 256 B/token → **≈ 21 GB per 2 M tokens** (full run 10 M ≈ 105 GB), well inside the ~350 GB free. No rolling shards needed.
- **Training** (`bench_train.py`, measured):
  - Recursive K=4, T=2048, bf16, frozen 64k head and embedding, no activation recompute: **2.3 k tokens/s fwd+bwd, 12.1 GiB peak**. fp32 master weights and Adam add ~5 GB, which still fits.
  - Pilot 2 M × 3 epochs ≈ 45–60 min. Full 10 M × 2 epochs ≈ 2.5 h. Train in ≤10-min GPU blocks with checkpoints.
  - Recipe:
    - loss = TV/forward-KL against the stored top-32 sampler distribution p', plus 0.1·CE;
    - per-depth weights β=0.6–0.7;
    - lr 5e-5 cosine, AdamW(0.9, 0.95), grad clip 1;
    - loss on response tokens only; drop targets outside the draft vocab (2.8 %);
    - draft-chain KV layout exactly as `forward_chain_step`.
- **Evaluation and writeback:**
  - Offline held-out table from this phase (base vs trained, greedy and Σmin), using the parity-validated mirror.
  - Requantize to Q6_K/Q8_0 with `ggml_quantize_chunk` (ctypes) into a **copy** of the GGUF, then rerun the extractor's chain evaluation and `spec_sweep.sh` (greedy and probabilistic, n=4/5/6).
- **Pilot wall time:** ≈ 8–9 h, mostly unattended (generation 5.3 h, extraction 1.5 h, training 1 h, evaluation 0.5 h).

## Recommendation: GO for the 2 M-token pilot, with a hard abort gate

- **Expected gain:** realistic greedy gain is +5–11 % tok/step overall (≈ +4–9 t/s on 88 t/s), roughly the same for PL and EN. The largest relative gains are on prose/chat, at deeper positions.
- **Why the cost is bounded:** the infrastructure is built and validated (extractor, mirror parity, offline evaluation), and the pilot is ~8 h of unattended GPU time with no change to the trunk.
- **Upside:** if KL/TV training makes probabilistic drafting pay off at T=1. The shipped head can't, being overconfident.
- **Abort gate:** if the trained head's held-out offline tok/step (greedy *and* probabilistic) is < +4 % over shipped on `all` and < +6 % on PL/EN chat+prose, stop. Don't scale to 10 M.
- **Don't plan a PL-specific head.** The data shows no PL-specific deficit to recover (unlike the KaedeTai zh case).
