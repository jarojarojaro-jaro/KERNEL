# Training a better drafter for Qwen3.8-27B-UD-Q4_K_XL on one RX 7900 XTX

Scope: training or fine-tuning a drafter for this target, on this machine. Everything here was read, not run. No GPU work was done.
Tags: `[V]` = verified locally or at a cited URL. `[INFERENCE]` = my estimate.

## TL;DR / recommendation

1. **Do this: fine-tune the built-in MTP head (`blk.64.*`) by self-distillation.** Use the FastMTP recipe. Take hidden states and teacher distributions from **the Q4 GGUF itself, through llama.cpp**. Train in PyTorch-ROCm on the same GPU, alternating with extraction. Patch the trained weights back into `blk.64.*`, keeping the same quant types.
   - Cost: a few hundred lines of code (a C++ extractor plus a PyTorch trainer), about 3–6 h wall-clock for a pilot, about 1–2 days for the full run.
   - Expected chat/prose gain from the CE recipe alone: **+10–17 %** tokens/step, i.e. ~60 → 66–70 t/s on en-chat [INFERENCE, arithmetic in §1.6].
   - Upside if KL/TV distillation makes `--spec-draft-sampling probabilistic` work at T=1: **+25 %** or more [INFERENCE, §1.6]. That is the only route here that plausibly gives a "big jump" on T=1 chat.
2. **Don't train EAGLE-3.** The public EAGLE-3 drafter for this model family reaches τ≈2.2 (stock Qwen3.6-27B). The native Qwen3.8 MTP reaches τ≈3.74 on MT-Bench. Training from scratch needs ~10–50× more data, 3× the hidden-state storage, and days of GPU time.
3. **DFlash2 fine-tune: only after llama.cpp's DFlash path gets rejection sampling.** Today it verifies by exact match only (NOTES.md:174), so a better drafter can't fix T=1 chat. The public DFlash2 training objective is not released either.

---

## 0. Facts about this setup that drive the design

| Fact | Source |
|---|---|
| MTP block = one full-attention Qwen3.5 decoder block with a gated query. Data flow: `eh_proj([enorm(emb(tok)); hnorm(h)])` → attn (Q/gate interleaved per head, q/k norm, partial MRoPE) → FFN SwiGLU → `shared_head_norm` → LM head | `~/llama-master/src/models/qwen35.cpp:555-671` [V] |
| The MTP has no own `embed_tokens` or `shared_head_head` here. It uses the trunk's `token_embd` (**Q4_K**) and `output` (**Q6_K**) | qwen35.cpp:534, :651; GGUF dump [V] |
| `h` fed to the MTP = `output_norm(final residual)` of the target, i.e. `t_h_nextn` | qwen35.cpp:210-213 [V] |
| Inference pairing: MTP input at pos t = (token t, target h at t-1). The output predicts t+1. Draft step k feeds back the MTP's own output h (`llama_get_embeddings_nextn_ith(ctx_dft)`) | `common/speculative.cpp:1599-1610, 1747, 1803-1805` [V] |
| MTP KV during drafting: the prefix KV was written from (token, **target** h) pairs. Only the current draft chain's KV comes from recursive h | speculative.cpp:1713-1717, 1803 [V] |
| Draft sampler: top-k 10. Greedy unless `probabilistic`. With rejection, q is re-tuned to the target temperature | speculative.cpp:1456-1460, 1685-1697, 34-36 [V] |
| Hidden-state API: `llama_set_embeddings_nextn(ctx, true, /*masked*/false)` + `llama_get_embeddings_nextn[_ith]` give every token's h. `llama_set_embeddings_layer_inp` / `llama_get_embeddings_layer_inp` give any layer's input (for EAGLE-3/DFlash features). qwen35 fills `t_layer_inp[il]` | `src/llama-ext.h:93-129`, qwen35.cpp:160 [V] |
| MTP tensors in this GGUF: attn_q Q6_K, attn_k/v Q8_0, attn_output Q6_K, ffn_{gate,up,down} Q6_K, nextn.eh_proj Q6_K, norms F32. Total ≈ **351 MB**, ≈ **424.7 M** matmul params | GGUF dump [V] |
| The bf16 originals of all 15 `mtp.*` tensors are in `Qwen/Qwen3.8-27B` shard `model-00018-of-00018.safetensors` (3.39 GB; also holds `lm_head`) | HF index.json [V] |
| GGUF norm weights already include the Qwen3.5 `+1` (zero-centred RMSNorm). Use plain `x·w` when the weights come from the GGUF | `conversion/qwen.py:402-403` [V] |
| llama.cpp can load an MTP-only sidecar GGUF. But `token_embd` is created as required (qwen35.cpp:40), so a sidecar duplicates the ~1.76 GB embd+output in VRAM. **Patch `blk.64.*` in place instead** | `src/llama-model.cpp:3551-3568`, `conversion/qwen.py:341-345` [V] |
| Disk: 22 GB free (`df`), not 35. RAM 62 GB, ~40 GB free. User is in `render`/`video` groups → GPU usable without sudo | `df`, `free`, `id` [V] |

---

## 1. Option A (recommended): MTP-head self-distillation (FastMTP-style)

### 1.1 Evidence

- **FastMTP** ([arXiv 2509.18362](https://arxiv.org/abs/2509.18362), [code](https://github.com/Tencent-BAC/FastMTP)) on MiMo-7B. Freeze the trunk, embeddings and LM head. Fine-tune only the single MTP head, **recursively** (step k consumes step k-1's output h). Loss is CE with weights α_k = β^(k-1)/Σβ^(j-1), β=0.6, K=3. Data is **self-distilled** (prompts re-answered by the target): 389 K samples, 3 epochs, lr 5e-5 cosine, warmup 0.05, AdamW(0.9, 0.95), global batch 64, under 1 day on one H20 server. Table 1, K=3:
  - MT-Bench τ: vanilla MTP 1.86 → fixed-data FT 2.48 → **self-data FT 2.69**. Self-generated data beats original dataset responses: +0.21 τ on MT, +0.19 mean.
  - Mean over 7 tasks: 1.83 → 2.73 τ.
  - Caveat: MiMo's MTP was **never trained recursively**, so most of FastMTP's gain does not transfer here.
- **The more relevant data point: Qwen3-Next, whose MTP was already trained multi-step.** The [Qwen3-Next blog](https://www.alibabacloud.com/blog/qwen3-next-towards-ultimate-training-%26-inference-efficiency_602580) says "multi-step training that maintains consistency between training and inference". Red Hat fine-tuned its native MTP FastMTP-style on ~8 K GSM8K samples ([Speculators 0.6.0 article](https://developers.redhat.com/articles/2026/09/08/optimize-vllm-speculative-decoding-fastmtp-heads)):
  - Per-position acceptance 0.897 / 0.719 / 0.476 → 0.912 / 0.776 / 0.616.
  - τ = 1+Σ: 3.09 → **3.30 (+6.8 %)**, in-domain.
  - Conditional per-step acceptance: 0.897 / 0.80 / 0.66 → 0.912 / 0.85 / 0.79. **The gain grows with depth** (+0.015, +0.05, +0.13).
- Qwen3.8-27B's MTP is strong at 7 draft tokens: τ 3.74 MT-Bench, 3.91 HumanEval at T=1 on a BF16 target ([DFlash2 card](https://huggingface.co/z-lab/Qwen3.8-27B-DFlash2)). On this Q4 target at n=5 and T=1, the user measures ~2.6–2.8 tokens/step on chat and ~2.2 on PL prose. Part of that gap is content (no thinking, PL), and part may be the Q4 trunk feeding the MTP different h than it was trained on. **Self-distilling on the Q4 trunk's h directly removes the second part.**
- Domain and language matter: language-specific drafters trained with pretrain-then-finetune give large multilingual speedups ([Yi et al., EMNLP 2024, arXiv 2406.16758](https://arxiv.org/abs/2406.16758)). For domain drafters, offline distillation beats online by 11–25 %, white-box (logits) beats black-box (tokens) by 2–10 %, and synthetic prompts reach 80–93 % of the benefit of real user prompts ([arXiv 2503.07807](https://arxiv.org/abs/2503.07807)).
- The divergence should match the decoding mode. DistillSpec ([arXiv 2310.08461](https://arxiv.org/abs/2310.08461)) gets 10–45 % over standard SD with on-policy data and a task-specific divergence. TV distance is exactly 1 − acceptance under rejection sampling. Speculators' DSpark example uses `--loss-fn '{"ce": 0.1, "tv": 0.9}'` ([train tutorial](https://docs.vllm.ai/projects/speculators/en/latest/user_guide/tutorials/train/)).

### 1.2 Q4 outputs vs bf16: does it matter? Yes. Train on Q4.

- At serve time the verifier is the **Q4 model**. Acceptance is Σ min(p_Q4, q), or p_Q4(argmax q) for greedy drafts. So the distribution to match is p_Q4, not p_bf16.
- At serve time the MTP's input h comes from the **Q4 trunk**. Shipped MTP weights were trained on bf16 h, so feeding Q4 h is a train/test shift. Training on Q4 h removes it [INFERENCE: size unknown. A per-depth offline acceptance measurement (§1.5 step 6) quantifies it before training].
- The MTP also reads Q4_K `token_embd` and Q6_K `output` at serve time. Train with exactly those tensors dequantized from the GGUF, not the bf16 HF ones.
- All drafter papers stress "responses generated by the target model". Here the target *is* the Q4 GGUF. bf16 can't run on this box anyway (55.6 GB `total_size` in the HF index).

### 1.3 Toolchain (no sudo)

- **PyTorch for gfx1100 via pip in a venv.** Two working indexes [V, checked 2026-10-10]:
  - AMD per-arch (self-contained runtime): `https://repo.amd.com/rocm/whl/gfx110X-all/`. Provides `torch-2.11.0+rocm7.13.0-cp312` (722 MB) + `rocm_sdk_libraries_gfx110x_all-7.13.0` (881 MB) + `rocm_sdk_core-7.13.0` (414 MB).
  - Or `https://download.pytorch.org/whl/rocm7.14` with `torch-2.14.1+rocm7.14-cp312` (1.39 GB). It depends on `rocm[device-all,libraries]==7.14.*` from pip.
  - Commands (adjust `--index-url` if uv needs `--extra-index-url` for dependencies):
    ```
    uv venv ~/qwen-opt/train-venv --python 3.12
    ~/qwen-opt/train-venv/bin/python -m ensurepip   # or: uv pip --python …
    uv pip install --python ~/qwen-opt/train-venv/bin/python --index-url https://repo.amd.com/rocm/whl/gfx110X-all/ torch
    uv pip install --python ~/qwen-opt/train-venv/bin/python numpy safetensors gguf sentencepiece
    ```
  - Disk ≈ 4–7 GB including the uv cache. The kernel driver comes from the system ROCm 10.0; the userspace comes from the wheel [INFERENCE: generally compatible; check `torch.cuda.is_available()` and one bf16 matmul].
- **Don't use speculators/SpecForge end-to-end.** Both get hidden states from a vLLM/SGLang server running the bf16 target, which doesn't fit in 24 GB. Use `speculators/src/speculators/models/mtp/core.py` (recursive loop + `compute_step_weights`) as a reference only [V, cloned at 55ebbd5].
- **Don't train inside ggml either.** `llama-finetune`/ggml-opt can't backprop this graph (rope_multi, gated attention, quantized weights) [INFERENCE].

### 1.4 Data volume, disk, time

Per-token storage [V arithmetic]:

| item | bytes/token | per 1 M tokens |
|---|---|---|
| tokens + loss mask | ~5 | 5 MB |
| MTP input h (5120 × fp16) | 10 240 | **10.2 GB** |
| teacher top-20 probs (id int32 + fp16) | 120 | 0.12 GB |
| (EAGLE-3: 3 layers × 5120 × fp16) | 30 720 | 30.7 GB |
| (DFlash2: 5 layers, ids [6, 20, 34, 48, 62] per GGUF) | 51 200 | 51.2 GB |

- 22 GB of free disk holds ~2 M tokens of h. So **store tokens + teacher probs permanently and h as rolling ~1 M-token shards** that get re-extracted.
  - Re-extraction is cheap: prefill runs at ~850–1044 t/s (NOTES.md:16) → ~17–20 min per 1 M tokens.
  - Alternative: keep a shard in RAM. 40 GB free ≈ 3.5 M tokens.

Data volume:
- **Pilot:** ~4 K conversations ≈ 2 M tokens (prompt + response).
- **Full:** 20–30 K conversations ≈ 10–15 M tokens.
- Reference points: Red Hat got +7 % τ from ~8 K samples. DFlash's long-context fine-tune used **1.6 K samples × 3 epochs** ([DFlash paper §long-context](https://arxiv.org/html/2602.06036v2)). FastMTP used 389 K samples, but its head started untrained for recursion.

Generation of the self-distilled responses (llama.cpp, same Q4 GGUF):
- Run `llama-server` with `-np 8..16`, a small context (e.g. `-c 65536` total), and the user's real sampler (T=1, top-p 0.95, top-k 20 unless the user uses something else) and thinking setting.
- Aggregate throughput ≈ 150–300 t/s [INFERENCE: memory-bound decode amortises weight reads across slots; plain single stream is 38.6 t/s].
- Pilot (1.5 M response tokens): ~1.5–3 h. Full (10 M): ~10–18 h, overnight.

Training compute (K=5 steps, 64 k draft-vocab head, seq ≤ 4096) [arithmetic]:
- P = 424.7 M trainable matmul params. H = 65 536 × 5120 = 335.5 M frozen head params.
- Forward per token per step = 2P + 2H = 0.85 + 0.67 = 1.52 GF. Backward = 4P + 2H (no weight grad for H) = 1.70 + 0.67 = 2.37 GF. Attention is negligible (~25 MF fwd at L≈1 k).
- With activation recompute (+1 fwd): ≈ 5.4 GF/token/step → **27 GF/token for K=5**.
- Pilot: 2 M tokens × 3 epochs × 27 GF = 162 PF. At 35 TF/s effective that's **~1.3 h**; at 20 TF/s, ~2.3 h. The 7900 XTX peaks at ~123 TF/s dense fp16/bf16 WMMA; 30–60 % of that is realistic for big GEMMs [INFERENCE].
- Full: 12 M × 2 epochs ≈ 650 PF → ~5–9 h.

Training VRAM [arithmetic]:
- bf16 weights 0.85 GB + fp32 master 1.7 GB + Adam m,v 3.4 GB + grads 0.85 GB ≈ **6.8 GB**.
- Frozen 64 k head (bf16) 0.67 GB.
- Embedding rows gathered on CPU from the dequantized Q4_K table (248 320 × 5120 bf16 = 2.5 GB RAM).
- Activations with checkpointing and chunked CE: ~2–4 GB.
- **Total ≈ 10–12 GB.** It can't share the GPU with the 18 GB llama.cpp model, so extraction and training must alternate. The user's chat server is down during these phases.

Wall-clock summary:
- Pilot: env 0.5 h + generation 2–3 h + extraction 0.7 h + training 1.5–2.5 h (with per-epoch re-extraction ~1 h) ≈ **6–8 h**, mostly unattended.
- Full: **~1.5–2 days**.

### 1.5 Step-by-step pipeline

1. **Prompts.** Mix: ~40 % PL chat/prose, ~35 % EN chat, ~25 % EN/PL code/tech. Keep the code share so code acceptance doesn't regress.
   - **Best source: the user's own past prompts**, e.g. llama-server/frontend logs if they exist (on-policy; synthetic prompts reach only 80–93 % of real-query benefit per arXiv 2503.07807).
   - PL datasets: `allenai/WildChat-1M` / `WildChat-4.8M` (per-turn `language` field → `language=='Polish'`; count not verified), `OpenAssistant/oasst2` (`lang=='pl'`), `CohereLabs/aya_dataset` (`language=='Polish'`), `pelcra/PLLuMIC` (<1 K organic PL instructions, [card](https://huggingface.co/datasets/pelcra/PLLuMIC)).
   - EN: `HuggingFaceH4/ultrachat_200k`, ShareGPT, WildChat EN.
   - More PL prompts: have the Q4 model translate EN prompts.
   - Only prompts are used. Responses are regenerated, so dataset response quality is irrelevant.
2. **Generate** responses with the Q4 GGUF (`llama-server -np 8`, OpenAI API, the user's sampler and chat template, thinking as the user uses it). Save `{prompt_ids, response_ids}` using the server's `/tokenize`, or keep text and tokenize with the GGUF tokenizer.
3. **Extractor** (new C++ tool, ~200 lines, modelled on `examples/embedding`). Include `../src/llama-ext.h` as `common/speculative.cpp:13` does.
   - Load the GGUF with `n_ubatch` 2048, `-c 8192`, KV f16.
   - Call `llama_set_embeddings_nextn(ctx, true, false)`.
   - Decode each full conversation with logits on for all tokens.
   - Write `h = llama_get_embeddings_nextn()` as fp16 shards.
   - For each response position, apply the user's sampler transform to `llama_get_logits_ith(i)` (T=1, top-k 20, top-p 0.95) and store the top-20 (id, prob). That set is exact when the user's sampler has top-k ≤ 20.
4. **PyTorch MTP module.** Mirror qwen35.cpp:555-671 exactly:
   - `concat(enorm(e), hnorm(h))` — **embedding first**.
   - `eh_proj` → attn_norm → q_proj (6144×2 per head: `[q(256) | gate(256)]` per head; qwen35.cpp:579-592) → q_norm/k_norm → MRoPE with sections [11, 11, 10, 0], n_rot 64 of head 256, base 1e7, text positions.
   - GQA 24/4 → `·sigmoid(gate)` → wo → residual → post_norm → SwiGLU FFN → residual → `shared_head_norm` → head.
   - Init options: `blk.64.*` dequantized with gguf-py (Q6_K/Q8_0 dequant supported [V]), or the bf16 `mtp.*` originals from shard 18. With bf16 originals, add +1 to the norms to match GGUF semantics. Fetch with HTTP range requests on the safetensors header to get only the ~0.85 GB of `mtp.*`.
   - `token_embd` (Q4_K) and the 64 k rows of `output` (Q6_K) come dequantized from the GGUF and are frozen.
   - **Gate:** reproduce llama.cpp's draft logits on a few sequences (dump them via the ext API or `llama-eval-callback`) to ≤1e-2 relative error before training anything.
5. **Train.**
   - Recursive K=5 (matches n=5), β≈0.6–0.7, lr 5e-5 cosine, warmup 5 %, AdamW(0.9, 0.95), wd 0, grad clip 1.0, bf16 autocast, tokens/batch ~32 k. These follow FastMTP §3.1.
   - Loss on response tokens only. Exclude targets outside the 64 k draft vocab (3.5 % of PL prose).
   - **Loss: TV or forward-KL against the stored top-20 teacher probs, plus 0.1·CE.** TV = 1 − acceptance under rejection sampling, so it directly optimizes `--spec-draft-sampling probabilistic` at T=1. Plain CE suits greedy drafting.
   - **Attention mask fidelity** [INFERENCE, improvement over speculators/FastMTP]. At inference, draft step k attends to prefix KV built from *target* h (speculative.cpp:1713-1717) plus k-1 recursive entries. Speculators' loop (core.py:238-271) instead attends over step-k hidden for all positions.
     - Fix: build K/V for steps 1..k and use an explicit mask. The prefix comes from step-1 K/V; the last k-1 diagonal positions come from steps 2..k. This is the EAGLE-3 "training-time test" idea.
     - Cost: K× attention keys, which is small at seq ≤ 4 k.
6. **Offline evaluation, before any GPU benchmark.** On a held-out 5 % split, compute per-depth teacher-forced and free-running estimates for base vs trained:
   - greedy acceptance E[p_Q4(argmax q)];
   - probabilistic acceptance E[Σ_v min(p, q_top10)], with q truncated to top-10 as the llama.cpp draft sampler does.
   - Turn these into expected tokens/step = 1 + Σ_k Π_{j≤k} a_j. This quantifies the Q4-shift headroom even before training.
7. **Write back** (no extra disk; the trunk stays bit-identical):
   - Back up the original `blk.64.*` bytes (~351 MB).
   - Quantize the trained fp32 weights to the **same** types (Q6_K; Q8_0 for k/v) with `ggml_quantize_chunk` from `~/llama-opt/lib/libggml-base.so` via ctypes. It's exported [V]. gguf-py lacks a Q6_K quantizer [V]; Q8_0 alone is available in numpy.
   - Overwrite the tensor bytes in place: `gguf.GGUFReader(path, 'r+')`, `tensor.data[...] = new_bytes`. Byte size is unchanged, so offsets are unchanged.
   - Copy the norm vectors (F32) directly.
8. **Benchmark** with the existing `spec_sweep.sh` / `serve_bench.py`. Retest n ∈ {5, 6, 7} and probabilistic on/off, because higher deep-position acceptance shifts the best n. n=8 → 9-column verify falls off the mmvq 2–8-col kernels (NOTES.md:159).

### 1.6 Expected gain, with arithmetic

- Step cost is ~45 ms, independent of acceptance. So t/s ∝ tokens/step, and en-chat 60 t/s ≈ 2.7 tokens/step.
- Model the current en-chat conditional acceptance a ≈ [0.75, 0.62, 0.55, 0.45, 0.40] [INFERENCE, fits the measured ~1.6–1.9 accepted drafts]. Cumulative: 0.75, 0.465, 0.256, 0.115, 0.046 → Σ=1.63 → **2.63 tokens/step**.
- **Conservative (Red Hat-like Δ, growing with depth, +0.02 / +0.05 / +0.10 / +0.12 / +0.12):**
  - a = [0.77, 0.67, 0.65, 0.57, 0.52] → cumulative 0.77, 0.516, 0.335, 0.191, 0.099 → Σ=1.91 → 2.91 tokens/step.
  - **+11 % → ~66 t/s en-chat.**
- **Domain-shift case (PL prose, Q4 shift; +0.05 / +0.08 / +0.12 / +0.15 / +0.15):**
  - a = [0.80, 0.70, 0.67, 0.60, 0.55] → Σ=2.08 → 3.08 tokens/step.
  - **+17 % → ~70 t/s; PL prose 64 → ~75 t/s.**
- **Probabilistic drafting with a TV-distilled head at T=1** [INFERENCE, not shown in a paper for this model]:
  - Greedy drafting at T=1 accepts with probability p(argmax q). That is ≤ max p, e.g. 0.4 for p = (0.4, 0.3, 0.3).
  - Rejection with q ≈ p accepts with Σ min(p, q) → 1.
  - With the shipped head, probabilistic gave no gain (NOTES.md:175), which is consistent with a miscalibrated q.
  - If TV training lifts a to [0.80, 0.75, 0.75, 0.72, 0.70]: cumulative 0.80, 0.60, 0.45, 0.324, 0.227 → Σ=2.40 → 3.40 tokens/step → **+29 % → ~77 t/s**.
- Ceiling at n=5: 6 tokens/step ≈ 133 t/s.

### 1.7 Risks

- **Small gain.** Qwen already trained this MTP multi-step. Red Hat saw only +7 % τ in-domain on such a head. The offline eval in step 6 tells you in ~1 h of GPU time whether there is headroom.
- **Implementation mismatch** (rope sections, Q/gate interleave, norm +1, embedding-first concat) silently wastes the run. Mitigation: the step-4 parity gate.
- **Regression on code** if the data is too chat-heavy. Keep 25 % code/tech and evaluate all prompt classes.
- **Q6_K re-quantization** of the trained weights adds noise. The shipped head is Q6_K too, so this is neutral vs baseline; the offline eval can use the requantized weights.
- **Disk** (22 GB) forces rolling h shards. **GPU exclusivity** means no chat server during training phases.
- **The "main model stays this Q4 GGUF" constraint.** The trunk bytes are untouched, but the file is modified in `blk.64.*`. Keep the 351 MB backup, or patch a copy if the user objects. A copy needs 17.6 GB of disk and is only possible after the h shards are deleted. A sidecar MTP-only GGUF costs ~1.76 GB more VRAM, and VRAM is already at 22.3 GB.
- **PyTorch ROCm wheels on a ROCm 10.0 pre-release kernel stack** are untested here. The fallback is the download.pytorch.org rocm7.14 wheel.

### 1.8 Optional extension: separate per-depth MTP heads

- llama.cpp already chains multiple NextN heads: `llama_set_nextn_layer_offset`, `chain_heads` when `n_layer_nextn > 1` (speculative.cpp:1500-1509, 1704-1726; llama-ext.h:98-101). DeepSeek-V3-style separate heads, initialized from `blk.64` and fine-tuned per depth, could beat the shared head at deep positions.
- Costs:
  - +351 MB VRAM per head (tight).
  - `chain_heads` re-decodes the whole chain prefix at every head (speculative.cpp:1785-1795), which raises draft cost.
  - `qwen35.cpp:503` asserts `n_layer_nextn == 1`, so a C++ change is needed.
- Not first priority [INFERENCE].

---

## 2. Option B: EAGLE-3 trained from scratch. Not recommended.

- **Support in llama.cpp:**
  - `draft-eagle3` exists. The loader needs exactly 3 `target_layers` (`src/models/eagle3.cpp:6-15`).
  - qwen35 exposes layer inputs (qwen35.cpp:160).
  - The converter has EAGLE-3 classes (`conversion/llama.py`, `conversion/qwen.py`).
- **Evidence that it won't beat the native MTP:**
  - [Ex0bit/Qwen3.6-27B-PRISM-EAGLE3](https://huggingface.co/Ex0bit/Qwen3.6-27B-PRISM-EAGLE3) is a self-distilled EAGLE-3 trained with NVIDIA ModelOpt on REAP + UltraChat + tulu-3 with layers [1, 31, 60].
  - It reaches **τ 2.4 (PRISM) / 2.2 (stock)** in chain mode; tree mode reaches ~3.35 but is "throughput-neutral on this hybrid GatedDeltaNet target".
  - Qwen3.8's native MTP reaches 3.74 (MT-Bench, 7 tokens).
- **Cost here:**
  - Data: 30.7 GB of features per 1 M tokens. DFlash-scale corpora run to hundreds of K samples (DFlash: 800 K samples, 6 epochs).
  - Compute (K=7 TTT steps): ~0.6 B trainable + a 32 k head → ≈ 6·(0.6 + 0.08 + 0.16) B ≈ 5 GF per step → ~35 GF/token.
  - Example: 50 M tokens × 2 epochs = 3.5 EF → ~28 h at 35 TF/s, on top of ~55 h of generation at 250 t/s and repeated feature extraction.
  - It replaces a head that is already better.

## 3. Option C: DFlash / DFlash2 / DSpark fine-tune. Conditional.

- **Public recipes:**
  - DFlash: [paper](https://arxiv.org/abs/2602.06036) App. A.1, 800 K samples (Nemotron Post-Training v2 + CodeAlpaca) with target-regenerated responses, 6 epochs AdamW, cosine, warmup 0.04, seq 3072, 512 random anchors per sequence, 5 layers.
  - Long-context adaptation worked with **1.6 K samples × 3 epochs**, which shows small fine-tunes adapt a DFlash drafter.
  - The **DFlash2 objective is not public**. Speculators implements it as "experimental" ([doc](https://docs.vllm.ai/projects/speculators/en/latest/user_guide/algorithms/dflash2/)).
  - DSpark training exists in speculators (CE 0.1 + TV 0.9).
- **This drafter:**
  - 1.9 B params (GGUF `general.size_label`), 5 layers, `target_layers` [6, 20, 34, 48, 62], block 8, selector rank 256 / top-k 16.
  - Full fine-tuning with Adam needs ~1.9 B × 16 B ≈ 30 GB, so it doesn't fit in 24 GB. You'd need LoRA or freezing (e.g. train layers + fc only).
  - Features: 51 GB per 1 M tokens.
- **Blocker for the user's goal:** llama.cpp's DFlash path verifies by exact match only (no rejection sampling), so at T=1 it loses to MTP regardless (NOTES.md:172-174). A PL fine-tune could help PL at T=0 and code, but not T=1 chat. Revisit only if DFlash rejection sampling gets implemented.

## 4. Why MTP self-distillation wins here

| | MTP self-distill | EAGLE-3 scratch | DFlash2 fine-tune |
|---|---|---|---|
| Starting point | native head, already τ≈3.7 class | random | trained drafter, weak PL |
| Target features | 1 × 5120 (10 KB/tok) | 3 × 5120 (31 KB/tok) | 5 × 5120 (51 KB/tok) |
| Trainable params | 0.42 B (fits 24 GB with full Adam) | ~0.6–0.8 B | 1.9 B (needs LoRA) |
| Data needed | 2–15 M tokens | 50 M+ tokens | small fine-tune possible |
| Works at T=1 in llama.cpp | yes (rejection sampling) | yes | **no** (exact match) |
| Serve integration | in-place byte patch of `blk.64.*`, zero VRAM change | new GGUF + d2t | new GGUF |
| Expected chat gain | +10–17 % (CE); ~+25–30 % if probabilistic works [INFERENCE] | likely negative vs MTP | ~0 at T=1 |

## 5. Things the main agent / parent should run (GPU)

1. Install the torch venv and check `torch.cuda.is_available()` and one bf16 matmul.
2. Extractor smoke test: 100 sequences, then the MTP parity check (PyTorch vs llama.cpp draft logits).
3. Offline per-depth acceptance of the **shipped** head on Q4 h (step 6). This is the go/no-go for the whole effort.
4. Pilot (2 M tokens), write back, then `spec_sweep.sh` at T=1 with greedy and probabilistic, n=5/6/7.
