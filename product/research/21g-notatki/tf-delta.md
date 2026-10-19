# TensorFold delta: v1.0.12 (833bbfcb) → v1.1.0 (76aafcf2) → HEAD d46d17a7 (2026-10-19), app beta.7/beta.8

Working notes for 21g. These cover only what is new since 15c §2.4/§3.4 and the wiki entry `repo/tensorfold.md`. Clone: `~/qwen-opt/research-src/tensorfold-new`. Site pages and the board were fetched 2026-10-19 around 03:10 local.
Bandwidths used below: RTX PRO 6000 and RTX 5090 1792 GB/s; RTX PRO 4500 896 GB/s ([CDW](https://www.cdw.com/product/pny-nvidia-rtx-pro-4500-graphic-card-32-gb-gddr7-full-height/8388914)); RTX 4090 1008; GB10 273; M3 Ultra 819; M5 Ultra 1.2 TB/s; M5 Max 460 or 614 GB/s ([Apple](https://support.apple.com/en-us/128107)); Strix Halo 8060S 256 GB/s; XTX 960.

## 1. Delta stats

| Item | Value | Source |
|---|---|---|
| Tags | v1.0.0-beta.7 `46a08c18` (10-16 08:00), v1.1.0 `76aafcf2` (10-18 10:23), v1.0.0-beta.8 `b7ce8121` (10-18 21:47) | `git tag` |
| Commits v1.0.12..v1.1.0 | **901**, of which 163 are merges and 823 touch non-`app/` paths | `git rev-list --count` |
| Commits v1.1.0..HEAD | 3: `b7ce8121` beta 8, `7d34f3dc` README model table, `d46d17a7` doc fixes | — |
| Non-merge commits v1.0.12..HEAD | 700 non-app, 9 app (app work arrives as bulk squashes) | — |
| Distribution by day | 10-15: 167; **10-16: 394**; 10-17: 73; 10-18: 217 | `git log` |
| Authors / PRs | 28 git authors (36 credited in the release); 98 distinct PR numbers referenced in merges | — |
| Files, whole repo | 2686 files, +255,007 / −12,513 | `git diff --shortstat` |
| Files, non-app | 1285 files, +140,114 / −5,179. `zig/src` 828 files +82.6k; `zig/tests` 178 files +22.2k; `docs` 78 files +10.6k | — |
| Kernels | 112 files +17,982. CUDA 76 files +12,582; Metal 35 files +5,259; **HIP 6 files +12/−9** | — |
| HIP functional change | **None.** Qwen HIP only gets the Windows platform-layer `clock_gettime` refactor (`b923e554`, `48dcc42c`); Flash Next HIP gets a graph-pool fix (#963) | `git diff -- zig/src/families/qwen3_5/backend/hip` |
| App, beta.7..beta.8 | `app/` 1401 files, +114,893 / −7,334 (single commit `b7ce8121`) | — |
| Traction | 1382★, 263 forks. Downloads of 1.1.0: macos-arm64 120, linux-aarch64 79, linux-x86_64 16. Beta.7: DMG 39 + zip 29. Beta.8: DMG 9 + zip 11 | `gh api`, `gh release view` |
| Maintainer replies | Signed "*Posted by Ash's AI Assistant Synthena*". The project is run by an AI agent at about 400 commits a day | #918, #1001, #426 |

## 2. Engine changes (1.1.0), with sources

Release notes: https://github.com/ashhart/TensorFold/releases/tag/v1.1.0 (same text in `CHANGELOG.md#110`).

**New served families and paths**
- **Qwen3.5-2B and Qwen3.8-27B on CUDA** through the native server (#836). Each decode shape replays as a CUDA graph. The 27B drafts with DFlash2 in chains and trees. Concurrent streams share rounds. Mixed-width MLX checkpoints at 2–8 bits are supported (#849, #859), plus vision (#885), a pinned-host prompt cache (#888, 8 GiB) and `--kv-cache fp8`: e4m3 with a per-row fp32 scale of amax/448 (#886, `zig/kernels/cuda/qwen35_kv8.cu`). The windows/arm64 platform layer has a contributor RTX 4090 receipt (#836).
- Larger Qwen CUDA lane rounds, verify trees, batched drafting and lone-stream speed work (#978) are **moved to 1.1.1**.
- **Qwen3.6-35B-A3B on CUDA** with MTP chains and trees (#856, #972). **Qwen3.8 Flash Next on CUDA** from MLX 4-bit g32 with MTP, with a 512-block indexer past 2,048 keys (#952).
- **Nemotron 3.5 Bolt 74B-A9B on CUDA** from NVIDIA's 24 GB checkpoint. Experts are in **GGML IQ2_XXS and Q8_0 blocks on TF's own mma.sync kernels** (`zig/kernels/cuda/ggml.cu`, #897, #938).
- Other new families: Gemma 4 31B and 12B on Metal (#879, #975), Step-5 on a 256 GB Mac (#903), GLM-5.3-Flash on 2 CUDA ranks from EXL3 (#855, #976) with DFlash2 (#979), Fish Audio Drama 3 TTS (#927), plus test tools MiniMax H3 (#961, #958) and Qwen-Image (#948).
- **Intel Arc B70 (XPU, Level Zero)** hardening for the 27B (#802).

**Speculative and drafting**
- **Metal 27B (#887, #918 work):**
  - K split per shape measured over every layer's distinct matrices (`QWEN27_DISTINCT`). "A matrix called again sits in the system cache and misleads" (`docs/recipes/qwen3.8-27b.md`).
  - An undrafted one-row window is kept by its own verify, saving 1.1 ms a token.
  - The GDN one-row step drops from 5 dispatches to 3, because `tf_delta_gdn_pre_step` writes the conv history as it reads it: 1.75 → 1.19 ms a token.
  - Decode attention uses 128-key chunks below position 8,192 and 512-key chunks above, chosen per row by its own position. This changes bits relative to 1.0.12: "replies can differ from 1.0.12's".
  - Up to 128 streams share a round, each drafting its own DFlash2 tree. Trees verify up to 64 rows and prompts run in 512-row passes.
  - The HEAD commit `d46d17a7` only corrects the README: the old text said DFlash2 drafts for one stream at a time.
- **Nemotron Super on CUDA:**
  - Verify windows up to 32 rows, i.e. 31 MTP drafts a round (#1006).
  - `--mtp-drafts` and `--mtp-confidence` set depth and a cumulative confidence threshold (#997).
  - **Subset draft head with a coverage switch (#1011).** A stream drafts on a 49,152-id FP8 subset head while its last 16 context tokens are all draft ids, and on the full head otherwise (`zig/src/families/nemotron/draft_ids.zig`, `Coverage.recent = 16`).
- **Drafter release format (#893) and a training recipe from `--record` recordings (#894)** (`docs/recipes/training-a-drafter.md`). Lessons there:
  - KL over the draft vocabulary, weighted 0.8^j, gains about 2× what L1 plus CE gains.
  - Every language goes in every batch. One batch without German cost 18% of German acceptance.
  - Coverage of the draft vocabulary caps acceptance: a 32k slice covered German at 0.896. Widening it to 60,614 ids gave +0.075 / +0.014 / +0.037 accepted (code / chat / German).
  - "Depth 4 on a MoE target: slower than depth 2" (lines 77–134).
- **First token is sent before the first drafts are prepared** (#932): TTFT 131.9 → 119.1 ms (`docs/receipts/qwen-cuda-first-token/README.md:53-60`).
- Grammar-constrained drafting: drafts grow under the same grammar for `tool_choice: required` on the 27B Metal path (#918 fix).

**Recall:** minor. Super's copied and Recall chains start at 15 tokens (#1006). `recall_store.zig` changed by about 83 lines, with no new mechanism.

**TP and clusters (engine):**
- GLM ring prefill reduce (#902), split-reachability probe before load (#899), one-shot RoCE all-gather for 2 ranks (#852, after b12x).
- The Nemotron TP worker sends a single 1-row message per decode step instead of 16 padded rows (#1000).
- Heat bands (#988).
- **App "clusters" are only management** (SSH trust, headless install, receipts). No distributed inference is enabled (`app/docs/clustering.md` "Current engine support").

**NVFP4 and formats:**
- Exact decode of compressed NVFP4 scale planes and TP slices; no shipped checkpoint uses the layout (#904, #906).
- Nemotron FP8/NVFP4 on sm_80–89 via split-K fp32 partials (+21.9 MB) (#901).
- The kernel contract runs on sm_80–89 (#954).
- MXFP8 qlinear (#907). EXL3 operators on CUDA (#837, #806, #741, #740) and Metal (#729).
- GLM NVFP4 2×GB10 known issue replaced by a contributor run in HEAD (#1040).

**Infrastructure and quality gates:**
- Kernel-contract launch records are kept **per nvcc release** (13.0 / 13.2 / 13.3) (#945).
- `quant-ref` fails on non-finite error (#933). Poisoned outputs catch dispatches that write nothing (#908).
- File content digest cached by (dev, inode, size, both times in ns) in `~/.cache/tensorfold/file-digests/v1` (#900).
- Memory receipts tool (#865). CUDA paged KV pool (#935). TCP_NODELAY (#929).
- `tensorfold merge` (LoRA fold) (#710).
- Benchmark manifest `GET /v1/benchmark/manifest` (#980). Benchmark exit-2 reasons (#969).

**AMD:** the only new AMD artifact is `docs/receipts/gfx1151-qwen-833bbfcb/`, an equality receipt for **1.0.12** on Strix Halo (#994). It makes no performance claim. The 27B cancel test failed (5.0 s vs 1.9 s, README:120-128). There are no new W7800, R9700 or XTX numbers. The HIP server accepts `--drafter` and ignores it (#1001).

**LFM2.5-24B-A2B:** no engine change. The README table lists it as "One Mac; M4 Pro checked… No separate native model recipe yet" (README:132). There is still no CUDA path.

## 3. Claim verification

| # | Claim (source) | What was measured | Arithmetic | Weak points | Verdict |
|---|---|---|---|---|---|
| C1 | Site hero "**874 tok/s** Nemotron 3.5 Lightning, RTX PRO 6000, greedy code with drafting, MLX affine 4-bit", labelled "Release 1.0.6" ([tensorfold.dev](https://tensorfold.dev/)). Source is the maintainer comment in #610 (2026-10-11): 875 code / 607 prose, 256 tok, median of 5 | `tools/bench_openai.py` "fib" prompt (Fibonacci), 1 machine, maintainer. Same-family 5090 receipt (#610): **plain 274–283**, drafted 736–751 code / 509–522 prose | Active params from config ([HF](https://huggingface.co/TensorFold/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-MLX-4bit/resolve/main/config.json)): 23 MoE layers × (6×2×2688×1856 + 2×2688×3712 + router) + 6 attn + 23 Mamba + head 131072×2688 ≈ **3.23 B → 1.82 GB/token at 4.5 bpw** `[INFERENCE: relu² MoE without gate]`. Plain 280 t/s × 1.82 = 0.51 TB/s = **28% of 1.79** (latency-bound). 874 × 1.82 = 1.59 TB/s = 89%, so it needs ≥1 tok/step. At a step of 1.3–1.6× the plain 3.6 ms that is **~4–5 tok/step** | Hero uses the best prompt class (Fibonacci, most memorized code) with a stale release label. The site disclaimer says "not like-for-like". Board 1.0.12 5090: code T0 917.7, chat T0 633.2 (BobClawblaw) | **Plausible but cherry-picked.** The realistic number is prose 607 / chat 633 |
| C2 | 27B M5 Ultra, 1.1.0 vs 1.0.12: greedy prose 116→126, code 386→432 (512 tok); t=0.7 97→104 / 305→325; prefill 931→1349 @8k; 8 streams 222–239→314 (release notes) | TF's own run "on the cells #918 asked for". The reporter gave only prompt descriptions, not text (#918 comment 2026-10-17) | Plain round 19.5 ms; 14.1 GB in 16.2 ms = 870 GB/s = 72.5% of 1.2 TB/s (recipe). With step ≈ 1.3×19.5 + ~2 ms drafter ≈ 27 ms: prose 126 → **3.5 tok/step**; code 432 → **~11.8 tok/step of max 16**; t=0.7 code 325 → 8.8. Prefill 1349 t/s × 54 GFLOP/token ≈ 73 TFLOPS | 1) Board 1.0.12 on the same chip: code T0 **211.5**, chat T0 142.6, so TF's 1.0.12 "code" baseline (386) is 1.8× the board's. 2) Independent M3 Ultra exclusive A/B on the same checkpoint: **native 1.0.12 28.6 t/s flat** (code = prose, i.e. drafting ineffective) vs python 0.6.6 86.2 / 54.0; cold prefill 836.6 s vs 298.0 (#918, 2026-10-18). 3) TF native *plain* is slower than mlx-lm: 51.6 vs 54.7 decode @2k, 1269 vs 1860 prefill @8k (recipe table) | Prose **plausible**. Code 432 **doubtful** as a general claim (unpublished fixture, needs about 12 accepted tokens a round). M3 Ultra path **regressed or broken** |
| C3 | 27B CUDA on RTX 4090 (Windows): DFlash2 code 135 / chat 104 greedy, plain ≈40 t/s (#836 body) | `bench_openai.py --tokens 128 --reps 3`, 1 stream, contributor | 17.2 GB × 40 = 688 GB/s = 68% of 1008. At step ≈ 1.25×25 + 1 ms: chat ≈ 3.4, code ≈ 4.4 tok/step | 128 tokens only, no "before" | **Plausible** |
| C4 | Board 27B CUDA 1.0.12: 5090 chat T0 263 / code T0 367. PRO 4500 chat T0 142.4 / code 198.5 (official); 152.9 / 206.8 on custom build `+4500v13` | community-v1 (one prompt per class), 5 reps, 256 tok | Plain roofline 127 t/s (5090) and 63.5 (PRO 4500). At 70% BW and 1.3× verify: 5090 chat 3.8 tok/step, PRO 4500 chat 4.2, code 5.8. **Normalized to 960 GB/s: 141–153 chat, 197–213 code** | No plain baseline in receipts, no acceptance counts. Board accepts custom builds | **Plausible.** DFlash2 on CUDA ≈ **1.4–1.5× our MTP n=4 (~103) per GB/s** `[INFERENCE: different prompts]` |
| C5 | gfx1151 27B (HIP 1.0.12) | 64 tok, engine-reported **13.06 t/s** (`docs/receipts/gfx1151-qwen-833bbfcb/27b-serve-check.jsonl:1`); 12.88–13.17 community-v1 with or without DFlash2 (#1001) | 15.1 GB × 13.06 = 197 GB/s = **77% of 256** | Drafter silently ignored on HIP; maintainer: "equal timings alone do not show that DFlash2 executed" | **Credible plain; no AMD speculation** |
| C6 | Bolt 74B-A9B on RTX PRO 6000: 153–155 t/s vs 144–146 for #897's own build (release notes) | Self-comparison only | 24 GB / 74 B ≈ 2.6 bpw avg → ~9 B active ≈ 2.9 GB/token `[INFERENCE]` → plain roofline ≈ 617 t/s; 153 = **25%** | **No llama.cpp baseline, although these are GGML blocks that llama.cpp runs natively** | **Plausible but weak** |
| C7 | Super subset head (#1011): count +16.7%, code +8.2%, prose +7.6%, English +5.1%; ES/FR/DE/IT/JA +0–0.5%; draft level 3.48 → 2.07 ms | 2 GB10s, ABBABA holds, medians of 9, 7 languages, hashes equal | Saved 1.4 ms/level × ~2.5 levels/round against a 46 ms window ≈ +7%. Matches | Contributor (plotarmordev) | **Credible.** Best methodology in the delta |
| C8 | Kolibri block drafter 1.31–1.49× vs copy drafting (`training-a-drafter.md:7-10`) | 1 GB10, 1 target | — | Baseline is n-gram copy, not MTP or EAGLE. Dev slices chose the checkpoint (line 109–110, self-admitted) | **Plausible, weak baseline** |
| C9 | `tensorfold merge`: "fresh quantization kept a median 99.6% of the adapter's change against **0.1% for the fold**", yet "Ours: the fold as the default" (#710 in release notes) | Qwen3-4B, 1 case | The fold rounds the LoRA delta into existing 4-bit scales, so 99.9% of the delta vanishes | The default discards the adapter | **Claim true, default indefensible** |
| C10 | First token before drafts: TTFT −9.7% at 1 stream (#932 receipts) | GB10, 27B, alternated orders | Decode 53.94 → 53.96 (unchanged) | Small effect | **Credible** |
| C11 | Digest cache: 2nd start 370 → 169 s; 1st reads 164 GB in 199 s (#900) | 2×GB10 GLM | 0.82 GB/s hashing | — | **Credible** |
| C12 | Flash Next Metal shared host: lone request 79.6 vs 86.2 (−7.7%), so the default stays single host (#606) | M3 Ultra | — | Honest negative | **Credible** |
| C13 | Board LFM2.5-24B-A2B 1.0.12: M5 Ultra 4-bit chat T0 263.0 / code 278.3; 8-bit 214.7; M5 Max 4-bit 214.2 | community-v1 | 1.388 GB/token (15c F1) × 263 = 365 GB/s = **30% of 1.2 TB/s**. 8-bit 2.62 GB × 215 = 563 GB/s = 47%, only 18% slower than 4-bit, so decode is latency-bound. Ours: XTX Q5_K_M ≈1.70 GB × 293.7 = 499 GB/s = **52%** | — | **Plausible; we are faster absolutely and per GB/s** |
| C14 | GB10 27B CUDA DFlash2: code 53.9 / chat 33.7 t/s (`qwen-cuda-first-token/README.md:55,58`) | 1 stream | Plain roofline 273/15.1 = 18 t/s, so ≥3.0 / 1.9 tok/step at 100% BW (~4.3 / 2.7 at 70%) | — | **Plausible** |
| C15 | "Drafted == plain" exactness on all families | GB10, M5 Ultra, RTX PRO 6000 | — | Not on HIP drafting (never ran). 1.1.0 changes 27B Metal bits vs 1.0.12 (attention chunks): exact *within* a release, not across releases | **Credible, with that scope** |

## 4. App: beta 7 and beta 8

Sources: `app/docs/beta/1.0.0-beta.{7,8}.md`; [beta.8](https://github.com/ashhart/TensorFold/releases/tag/v1.0.0-beta.8) and [beta.7](https://github.com/ashhart/TensorFold/releases/tag/v1.0.0-beta.7) release pages; [guide](https://tensorfold.dev/guide).
- **Platform:** Mac-only (Electron). `recommendEngineModel` returns 'unsupported' for anything other than darwin/arm64 (`app/src/lib/model-recommendation.ts:86`).
- **Beta 7** (engine 1.0.12):
  - Models workspace split into My models / Discover.
  - **Per-model context and sampling profiles**. The guide says: "Add small context, Add large context or Create profile… Advanced sampling and acceleration… Speculative drafting".
  - Favourites, **"Compare models"**: A/B on one prompt, both answers with timings, then the previous model is restored.
  - Task starters, revision-preserving message edit, OCR uncertainty, in-app update prompt.
- **Beta 8** (engine 1.1.0):
  - Full-text conversation search, document collections with citations, backups.
  - **14 UI languages including Polish**.
  - **Built-in benchmarks** (community-v1 at 4,096 ctx, 4 warmups + 20 measured requests, a **"Serial baseline" toggle** that disables drafting). Profiles and results are retained. Strict receipt export; never auto-publishes (`app/docs/benchmarks.md`).
  - Connectors: Gmail, Calendar, Slack, Discord, Telegram, plus WhatsApp, iMessage, Mattermost, Matrix, Google Chat, docs, browser, webhooks in the catalogue (`app/shared/connector-catalog.ts`).
  - "Compute and clusters": SSH, headless node, receipts; management only.
  - Cache planner instead of a fixed 8 GiB (#989).
- **Model picker:**
  - Curated list of 4 models: Qwen3.5-2B, Lightning 30B-A3B, Qwen3.8-27B (+DFlash2), Flash Next 6-bit.
  - The rank depends on a chip regex: 27B first on M5 Max/M3 Ultra, Flash Next first on M5 Ultra.
  - Each candidate must pass an engine preflight (format, memory floor, disk) and a recheck against the current device's memory limit. The fallback is the next smaller model that passes. There is a single English "reason" sentence (`model-recommendation.ts:66-108`). **No speed prediction.**
- **Hardware detection:** chip and memory come from engine status. The benchmark receipt has `hardware.source` detected/partial. On ROCm, GPU names and driver stay unknown (`docs/community-benchmarks.md:109`); a rocminfo PR is proposed in #1001.
- **Onboarding:** language selector on the first-run welcome screen before model setup. "Minimal or Full" modes. "Use this language for new assistant replies" is on by default and adds an ephemeral response preference (`app/docs/language-packs.md:4-23`).
- **Anthropic:** the engine serves Anthropic Messages (README:57; not new). The app can use Codex and Claude CLI logins and cloud providers (guide).

**Polish locale evaluation** (`app/src/lib/preferences/packs/pl/*.json`, 27 files; 4,922 source phrases, 100% key coverage):
- Good:
  - Grammar and diacritics are correct overall: "Pobierz model pasujący do Maca, aby zacząć.", "Brak pobrań; znajdź model w Odkrywaj."
  - **Plurals are avoided by design** with a "Label: {count}" pattern ("Znalezione modele: {count}"). This is a smart trick for Polish's 3 plural forms, worth copying.
- Systematic error: **42 of 52 "Could not …" strings are rendered as an impersonal past** ("Nie uruchomiono połączenia mobilnego.", "Nie sprawdzono postępu konfiguracji VM."). That reads as "it was not done", not "it failed". Only 7 use the native "Nie udało się …".
- Compression and meaning loss: median PL/EN length ratio is **1.00** (natural Polish runs ~1.2–1.3×). Examples: "Finish active local work before comparing models" → "…przed porównaniem" (drops "models"); "edit the bot to configure a new chat" → "edytuj bota dla nowego czatu".
- Awkward:
  - "w Odkrywaj" (tab name used as an imperative in the locative case)
  - "tok./s"
  - "Szeregowy pomiar bazowy" for "Serial baseline" (better: "bez spekulacji")
  - "Generowanie spekulacyjne" for "Speculative drafting"
  - "Living Weights" left in English
- **Gap:** the recommendation reason ("A balanced model for everyday work on this Mac…") and the hardware label ("… with 64 GiB memory", en-US number format) are rendered raw. They are not in the catalogue (`ModelRecommendationPanel.tsx:23,27`). The most important onboarding sentence stays English in the Polish UI. The same applies to the benchmark summary line "Measured speed is not a quality ranking." (`benchmark-display.ts:20`).
- Verdict: machine-authored, competent but not native-quality; beta 8 itself admits "translation quality can vary". Podkręt can beat it with native copy.

## 5. Community benchmark board (/benchmarks)

API: `https://tensorfold.dev/api/benchmarks/v1/{results?limit≤50,community,size-rankings,contributors/ID}` (from `/benchmarks/app.js`).
- **Contents:**
  - **45 runs**, 9 contributor IDs (8 names), 16 models, 5 hardware types: M5 Ultra 16, M5 Max 14, RTX PRO 4500 9, RTX 5090 3, GB10 3. Dates 10-16 to 10-18.
  - **All on engine 1.0.12, none on 1.1.0.** Versions: 37 official, 7 custom builds (`1.0.12+4500kernelpilot`, `+4500v13`), 1 Python `0.6.6+mini-managed2`.
  - **0 AMD** entries: the board refuses `rocm` (`docs/community-benchmarks.md:109`, #1001 open). **0 serial-baseline runs.**
- **Receipt** (schema v1):
  - hardware: cpu, gpus name/memory/cores, memory_type, source
  - model: repo, revision, config/tokenizer sha256, quantization, drafter repo
  - runtime: backend, version, driver
  - settings: tokens 256, reps 5, temperatures [1, 0], serial, context, managed, rank_count
  - suite: id + sha256
  - per-sample: delivery_tps, ttft, prefill, server_decode_tps, token_sha, seed, status
  - No prompts, outputs or paths. **No acceptance or drafted counts. No power or memory.**
- **Methodology** (`zig/src/server/benchmark_suite.zig:12-50`, `docs/community-benchmarks.md`):
  - **One prompt per class.** code = raw *completion* "Write a short Python function that computes the Fibonacci sequence and explain it." (14 prompt tokens); chat = "Explain how matrix multiplication uses a GPU…" (31 tokens). English only. Thinking off, concurrency 1, prompt reuse off, 1 warm-up per cell.
  - Cells run **in blocks, not alternated** (code T1 ×5, chat T1 ×5, code T0 ×5, chat T0 ×5). At T0 the 5 repeats give identical tokens, so spread ≈ 0 (e.g. 5090 27B chat T0 262.6–263.2). That measures timer jitter, not workload variance.
  - Rate = (completion − 1) / (last − first SSE delivery).
  - Ranking uses the greedy-chat median and a "Size × speed" podium (B params × t/s). Trophies at 1/5/10/100 runs. A contributor uploaded 6 near-identical Lightning runs at the same minute.
  - "All community measurements remain self-reported; automatic approval does not independently verify speed or hardware" (line 66). Token hash ≠ exactness proof (line 48).
- **Strengths to copy:**
  - Strict schema with pinned checkpoint revision and config sha.
  - Server recomputes statistics.
  - Failed or early-EOS cells are never aggregated.
  - Attested manifest from the server (`/v1/benchmark/manifest`, #980).
  - Upload without an account (cookie profile).

## 6. What is genuinely new

**vs llama.cpp:**
- DFlash2 block drafter with tree verify over GDN hybrids, on CUDA and Metal.
- A subset draft head switched on context coverage.
- Exactness drafted == plain incl. seeded sampling and concurrency.
- Per-compiler kernel contracts.
- A drafter-training pipeline from recorded serving.
- A first-token-before-drafts scheduler.
- A receipts board.
- Not new (llama.cpp already has equivalents): pinned host prompt cache (cf. llama.cpp `--cache-ram`), fp8 KV (cf. q8_0 KV), paged KV pool (multi-user), GGML IQ2_XXS/Q8_0 kernels (llama.cpp's home turf).

**vs our fork:**
- We already have: MTP n=4 with a 65K iq4 draft head, lookup, kvq, PM4, a bit-exact default path and a KLD gate.
- New to us:
  - (a) DFlash2 on 27B. It is shipped on CUDA and Metal but never on HIP. Up to 16-token blocks and 64-row trees vs our max 5 tokens/step.
  - (b) the coverage-switched head
  - (c) distinct-matrix autotune
  - (d) 3-dispatch GDN step
  - (e) training lessons for the draft head
  - (f) per-toolchain bit records
- They have **nothing on AMD**: HIP is frozen and the drafter is silently ignored on HIP.

## 7. Adoptable ideas, ranked

Score = expected gain × confidence / effort. GPU experiments only with approval. Kill criteria are decided before running.

| Rank | Idea | Effort | Expected gain (arithmetic) | Minimal experiment | Kill criterion |
|---|---|---|---|---|---|
| 1 | **DFlash2 drafter for Qwen3.8-27B on XTX** (block drafter, then tree or chain verify over our GDN rollback). Coordinate with ResDSpine (DFlash draft cost on XTX) | High | TF normalized to 960 GB/s: 141–153 t/s chat-greedy vs our 103 (§3 C4). On our side: plain 23.3 ms, step ≈ 29 ms verify + ~1 ms drafter (0.5 GB 4-bit `[INFERENCE]`) ≈ 31 ms. Beating MTP by 10% (113 t/s) needs τ ≥ 3.5; TF's numbers imply τ ≈ 3.8–4.2 chat → **+25% (≈129 t/s)** `[INFERENCE]` | Offline (CPU-only) where possible: acceptance of the z-lab drafter on our spec_sweep outputs (6 PL/EN prompts, T=1). Then a GPU step-cost microbench | τ < 3.5 on spec_sweep, **or** (drafter + 16-row verify) > 1.35× plain step |
| 2 | **Coverage-switched draft head** (#1011): subset head while the last 16 context tokens are inside our 65K draft vocab, full head otherwise. This matters for Polish text | Low–med | Head per MTP level: 65,536×5120×4.25 bit = 0.18 GB (0.19 ms) vs full ~248K vocab `[INFERENCE from token ids ≥248,069 in TF prompt files]` = 0.675 GB (0.70 ms). ×4 levels = 0.74 vs 2.8 ms/step. Going full on Polish costs +2 ms (−7%), so it pays only if PL tok/step rises >7%. TF: +5–17% on covered text, 0% elsewhere | **CPU-only first:** coverage of our 65K subset over the target's own Polish outputs, and P(a 4-token draft window contains an uncovered token) | P(uncovered in window) < 5% on PL means no headroom, kill. Otherwise do a GPU ABBABA A/B and kill if PL tok/s gain < +3% |
| 3 | **Draft-head training lessons** for `~/qwen-opt/mtp-train`: KL over draft vocab weighted 0.8^j (2× vs L1+CE); Polish in every batch (−18% acceptance when a language is skipped); draft vocab from the target's own top-1 output per class (coverage caps acceptance); MoE (LFM2.5) depth ≤2 | Low (config) | Kolibri: widening the slice gave +0.075 accepted per round on code. LFM verify-window cost 1.24–1.68× for k=2–4 (#868, 15c) favours k≤2 | One retrain arm vs the current recipe on held-out PL/EN recordings | Accepted-per-round gain < +0.05 on PL |
| 4 | **Distinct-matrix autotune** (Infinity Cache aware). TF: "a matrix called again sits in the system cache and misleads". The XTX has a 96 MB IC, and a 5120×17408 4.5-bit matrix is ~50 MB | Low | 1–3% `[INFERENCE]` from fixing mis-chosen splits | Re-time each tuned shape over a rotating set of all layers' matrices vs repeated single-matrix timing | Same winner config for all shapes, kill |
| 5 | **3-dispatch GDN one-row step** (conv history written in the pre-step; M5 Ultra 1.75 → 1.19 ms/token = −2.9%) | Med | XTX: 48 layers × 2 launches × ~3 µs + state traffic ≈ 0.3 ms = **~1.2%** of 23.3 ms `[INFERENCE]` | rocprof kernel count per GDN layer in our plain step | Our step already uses ≤3 kernels per layer |
| 6 | **Bit records per ROCm/hipcc version** (TF #945 keeps them per nvcc release). Our md5 greedy baselines keyed by toolchain, so a user's ROCm update can't silently break the "bit-exact" claim | Low | Protects the claim; 0% speed | Store md5 sets for 2 ROCm versions in CI | — |
| 7 | **First token before drafts** (#932, −9.7% TTFT at 1 stream) | Low | ≈ one draft-level cost off TTFT (a few ms) | Compare TTFT with and without MTP on the same prompt | Δ < 5 ms |
| 8 | Product hygiene: digest cache keyed by (dev, inode, size, mtime_ns) (#900, saves re-hashing a 17 GB GGUF, ~8 s at 2 GB/s); Ed25519-signed checksum in the installer (`tensorfold.dev/install.sh:18-35`); `/v1/benchmark/manifest`-style attested facts for Podkręt receipts; never aggregate incomplete cells | Low | UX and trust | — | — |

Reject:
- LoRA fold default (C9)
- Living Weights
- Connectors and clusters
- Paged KV / 128-stream rounds (multi-user)
- fp8 KV (we have kvq)
- Heat bands
- Recall changes (nothing new)

## 8. Competition notes for Podkręt

- **AMD is uncontested.** HIP received no functional change in 901 commits. The drafter is silently ignored on HIP (27B 12.9 t/s with or without DFlash2, #1001). The board refuses ROCm receipts. The installer supports only macOS-arm64 and NVIDIA Linux (`install.sh:62-67`). The hardware wishlist on /contribute lists GB300, M5 Ultra, DGX Spark, RTX Spark, M6/M5 Pro and **no AMD**.
- **Consumer NVIDIA is now contested.**
  - The 27B CUDA + DFlash2 path ships. The kernel contract covers sm_80–89 (#954). There is a 4090 receipt (#836). Lightning is "checked on RTX 3090" (README:121).
  - Our 3090: 3.31 tok/step × 38.4 ms ≈ 86 t/s (15c §5.1). TF 4090 chat 104 / code 135, scaled to 936 GB/s ≈ 97 / 125 `[INFERENCE]`, i.e. **TF may be +13–45% on a 3090**.
  - Before claiming before→after leadership on NVIDIA, run an alternated cloud 3090 A/B (TF 1.1.0 vs our fork) on our spec_sweep plus a copy workload.
  - TF requires its MLX-4bit checkpoint, not GGUF, so Podkręt's "any GGUF" stays a differentiator.
- **Mac 27B story is shaky.** An independent M3 Ultra exclusive A/B has native 1.0.12 at 0.33× of TF's own Python engine on code (#918). Native plain is below mlx-lm on Metal (recipe table). Their headline wins are drafting on favourable prompts.
- **UX to copy:**
  1. **Serial-baseline toggle** next to the standard run, i.e. an in-app before→after. Ours should compare against *tuned upstream llama.cpp*, not only spec on vs off.
  2. Receipts with a strict schema, checkpoint revision and config sha, exportable JSON, no prompts or outputs.
  3. A **curated short model list + live preflight** (format, memory floor, disk) with a fallback smaller model. We add a predicted t/s (BW roofline) and then a measured t/s.
  4. Per-model profiles (small or large context).
  5. Compare two models on one prompt.
  6. Language chooser on the first-run screen before model setup.
  7. A "Label: {count}" pattern to avoid Polish plural bugs.
  8. Restore the previous model after a benchmark; closing the drawer keeps the job running.
- **What to counter:**
  1. Their benchmark is one English prompt per class with Fibonacci code, not alternated, and without any other-engine baseline. Ours should alternate, cover PL+EN in two workload classes (new writing vs copy/edit), compare against tuned llama.cpp, and show md5/KLD.
  2. Their Polish is machine-grade (systematic "Nie X-ono" errors, the onboarding reason untranslated). Podkręt ships native Polish.
  3. Scope: TF is becoming a general agent workspace (connectors, bots, clusters, Living Weights). Podkręt stays "pick a model, measure, accelerate, prove it".
  4. Their headline number is stale (site shows "Release 1.0.6" while shipping 1.1.0) and from the best prompt. We should publish both workload classes.
- **Pace risk:** about 400 commits a day with AI-run maintenance (Synthena). Expect fast feature catch-up, including a possible ROCm board and a HIP drafter in 1.1.1 (ThinkOffApp promised the PRs in #1001). Re-check 1.1.1 for "HIP refuses `--drafter`" and for the ROCm board.
