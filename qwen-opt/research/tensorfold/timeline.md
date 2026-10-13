# TensorFold: version-by-version timeline (v0.2.0 → v1.0.8)

This is a read-only study of `~/research/TensorFold` at HEAD `0efbd447` (= v1.0.8, 2026-10-12). Sources: `git log`/`show`, `CHANGELOG.md`, `RELEASE-NOTES-1.0.0.md`, `ZIG-PREVIEW.md`, the `docs/recipes/*`, and `gh release view` for all 32 releases (saved in `/tmp/tfrel/*.json`). `#N` means https://github.com/ashhart/TensorFold/issues/N (or `/pull/N`). Dates are tag-commit dates in BST unless marked. Hardware is named on every number. Anything I could not verify directly is marked [INFERENCE].

---

## 0. Summary

- **Timeline.** The repo spans 18 days (09-25 → 10-12), 1,560 commits and 32 tags, in two engine generations:
  - Python + MLX + Metal kernels + torch/Triton/.cu on CUDA: **v0.2.0 – v0.6.6**.
  - A native Zig binary that drives Metal and CUDA directly: **v1.0.0 – v1.0.8**.
- **The history was rewritten twice, both times on purpose:**
  1. The pre-0.2.0 project (a disk-paging MoE runtime from June 2026) was erased. A fresh root commit was made on 09-25.
  2. The Zig engine was published on 10-04 as one 105k-line squash. The original author's 91 commits were then grafted back in as a no-op merge parent (§1).
- **Qwen3.8-27B (our model) is the slowest-maturing line in the native engine.**
  - It was excluded from 1.0.0 because it was slower than Python 0.6.6 (`CHANGELOG.md:203`).
  - It came back in 1.0.3 (10-09).
  - At HEAD, its prefill is still "about half of mlx_lm" (`README.md:81`).
- **27B decode, by hardware (all single-stream):**
  - Mac (M3 Ultra, M5 Max): 64–77 tok/s on prose, 146–151 on greedy code, with DFlash2 trees.
  - RTX 4090: 64–86 tok/s (CUDA, Python, v0.6.0).
  - Radeon R9700, the community ROCm port (#100): about 96 tok/s on chat and 118–126 on code.
  - The community's native-HIP 27B on a W7800 (gfx1100, #490): only 25.8–27.2 tok/s plain and 45.8–53.4 with 3-bit MTP.
  - Our llama.cpp fork on a 7900 XTX is well ahead of all of these on chat.
- **What is new relative to Strata and our plan.** It is mostly negative results and data, not kernels:
  - Language-aware draft vocabulary: a CJK list took zh prose from 35.8 to 55.0 tok/s (#416).
  - A cost-model draft depth with robust self-timing: +6–7% on CUDA.
  - Persistent grid-barrier kernels lose to plain relaunches on M5 Ultra.
  - Adaptive "landed+1" depth loses to fixed depth.
  - Power-cap scaling data from an RTX 3090 (#592).
  - Two-queue staggered prefill: +5–8% TTFT, only at ≥4,096 rows per segment.

---

## 1. Anatomy of the history (the "rewrite" question)

| Fact | Evidence |
|---|---|
| One root commit, `094f5e4d` 2026-09-25 20:42 ("TensorFold: a CLI engine with an OpenAI-compatible endpoint", 79 files, +19,719 lines) | `git rev-list --max-parents=0 --all` |
| The repo is older than its root. Issues #1 and #2 are dated 2026-06-22 and 06-26 and concern a runtime with `--resident-budget` / `--loader-backend` that paged weights from disk | #1, #2. ashhart closed #2 with: "The runtime this was about … has been replaced" |
| v0.2.0 release notes: "This release is a rewrite. It replaces the earlier MoE runtime, and that runtime's flags, such as `--resident-budget`, are gone." | release v0.2.0 |
| ⇒ **Rewrite #1**: the June history was force-replaced by a fresh root on 09-25 [INFERENCE: force-push; the old commits are not reachable from any ref] | |
| Early releases are single squash commits: v0.3.0 `3283e59b` (+96,186 lines, PR #8), v0.3.4 `2f8e514b` (+37,099, PR #15). Each of v0.3.1–v0.3.4.1 is exactly 1 commit on top of the previous tag | `git show --shortstat` |
| Sebastian Christiansen (@CerebralCoding) wrote a Zig/Metal port on `feat/zig`: 91 commits, author-dated 09-27 → 09-30 (+0200). 48 of them carry the identical committer timestamp 09-29 21:02 (committer "ashhart"), i.e. a bulk rebase onto 0.4.0 `7a00336b` | `7089b7b9` "feat: add native Zig Metal inference backends", `c222e721` "migrate native Metal engine to mlx-serve Zig 0.17 nightly"; `bcf697e6` merges upstream into feat/zig on 09-30 |
| On 10-04 the Zig preview was published as one squash, `cd7ebe98` ("Zig engine preview: native Metal engine and server for Nemotron 3.5 Lightning", **552 files, +105,364 lines**), on top of 0.6.5 | `git show --stat cd7ebe98` |
| 26 minutes later, `f24b5c8f` "Keep the original Zig branch history in the preview, under its author" merges Sebastian's 91 commits as a second parent with **no tree change** (`git diff cd7ebe98 f24b5c8f` is empty) | commit message: "His 91 commits stay in this history under his name." |
| ⇒ **Rewrite #2 (cosmetic)**: these grafted commits are why commits with committer dates of 09-29/30 appear "below" a 10-04 preview. The real development happened on an unpublished branch: `febba15f` "docs: name no private branch in the five public pages"; `adding-a-zig-family.md:211` "These wins are on a branch we haven't pushed yet" | |
| 1.0.0 `8b003018` is a merge: first parent = the Zig line `19dd2f32`, second parent = the python-0.6 head `ed78d6fc`. That is why `rev-list --count` jumps from 360 (v0.6.6) to 779 (v1.0.0) | "The Python engine's history stays in main's history, and its code stays on the python-0.6 branch at 0.6.6." |
| The 27B native engine also landed as a squash: `34c44245` (10-09, 216 files, +20,320) | |
| One stray author date, 2026-09-01 (`1cb1d7e7`, Eduardo Dias, "configurable image history limits"). It is a contributor commit that kept its original author date (#170) | |
| Branches: `zig-preview` ends at v1.0.2 (`f8fe17d2`). `zig-flashnext` = main = HEAD. `python-0.6` = v0.6.6 + 12 Ampere/vision/copy-draft commits up to `ed78d6fc` (10-07). All three are ancestors of main | `git merge-base` |

---

## 2. Every tag

`+n` = commits since the previous tag. "Measured" lists numbers from the release notes or CHANGELOG with their hardware. Unless a cell names another format, the 4-number cells are code-sampled / chat-sampled / code-greedy / chat-greedy (64-token replies, `tools/bench_openai.py`).

| Tag (date, commit, +n) | Headline changes | Measured effect (hardware) | Author's stated reasoning / notes |
|---|---|---|---|
| **v0.2.0** (09-25, `50a58485`, +8) | Rewrite: `serve/pull/models/info`. Nemotron 3.5 Lightning, Qwen3.8-27B + DFlash2 and Flash Next on Apple Silicon, "drafts that never change the output" (`CHANGELOG.md:632-635`) | Nemotron 188–206 tok/s before MTP and 217 prose / 228 code with MTP (M5 Max). 27B 120–124 short, 189 code (M5 Max). Flash Next 88–92 / 110 (M3 Ultra) | Replaces the paged MoE runtime. 27B lane kernels need M5; on older chips a drafted reply could differ from serial (known limit) |
| **v0.3.0** (09-26, `3283e59b`, +5) | CUDA: DGX Spark, 1–2 ranks (`--tp 2`). GLM-5.3-Flash on two Sparks (`CHANGELOG.md:627-630`) | 27B + DFlash2 on 1 Spark: 49.6 / 45.8 / 49.2 / 45.9 vs vLLM MTP=3 17.7 / 15.0 / 17.7 / 17.0 (2.7–3.1x). 2 Sparks: 82.4 / 58.9 / 76.2 / 71.1 | Install inside NVIDIA's pytorch container |
| v0.3.1 (09-26, `d7470ed8`, +1) | `info`; refuse unsupported checkpoints before download | – | |
| v0.3.2 (09-26, `a83ed1ef`, +1) | GLM on EXL3 (experimental); `tensorfold update` | GLM EXL3: 36.4 / 29.7 / 43.8 / 32.9 vs vLLM 24.5 / 24.3 / 32.2 / 24.7 (2 Sparks) | The MLX checkpoint is still faster: 5.0 vs 10.7 GB read per token |
| v0.3.3 (09-26, `b08e0141`, +1) | 27B verifies windows on M1–M4 via a row-exact 4-bit matvec (`CHANGELOG.md:614`) | M3 Ultra serial 38.2–39.3 → drafted 47.0–64.4 | Before this, the drafter stopped after round 1 on non-M5 chips |
| v0.3.4 (09-26, `2f8e514b`, +1, **pre-release**) | Every model on the lane engine, serial engine removed; row-exact prefill; `simd_qmm` (8×8 tile dequant once, ≤16 rows); reduced draft vocab (Nemotron 32,768 ids, Flash Next 79,592); CUDA ≥2 rows per round (`:607-610`) | 27B M3 Ultra 141.3 / 73.9 / 158.4 / 74.2 (from 63.9 / 47.0 / 64.4 / 51.6). Nemotron M5 Max 288 / 222.9 / 291.8 / 242.6. 27B M5 Max verifies 16 rows ≈36 ms and 128 rows 145 ms. M3 Ultra 2–8 rows ≈32 ms vs 25 ms for 1 row | Floor goal: "every cell at least twice the standard". Next step stated as drafter training: 27B chat lands 3.5–3.95 tokens a round where DFlash2's own top candidates allow 5.6–6.1; Nemotron chain drafts 1–4 are right 74 / 48 / 31 / 16% |
| v0.3.4.1 (09-27, `bb4b4a35`, +1) | Prefill goes back through MLX's own forward on a fixed 2,048-token grid (`:601-602`) | Nemotron 8k ≈550 → 3,400 (M5 Max). 27B 2k 542 → 867, 32k 510 → 560, 64k 441 → 465 (M5 Max). Flash Next 2k 305 → 934 (M3 Ultra) | Row-exact prefill had made prompts "several times slower" |
| **v0.3.5** (09-27, `a3274f1d`, +10) | Concurrency (`--parallel auto`); resume at message starts; 70%-RAM cap; 2–8-bit lanes; CUDA FP8 prefill | 27B decode vs 0.3.4.1: M3 Ultra 1.17–1.20x; M5 ≈0.97 ("each round ~1.3 ms dearer"; a bounds check costing ~8% was removed); Spark 1.12–1.13x. CUDA prefill 2.5–3x (27B). 12-turn agent first-token time 31.9 → 14.9 s | |
| v0.3.5.1 (09-28, `beddbb7b`, +1) | M1/M2 per-kernel threadgroup limits | level, 0.99–1.02x | |
| v0.3.6 (09-28, `85653c77`, +25) | GLM-5.3-Flash and Gemma 4 on Macs; `--ple-on-ssd`, `--ssd-experts`; EXL3 on CUDA | 27B EXL3 on 1 Spark: 3.56 / 1.74 / 2.50 / 1.62x vLLM. Nemotron 8,192-row chunks on M5: +12–15% prefill | "3x decode floor" stated as the goal |
| v0.3.6.1 (09-28, `34bae79a`, +1) | CUDA builds inside NVIDIA containers | – | |
| v0.3.6.2 (09-28, `71377a53`, +32) | Ten community PRs: int8/int4 KV for Flash Next on CUDA, mixed-bit Qwen, 27B `--parallel 16` on CUDA, `--spill-gib` | oQ4 27B 114–120 code / 59–61 chat vs mlx_lm 34–36 (M3 Ultra). Spark 16 streams 161.7 tok/s | |
| v0.3.6.3 (09-29, `19118807`, +34) | Vision, DeepSeek-V4-Flash, Bonsai, NVFP4 on CUDA, `--decode-share` | 27B with images 77.6 vs 37.3 serial (M3 Ultra). Longest pause 164 → 7 s | Known: Nemotron −2% (later withdrawn, see §5) |
| v0.3.7 (09-29, `6b2e4c40`, +1) | Two concurrency fixes | – | "Versions have three parts from here on" |
| v0.4.0 (09-29, `7a00336b`, +3) | oQ / 8-bit at 4-bit speed on M1–M4; a stream reserves 2,048 tokens, not its whole reply | 27B oQ4e 8-row verify 40.8 → 31.9 ms (M3 Ultra). 64 GB Mac: 16 streams vs 4–9 | Corrects 0.3.6.3: the "2% slower" was ±2.5% start-to-start noise (`:448-449`) |
| v0.5.0 (09-29, `9cd52ab4`, +17) | Responses API; long context on Spark | 27B on Spark: decode 128k 18.4 → 38.9, 96k 23.6 → 45.9; prefill 128k 860 → 1,173, 255k 545 → 809 (`:379-382`) | Attention reads each key chunk once for all of a round's rows, with 16-byte loads |
| **v0.6.0** (09-30, `c4646171`, +43) | RTX 40; prompts fill inside decode rounds; **bf16 prompts by default**; Apache-2.0 | 27B on RTX 4090: prefill 2.4–2.6k tok/s (2k–32k), decode 64–86 tok/s, DFlash2. M5 Ultra oQ4e + DFlash2: 33 → 131–160 tok/s | bf16 vs FP8 prompt rows: KL 0.0031 vs 0.0624 against fp32 (`:338-339`). Accuracy chosen over speed |
| v0.6.1 (10-01, `17c73e18`, +54) | NVFP4 in its own math; waiting prompts fill together; projections sharing one input launch together | 27B on RTX PRO 6000 (250 W): 1.4–2.0x vLLM per stream. Verify step −4% (Spark), −7–15% (RTX PRO 6000). 8 streams 1.14–1.36x | |
| v0.6.2 (10-02, `56e2e3ec`, +12) | Flash Next at long context; GDN tree kernel | GDN tree −17–35% (RTX PRO 6000), −8–28% (Spark). 8 streams 1,196 → 1,232 tok/s | |
| v0.6.3 (10-02, `9356df5c`, +81) | Nemotron copy windows up to 64 rows (M5); Anthropic Messages API; Control Room | Nemotron code edits 550 → 760 tok/s (M5 Max) | Revert `a5f518b4`: an exact eviction policy failed the "no-slower gate" |
| v0.6.4 (10-03, `6ea5ade2`, +23) | Flash Next concurrent on 2 Sparks; one communicator interface; `tensorfold plan` | – | |
| v0.6.5 (10-03, `609ca419`, +2) | Qwen3.6 MTP on Macs; **Nemotron CUDA draft depth by measured cost, up to 15 levels**; API keys (`:215-219`) | +6% (1 and 2 Sparks), +7% (RTX PRO 6000) vs 0.6.4. Qwen3.6 1.46–2.05x over no-drafts (M3 Ultra) | The Python engine is "frozen at 0.6.5" (`adding-a-zig-family.md:13`) |
| v0.6.6 (10-06, `cb2ebf05`, +3) | `--name-priority` (CUDA) | Foreground TTFT 21 → 0.2 s behind 4 background requests (Spark) | Last Python release. Its entry exists only on `python-0.6:CHANGELOG.md:6`; main's CHANGELOG jumps from 1.0.0 to 0.6.5 |
| **v1.0.0** (10-07, `8b003018`, +419) | The native Zig server becomes main. Qualified: Nemotron (Metal M1–M5, GB10), Flash Next (M5 Ultra), GLM-5.3-Flash (two M5 Ultras), Qwen3.5-2B; compaction (`:193-204`) | Nemotron 8 streams 436.7 vs 262.8 for one (M5 Max). GB10 decode 1.01–1.10x Python 0.6.6 | 27B excluded: "slower than Python 0.6.6". Bonsai, Gemma 4, Qwen3.6, DeepSeek-V4 dropped to "ports for 1.0.x" |
| v1.0.1 (10-07, `041d14a9`, +1) | `pull/models/info` in the shipped binary | – | Released 8 minutes after 1.0.0 |
| v1.0.2 (10-07, `f8fe17d2`, +11) | GLM-5.3-Flash two-Mac TP (heads, dense, vocab), concurrency, prompt cache, `--learn` (`:183-187`) | 8 streams 100 → 199 tok/s. Plain 83 → 91; drafted 114–148. 7.3k TTFT 6.5 → 4.4 s | |
| **v1.0.3** (10-10, `24b009ff`, +105) | **27B native** (`34c44245`); Sliding Weights; Ampere sm_86; GB10 kernels all its own (no captured Triton); robust draft timing (`:150-179`) | 27B M5 Max: 64–77 prose / 151 code (512-token replies), plain 18–19.5. 27B prefill 252 vs mlx_lm 441 at 8k, 184 vs 404 at 30k (M3 Ultra). RTX 3090 Nemotron: 252 / 313 drafted, 194 plain, prefill ≈4,800 at 2k | Draft timing: fastest of 7, outliers re-timed. "One RTX 3090 start had recorded 0.61 ms for a step that measures 0.34" (`:159`) |
| v1.0.4 (10-10, `d4fc1964`, +4) | `--slide` refuses linked folders | – | Data-safety hotfix 40 min after 1.0.3: learning rewrote the HF-cache originals |
| v1.0.5 (10-10, `bec00ae6`, +191) | Nemotron prompt states (Metal and CUDA); states before the latest user message (edit/regenerate); GLM on one Mac; GLM tensor-unit prompts; opt-in HIP runtime (`:86-143`) | 27B 9k-chat edit / regenerate: 10.9 → 1.7 s (M3 Ultra). GLM prefill 1,417–1,803 → 2,079–2,513 (two M5 Ultras). 64 sessions 376 → 409 (M3 Ultra) | Known: GLM prose −4%; 27B sampled requests not drafted (≈19 tok/s) |
| v1.0.6 (10-11, `c080a18e`, +131) | Structured output; **27B concurrency + sampled drafting** (#578); sm_120 fatbins; NVFP4 Nemotron; Living Weights on GB10 (`:63-84`) | 27B sampled: 19–21 → 47–191 (M3 Ultra: code 125, prose 51). 8 streams 1.6–1.8x (124 vs 73). RTX PRO 6000 Nemotron 874 code | Known: 27B greedy code −4.5% on M3 Ultra (138–140 vs 146) |
| v1.0.7 (10-11, `e7c523eb`, +94) | Living Weights "pocket neurons"; 4x faster learning; 27B lone requests back to DFlash2 trees (`:56-61`) | 27B M3 Ultra greedy code: 146 vs 138 (CHANGELOG `:61`), or 150.7 vs 1.0.5's 150.6 (release page) | Known: a promised LRU slot pick for GLM did not ship |
| **v1.0.8** (10-12, `0efbd447`, +244) | GLM-5.3 744B from EXLR8 on two Macs; 27B keeps weights once; Nemotron states at any row; CUDA logprobs; Living Weights learns more; refuses flags it used to ignore silently (`:5-54`) | GLM-5.3: 21 plain / 31–32 drafted, prefill ≈200 (two M5 Ultras). 27B memory 44.2 → 26.5 GiB (M5 Max), same speed. Grammar windows in graphs +4.4% (GB10) | |

---

## 3. Phases and turning points

| Phase | Dates | What happened | Evidence |
|---|---|---|---|
| P0, pre-history | June → 09-24 | Disk-paging MoE runtime (`--resident-budget`); erased | #1, #2 |
| P1, exact Python lanes | 09-25 → 09-27 (0.2.0–0.3.4.1) | MLX engine plus its own Metal kernels (`mx.fast.metal_kernel` in 26 files at v0.6.6) and torch/Triton/.cu on CUDA (Triton imported in 38 files, torch in 107). The contract: drafted == serial byte for byte. Lanes on every chip (0.3.3/0.3.4) and CUDA on Spark (0.3.0) | `git grep` at v0.6.6; releases |
| P2, breadth | 09-27 → 10-03 (0.3.5–0.6.5) | Concurrency; 6 new families (GLM, Gemma 4, DeepSeek-V4, Bonsai, Qwen3.6, Kimi research); formats (EXL3, NVFP4, oQ, GGUF via #144); consumer CUDA (RTX 40/50, PRO 6000); API parity; a flood of community PRs. Python code grew from 0.9 MB (v0.2.0) to 6.9 MB (v0.6.6) | `git ls-tree -l` |
| P2′, Zig port in parallel | 09-27 → 09-30 | Sebastian's `feat/zig`, based on **mlx-serve**'s Zig (`c222e721`), with an `AGENTS.md` for coding agents (`4ee9f03b`) | §1 |
| P3, private Zig sprint → preview | 10-03 → 10-06 | Nemotron on Zig, Kimi K3 on four M3 Ultras, the Flash Next "replay" engine, **speed-up mode over MCDMA** (`78165b08` 10-05 23:18 → `8ee01bab`, `a3c29c6f`), CUDA Zig replaying Triton kernels captured from Python | `adding-a-zig-family.md:7-10, 117-124, 211-212` |
| P4, cutover | 10-07 (1.0.0) | Zig becomes main; the Python line freezes; 27B and 5 families are dropped from the qualified set | `RELEASE-NOTES-1.0.0.md` |
| P5, native breadth | 10-07 → 10-12 (1.0.1–1.0.8) | GLM TP on two Macs (1.0.2); 27B native (1.0.3); Ampere (1.0.3), sm_120 (1.0.6); Living Weights (1.0.3 → 1.0.7 redesign); prompt-state engineering (1.0.5–1.0.8); HIP runtime slices from the community (1.0.5–1.0.8, no model on HIP yet); EXLR8 GLM-5.3 (1.0.8). Zig source 4.6 MB (v1.0.0) → 8.2 MB (v1.0.8) in 5 days | |

**Why Python/MLX was abandoned (the author's own statements):**
- "no Python or MLX in the decode path" (`ZIG-PREVIEW.md:3`).
- Measured gains (`adding-a-zig-family.md:7-10`):
  - Nemotron prose: 220 → 272–277 tok/s (M5 Max).
  - Flash Next: 117–120 → 134–160 decode, and 2,000–2,500 → 4,000–4,200 prefill (M5 Ultra).
  - Kimi K3: 2.7 → 11.6 tok/s.

**Supporting pain points in the Python era:**
- MLX versions kept breaking exactness:
  - v0.2.0: MLX 0.32.2 failed Nemotron's row check.
  - v0.3.6.3: MLX 0.32.3 changed a kernel (#88).
  - v0.3.4: "every verify matmul is now TensorFold's own, so exactness no longer depends on the MLX version".
- Per-round host cost: 0.3.5's 27B round was "~1.3 ms dearer" in the new Python path.
- #100 removed "about 200 kernel launches and 3 host syncs from every drafted round".
- [INFERENCE] The ordered list of Zig wins is mostly host-side: one command buffer per round, GPU-side accept, two rounds in flight. That is exactly what Python and MLX made hard.

**Notable turning-point commits (Zig, 10-05):**
- `c6d5fd35` One command buffer a round: Flash Next 117.8 → 123.2 tok/s at depth 3; GPU busy 94–95%.
- `3673a760` Lane matmuls sum their own groups on a serial encoder. Removed 99 launches a step: → 128.9.
- `4495f918` GPU-side rounds: an accept kernel on the GPU, a ring readback, the host encoding round N+1 while round N runs: 142.4 → 144.8; GPU busy 97%.
- `1fbd9ba7` Persistent dispatch with a GPU-wide atomic barrier: 4.6–18 µs per phase, against 4.01 µs per dependent relaunch (M5 Ultra). Conclusion: "a layer megakernel built on grid barriers would not cut the launch floor".
- `11ecb46b` Adaptive depth (landed+1 or +2, over depths 1–6): 137.6–139.9 tok/s vs 143.1 at a fixed depth of 3.
- `c2bede8f` Two staggered prompt segments on two Metal queues from 8,192 tokens: prefill +8%, same bits.

---

## 4. Model trajectories

### 4.1 Qwen3.8-27B (MLX 4-bit + z-lab DFlash2; our model)

| Version / engine | Hardware | Decode | Prefill | Acceptance / round cost | Source |
|---|---|---|---|---|---|
| 0.2.0 Python | M5 Max | 120–124 short, 189 code | – | – | release v0.2.0 |
| 0.3.0 Python/CUDA | 1 Spark; 2 Sparks | 45.8–49.6; 58.9–82.4 | – | – | release v0.3.0 |
| 0.3.3 | M3 Ultra | serial 38.2–39.3 → 47.0–64.4 | – | – | release v0.3.3 |
| 0.3.4 | M3 Ultra; M5 Max | 141.3 / 73.9 / 158.4 / 74.2; 153.2 / 69.8 / 154.2 / 72.8 | 0.3.4.1 (M5 Max): 867 @2k, 560 @32k, 465 @64k | Chat 3.5–3.95 tokens a round vs 5.6–6.1 possible. M5 Max: 16 rows ≈36 ms, 128 rows 145 ms | release v0.3.4 / 0.3.4.1 |
| 0.3.5 | M3 Ultra / M5 / Spark | ×1.17–1.20 / ×0.97 / ×1.12–1.13 | CUDA ×2.5–3 | M5 round +1.3 ms | release v0.3.5 |
| 0.3.6.2 oQ4 | M3 Ultra | 114–120 code, 59–61 chat | – | – | `:525-527` |
| 0.4.0 oQ4e | M3 Ultra | sampled code +14%, chat +5–7% | – | 8-row verify 40.8 → 31.9 ms | `:401-406` |
| 0.5.0 CUDA | 1 Spark | 128k: 18.4 → 38.9; 96k: 23.6 → 45.9 | 128k 860 → 1,173; 255k 545 → 809 | – | `:379-382` |
| 0.6.0 CUDA | RTX 4090 | 64–86 | 2.4–2.6k (2k–32k) [INFERENCE: measured near the FP8→bf16 switch; precision path not stated] | – | `:326-329` |
| 0.6.0 | M5 Ultra, oQ4e | 33 → 131–160 | – | – | `:348` |
| Python recipe (Spark) | GB10 | MLX 4-bit 50.0–57.8; EXL3 3.0 bpw 39.9–83.4 | MLX FP8 prompts 1,834 @2k … 1,240 @64k; EXL3 880–970 | Tokens a round 4.0–5.2 (MLX); EXL3 chat 3.0–3.3 vs 4.2. 12-row round 84 ms MLX (14.4 GB/token), 75 ms EXL3 (10.1 GB) | `docs/recipes/qwen3.8-27b.md:87-131` |
| #100 Python ROCm (community) | R9700 gfx1201, 640 GB/s | 117.9–126.1 code, 95.7–96.8 chat; plain 33.9–34.2 | 1,834 @2k, 2,121 @8k (FP8 WMMA GEMM 150–158 TFLOPS) | Code: 12 verify rows, 6.4 tokens a round, 37 ms, of which 29 ms matmuls at ≈80% of 639 GB/s | #100 |
| 1.0.0 native | – | **excluded: slower than Python 0.6.6** | – | – | `:203` |
| 1.0.3 native | M5 Max / M3 Ultra | 64–77 prose, 151 code; plain 18–19.5 | 470–515 (7k, M5 Max); 252 @8k vs mlx_lm 441, 184 @30k vs 404 (M3 Ultra) | – | `:152-154` |
| 1.0.5 | M5 Max / M3 Ultra | sampled requests not drafted: ≈19 | edit / regenerate 10.9 → 1.7 s | – | `:118, 142` |
| 1.0.6 | M3 Ultra / M5 Max | sampled 47–191 (code 125, prose 51); 8 streams 1.6–1.8x | – | M3 Ultra greedy code −4.5% (copies land less often than trees) | `:65`, release v1.0.6 |
| 1.0.7 | M3 Ultra | 146–150.7 greedy code (back to 1.0.5) | – | – | `:61` |
| 1.0.8 | M3 Ultra / M5 Max | 150.6 vs 144.0 after sampled requests; memory −17.6 GiB | – | Draft landing counts persist for the server's life: after 4 prose replies, greedy code runs 141.7–146.4 | `:9, :29`, release v1.0.8 |
| #490 native HIP (community, open) | W7800 gfx1100, 48 GB | 4-bit 25.8 / 27.2; 3-bit + MTP 53.4 / 45.8 | 629–648 @2k, 431 @64k | Matrix cores off: prefill 629 → 394 | #490 |

**Reading this against our numbers.** We do 88–90 t/s on short chat and 660–910 t/s prefill on a 7900 XTX.
- TensorFold's best chat-prose 27B number on any single device is 64–96 tok/s (M5 Max, Python R9700). Its strength is greedy code with DFlash2 trees: 146–189 on Macs, 126 on R9700.
- Their stated DFlash2 acceptance ceiling (3.5–3.95 tokens a round on chat; 4.0–5.2 on Spark cells) is in line with our observation that DFlash2 ≈ MTP on mixed English. We see 3.16 tokens a step with MTP n=4.
- The native-HIP gfx1100 port is about 3x behind our fork on plain decode [INFERENCE: different quantization, and a 864 GB/s W7800].

### 4.2 Nemotron 3.5 Lightning 30B-A3B (hybrid Mamba MoE + MTP)

| Version | Hardware | Decode | Prefill | Acceptance / notes | Source |
|---|---|---|---|---|---|
| 0.2.0 Python | M5 Max | 188–206 (before MTP); 217 prose / 228 code (MTP) | – | – | release v0.2.0 |
| 0.3.4 | M5 Max / M3 Ultra | 288 / 222.9 / 291.8 / 242.6; 295.1 / 277.0 / 332.8 / 278.5 | 0.3.4.1: 3,400 @8k, 2,456 @32k (M5 Max) | Chain drafts 1–4 right 74 / 48 / 31 / 16% (chat); 32k-id draft vocab | release v0.3.4 / 0.3.4.1 |
| 0.3.5.1 | M5 Pro 64 GB | 123.3–146.0 MTP; 107.8–109.5 plain | 261,780 tokens in 311.5 s | – | `docs/recipes/nemotron-3.5.md:155-161` |
| 0.3.6 | M5 | – | +12–15% (8,192-row chunks) | – | `:566-567` |
| 0.6.3 | M5 Max | Code edits 550 → 760 (up to 1,000 cool) | – | 64-row copy windows; Mamba state kept every 8th row | `:258-261` |
| 0.6.5 | Spark / RTX PRO 6000 | +6% / +7% | – | Depth up to 15 levels by measured cost | `:215-219` |
| Zig preview | M5 Max | 277 essay, 357 code, 459 edit, 581 rename (Python ≈220, mlx_lm ≈175) | – | 64 sessions: Zig 502 vs Python 607 (fixed later: 128 rows) | `ZIG-PREVIEW.md` |
| 1.0.0 | M5 Max | 8 streams 436.7 vs 262.8 single | – | GB10 1.01–1.10x Python | release v1.0.0 |
| 1.0.3 | RTX 3090 | 252 prose / 313 code drafted; 194 plain (1.44–1.69x llama.cpp's "faster mode") | ≈4,800 @2k, 4,200 @16k | GB10 kernels replace captured Triton | `:157-158` |
| 1.0.4 receipt (#592) | RTX 3090, 225 W / 350 W | 316.7 / 372.5 prose, 543.2 / 644.2 code (T=0) | 6,110 / 7,314 @2k; 3,061 / 3,673 @131k | Decode at 131k: 167 / 215 | #592 |
| 1.0.5 | M3 Ultra | 64 sessions 376 → 409 | 2nd turn of a 19.8k chat 8.1 → 0.16 s | `tf_experts_w`: 3 member rows a pass | `:107-110` |
| 1.0.6 | RTX PRO 6000; GB10 NVFP4 | 874 code, 510–607 prose; NVFP4 105–174 drafted vs MLX 133–189 (serial 77–79 vs 98–101) | NVFP4 6,090–7,270 (2k–32k) | NVFP4 reads 1.3x the bytes a token | `:72, :83` |
| 1.0.8 | M3 Ultra / M5 Max / GB10 | grammar graphs +4.4% (draft off) | +0.9–1.2% / +2–5% | Living Weights cost: 248 → 213 tok/s after 10 facts (M5 Ultra) | `:40, :49`, release v1.0.8 |

---

## 5. Reversals, regressions and withdrawn features

| What | When | Why | Evidence |
|---|---|---|---|
| Row-exact prefill (decode kernels for prompts) | added 0.3.4, reverted 0.3.4.1 | 5–6x slower prompts. Exactness was kept instead by prefilling through MLX on a fixed 2,048 grid; message-start resume returned in 0.3.5 | release v0.3.4.1 |
| `--prefill-grid` | 0.3.4.1 → removed 0.3.5 | Replaced by chunking at message starts. Cost: +7.8% cold prefill on a 40-message 18.7k session (27B) | release v0.3.5 |
| "Nemotron −2%" known issue | 0.3.6.3 → withdrawn 0.4.0 | Run-to-run spread ±2.5% between server starts | `:448-449` |
| One shared draft slot | 0.3.6.3 → fixed 0.3.7 | 5 of 6 concurrent Nemotron requests failed with HTTP 500 | `:453-455` |
| FP8 prompt default on CUDA | 0.3.5 → bf16 default in 0.6.0 | KL 0.0624 vs 0.0031. FP8 kept as `--prefill-fp8`; bf16 is 0.73–0.82x its speed (`qwen3.8-27b.md:59`) | `:338-339` |
| Exact prefix-cache eviction policy (CUDA) | merged then reverted for 0.6.3 (`a5f518b4`) | Exact, but failed the paired "no-slower gate" at both lengths | commit |
| Python engine as a whole | frozen 0.6.5/0.6.6 | Superseded by Zig. 27B, Bonsai, Gemma 4, Qwen3.6, DeepSeek-V4 and EXL3/NVFP4 on CUDA stayed on Python. 1.0.5 points users to the "Python 0.6.6 install line" | `RELEASE-NOTES-1.0.0.md` |
| 27B on 1.0.0 | excluded | Native decode / prefill slower than 0.6.6 | `:203` |
| CUDA `top_k` default 20 (#542) | taken back in 1.0.5 (#515) | One default everywhere | `:89` |
| Speed-up guide's dump-free claim | 1.0.5 | The two-Mac numbers came from a build with a recorded dump; the release binary had not passed that gate | `:99` |
| GLM prose drafting −4% | 1.0.5 → fixed 1.0.6 | Draft-window prices came from a fixed table; load-time timing fixed it (114.8 vs 110.6) | `:79, :141` |
| 27B greedy code −4.5% (M1–M4) | 1.0.6 → 1.0.7 → 1.0.8 | #578's shared rounds gave every stream copy drafts, which land less often than DFlash2 trees. Then sampled rounds polluted the round-cost table. Then landing counts persist for the server's life (still a known issue at 1.0.8) | `:61, :29`; release v1.0.8 known issues |
| Promised GLM LRU slot pick | promised in 1.0.6 notes, not in 1.0.7, shipped in 1.0.8 | – | release v1.0.7 known issues; `:12` |
| Sliding Weights v1 (deltas to output projections in bf16) | 1.0.3 → replaced by pocket neurons in 1.0.7 | v1 folders refused with `--slide`. Builds of main earlier on 10-11 "could learn the fact finder's own example facts" | `:155`, release v1.0.7 |
| Living Weights thinking-recall change | reverted `b72b8c3c` (10-11) | – | commit |
| Flags accepted silently and ignored | fixed 1.0.8 | `--learn` on CUDA / 27B / 2B and `--slide` on non-Nemotron "took the flags and learned nothing" | `:21-22, :54` |
| `FZ_LANE=1 FZ_GDN=2` in the speed-up guide | removed 1.0.8 | Decoded 2–5% slower | release v1.0.8 |
| Release notes vs CHANGELOG drift | 1.0.6 / 1.0.7 | The 27B figures differ between the release page and the later-edited CHANGELOG (`27e270dd`), e.g. 150.7 vs 150.6 against 146 vs 138 | – |

**Negative results ("Don't bother", `adding-a-zig-family.md:264-299`)** that matter for decisions:
- Persistent kernel with a GPU-wide barrier.
- Grouped experts (one read per expert across lanes).
- Split command buffers.
- Dense matvec for the target ("wins one row, loses wide windows").
- DeltaNet step / hyper-connection tensor-op kernels at 2–7 rows.
- 128-row prompt tiles.
- Adaptive depth by landed+1; full-vocabulary drafts.
- Drafter-less lanes: Jacobi landed 1.1–1.3 of 32; recycled lanes 0.59 a round vs MTP's 3.01; a phrase store added 2–15%; logit-lens top-64 hit ≤6%.

---

## 6. Cadence and working pattern

**Volume**
- 1,560 commits in 18 days (≈87 a day).
- Busiest committer-date days: 10-10 = 298, 10-11 = 285, 10-07 = 167, 10-06 = 147.
- Quietest: 10-03 to 10-04 (12 and 3), the private Zig sprint before the squash publish.

**Authors**
- ashhart: 1,088 commits (+9 as "Ash"), 70%.
- Sebastian Christiansen: 93.
- BobClawblaw: 40; Jürgen Schmied: 32; then a long tail (`git log --format=%an`).
- Committer: ashhart on 1,420 of 1,560 (91%).
- 174 merge commits.

**Issues and PRs**
- 552 PRs. Only 97 show "MERGED", 351 "CLOSED", 104 open. Most closed PRs landed by maintainer port.
- 235 issues.
- Busiest PR days: 10-04 = 60, 10-10 = 58, 10-11 = 56.

**Integration style**
- CONTRIBUTING: "We review a candidate, preserve its authorship and run the release gates before landing it" (`CONTRIBUTING.md:90`).
- PRs are rebased onto a release "candidate" branch, e.g. `0570b7e3` "Merge #643 … into the 1.0.8 candidate".
- The PR's own head commit is then recorded with a tree-neutral merge so GitHub sees it. 20 such commits, e.g. `58bd07ef` "Merge #681's head (484508f94): the same change", whose body reads: "#681 landed above as 841cdbbd3 (the author's commit, rebased onto this candidate). This keeps the PR's own head commit in the history, with no change to the tree."
- Side effect: duplicate commits with identical subjects (`126ee705` / `18592769`, `0a4d585d` / `650a714d`, `281a7f0c` / `009fef3f` for #578).
- Before 10-07 GitHub-style "Merge pull request #N" was used (7 times). 81 "Merge #N…" merges in total.

**Release gating**
- Every note carries receipts: hardware, paired before/after, alternated runs, and token-hash equality (`CONTRIBUTING.md:48-75`).
- "Known issues" sections with numbers. Public corrections of earlier notes (0.4.0 retracting 0.3.6.3).
- Hard house rules (`ZIG-PREVIEW.md` "House rules"; `CONTRIBUTING.md:79`):
  - drafted == plain;
  - bf16 activations with fp32 accumulation, "no precision trades";
  - files ≤600 lines and one-line comments, enforced by `tools/zig/lean_check.py`.

**AI-agent signs**
- Day-1 commit `5011b1d7` "docs: add AI agent setup runbook" (RUNBOOK "for setting up with an AI agent", release v0.2.0).
- Sebastian's `AGENTS.md` / `native/AGENTS.md` (`4ee9f03b`) is an explicit coding-agent brief: "Give concise findings in the conversation … without adding investigation diaries".
- `CONTRIBUTING.md:95`: "tool co-author trailers do not belong in the history". This explains why no Claude/Codex trailers appear: they are stripped by policy.
- `packaging/omp/sliding-weights.ts` is an extension for the **omp** agent harness (the `/learn` command, `:155`).
- Timing: 201 of 744 consecutive ashhart first-parent commits are less than 1 minute apart. Activity runs around the clock, with a peak of 96 commits in the 01:00 hour and 59–63 in the 02:00 and 03:00 hours.
- Series of "tried (exact, slower)" experiment commits 4–10 minutes apart (10-05 09:02–12:43).
- A uniform prose style everywhere: full-sentence subjects, numbers in every message.
- [INFERENCE] Several contributor handles end in "Claw" (BobClawblaw, EugeneClaw, liumorrisclaw), suggesting agent-operated accounts. This is by name only and unverified.
- The pattern closely mirrors Strata: maintainer ports of PRs, exactness gates, ≈1.5–1.9k commits in about 19 days. See `strata/README.md:3`.

---

## 7. Non-speed features

- **Living Weights / `--slide`**:
  - The server learns user facts into the checkpoint itself.
  - In 1.0.3 these were bf16 deltas to output projections.
  - From 1.0.7, they are about 10 new "pocket" neurons per fact in each MoE shared expert (64 per layer); any MLX loader reads the result as a slightly wider model.
  - A fact takes 1.5–3 minutes to learn. It is kept only if held-out wordings recall it and nothing else moves (`:58-59, :42-48`).
  - Nemotron only. It costs decode: 248 → 213 tok/s after 10 facts (M5 Ultra).
- **Context compaction** (`--compact-at/--compact-keep/--compact-memory`, 1.0.0):
  - Instead of refusing an overflowing conversation, the server keeps the system prompt and recent turns verbatim and folds older turns into a structured memory note, updated incrementally.
  - It is deterministic (`README.md:109-117`).
- **`--learn` prefixes** (1.0.2):
  - Shared prefixes (system prompt + tools) are persisted to disk, keyed by checkpoint, kernel sources, chip, OS and a startup probe's bits.
  - A restart or an upgrade that computes the same bits resumes them: 4.43 → 0.64 s TTFT (GLM).
  - Crash-safe index; disk floor `--learn-min-free-gib` (1.0.5).
- **Speed-up mode** (`--speed-up`, 10-05/06):
  - One model on two Macs over Thunderbolt (MCDMA RDMA).
  - Prompt rows are split between the Macs; decode splits DeltaNet heads, experts by rows, and the vocabulary head.
  - Prefill 1.7–1.8x; decode 1.2–1.3x (Flash Next, two M5 Ultras, `docs/recipes/speed-up-mode.md:17-31`).
  - Needs MCDMA QoS threads to hold speed under CPU load: 104.5 vs 64.5 tok/s (1.0.8).
- **EXLR8** (1.0.8):
  - kindlingai's trellis format with per-expert widths K2/K3/K4 picked by a profile.
  - Per-node ranged pull; GLM-5.3 744B over two 256 GB M5 Ultras at 21 / 31–32 tok/s.
- **Others**: structured output via xgrammar with drafts kept (1.0.6); logprobs and `prompt_logprobs` (CUDA, 1.0.5/1.0.8); Anthropic and Responses APIs; `/v1/decisions`; API keys; Homebrew binary.

---

## 8. What is new for us (vs Strata and our K1–K5 / S1–S4 plan)

Arithmetic from the brief: step 35.7 ms, 3.16 tokens a step, so 1 ms a step ≈ +2.9% t/s.

**N1. Audit the draft vocabulary's coverage per language (new data point).**
- *Mechanism.* #416 measured how much text a reduced draft vocabulary covers. Flash Next's 79,591-id list (ranked over Python sources) covered only **33–43% of Chinese token occurrences**, and a token outside the list "cannot be drafted at all".
- *Measured* (GB10, accepted drafts a round): zh prose went from 0.21 to 0.65, and from 35.8 to 55.0 tok/s (+54%). zh chat 38.0 → 58.0.
- *Cost.* The CJK list has 135,040 ids, so the head reads ≈1.7x the rows. English cells lost −2 to −6% single-stream.
- *Relevance to us.*
  - Our `--spec-draft-vocab` 64k list is already ranked over a mixed EN/PL/code corpus plus model generations (`qwen-opt/build_draft_vocab.py:1-6`). The failure mode is probably already mitigated.
  - Our own data agree that coverage matters: a 16k list lost 5%, 64k gained 7.5% (`NOTES.md:101-103`).
- *Action.* Compute the fraction of PL token occurrences inside the top-64k on a held-out Polish text. This is a CPU-only script.
  - If coverage is below about 97%, append the missing PL-diacritic tokens, as `draft_vocab_extend.py --script` does. Adding 16k rows to a 64k head costs ≈+25% of head reads, ≈0.3 ms a step ≈ −0.9% [INFERENCE].
  - The gain only shows up if PL misses are real.
- *Effort:* hours. *Risk:* low. Overlaps S2 / B2 (MTP self-distillation): fix coverage before training.

**N2. Price draft depth with a cost model, timed robustly at startup.**
- *Mechanism.* Time every window width at startup. Keep the fastest of 7 runs, re-time outliers, and sample the draft step between widths. Cache the table per build, chip and model. A chain stops when the next verify row would cost more than its expected saving, using per-level confidence.
- *Measured.*
  - Nemotron CUDA, up to 15 levels: +6% (Spark), +7% (RTX PRO 6000) (`:215-219`).
  - Timing noise: one RTX 3090 start recorded 0.61 ms for a 0.34 ms step (`:159`).
  - Negative: landed+1 adaptive depth lost 2–4% to a fixed depth (`11ecb46b`), and our own p_min 0.5 sweep lost at T=1 (`NOTES.md:145-160`).
- *Relevance.* Applies to our MTP chain once K4 / B1 gives cheap widths of 9–16. Each extra row costs ≈1.4 ms (B1 hypothesis) plus one MTP draft step. A token is worth 35.7 / 3.16 ≈ 11.3 ms, so drafting depth k pays only while P(chain reaches k) is above roughly 0.15–0.2 [INFERENCE].
- *Expected gain:* 0 to +4% on chat; more on code once widths >9 exist [INFERENCE].
- *Where in llama.cpp:* our server MTP draft loop / `common/speculative.cpp` stop rule. With HIP having no conditional graph nodes, this needs one graph per chain length (ties to B3).
- *Effort:* medium. *Risk:* low (lossless). Overlaps K4, B1, B3.

**N3. Counter-evidence for persistent megakernels.**
- On M5 Ultra a GPU-wide barrier costs 4.6–18 µs a phase, vs 4.01 µs for a dependent relaunch (`1fbd9ba7`).
- On HIP our boundary cost (3.2–3.4 µs) comes from the AQL barrier bit plus cache invalidate (roadmap §0). A persistent kernel avoids AQL packets entirely, so the trade-off may differ on RDNA3 [INFERENCE]. Strata's open #2226 tries exactly that on gfx1030.
- *Takeaway for K2:* keep "fewer kernels by fusion" as the main route, and treat a persistent kernel only as a measured micro-bench first. Copy TF's 600-phase bench design.

**N4. Host/round pipelining numbers (cross-reference: the spec-host slice).**
- One command buffer a round: +4.5%. Removing 99 launches a step: +4.6%. GPU-side accept with two rounds in flight: +1.7%, GPU busy 97% (Flash Next, M5 Ultra).
- Our step has ≈4.7 ms outside the verify. Overlaps K3 and B3; no new mechanism beyond what the spec-host slice covers.

**N5. Two-queue staggered prefill.**
- *Mechanism.* One segment's scan and glue run beside the other's matmuls, ordered with MTLFence / MTLEvent.
- *Measured.* TTFT −5 to −8% from 8k (Flash Next). It loses below 4,096 rows per segment (2k: −7%) because each segment re-reads the weights.
- *Relevance to us.* Our prefill is 90% MMQ (roadmap §0); GDN + FA + small ops are about 10% of a 512-token ubatch. The best case is roughly +3–5% at long prompts [INFERENCE], and ggml has no multi-stream graph execution.
- *Effort:* high. Low priority; overlaps K5.

**N6. Power-cap scaling from a third party (#592, RTX 3090, Nemotron).**
- 225 W vs 350 W: decode −15% (prose 372.5 → 316.7, code 644.2 → 543.2); prefill −16 to −17% (7,314 → 6,110 at 2k).
- This is context for A11 / B7 only: a bandwidth-bound decode still lost about 15% at 64% power on GDDR6X [INFERENCE: transfer to our 285 W cap is qualitative].

**N7. Methodology to copy.**
- Paired, alternated A/Bs on one box: "Two GB10s ran identical code 4–6% apart" (`adding-a-zig-family.md:250`).
- ±2.5% start-to-start spread even at a fixed depth (0.4.0).
- "Never quote a speed before checking that run's tokens. A Nemotron build once looked 25% faster because a bug gave wrong tokens that were easier to draft" (`adding-a-zig-family.md:319-320`). Relevant to every K1/K2 fusion A/B: run `greedy_check.sh` in the same run.

**Not new / already covered:**
- Prompt states before the latest user message (1.0.5, #571): llama-server already checkpoints at the last user message (roadmap A1).
- Reduced draft vocabulary itself (Strata, and ours).
- GDN rollback (S4; Strata).
- TensorFold's HIP track (#490, #607, #609, #611, #630) is slower than our fork on gfx1100 and contributes no kernel idea beyond Strata's.
- R9700 #100 relies on FP8 WMMA, which RDNA4 has and RDNA3 lacks.
