# Project Maya — working notes (for 21g-nowe-silniki.md)

Source: https://github.com/mw00/project-maya, clone `~/qwen-opt/research-src/project-maya`, HEAD `a4e1ff0` (v1.1.15, 2026-10-16).
All `file:line` refer to that tree. Nothing was run, built or measured on a GPU. Every number below comes from the repo or from GitHub issues/PRs; anything I derived or guessed is marked [INFERENCE].

## 1. What it is

- A **single-model engine** for GLM-5.3-Flash (zai-org, MIT): 321 B total / ~18 B active. 45 layers: 34 KDA linear-attention layers plus 11 MLA+DSA sparse-attention layers, each MoE layer with 288 routed experts + 1 shared expert, top-8. Layers 0-2 are dense, 3-44 are MoE (42 MoE layers), plus a NextN/MTP block. Routed experts are 304.6 B params = 95% of the model (`docs/GLM5-FLASH.md:19-34`). One expert = 3×4096×2048 = 25.17 M params.
- **Not a llama.cpp fork.** The engine is C++/CUDA (~104 k lines in `src/`+`include/`), with HIP built from the same source through `include/strata/hip_compat/` and `cmake/hip_backend.cmake` (`CMakeLists.txt:36-51`). It descends from **Strata** (Niko1221/Strata, MIT), a native engine for one architecture (Qwen3.8-Flash-Next). Maya started from Strata's engine and rewrote it for GLM (`README.md:202-204`; `docs/GLM5-FLASH.md:7-13`). The CMake project is still named `strata` (`CMakeLists.txt:11`), and every environment knob is `STRATA_GLM_*`.
- **Which parts of ggml/llama.cpp it uses** (pinned llama.cpp `3cf03257`, `third_party/ggml/VERSION.txt`):
  - the block layouts and codebooks from `third_party/ggml/ggml-common.h` (`CMakeLists.txt:295-296`);
  - the CPU lane's dot products from **ggml-cpu** (`CMakeLists.txt:801-864`, `ggml_get_type_traits_cpu`);
  - the **ggml MMQ** kernels for the prompt path, with its own fused-SwiGLU patch `third_party/ggml/mmq-fused-swiglu.patch` (`CMakeLists.txt:890-944`);
  - the CUDA ggml build as a parity oracle in tests (`CMakeLists.txt:322-333`);
  - llama.cpp's mtmd for the image encoder ("strata-vision", `maya.py:79`).
  Decode GEMV/MoE kernels, tiering, speculation and the server are its own.
- **Quants:** Maya-S 96.5 GB, Maya-S24 94.7 GB (4-bit attention), Maya-M 116 GB, Maya-M-Derisked, Maya-L 156.3 GB (`README.md:31-37`). Community EXL3 (turboderp) and any `glm5-next` GGUF also run.
- **Team and cadence:** created by @mw00 (Peasant Smith), co-maintained by @needmorevram (DFlash2, EXL3, KV streaming, CPU kernels) (`README.md:7-8,196-201`). 51 releases in 10 days (v1.0.0 2026-10-07 → v1.1.15 2026-10-16), 404 commits (`CHANGELOG.md`, `git log`). Development is heavily AI-assisted: the Pascal PR is "Generated with Claude Code" (#214).

## 2. Architecture, with code pointers

| Piece | What it does | Where |
|---|---|---|
| Expert tiers | **VRAM pool** (per-layer slots plus 3 spares a layer) → **pinned RAM tier** (cudaHostAlloc/mlock) → **NVMe via O_DIRECT** (no page cache, "buffered reads pushed the system into swap") | `src/core/glm_model.cu:2633-2645`, `src/platform/memory.cpp:64`, `src/platform/direct_file.cpp:263-308` |
| RAM-tier sizing | Free RAM minus `STRATA_GLM_RAM_HEADROOM_GB` (default **6**; 16 on HIP APU/discrete configs); counts reclaimable ZFS ARC as free | `glm_fast_path.cu:1008-1032,1395-1430`; `docs/SETTINGS.md:29`; `docs/AMD_MAYA.md:43-49` |
| Live migration | On a miss, a spare is filled and the layer's **LRU** resident is demoted to RAM (since v1.1.13 with one conversation). Several conversations use aged counts (`STRATA_GLM_VRAM_EVICT`). Background promote/demote runs on a copy stream: a moved expert stays live where it was until its copy lands. "Refill" of free slots after a prompt: 24 per boundary | `glm_fast_path.cu:4628-4660` (evict), `4735-4800` (bg moves, `STRATA_GLM_PROMOTE`=8, `_FILL`=24) |
| CPU lane | The CPU computes RAM-tier experts while the GPU runs the rest. At start it times one expert on the CPU against one over PCIe and builds a plan: "of f = 0..8 RAM-tier experts in a route, the CPU takes k". The plan is re-timed during decode (`CPU_RETIME`). Threads: one per physical core (2/3 without SMT; one NUMA node minus 4) | `glm_fast_path.cu:2600-2663,2942-2989,3651-3666` |
| Expert profile | `data/expert-profile-glm.bin` (106 KB) ranks 13,248 (layer, expert) pairs (46×288). It sets the warm-up order and the per-layer VRAM slot counts. It was built from a routing trace of Maya-L with MTP over 66 requests. Fresh start, 3090 + 8×5060 Ti: 35.4 → 40.7 t/s, VRAM route hits 89% → 96% | `docs/SETTINGS.md:127-150`, `tools/make_profile.py:1-30`, `glm_fast_path.cu:1134-1161,3234-3260` |
| Layer split (≤16 GPUs) | `split auto` prices each placement from each card's VRAM, the host RAM bandwidth and a coverage curve 1-(1-f)^3 (or the user's usage counts). One 64 KB host hop per boundary per token, no P2P needed | `glm_model.cu:1320,1534,1754`; `docs/SETTINGS.md:35` |
| MTP | **Only on ≥2 GPUs, as a pipeline:** the second half drafts while the first half finishes. **One GPU: no MTP by design**: "each token needs mostly different experts, so a window costs nearly as much as writing the tokens one by one" (#43 maintainer). Exception: `STRATA_GLM_MTP_DECODE` defaults on for gfx115x APUs where every expert is resident (+44-50%) | `src/core/glm_mtp.cu`, `src/core/mtp.cpp`; `docs/SETTINGS.md:69-71` |
| DFlash2 | External 0.7 GB block drafter (Anbeeld, **CC BY-NC-ND**). It reads 5 hidden layers and drafts up to 7 tokens. Verification: one GPU uses a batched window, 3+ GPUs a pipelined one | `src/core/glm_dflash.cu`, `glm_window.cu`, `verify.cpp`; `docs/SETTINGS.md:241-299` |
| KV streaming | The MLA latent cache lives in pinned RAM; a 32K-position window (≥20,480) stays in VRAM. After the DSA indexer picks 2,048 positions, the missing blocks of 4 are copied over PCIe, with clock-sweep eviction | `src/kernels/cuda/glm_kv_stream.cu`, `glm_model.cu:837-941`; `docs/SETTINGS.md:88` |
| Prompt path | Chunked MMQ; chunk buffers are borrowed from the expert pool (`--prefill auto`, up to 32K tokens on one GPU); prestage of the next layer's experts; the CPU takes the least-routed experts | `src/core/glm_prefill.cu`, `src/prefill/*`; `docs/SETTINGS.md:152-163` |
| Conversation slots | A conversation that is not continued is set aside **on disk** (default 4 slots, ≤16 GB, refused below 8 GB free); checkpoints live in RAM (~150 MB each) | `src/program/generate.cpp:1174-1200,1344-1390`; `docs/SETTINGS.md:57-60` |
| Server / UI | OpenAI + Anthropic API, tool calls, chat + Monitor dashboard, About→Update (git pull + incremental rebuild), update check every 6 h | `serve/`, `docs/SETUP.md:35-44` |

## 3. Changelog v1.1.12–v1.1.15 (`CHANGELOG.md:7-109`)

- **v1.1.12 (10-15):**
  - EXL3 on one GPU: the CPU takes more experts (split-K, AVX2 tier). 3090 EXL3-3.05bpw 14.3-16.8 → 20.9-22.1 t/s (29.2 with DFlash2).
  - `STRATA_GLM_SPLIT_ROWS` (opt-in) batches requests per split part: 4×RTX 4000 Ada, 8 requests, 74.4 → 94.5 t/s aggregate.
  - VRAM tier promotions keep running under DFlash2: hits 49-62% → 54-67% (V100).
  - RDNA2 (gfx1030) accepted as experimental.
- **v1.1.13 (10-16):**
  - LRU eviction with one conversation: 3×V100-16 GB Maya-S 128K, 24.8 → 26.5 t/s. **Answers can differ from v1.1.12.**
  - Windows Strix Halo: the pool stays inside the dedicated carve-out (prefill on a 96 GB share had dropped 159 → 62 t/s).
  - A system-prompt prefix slot is kept on disk (#179).
  - Mixed AMD pair, plus an experimental "expert helper" GPU.
  - hipBLASLt table for ROCm 10 (8060S prefill 204 → 341 at 2K).
  - zai-org's current chat template: 288 conversations byte-identical, up to 15× faster template rendering with many tool calls.
- **v1.1.14 (10-16):**
  - Pascal experimental (#212/#214), see §5.
  - unsloth UD-Q6_K_XL / Q8_0 routed experts (type 8 added to the expert kernels, #216).
  - "sm_70+ gives v1.1.13's tokens".
- **v1.1.15 (10-16):**
  - EXL3+DFlash2 on 3090 + 8×5060 Ti: 71 → 81 greedy, 46 → 59 at 32K (#225).
  - V100/RTX 20 prompt attention in two passes: a 27K prompt's attention 22.5 → 11.8 s.
  - AVX-512 VBMI IQ2_XXS CPU rows, bit-identical to ggml: +6-8% decode on Zen 5.
  - EXL3 on AMD (tests pass on a 7900 XTX and an 8065S; speed untuned).
  - DFlash2 OOM fix on V100.
  - Opt-in `MISS_SKIP` (changes answers).
  - **Three default paths now sum in a different order, so tokens differ from v1.1.14** (`CHANGELOG.md:33-36`).

Pattern: nearly every release says which configurations keep the previous release's tokens. That is good bookkeeping, but the default output changes from release to release.

## 4. Claims verification

Per-token bytes [INFERENCE from logs]:
- **Maya-M:** 12,096 experts = 104.8 GB (#172 log) → 8.66 MB/expert = **2.75 bpw**. Routed bytes per token = 42 layers × 8 = 336 experts × 8.66 MB = **2.91 GB**. Dense in VRAM 6.86 GB (#157, #172), of which ~0.7 GB is the Q8_0 token_embd that is not streamed (`glm_model.cu:2653`). So **≈9.1 GB read per forward pass**.
- **Maya-S:** expert pool 80.17 GiB (`AMD_MAYA.md:172`) → 7.12 MB/expert = **2.26 bpw**, 2.39 GB routed per token.
- **Maya-S24:** 7.2 MB/expert (#89: 2,880 experts = 20.8 GB), ~5.25 GB dense over 4 cards → **≈7.65 GB/forward**.

| Claim (README) | What was actually measured | Arithmetic check | Verdict |
|---|---|---|---|
| **81 t/s, RTX PRO 6000 96 GB, Maya-M 116 GB** (#172, v1.1.7) | `--bench`: 3×256 tokens, greedy, thinking off, 2 runs (80.7/81.0). Pool 85.51 GB = 10,567 of 12,096 slots (**87% of experts in VRAM**), **98% of routes hit VRAM**, 4-6 RAM fetches/token, 0 disk. RAM tier 21.4 GB (61 GB box). **No drafting**: DFlash2 lost its calibration, 67.1 vs 79.3, and MTP does not draft on one GPU | 12.35 ms/tok × 9.1 GB → **737 GB/s = 41% of 1,792 GB/s**. Roofline ~197 t/s. Experts are skewed: the 13% of experts not in VRAM serve only 2% of routes | **Plausible, honest** (log lines attached). Essentially a "nearly everything in VRAM" case: it tests the decode kernels, not the tiering |
| **118 t/s, 4×4090** (#89, v1.0.31) | Maya-S24, **100% of routed experts in VRAM** (98.5-99.2% hits), MTP on a 4-way split, 3×256 greedy. Per answer 109.7-122.2; the same setup the next day gave 110.8 | 7.65 GB/forward. Sequential split without spec: 7.6 ms roofline. The pipelined MTP keeps 2 cards busy at once (2×1,008 GB/s) → ideal ~3.8 ms/tok; measured 8.2-9.1 ms → ~45% of 2-card roofline | **Plausible.** But it is the **best of several runs** (110.8-118), on 96 GB of VRAM. Tiering plays no role. Real agent workload: 96.8-98.3 t/s (same issue) |
| **1×3090, 26-27 t/s** (#157 Maya-M 27.0; #135 S24 26.0) | #157: EPYC 7702P **8-channel DDR4 (111 GB/s measured)**, a VM with 141 GB RAM, everything resident (0 disk). Pool 14.32 GB = 1,771 slots (14.6%), hits 44-52%, CPU lane ~20 ms of ~37 ms/token. After `--calibrate` (PCIe share 0.10). DFlash2 lost (25.7 vs 18.0) | Misses ≈ 175 experts × 8.66 MB = 1.5 GB/token. CPU lane ≈ 1.35 GB / 20 ms ≈ 68 GB/s (61% of 111). GPU ≥ 7.6 GB / 936 GB/s = 8.1 ms. Sum 30-37 ms ✓ | **Plausible, but the hardware is workstation-class** (8-ch EPYC, 4-ch Threadripper). On a desktop with dual-channel memory (~60-70 GB/s DDR5 in practice; our 64 GB DDR4 box ~40) the CPU lane takes ~2× longer → **~17-20 t/s Maya-M** [INFERENCE]. Data point for that: 13900K + DDR5 + 24 GB card, S24 **24.7** (#174) |
| **30+ t/s, RTX 5090 + 96 GB DDR5** (#43, early v1.0.x) | Free text: "decode over 30 tok/s", Maya-M, 7950X, DDR5-6400. The report is an attachment; no bench lines in the issue | Pool ~23 GB ≈ 2,650 slots (22%) → coverage 1-(1-0.22)^3 ≈ 52% hits. Misses ≈ 1.4 GB/token. CPU (~65 GB/s) + PCIe5 (~55 GB/s; 0.157 ms per 8.66 MB in #172) in parallel ≈ 12 ms, GPU ~5-7 ms → ceiling ~40-50 t/s. "30+" ≈ ≤33 ms ✓ | **Plausible but weak evidence** (unspecified version, no `--bench` lines). The other 5090 row (Windows, 64 GB, Maya-S) shows **23.0** |
| **Pascal: 2×P40, S24 28 t/s** (#212) | `--bench` 27.5/27.4/29.1, MTP split, 80-82% VRAM hits, CPU lane 19 ms/tok (KVM, 32 vCPU), drafts accepted 83-95% | 2×347 GB/s; dense 2.6 GB per card → ≥7.5 ms per card. 36 ms/tok → ~30% of roofline; the CPU lane dominates | **Plausible, careful A/B** (profile, SASS diff, 3 prompts identical "to the character"). 1×P40 S24 is 15.6; Maya-L 9.9 |
| **--kv-streaming "512K on a 3090: prompts 4-9× faster, decode +5%"** (v1.1.6, #86) | At 512K: 1,176 vs 714 expert slots | Latent cache: 11 layers × 1 KB = 11.3 KB/token → 5.9 GB at 512K, minus a 32K window (0.37 GB) ≈ 5.5 GB freed ≈ 462 slots × 7-8.7 MB = 3.3-4.0 GB ✓. **714 slots = 17 per layer**, barely more than top-8 + spares, so the prompt chunk is tiny and every chunk re-streams the experts | **The mechanism is real, the baseline is pathological** (512K context on one 3090). "4-9×" is cherry-picked; +5% decode fits +65% more slots (5.9 → 9.7% of experts). Default 32K-context users gain little |
| **--parallel** ×1.41 (2 seqs, V100 RAM-bound), ×2.02 (4 seqs, Gorgon Halo all resident) (`README.md:92-97`) | Real chat questions; greedy, CPU lane off: "the same tokens as alone" | Resident case: dense ~6.5 GB read once + 4×2.39 GB routed → 16.1 GB per 4 tokens vs 35.6 → **ideal ×2.2**, measured ×2.02 ✓. RAM-bound: the CPU lane does not amortise → ×1.4 ✓ | **Plausible.** This is ordinary batching; llama.cpp `-np` does the same |
| **DFlash2 "+44% 9 GPUs, +12% 2 GPUs, +19% 1×3090"** (`SETTINGS.md:282-298`) | Maya-L, 5 prompts, 2-3 runs each | — | **Cherry-picked by design:** user reports lost on one 3090 (#157: 18.0 vs 25.7), on a PRO 6000 (#172: 67.1 vs 79.3) and in #127/#129/#140. The maintainers admit it: "on one GPU that reads much of the model from RAM it is often slower" (`README.md:154`), so the speed calibration keeps it only where it wins |
| **"same answers" with MTP/DFlash2** | Greedy acceptance (longest correct prefix + the model's own token). The window kernels claim bit-for-bit per-token arithmetic. Test in #225: "256/256 tokens on every request" **with the split, CPU plan and tiers pinned** (`STRATA_GLM_DFLASH_CUM=2`) | — | **True only in a narrow sense:** drafts vs no drafts under the *same tier state*. **The default path is not deterministic across restarts:** with defaults only **17/70** pairs of starts matched. The CPU lane and the GPU round differently (ggml-cpu Q8_K blocks of 256 vs GPU q8_1 blocks of 32; ~2% relative L2 per expert) and top-8 routing amplifies that (`SETTINGS.md:187-216`). Releases also change the tokens (§3). Our md5-greedy bit-exactness has no counterpart here |
| **Quants "97.7-99.2% of FP8 zero-shot accuracy, same next token 83%"** (`bench/results/MAYA-S.md`, `MAYA-L.md`) | Zero-shot: 5 MC log-likelihood tasks × **400 questions**. KL: KL(FP8‖quant) over the **top-64 + one bucket** (a lower bound on the full KL), **8 texts / 7,672 positions**, against **FP8** (not BF16) | 400 q at p≈0.8 → SE ≈ 2 pp per task, average over 2,000 q ≈ 0.9 pp. S vs L (80.8 vs 81.8) ≈ 1 SE → **not resolvable**. MC log-likelihood barely moves until quantisation is severe → **a weak metric**. KL: S **0.428** / 83.3%, M 0.291 / 86.8%, L **0.188** / 90.0%; wikitext 0.934 / 68.8%; tool calls 0.850 / 76.5% | "97.9%" is **marketing**; the KL table is the honest number (and they publish it, which is to their credit). For scale (llama.cpp `tools/perplexity/README.md:115,125`): L3-8B q4_K_M 0.031 / 91.9%, q6_K 0.0055 / 96.0%, q2_K 0.445 / 71.1%, L2-7B q2_K 0.109 / 85.6%. Ours: LFM KV q8_0 0.044 / 92.3%; our q4_0-KV canary (which we FAIL) 0.128 / 85.2% (`patches/llama.cpp-amd-opt/0055…:20-22`). **83% ⇒ greedy diverges from FP8 every ~6 tokens; Maya-S ≈ L3-8B q2_K in KL.** That is expected at 2.26 bpw, but it is "a different model in the details", not "close to the original". Top-1 on the real next token is 68.8 vs 71.5 (FP8): a modest drop |
| AMD: "RX 7900 XT / XTX" (`docs/AMD_MAYA.md`) | Measured **on a 7900 XT 20 GB** (not an XTX), 9800X3D, 192 GB DDR5. Single card Maya-S ~15 t/s (v1.0.11) → 16.4 after the RDNA3 expert kernels; R9700 + 7900 XT ~33 t/s (drafts accepted 76%). Prefill 413 t/s (tuned hipBLASLt + SUB=1024). **No XTX numbers**; v1.1.15 only says the "EXL3 tests pass on an RX 7900 XTX" | Our box, XTX + 64 GB dual-channel DDR4 [INFERENCE]: pool ~15 GB (~2,100 slots), RAM tier ~50 GB, ~20 GB of experts on NVMe → ~1.1 GB/token RAM (≈28 ms at 40 GB/s) plus a disk tail → **~8-14 t/s Maya-S24** | XTX untested; the AMD path is "experimental, text only" |

**Pattern across the README table:** the rows span different versions (v1.0.6 to v1.1.13), different models (S/S24/M/L) and different contexts. They are mostly best-of runs on a short benchmark (3×256 tokens, thinking off). Ten of the top rows are multi-GPU or ≥45 GB-VRAM machines. There is **no llama.cpp baseline anywhere** in the README. The maintainer states that the first answers after a start are the slowest (`README.md:88-89`). The benchmarks are honest about their setup, but the selection favours the best rows.

## 5. Pascal (v1.1.14; #212, #214)

- **The change is 38 lines:**
  - the wmma bodies of `mla_attn_tc*` compile to nothing below sm_70; the F32 attention is used instead;
  - `__nanosleep` becomes a plain spin in the doorbell/flag waits (`elementwise.cu:214`, `verify_kernels.cu:426,479`);
  - **`-Xptxas -dlcm=ca`** for sm_6x (`CMakeLists.txt:84-98`). GP102/GP104 cache global loads in L2 only, so the many small loads of the GEMVs (`get_int_b2`, scales, q8_1 activations) starved.
  - Setup: `MIN_CC=60`, `VALIDATED_CC=70` (`maya.py:81-82`); CUDA 12.x only, because CUDA 13 dropped sm_6x (`maya.py:748`).
- **Profile (P40, Maya-L, before the fix):** `mv_kernel_t<14>` (Q6_K) took 51% of GPU time, 563 µs × 150 calls/token ≈ 84 ms of a ~150 ms token, "a quarter of 347 GB/s".
- **Results (#212):**

  | Config | Before | After | Speed-up |
  |---|---:|---:|---:|
  | Maya-L, 1 P40 | 5.8 | 9.9 | ×1.7 |
  | Maya-L, 2 P40 | 9.7 | 16.9 | ×1.7 |
  | Maya-S24, 1 P40 | 5.3 | 15.6 | ×2.9 |
  | Maya-S24, 2 P40 | 9.4 | 28.0 | ×3.0 |
  | Maya-S24, 3 P40 | 9.6 | 28.4 | ×3.0 (no gain over 2 cards: 3 parts run serially) |

  Prefill stays at 160-210 t/s: no tensor cores, F32 attention.
- **Verification:** greedy, 3 prompts of ≤200 tokens, identical to the character. The sm_70+ SASS is identical after normalising hashes (2,944,748 lines). Maintainers also checked a GTX 1050 Ti (12 layers on it + V100).
- **Not measured:** parity tests on sm_61, long context, **P100 (sm_60)**, Windows (#214 "Not measured").
- **P100/sm_60 flag [INFERENCE, not compiled]:** the engine calls the raw `__dp4a` intrinsic in the decode kernels (`native_mmvq.cu:168…`, `iq_kernels.cu:53` `#define ggml_cuda_dp4a(a,b,c) __dp4a(...)`; 73 uses in `glm_fast.cu`). `__dp4a` requires CC ≥ 6.1; ggml itself falls back to scalar code below 610 (`~/llama.cpp/ggml/src/ggml-cuda/common.cuh:51,733-738`). So a P100 build most likely **fails to compile**, even though the README advertises "P40 / P100" and the setup accepts CC 6.0.
- **For our fork:** the `-dlcm=ca` insight (Pascal does not L1-cache global loads by default) is free to test in llama.cpp for sm_61 builds. llama.cpp's mmvq on P40 might gain too [INFERENCE; no hardware].

## 6. SSD / RAM / thermal safety

- **SSD reads:** experts are read with O_DIRECT (`glm_model.cu:2643-2645`), `READ_CHUNKS` 8 per part. Reads do not consume NAND P/E cycles (only read-disturb refresh, negligible), so **the read tier does not wear the drive**.
- **Sustained random reads:** at 3-7 GB/s, drives without a heatsink can throttle thermally [INFERENCE]. Maya does not monitor SSD temperature: nothing in docs or settings mentions it.
- **SSD writes:**
  1. The pack (~1 GB) is written once into the model folder (`docs/SETUP.md:22`).
  2. **Conversation slots:** each switch to another conversation writes a snapshot (`generate.cpp:1344-1390`), default 4 slots ≤16 GB, refused below 8 GB free, emptied at start unless `SLOT_KEEP`. Size per slot: 0.18 GB at 2K tokens (#89, #212 logs) = KDA recurrent state ~143 MB (34 layers × 64 heads × 128 × 128 × 4 B) + latent KV ~11-15 KB/token → **~1.3-1.6 GB per slot at 100K** [INFERENCE].
  3. `STRATA_FAIR_SLICE_S` writes a slot on every time-slice switch; #179 adds system-prompt prefix slots.
  - Estimate [INFERENCE]: an agent with interleaved side requests, 300 switches/day × 0.5-1.5 GB = **150-450 GB/day**. A 1 TB TLC drive rated 600 TBW lasts 3.7-11 years at that rate. Not dangerous, but for QLC drives (870 QVO in #89) it matters. Turned off with `STRATA_GLM_SLOTS=0`.
  4. Checkpoints stay in RAM (~150 MB each).
- **RAM:** the engine **pins all but ~6 GB** of free RAM (`README.md:126`, `SETTINGS.md:29`), and pinned memory cannot be swapped.
  - Problems seen: #77 (a desktop with 3 monitors swapped at 12 GB headroom and stayed responsive at 16); ZFS ARC hiding free RAM (#89 → fixed in #99).
  - The HIP configs default to 16 GiB headroom; an APU leaves 16 GB (`glm_fast_path.cu:1019`).
  - On a 2-socket host the page cache of the model is dropped before pinning (`STRATA_GLM_DROP_CACHE`).
  - For a consumer PC, other programs "get little RAM while Maya runs" (`docs/SETUP.md:32-33`), so OOM/swap risk on desktops is real.
- **CPU load:** during decode the CPU lane **spins one thread per physical core** (`glm_fast_path.cu:2618-2663`), so all cores run at full power and heat while generating. It sleeps after 200 ms idle (`STRATA_GLM_SERVICE_IDLE_MS`), using ~1% of a core when idle.

## 7. New vs llama.cpp and vs our fork

**llama.cpp now** (parent's note): `--moe-cache-mib` (PR ggml-org/llama.cpp#29887, merged 2026-10-07, port of qvac-fabric; also in our fork base at `~/llama-master/common/arg.cpp:2795`).
- It is an LRU GPU cache for host experts, **single GPU only**, decode-only (batch ≤32); misses are uploaded and computed on the GPU; the source is pageable mmap memory.
- Qwen3.8-Flash-Next Q4_0: 4090 25.0 → 40.7, 5090 30.8 → 67.8 t/s, hit rates 72-89% (PR body).
- Community A/B (Niko1221/Strata#3082, a V100 on PCIe Gen3 **x4**, 16 GB RAM): Strata about 2.4× faster than llama.cpp with the cache (1.5× without MTP). A single box with an unusual link; llama.cpp's cache cost ~10% against loading normally (50 graph splits per token vs 2).
- **Expert offload with live caching is therefore no longer unique to Maya.**

**What is still genuinely new in Maya vs llama.cpp:**
1. **CPU-lane hybrid:** RAM-tier misses are computed on the CPU *in parallel* with PCIe fetches, with a per-machine split by miss count and re-timing during decode. llama.cpp's cache only uploads misses; `-ot`/`-ncmoe` is a static all-CPU placement.
2. **A third tier on NVMe** via O_DIRECT with chunked parallel reads, instead of mmap page faults.
3. **Profile-guided warm-up and per-layer slot budgets** (+15% on fresh starts).
4. Background promotion that never blocks a route; refill after prompt lending; next-layer expert prefetch (router on the current input, `PREFETCH_N`).
5. **A split cost model** pricing placements across up to 16 heterogeneous GPUs (RAM bandwidth, PCIe, coverage curve).
6. **Pipelined MTP across a 2-GPU split**, and the explicit finding that spec decoding loses on a single RAM-bound GPU.
7. DSA-aware KV streaming.
8. Self-calibration (`--calibrate` sweeps PCIe share, threads and read chunks; a speed calibration decides whether the drafter stays).
9. Opt-in approximations with published KL (`MISS_SKIP`, `TRUNK_KEEP`, `DISK_SKIP`: +23-62% on RAM-bound setups for KL 0.01-0.12; `SETTINGS.md:72-74`).

Not new: `--parallel` batching (llama.cpp `-np`), slot save (`--slot-save-path`), prompt cache, checkpoints for hybrid models.

**vs our fork:**
- Different problem. Ours is decode on one card with everything resident (Qwen3.8-27B at 29 ms/step with MTP, LFM at 293.7 t/s on the XTX). Maya's is a model that does not fit, where PCIe and host RAM set the speed.
- Both keep a kernel-parity discipline (Maya: parity tests, bit-identical CPU rows against ggml).
- **But Maya's default output is history-dependent** (the CPU lane, auto-sized pools, background moves), whereas our default is md5-bit-exact.
- RDNA3 overlap:
  - its IQ2_XXS/IQ2_S/IQ3_XXS decode expert kernels on gfx1100 use a packed sign expansion instead of HIP's emulated per-byte compare/subtract: −26-35% kernel latency, bit-identical; full model on a 7900 XT 15.1 → 16.4 t/s (`docs/AMD_EXPERT_KERNELS.md:17-23,90-113`);
  - `STRATA_GLM_MV_RDNA` (Q6_K/BF16 GEMV with two blocks' loads in flight): +3.1% on an 8065S, **not measured on an RX 7900** (`SETTINGS.md:68`).
  - Both matter only to users running IQ2/IQ3 quants on an XTX (big models), not to our Q5_K_M LFM.

## 8. Adoptable ideas, ranked

Our hardware: XTX + 64 GB dual-channel DDR4 (~40 GB/s practical); 3060 12 GB / 3090 / 5060 Ti 16 GB.
LFM2.5-24B-A2B Q4_K_M = 14.53 GB, 1.52 GB/token (`KERNEL/app/landing/src/lib/data/models.json:26`). It **does not fit a 12 GB card**; it fits the XTX entirely.

| # | Idea | Effort | Expected gain (arithmetic) | Minimal experiment → kill criterion |
|---|---|---|---|---|
| 1 | **Profile-guided warm-up for `--moe-cache-mib`**: ship a per-model expert-usage ranking; fill the cache in that order at load; budget slots per layer by profile | S-M (preload hook in the moe-cache + a small `--dump-routing`-like tool) | Maya: fresh start 35.4 → 40.7 t/s (+15%), route hits 89 → 96%. **Matters most for Podkręt, whose "after" number comes from a short run on a cold cache** | LFM Q4_K_M on a 3060 12 GB with `-cmoe --moe-cache-mib ~8000`: first 256 tokens tg, plus hit rate, with and without preload (5 fresh prompts, interleaved). **Kill if <5% on the first answer and <3 pp hit rate** |
| 2 | **CPU-lane hybrid for misses** (compute some missed experts on the CPU while others upload over PCIe; split calibrated per machine) | L (MUL_MAT_ID split between backends inside one op, in ggml's scheduler) | 3060 + LFM [INFERENCE: experts ≈ 0.9 of the 1.52 GB/token, hits ~80%]: misses 0.18 GB/token → upload-only 0.18/20 GB/s = 9 ms + GPU ~5 ms ≈ 14 ms (~70 t/s); hybrid with 40 GB/s CPU ∥ 20 GB/s PCIe ≈ 3 ms + 5 ms ≈ 8 ms (~120 t/s) → **up to +60-70% at a low hit rate, ~0 at a high one** | First measure the miss-time share: llama-bench with `--moe-cache-mib` at 4/8 GB vs everything in VRAM on a 16 GB card. **Kill if miss time is <25% of token time at the realistic cache size, or if `--moe-cache-mib` already reaches ≥85% of the fully-resident speed.** Bit-exactness: the CPU path changes the numbers, so opt-in, behind the KLD gate, with a fixed split plan for determinism |
| 3 | **Calibration discipline for Podkręt's "measure" step**: fresh prompts per measurement (no cache contamination), interleaved A/B, keep a setting only if it is >3% faster, store the result per PC+model+context; a speed calibration decides MTP/lookup on/off per machine | S (Python in the product) | Prevents regressions like DFlash2's on RAM-bound cards (#157 −30%, #172 −15%); a better-grounded before→after | Run Podkręt's measure twice on the same box. **Kill/rework if run-to-run spread is >3%** (then the threshold is meaningless) |
| 4 | **Auto-off for speculative decoding when experts stream from RAM** (Maya's rule: one RAM-bound GPU, no MTP) | S | Avoids −15…−30% (#157, #172). On the XTX everything is resident, so MTP stays on (43 → 102 t/s) | Future MoE+MTP models on 12-16 GB cards: MTP on/off at cache sizes of 25/50/75%. **Kill if MTP never loses** |
| 5 | `--bench` + `--report` → issue template → a public results table (hardware, versions, engine lines, median of N) | S | Credibility and data (Maya collected ~30 rows in 10 days). Improve on it: show the median, **the upstream baseline in the same report**, and the version | A Podkręt "Udostępnij wynik" button generating sanitised text. **Kill if users find it privacy-intrusive** |
| 6 | `-Xptxas -dlcm=ca` for sm_6x builds of our fork | XS (one CMake line) | Maya ×1.7-3 on its own GEMVs; llama.cpp mmvq unknown [INFERENCE: smaller] | tg128 on a rented P40/1080 Ti. **Kill if <3%** |
| 7 | RDNA3 packed sign expansion for IQ2_XXS/IQ2_S/IQ3_XXS mmvq in our HIP fork | M | Maya kernel −26-35% latency → full model +8.6% on a 7900 XT. Only for IQ-quant users (24 GB with big models) | Compare our HIP iq2 mmvq on gfx1100 against Maya's `hip_expert_kernel_bench` pattern; parity bitwise. **Kill if <10% per kernel** |
| 8 | Opt-in approximations ("skip light misses", KL-gated) | S-M | +23-62% on RAM-bound setups for KL 0.01-0.12. LFM's top-k is smaller, so each dropped expert costs more [INFERENCE] | KLD vs full computation on our wikitext suite. **Kill if KLD > our gate (0.128 canary level)**. Never a default |
| 9 | NVMe tier (O_DIRECT) for models larger than VRAM+RAM (gpt-oss-120b 63 GB, Mistral Small 4 74 GB on our 24+64 GB) | L | Lets them run at all; speed set by NVMe (~3-7 GB/s) × miss bytes | Only after #1-2. **Kill if llama.cpp's mmap + moe-cache gets within 20% of it** |

## 9. Competition notes vs Podkręt

- **Different promise.** Maya: "a 321 B datacenter model on your PC" — one model, its own engine. Podkręt: "your model, faster, proven against tuned upstream". They overlap for users with 24-32 GB cards and ≥96 GB RAM who want a frontier-class local coder.
- **Setup UX, a strong benchmark:**
  - one command, a textual TUI, the PC check prints the exact commands for anything missing, nothing is installed system-wide;
  - the model download is sha256-checked, resumable and shown before it starts;
  - **it builds from source in 20-40 min** (CUDA toolkit, g++, CMake needed), a weakness Podkręt can beat with prebuilt binaries;
  - it recommends a quant for the PC, with an optional 10-15 min calibration and a speed calibration;
  - Windows `.bat` and native ROCm on Windows;
  - the Update button does git pull plus an incremental rebuild.
- **Dashboard:** chat (stored in the browser), a Monitor showing where experts live and what fills each GPU's VRAM, a context-size setting, thinking levels, images.
- **API:** OpenAI + **Anthropic** (Claude Code via `ANTHROPIC_BASE_URL`) — **a feature Podkręt should match**.
- **Community benchmark loop:** `--bench` (3×256 greedy + 2K/8K prefill) → `--report` (hardware, versions, engine lines; nothing sent automatically) → a GitHub issue → a README row, credited by name. A very effective growth and validation loop. Weaknesses we can exploit:
  - **no comparison with llama.cpp**;
  - best-of runs, rows from mixed versions;
  - the first answers are slow (cold tiers);
  - output is **not reproducible** across restarts (§4);
  - it **pins all but 6 GB of RAM** (the desktop gets unusable);
  - writes conversation slots to the SSD;
  - 100% CPU spin during decode;
  - English only;
  - drafter licence CC BY-NC-ND.
- **Cadence risk/strength:** 51 releases in 10 days, large external contributor base (V100/P40 homelabbers), maintainers reply within hours. Tokens change from release to release.
- **What Podkręt should copy:** the report-to-issue loop, the "what fills my VRAM" view, the speed calibration that keeps a feature only where it wins, the Anthropic endpoint, a clear first-start explanation ("the start takes a few minutes").
- **What Podkręt should differentiate on:** a bit-exact default plus a KLD-gated fast mode, before→after against tuned upstream on the same prompts, prebuilt binaries (no 30-minute compile), RAM that is not hogged, a Polish UI.
