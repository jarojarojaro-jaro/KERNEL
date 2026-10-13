# Strata — version-by-version timeline (v0.1.0 → v0.1.43.1)

Sources: `git log`/`git diff --shortstat` per tag range in ~/research/Strata, `gh release view <tag> -R Niko1221/Strata`. Hashes are short SHAs. "5070" = the author's only test PC unless noted: RTX 5070 12 GB, Ryzen 5 7600 (AVX-512), 64 GB DDR5, Windows.

## 0. Shape of the history (facts)

- 49 tags in 19 days (2026-09-24 → 2026-10-12); 1,892 commits; **no commits after v0.1.43.1**: tag `v0.1.43.1` *is* `a0116b27` (HEAD).
- The engine existed before the repo: root commit `01529aaa` (v0.1.0) already holds 219 files / 50,165 lines (CUDA engine, MTP, expert tiers, packer, vision). Its README table (5070): Q2_0 prompt 539 tok/s @4K, decode 94.6 @4K / 65.1 @128K / 56.3 @262K.
- Authors: Niko1221 1,150 commits; ~200 contributors after that (maxfridbe 69 = SYCL port, sergiywith 43, Jakub Luwierski 28, …). Commits/day: 3–31 for Sep 24–27, then 84–189/day from Sep 28 on.
- **History rewrite 2026-10-06**: `main` was force-pushed; issue #1276 says the rewrite "appears to remove Claude-related commit trailers". `UPDATE.bat` got a migration step (`495ba076`), v0.1.40.1/v0.1.40.2 notes give `git reset`/`checkout -B` commands. [INFERENCE: much of the code is written with an AI coding agent; the commit/notes style (long, exact, measured sentences) fits that.]
- Size per range: tiny until v0.1.20 (1–19 commits/tag); then v0.1.30 71, v0.1.31 61, v0.1.32 89, v0.1.39 217, v0.1.40 307, v0.1.40.2 242, v0.1.41 126, v0.1.42 235, v0.1.43 72, v0.1.43.1 33.

## 1. Phases and turning points

| Phase | Tags | Theme |
|---|---|---|
| A. Ship & stabilize (single NVIDIA, Windows one-click) | 0.1.0–0.1.12 | server/API, conversation cache, KV streaming, prompt lookup, sampling, hang/race fixes |
| B. First perf push: prefill | 0.1.13–0.1.15 | 2x long prompts (MMQ experts, 8K chunks, next-layer expert streaming); stall hunting via thread dumps |
| C. Community + open source | 0.1.16–0.1.20 | MIT (0.1.16), Coder pruned model, sampler correctness, `--calibrate`, MCP |
| D. Multi-GPU + lettered perf plan (C-/D-/E-/F- items) | 0.1.21–0.1.26 | layer split, prompt kernels on tensor cores, verify-window batching, HIP port lands (0.1.25), batched MTP prompt pass |
| E. Breadth: hardware/formats/community PR flood | 0.1.27–0.1.35 | Turing, RDNA4, Unsloth Q4 3-tier SSD, Windows AMD, every PR gated byte-identical |
| F. Second perf push: fused int8 prefill, decode launch-count | 0.1.36–0.1.39 | fused Q2_0 prompt experts (+16–22%), cluster kernels, zero-doorbell verify graph (#646, +6%), batching (`parallel`) |
| G. Fork merge + gfx1151 + everything opt-in | 0.1.40–0.1.40.4 | Eddoursul-fork fusions (F4/F7/F12), Strix Halo 18 arch defaults, Intel Arc official, history rewrite |
| H. Defaults that change bits | 0.1.41–0.1.43.1 | CPU prompt share, route tail skip, measured PCIe share, gfx12 defaults, then hotfix rollback of an over-eager default |

Turning points:
- **0.1.13**: first big measured perf release (prefill 2x); release notes switch to before/after tables with hardware.
- **0.1.21–0.1.22**: work is broken into a lettered plan (`C-1..C-4` prefill selection/conv/gather, `D-1..D-5` prefill attention/GDN/streaming, `E-2..E-9` decode/draft, `F-1/F-2` fusions) — see `git log --grep='^[C-F]-'`.
- **0.1.25**: AMD HIP backend (PR #121, `fa42f31d`, squashed onto a 0.1.21 base) with tensor-core paths kept CUDA-only (`78a5bf70`).
- **0.1.36**: first release whose *default* changes answers (fused Q2_0 prompt kernels), justified by a KL/perplexity check vs an FP16 reference.
- **0.1.40**: "opt-in everything" release — dozens of kill switches, arch-default tables (`arch_defaults`) enabling only *bitwise-exact* switches per GPU.
- **0.1.42**: first *decode-quality-changing* default (`STRATA_ROUTE_TAIL_SKIP=7`), justified by teacher-forced KL vs a measured noise floor.
- **0.1.43 → 0.1.43.1**: a default (`STRATA_ADAPT_OVERLAP` on Linux CUDA) that won on the author's boxes lost −19..−21% on users' desktops → made opt-in everywhere within a day.

## 2. Per-version entries

### v0.1.0 — 2026-09-24 (root `01529aaa`)
- Windows binary release (sm_86/89/120 + PTX, CUDA 13.0), `START-HERE.bat` one-click; engine + optional vision encoder.
- Engine already complete: QSA/GDN layers, VRAM expert cache + pinned-RAM experts computed by CPU (AVX-512), SSD n-gram (PLE) table, MTP self-speculation "identical to greedy".
- Baseline (5070, Q2_0): prompt 389/539/571 tok/s @1K/4K/32K; decode 88.7/94.6/87.5/65.1/56.3 @1K/4K/32K/128K/262K.

### v0.1.1 — 09-24 (1 commit)
- Swift 1.5 fine-tune: split-shard GGUFs, per-model chat template, PLE table from any shard (`6801c77f`).

### v0.1.2 — 09-25 (2)
- Streaming tool calls (OpenAI/Anthropic deltas), real cancel (`STOP`), `/status`.
- Fix: expert cache sized *after* slots are touched (Windows counts VRAM only once touched) → card filled to 0 MiB and paged; prompt chunk now shrinks instead.

### v0.1.3 — 09-26 (9)
- Conversation cache (#8): keep chat + up to 6 checkpoints (~118 MB RAM each) → follow-up in 7.7K chat starts **0.3 s vs 12.9 s** (5070).
- Short prompt parts ≤64 tokens go through decode windows (`--short-read`) → "hi" ~0.2 s.
- CPU pool sleeps when idle (5 busy cores → 0, same speed); Linux dangling-else that spawned thousands of workers.

### v0.1.4 — 09-26 (3)
- IQ3_S (ISTA-DASLab GSQ-RCO, 83.6 GB): 54 tok/s @4K, 42 @128K, prompt 374–397 (5070). HumanEval 95.1% (Q2_0 92.1%).
- GPU kernel for IQ4_XS; MTP head accepts any head format (Q6_K).

### v0.1.5 — 09-27 (2)
- **KV streaming** for QSA layers: KV lives in RAM ≥64K ctx, only the attended part stays on GPU; freed VRAM → more experts. Q2_0 @262K **50.9 → 62.6 tok/s** (experts in VRAM 1,589 → 3,872); @128K +6%; IQ3_S +1%. Cost ~13.7 KB RAM/token, prompt −1% @262K. Bit-identical attention.
- Opt-in suffix drafter (`--suffix-draft`).

### v0.1.6 — 09-27 (1)
- Fix: MTP KV falls back to VRAM when no pinned RAM left ("mtp: state init failed").

### v0.1.7 — 09-27 (14)
- **Prompt lookup on by default "only where measured to pay"**: drafts up to 5 tokens from earlier context copy; code edits +6–11% (101 → 112 tok/s), other text unchanged.
- Per-request sampling honored (was greedy for all); `max_tokens` unset = rest of context; sampler block-per-token head sampling (`8f3c21dc`).

### v0.1.8 — 09-27 (6)
- `--kv q4_0` (PR #21): Q4_0 KV after FWHT-256 Hadamard rotation; 0.83 vs 1.52 GiB @128K; PPL +8% @1K, +12% @8K; default stays int8.
- Web app (Chat/Monitor/About), `/metrics`.
- Expert-cache warning removed after measuring: cache on vs off PPL diff −0.005 ± 0.005 nats/token (GPU vs CPU rounding only).

### v0.1.9 — 09-27 (6)
- Fix: head loaded before sizing expert cache (IQ3_S @128K ended with 30 MiB free → Windows paging → stalls). Q2_0 @32K 71.7 → 78–79 tok/s as a side effect.
- LAN access + API key; `--fit-max-tokens`; "experimental speed projection" control vector (actually a refusal-direction projection, costs 0.2–0.4%/token; off by default, explicitly labelled as not a speed-up).

### v0.1.10 — 09-27 (2)
- Engine death mid-answer → error + auto restart (#27); RAM-headroom warning; README video.

### v0.1.11 — 09-27 (4)
- Web-app "use for other apps too" default sampling. Engine unchanged.

### v0.1.12 — 09-27 (2)
- Race in CPU expert pool (#29): late-waking worker picked up next batch's work → infinite wait; work items now tied to a batch generation. Same speed.
- Progress watchdog (120 s, `STRATA_WATCHDOG_S`) → engine exits with location instead of silent hang.

### v0.1.13 — 09-28 (4) — **prefill ~2x**
- 5070: Q2_0 32K prompt **572 → 1,290 tok/s**; IQ3_S 383 → 1,208. Via: chunks up to 8,192 tokens sized to free VRAM, llama.cpp MMQ kernels for experts, next layer's experts streamed over PCIe during current layer, PLE for whole chunk. Needles 5/5 1K–262K.
- Watchdog 60 s + stall report (thread states, page faults, Windows minidump + PDB release asset). Two correctness fixes after release (`9ee557f7` zero tail before MMQ; `2838cbae` borrowable slots).

### v0.1.14 — 09-28 (14)
- Stall #31 root-caused from 0.1.13 dumps: waiting inside the NVIDIA driver on a DMA in mid-verify → **expert copies done by a GPU kernel (no driver call)**; ~1% slower IQ3_S; `--pcie-mode dma` restores.
- AVX2 multi-token i-quant kernels (PR #43): rows decoded once per verify window, ~+5% on AVX2-only CPUs. One worker per physical core on Linux (+16% on 13700K, PR #40). Profile ranks all 24,576 experts.

### v0.1.15 — 09-28 (4)
- `CUDA_MODULE_LOADING=EAGER`: all kernels loaded before cache takes VRAM (lazy load OOM mid-prompt at 64K+); costs ~30 MB (~20 experts).
- New speed tables: prompts 1.2x (1K) to 2.4x (32K–128K) vs old tables.

### v0.1.16 — 09-28 (13)
- GSQ-RCO Coder (256 of 512 experts, PR #54): 32 GB RAM; 599–1,350 prompt, 43–53 decode on 12 GB.
- Model files in `Strata-data` (no re-download). **MIT license.**

### v0.1.17 — 09-28 (7)
- Claude Code compatibility; sampler penalties applied twice → llama.cpp order; `--gpu N`; `needle_bench.py`.

### v0.1.18 — 09-28 (3)
- Sampler guard for empty penalty window; releases now published atomically with engine.

### v0.1.19 — 09-28 (6)
- Penalties applied only to first token of each verify batch → every checked token gets its own history; penalized requests 1–11% slower (more rejections). Found "by an engineering review".
- **`--calibrate`**: measures PCIe share, draft depth (`--spec-min-p`), CPU threads; keeps a setting only if >3% faster; Coder +7.6% on 5070.

### v0.1.20 — 09-28 (19)
- Prompt-cache root checkpoint at end of system prompt (≥2,048 tokens), pinned while others LRU-rotate.
- PCIe bandwidth probed at start (PR #44); x8 links lower the share; per-request expert hit-rate telemetry.

### v0.1.21 — 09-29 (16) — **multi-GPU**
- Layer split across GPUs (no P2P needed), pipelined prompt chunks, auto placement by a decode-window cost model (`641c62a0`: per-layer time from SMs×clock + missed routed mass), within 0–12% of best measured.
- 5080+3090: prompts +18–20% (2,357 vs 1,970 @28K); decode on par (84/110 tok/s) — "the per-layer GPU time decides".
- <4 GB/s links: PCIe share 0 (CPU computes all misses). Single-GPU byte-identical to 0.1.20.

### v0.1.22 — 09-29 (25) — lettered plan items
- 5070 Q2_0: 32K prompt **1,213 → 1,646**; 128K 1,144 → 1,596 (TTFT 116 → 83 s).
- D-1 QSA prompt attention on tensor cores (4x, 3xTF32 "FP32-level"); C-4 multithreaded n-gram reads (Linux 16K 3x); C-1..C-3, D-2, D-5 remove host waits (bit-identical, `STRATA_PROMPT_ATTN_OLD=1` restores exact 0.1.21).
- Detokenizer O(1) per token (cost 4 ms/token after 16K).

### v0.1.23 — 09-29 (38)
- **Verify window per-token kernels (router, norms, RoPE, shared-expert cast, combine) run once for the whole window** (`4a50d4ce`, Andy, PR #109): bit-identical; 5080+3090 decode 81 → 89 (story), 105 → 118 (code).
- llama.cpp-compatible `/models`, `/props`, `/slots`, `timings`. Bulk expert reads on Windows.

### v0.1.24 — 09-29 (3)
- QSA selection: block scores on tensor cores (3xTF32), top-k keys in registers → selection 3.3–3.9x faster; 128K prompt 1,608 → 1,843 (`2f9c38f0`: +14.6%). Old path via `STRATA_SELECT_OLD=1 STRATA_TOPK_OLD=1` byte-identical.

### v0.1.25 — 09-29 (21) — **HIP backend**
- Prompts +7%: grouping tables via mapped pinned memory, off the copy engine (`1b3bb8f8`, +3.9/+4.5% @32K/128K); F-1 (no FP32 copy of normalized rows, +1.1–1.7%) and F-2 (HC write fused with next norm; together +4.0/+3.3%). Bit-identical.
- AMD RX 7900 XT/XTX Linux (PR #121): ROCm in venv, hipBLASLt table tuned for 7900 XTX (`5cb4ff28`: **+42–59% prompt on 7900 XTX**); Coder IQ1_M 1,200–1,330 prompt, 50–68 decode.
- `--kv k8v4` (int8 K + rotated Q4_0 V, PR #120): −23% KV VRAM; 3090 @198K 85 → 99 tok/s.
- E-8 (draft prompt pass in groups of 8, −6% of its time) committed then reverted same day (`86c904ca`).

### v0.1.26 — 09-29 (5)
- **E-9: MTP layer's prompt pass batched through the prefill kernels** (`a402eefd`): 0.9 s → 0.07 s of a 32K prompt; prompts +4–10% (32K +5–6%); acceptance 0.700 → 0.699 (Q2_0); HIP +13–19%. `STRATA_MTP_BATCH=0` reverts.
- Low-RAM mode (`--mmap-experts`): committed memory 36 → 13 GB on Coder.

### v0.1.27 — 09-29 (9)
- Draft vocab subset grown 40,525 → 106,299 ids to include all CJK (#137): Chinese answers +15–38% (55 → 76 tok/s etc.), English −1–2%, +110 MiB VRAM. `tools/draft_vocab.py`.
- RTX 20 (sm_75) with portable prompt kernels.

### v0.1.28 — 09-30 (8)
- Cache now reserves the larger draft head's VRAM (0.1.27 left 210 MiB, "below the stall line"); `--draft-vocab en`. Cancel-state leak fixed; API key hardening.
- Release check notes "AMD: not tested again (test PC unreachable)".

### v0.1.29 — 09-30 (24)
- Sampled decoding up to +40% (#197): top-k split over whole GPU + sampling on one warp; Q2_0 +38–42% at top-k 64, identical tokens.
- Bit-identical kernel wins: QSA block scores read each key block once for all window queries (#187); GDN prefill recurrence software-pipelined loads (#188, `STRATA_GDN_PIPELINE=0`); AVX2 prefetch of expert rows (#207).
- Correctness (#154): NaN→bf16 stays NaN, barrier before warp return, masked unresolved KV blocks.

### v0.1.30 — 09-30 (71)
- Short prompts +17–28%: experts stream from 1,024-token chunks (was 2,048) (`3e3d69b4`).
- RDNA4 gfx1201/1200 (PR #178); `doorbell_ring` volatile store so host sees ring on RDNA4 (`70e24f43`).
- Many opt-ins: YaRN/linear rope scaling, multi-conversation cache, `STRATA_IQ_MT_MIN=1` (draft-independent CPU rounding; −1–3% so opt-in, "the owner's choice" `31ad9627`), `STRATA_SPEC_COUPLED=1` ("no clear gain, stays off"), Docker, Pascal.

### v0.1.31 — 10-01 (61)
- Unsloth UD-Q4_K_XL (111 GB) on 64 GB: 3 tiers (VRAM / RAM budget / SSD with router-predicted 1-layer-ahead prefetch): ~7–8.5 tok/s on 5070.
- AMD RDNA4 decode +15% R9700, +5–7% 9070 XT via `__byte_perm`→`v_perm_b32` + SWAR byte intrinsics (`600d7307`, PR #262); R9700 67 → 82 tok/s.
- Q2_0/IQ expert kernels do less work per token, bitwise (#241, #242).
- Release gate text: "Every merged change was gated on its own … in nine rounds"; reworked/dropped: Windows pin cap (#243 → opt-in), polling wait in verify (cudaStreamQuery poll cost ~3% IQ3_S, `5865998a`), **#257 reverted** (AVX2 two-block unpack bit-exact but −2.6..−5% on Ryzen 3900X, `a88904e5`). `STRATA_GR_V3=1` (2-kernel HC read, +2–4%, other summation order) opt-in.

### v0.1.32 — 10-01 (89)
- **AMD router rewritten without serial parts** (`a2be1670`): R9700 decode 62 → 70 (+12%), 9070 XT +4%, bitwise. Opt-in `STRATA_HIP_WMMA=1` RDNA4 prompt attention +36–51% (bits change).
- **Verify commit no longer `cudaStreamSynchronize`s; overlaps the MTP draft** (`a1e4fb4c`, sergiywith): host held ~0.45 ms/round → IQ2_XS 128.6 → 135.8 tok/s (+5.6%), same tokens.
- Layer-split prompt regression (−35% on 2x A5000) fixed by concurrent refills; UD-Q4_K_XL prompts 2.8x (32 stager threads).
- Gate: "release decodes +1.5 to +3.8% faster than 0.1.31 with the same expert slots" (5 pairs); Unsloth MMQ kernels made a build option because eager-loaded kernels cost every model 1–3 expert slots (`bf7b181a`).

### v0.1.33 — 10-01 (17)
- Vision encoder rebuilt portable (0.1.32's was AVX-512+OpenMP → SIGILL). Setup "recommends instead of forcing"; golden test that `--yes` configs are byte-identical on 23 PC/model combos.

### v0.1.34 — 10-02 (22)
- AMD on Windows (ready-made HIP zip with bundled TheRock ROCm 10.2); MCP server for AI-assisted setup; README split into docs.
- Cancel on client hang-up within ~1 s (was 17–33 s); MMQ `J_best=0` falls back to FP16.

### v0.1.35 — 10-02 (13)
- Windows AMD: bundled `amdhip64_7.dll` beside exe (System32 copy won the DLL search and crashed). Low-RAM resident mode on 32 GB Windows.

### v0.1.36 — 10-02 (15) — **fused int8 prefill**
- Q2_0 (5070): prompt 4K 1,294 → 1,570 (+21%), 32K 2,170 → 2,653 (+22%), 128K 2,123 → 2,468; decode 128K 64.5 → 76.4 (+18%).
- Fused int8 tensor-core expert kernels reading each expert in place, grouping on GPU (#136; "inspired by the measurements of" flashrt). **First default that changes bits**: justified by teacher-forced KL vs FP16 reference (32K: KL 0.009 vs 0.012, PPL 4.121 vs 4.169, ref 4.129). `STRATA_PF_FUSED=0` reverts; IQ packs opt-in (IQ3 "about even").
- RTX 50 thread-block-cluster QSA selection + argmax (bit-identical over 650 cases).

### v0.1.37 — 10-02 (12)
- Server-side silence watchdog (#481); Windows AMD WDDM budget (RX 6800 31 → 42 tok/s); PCIe probe best-of-4 and smooth share below 20 GB/s.

### v0.1.38 — 10-03 (56)
- Prefill bitwise: MMQ group gathered in one launch/one wait (#372), n-gram rows beside layer 0 (#374), **DeltaNet recurrence 3 heads per thread** (#413). Q2_0 +10% @4K, +2.7–3% @32K/128K.
- `--kv q4_0` prompt attention on tensor cores (#452): 32K 18.8 → 14.3 s; KL 0.026 vs 0.031 old.
- #463: adaptive tier waits for its copies → greedy output independent of copy timing (changes acceptance on some prompts: 75.1 → 70.9 or 69.7 → 73.0).
- `STRATA_GR_DOWN_MAX4` opt-in; hipBLASLt tables gfx1200/1201 (~1.5–2x prompt with system ROCm 7.2).

### v0.1.39 — 10-04 (217)
- **Decode #646 (Stuart Chapin, `a36be1db`)**: zero-doorbell verify graph, sub-warp expert packing, staged inputs, batched PLE/MTP steps → Q2_0 +6% (68.4 → 72.7 story, 75.8 → 80.0 code), 10 interleaved pairs, byte-identical. Follow-up `39841946`: drop IQ-grid staging in single-matrix MMVQ (−10–20% at 3–8 cols on 5070).
- Long prompts: byte-sized expert ring (#583) IQ3_XXS +18.5% @32K with 1,500-slot cache; Coder −8% in one config → kept only where it gains (`56501a38`).
- QSA top-k beyond register reach via per-warp histogram: 9–12x at 262K–524K cells, 243K prompt +26% on 3060.
- `"parallel": N` batching (opt-in): 4 requests last-start 11.2 → 1.8 s but aggregate −11% on 12 GB (each slot steals 0.56 GiB of cache). Intel Arc SYCL port (maxfridbe) experimental; CUDA 12.9 engine for Pascal/Volta; AVX/SSE4.2 floor builds.

### v0.1.40 — 10-06 (307)
- Strix Halo gfx1151: 18 switches auto-on "all byte-identical" (`9708b549`: only exact switches become arch defaults; rounding-changing stay opt-in). +6% prompt, +4% decode over its branch.
- Eddoursul fork fusions (F7: draft layer front once, one-token window commits itself, final mixer fused, multi-block argmax) and #783 kernel set (QSA early exit +2.7% @120K, GDN decode kernels, vec4 router, batched KV append, multi-token GR), each with a kill switch.
- HIP: shared-expert stream fork off by default (regression #816/#826); doorbell fence after ring store (#697). Many bitwise HIP opt-ins (`STRATA_Q8_PACKED`, `TSUM`, `LFUSE`, `GDN_PP`, `GDN_CONVL2`, `GDN_NOY`, `HCD_EXACT`, `EXPERT_V2`).
- NVIDIA decode vs 0.1.39 (5070, 12 pairs): −0.3% to +3.4%. Opt-ins that lost: `STRATA_KV_PREFETCH` (−4–5%), `STRATA_DEFERRED_REGISTER` (−8%), `GR_DOWN_MAX4` (no gain, `46d01366` reverted its sm_120 default).
- Linux cold start 920 → 70 s (read-ahead).

### v0.1.40.1 — 10-06 (7)
- Server-only hotfix: tool-call rescue from thinking restricted (37 recorded cases), restart wait-list hang (#1012). First tag on the rewritten history.

### v0.1.40.2 — 10-07 (242)
- **Interleaved q8_1 activations for 2–4-token verify projections** (fork F4, `ffac97f7`): weight block decoded once, applied to every token; bitwise; 3060 +4.2% decode (12/12 pairs), 5070 +1.3–2.2%. Briefly made opt-in after a 2-GPU report (−15%, #1373, `f7610d2c`) then reverted within ~1 h (`668072aa`); later per-arch rows table (`2d6c6ae5`, docs/MMVQ_IL_TABLE.md).
- 4x R9700 split +60% prompt (tie-breaking); Linux low-RAM +20–42% via page cache; GB10 stager sleep 10x (Linux default only, Windows −1.2%).
- gfx1100 hipBLASLt table rows for **small-T expert GEMMs** (`a45783c7`): 642 fallbacks were f16 N=1280 K=2560 at T 1..1873 → 7900 XTX 3,151-token prompt 691.6 → 940.7 (+27.6–36%).
- Opt-ins: CPU prompt share (`STRATA_PREFILL_CPU_SHARE=auto`, short prompts −19–35% time, KL 0.006), Gumbel-max coupled drafts (+5.7–9% AMD, noise on 3060), PDL/mixer branches (`2e4ddf6e`, all off).
- Intel Arc official (B70/A750): aliased-page allocations, MTP acceptance 4% → ~60% (draft token read before GPU wrote it).

### v0.1.40.3 — 10-07 (23)
- Intel install/A-series fixes; Windows AMD 16 GB+ cards keep 2,560 MiB free (RX 7900 XT IQ3_S 24 → 55 tok/s possible); bundled HIP deps.

### v0.1.40.4 — 10-08 (2)
- Pascal decode halved since 0.1.40.2 (lost `__restrict__`, added prefetch Pascal can't overlap) — found by users' bisect; fix limited to < sm_70, newer archs' code byte-identical.

### v0.1.41 — 10-08 (126)
- Default `--batch-groups auto` on layer split: one request group per GPU stage, 8 clients +32–68%; 4x R9700 88 → 165 tok/s.
- **Default CPU prompt share for chunks <1,024 tokens on one NVIDIA GPU** (changes bits; first-token KL mean 0.004, max 0.025): 3060 512-token +28%, P100 +33%; 5070 0–2% (cache already holds the experts).
- Windows bigger-than-RAM prompts ~2x (unmap view; batched reads, #1323). Tokenizer cache 0.32 → 0.07 s for 89K prompt.
- Opt-ins that didn't pay: Foresight swap space (0.91–1.00x), `STRATA_GDN_CHUNKED` (1.8x on 128-SM cards, **0.87x/0.73x on 48/28 SMs**), `STRATA_ROUTE_RESIDENT` (+4.1% 5070, −1.6% 3060), `STAGE_PIN` (+8% P100 but corrupted IQ3_S in release gate → pulled back to opt-in `fb58e0db`).

### v0.1.42 — 10-10 (235)
- **`STRATA_ROUTE_TAIL_SKIP=7` default on CUDA** (PR #1668): in a verify window, a missed expert ranked ≥7th by every token is skipped. 3060 +15.6%, A4000 +12.9%, P100 +14.6% (5/5 rounds); all-resident split −0.2%. KL 0.003–0.006 vs noise floor 0.0007; top-1 97.7–98.2%; PPL ×1.005–1.011.
- Measured PCIe share: engine times CPU pool in first ~10 s of decode, balances GPU/CPU share (3060 0.55 → 0.20: 47.7 → 62.1 tok/s, +30%). 5070 Q2_0 77.0 → 85.6 (+11.2%).
- gfx12 prompt switch defaults (+0.8–1.8%, bitwise). Windows AMD 7900 XTX `--prefill auto` capped at 6,144 (8,192 charged ~70 GB commit; −14% prompt).
- Opt-ins: fused int8 gfx12 prompt experts (+15–19%, but IQ3_XXS KL worse than MMQ → opt-in), pipeline windows 3+ cards (+33.7% code 4x R9700, −3.3% on 2), replicas, `STRATA_HEAD_MIX_MULTI`/`ONE_TOKEN_COMMIT` (identical, "no measurable gain").

### v0.1.43 — 10-11 (72)
- AMD gfx12 gets NVIDIA's decode defaults (tail skip, measured PCIe), fused prompt experts default for IQ3; **fewer/fused graph nodes in decode window +1.6–2.0%** (`7fc02cb5` split HC norm from registers −1.8 µs/read, host-flag waits folded into following copies −2 nodes/layer; `a9917a55` HC up kernel writes its consumer's q8_1 image, `moe_hit_add` folded into combine).
- R9700 w/16 GB cache IQ3_XXS +21–38%; P100 +7–10.7%; B70 +14–21% (new expert ranking 60% → 71% hit).
- `STRATA_ADAPT_OVERLAP` default on Linux CUDA (A4000 +5–10%); opt-in on Windows (5070 −2.6%).
- Tail-skip off at ≥90% experts cached (#1884, V100 −1–2%); 60% on AMD split. NaN-logit guard (≤0.2% cost). Windows GGUF-in-place decode 1.35–1.85x (close mapped views so NTFS unbuffered reads parallelize). `BENCH.bat`.

### v0.1.43.1 — 10-12 (33; ends at `a0116b27` = HEAD)
- **Rollback**: `STRATA_ADAPT_OVERLAP` opt-in everywhere (`661ff293`): 5070 Ti desktop −21% (68.4 vs 86.4), 5060 Ti −19%, 5090 Laptop −21% (84.6 vs 106.6).
- Root cause (#1983): decode thread pinned to one core; CUDA host-callback thread created lazily inherited that affinity → ~1 ms per per-layer callback. Fix: warm the callback thread before pinning (`0e20d9ae`) and replace callbacks with a 4-byte stream-ordered copy into pinned memory as the "copies landed" signal. 3060: 36.5 → 56.5 tok/s with reporters' settings.
- PLE probe only warns (SATA SSD 10–14K rows/s < NVMe-calibrated 15K bar; mmap was 7x slower). 7900 XTX memory-access fault after ~30 min multi-slot: **all prompt-path H2D copies from pageable memory now go through a ring of pinned buffers**. Two-GPU `--batch` +35% back (`a0116b27`). RX 6000 prompt −16–20% since 0.1.40.2 fixed by restoring MTP side stream on gfx103x.

### Post-v0.1.43.1
- None: `git rev-list v0.1.43.1..a0116b27` is empty; `a0116b27` (2026-10-12 15:20 +0200, "Layer split + --batch: the default pipeline wins over --batch-mtp", #2038) is the tag commit itself. Last three commits: `017a672a` bench doesn't save expert profile, `85f839d8` gfx103x MTP side stream, `a0116b27`.

## 3. Introduced → reverted / disabled / kept opt-in (with reason)

| Idea | Where | Outcome & stated reason |
|---|---|---|
| E-8 MTP prompt pass in groups of 8 | `45d857c7` → `86c904ca` (09-29) | Reverted same day; replaced by E-9 full batching (0.9 → 0.07 s) |
| #257 AVX2 two-block Q2_0 unpack | `a88904e5` | Bit-exact but −2.6..−5% on AVX2-only Ryzen 3900X |
| cudaStreamQuery poll in verify (#267) | `5865998a` | Cost IQ3_S ~3% → blocking sync kept, watchdog handles hang |
| Windows arena pin cap (#243) | `f73b0e06` | Cost speed on 64 GB PC → opt-in |
| `STRATA_GR_V3` 2-kernel HC read | `aa0777f7` | +2–4% but different summation order → opt-in |
| `STRATA_IQ_MT_MIN` draft-independent CPU rounding | `31ad9627` | −1–3% IQ3_S → opt-in ("owner's choice") |
| `STRATA_SPEC_COUPLED` coupled draft sampling | `3b4230a1` | "No clear gain" → off |
| QSA top-k by active blocks (#337) | `01ec3ac9` | HIP only; CUDA 64K prompts −1–3% |
| BF16 GEMV on Turing tensor cores | `43cd140e` | Benchmark-only, 1.3–2.2x slower: GEMV bandwidth-bound, 1 token wastes 15/16 of m16 MMA tile; bench checked in "so this does not have to be measured twice" |
| IQ grid staging in single-matrix MMVQ | `39841946` | −10–20% at 3–8 cols on 5070 → only grouped kernels stage |
| Byte-budget prefill ring (#583) | `56501a38` | Coder −8% in one config → only where it gains |
| `STRATA_GR_DOWN_MAX4` default on sm_120 | `46d01366` | Bitwise but B/A 0.97/0.97/0.99 over 10 pairs → opt-in |
| `STRATA_HC_Q8` smem cap raise | `9c2be9fd` | Reverted (graph capture failure) |
| HIP shared-expert stream fork | v0.1.40 notes | Decode regression #816/#826 → off on AMD (but default on gfx1151 where +1.8–6.7%) |
| `STRATA_KV_PREFETCH`, `STRATA_DEFERRED_REGISTER` | v0.1.40 | −4–5%, −8% on 5070 → off |
| `STRATA_MMVQ_IL` default | `f7610d2c` → `668072aa` | Opt-in after 2-GPU −15% report, reverted ~1 h later (bitwise; report attributed to host load "lottery" in #1373) |
| `STRATA_STAGE_PIN` default | `d2e3f1c9` → `fb58e0db` | Release gate found IQ3_S corruption (buffer reused before copy done) → opt-in; fixed with per-buffer event in 0.1.42 |
| `STRATA_GDN_CHUNKED` (32-token chunked recurrence) | `0f78032f` | 1.8x on 128 SMs, 0.73–0.87x on 28–48 SMs → only ≥128 SMs |
| Foresight swap space | `14f9e4c5` | 0.91–1.00x → off |
| `STRATA_DOORBELL_CHECK` (SYCL) | `3157c789` | −17% A750 decode → opt-in |
| `STRATA_HCD_EXACT` in gfx12 defaults | `7609cc18` | "Inert without the tuning table, and noisy" → dropped |
| PLE auto-switch to mmap | `30017336` → `0cf3d510` | SATA SSD 7x slower prompts, watchdog kills → warn only |
| `STRATA_ADAPT_OVERLAP` default (Linux CUDA) | `f95f2eab` → `661ff293` | −19..−21% on user desktops (callback-thread affinity) → opt-in |
| Route tail skip near-full cache | `6ab541f6`, `60abf63e` | V100 at 94.8% cached −1–2%; AMD split −6% at 70% → off ≥90% (60% AMD split) |

## 4. Cadence, gating and note style

- **Gating ladder** (stated in every release from ~0.1.21): (1) byte-identical answers vs previous release on 4 quants, 10/10 prompts each "with a fixed cache" (`--prompt-cache 0 --adapt-swaps 0 --pcie-frac 0` needed for repeatability, #410); (2) prompt-path internal state ("exact_pp", residual dumps) identical at 4K and 20K tokens; (3) 5-pair (later 10–12) **interleaved A/B medians with equal expert-slot counts** (`tools/ab_engine.py`: restart server per arm, alternate order, warm-up, fixed greedy prompts); (4) real use at 57–59K prompt through server (needle, follow-up reuse, tool call, cancel, sampled answer); (5) server/setup test counts (68 → 376).
- **Every perf change ships with a kill switch** (`STRATA_*=0` restores the exact old path), and old kernels are kept (e.g. `STRATA_SELECT_OLD`, `STRATA_PROMPT_ATTN_OLD`, `STRATA_HIP_ROUTER_OLD`).
- **Default policy**: bitwise-identical → may be default (often per-arch via `arch_defaults`); changes bits → opt-in unless backed by teacher-forced KL against FP16 reference / against a run-twice noise floor plus multi-machine A/B (0.1.36 fused prefill, 0.1.41 CPU share, 0.1.42 tail skip). Every bit-changing default is listed under "Answers can differ" with its opt-out.
- **Community claims are labelled**: "the author's number", "measured by the reporter", "we have no such card", "untested here". Only the author's own hardware results drive defaults; foreign gains stay opt-in until measured (e.g. `STRATA_SM70_TABLE`, A770 fast path).
- **Measurement hygiene**: same expert slots between arms; medians over interleaved rounds; notes call 2–4% swings "noise" when attributable to draft acceptance or shared boxes; mention which rounds were faster ("5/5 pairs").
- **Release notes style**: one-line bold headline; "Faster" with tables (machine, model, before → after, pair count); "Fixes" with issue numbers and root cause in plain words; "New opt-ins" with numbers even when negative; "Checked before the release"; "Not fixed"; "Testers wanted". Plain-language, no marketing; 0.1.9 explicitly says the "speed projection" "is not an engine speed-up".
- **Hotfix cadence**: four-part versions (0.1.40.1–.4, 0.1.43.1) within 0–1 day for regressions reported by users; regressions found by users' bisects (Pascal), reverted narrowly (only < sm_70).
- **Commit style**: subject states mechanism + measured effect + kill switch, e.g. "prompt path: … (+3.9% at 32K, +4.5% at 128K, bit-identical)"; bodies record numbers/hardware/pair counts.

## 5. Transfer candidates (dense Qwen3.8-27B, one RX 7900 XTX, llama.cpp HIP fork, MTP n=4)

MoE/tier-only ideas (tail skip, PCIe share, expert caches, KV streaming, layer split, CPU prompt share) are excluded — no experts/offload in our setup.

1. **Remove the host sync between verify commit and next MTP draft** — `a1e4fb4c`: commit graph returns immediately, next window/drafter ordered on streams; ~0.45 ms/round saved → **+5.6% decode (IQ2_XS 128.6 → 135.8, NVIDIA)**. *Why for us:* our step is ~35.7 ms; any host `hipStreamSynchronize` between accept and next draft graph is pure loss → directly fits K3.
2. **Batch every per-token kernel of the verify window** (router/norm/RoPE/casts/combine once per window) — `4a50d4ce`: **81 → 89 / 105 → 118 tok/s (5080+3090), bitwise**. *Why:* we're at ~970 kernels/verify at ~3.3 µs gaps; audit for any per-column launches left (K2).
3. **Graph-node diet: fold host-flag waits into following copies, read split norms from registers, fold small adds into combines** — `7fc02cb5`/`a9917a55`: **+1.6–2.0% decode on R9700 (gfx12 HIP), bitwise**; also "zero-doorbell verify graph" #646 **+6% (5070)**. *Why:* on HIP graphs the per-node gap is the cost; same playbook as our K2 at ~3.2 ms of gaps.
4. **Interleaved q8_1 activation copy for 2–4-col MMVQ + per-arch rows-per-warp table** — `ffac97f7`, `2d6c6ae5`, docs/MMVQ_IL_TABLE.md: one small kernel interleaves activations so a warp decodes each weight block once and applies it to all tokens; **+4.2% decode RTX 3060, +1.3–2.2% 5070, bitwise**; rows/warp tuned per arch by a parity+bench tool. *Why:* we already unpack weights once per thread; the remaining pieces (interleaved activation layout for coalesced loads, a tuned rows table per width) are cheap K1 experiments. CUDA-only in Strata — unmeasured on RDNA3 [INFERENCE].
5. **Producer writes the consumer's q8_1 image; no separate quantize launches** — `a9917a55` (`STRATA_QFUSE_HC`), `be7889ed` (QDEDUP: one q8_1 image shared by shared-expert and experts; SwiGLU+q8_1 one launch, `e7a5fd30`). *Why:* we did this for some producers; check SwiGLU→down and any duplicated quantize of the same rows (K2).
6. **Byte-level intrinsics on AMD** — `600d7307`: `__byte_perm`→`v_perm_b32`, SWAR `__vsub4`/`__vcmpne4`; **R9700 decode +15%, 9070 XT +5–7%**. *Why:* if our HIP MMVQ dequant uses CUDA-compat byte ops that lower to shifts/masks on gfx1100, this is a free K1 win; verify ISA.
7. **Rewrite serial reductions/top-k as parallel on RDNA** — `a2be1670`: router without serial parts **+12% decode R9700, bitwise**; sampler top-k split across GPU **+38–42% at top-k 64 sampled** (#197). *Why:* our MTP drafter/sampler top-k over 64k/248k vocab may have serial tails; relevant if we sample at T>0.
8. **hipBLASLt tuning rows for the actual small-T shapes** — `a45783c7`: 642 fallbacks at f16 N=1280 K=2560 T=1..1873; 17 rows added → **7900 XTX prompt +27.6–36%**; earlier 7900 XTX table +42–59% prompt (`5cb4ff28`). *Why:* only applies to GEMMs that go through hipBLASLt (our prefill is ~90% MMQ), but any f16/bf16 GEMM left (e.g. GDN projections, lm_head in prefill) should be checked with a verbose fallback log (K5).
9. **GDN prefill recurrence kernels** — software-pipelined loads (#188), 3 heads/thread (#413, part of +10% @4K), `GDN_PP=2` two columns per lane at 10 waves/SIMD, `GDN_CONVL2` conv+L2-norm fused, `GDN_NOY` no dead FP32 write (all bitwise, gfx12/gfx1151 defaults, +0.8–1.8% prompt combined on R9700). Chunked 32-token recurrence only wins on ≥128 SMs (0.73–0.87x on 28–48). *Why:* our 48 GDN layers dominate non-MMQ prefill time; the 7900 XTX has 96 CUs, so chunked is borderline [INFERENCE] — measure.
10. **Batch the MTP head's prompt pass through prefill kernels** — E-9 `a402eefd`: **0.9 → 0.07 s of a 32K prompt, prompts +4–10% (5070), +13–19% on HIP**. *Why:* if our fork runs the MTP head over the prompt token-by-token or in small groups, this is a direct prefill win (K5); if already batched, nothing to do.
11. **Draft-vocab subset by script coverage** — 0.1.27: CJK added (40.5K → 106K ids): CJK answers +15–38%, English −1–2%. *Why:* our 64k reduced vocab trades the same way; check acceptance on non-English/code before self-distillation.
12. **Host-thread pinning pitfall** — 0.1.43.1: pinned decode thread made lazily-created runtime callback thread inherit one core → ~1 ms per callback, −19..−21% decode on desktops; fix = create runtime threads before pinning, use stream-ordered 4-byte copies to pinned memory as signals instead of host callbacks. *Why:* relevant if K3 adds thread pinning or `hipLaunchHostFunc`.
13. **Pageable H2D copies on gfx1100** — 0.1.43.1: 7900 XTX memory-access fault after ~30 min multi-slot; all prompt-path copies from pageable memory moved to a pinned ring. *Why:* reliability for long sessions with our prompt cache.
14. **Methodology to copy** — interleaved A/B with server restart per arm, medians, equal cache/state, bitwise identity gate + kill switch per change, teacher-forced KL vs run-twice noise floor for any bit-changing default, check-in of negative benches. *Why:* our noisy negatives (HIP env knobs, hipBLASLt env) look like the "load lottery" #1373 describes — interleaving and pair-counting would make 1–3% K1/K2 wins decidable.

Not transferable / weak: PDL & thread-block clusters (sm_90+ only); tensor-core GEMV (measured slower for 1 token); route tail skip/PCIe share/expert caches (MoE+offload); Gumbel-coupled drafts (gain only on AMD reporters, noise on 3060; only matters for sampled decoding); adaptive draft depth via `--spec-min-p` + `--calibrate` (we measured p_min gating with no gain — Strata also only tunes it per PC, no reported large gain).
