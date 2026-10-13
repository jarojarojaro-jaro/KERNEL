# TensorFold: speculative decoding, round scheduling and host mechanics (spec/host slice)

Repo `~/research/TensorFold` at HEAD `0efbd447` (v1.0.8, 2026-10-12). Paths are relative to the repo root and refer to HEAD unless a ref is named. `@py` means `origin/python-0.6` (the old Python/MLX/PyTorch 0.x engine). `#N` means https://github.com/ashhart/TensorFold/issues/N (PRs use the same numbering). "Ours" means 1× RX 7900 XTX, llama.cpp HIP fork, Qwen3.8-27B Q4, MTP n=4, 35.7 ms/step, 3.16 tok/step, 88-90 t/s. Arithmetic rule: **1 ms/step ≈ +2.9 % t/s**. `[INFERENCE]` marks my own reasoning.

**What TensorFold is, in this slice.** One rule governs every engine: a drafted reply must equal the `"draft": false` reply byte for byte (ZIG-PREVIEW.md:5). To make that hold, every kernel gives a row the same bits at any row count ("row-invariant"), and load-time checks turn drafting off if they do not (`50a58485@py`). Drafters by family:
- Nemotron 3.5 Lightning: its own MTP head, 4-bit, with a 32,768-id draft vocabulary.
- Qwen3.8-27B: DFlash2 only, as **trees**. The 27B's own MTP head was tried in closed PR #266, measured "~29 % first-draft acceptance" on MLX, and was dropped.
- Flash Next: MTP chains plus copy windows.

---

## 1. Measured numbers that anchor everything (closest analogs to us)

| What | Hardware | Number | Source |
|---|---|---|---|
| Nemotron MTP, one round | RTX 3090 | ~7.1 ms verify + 1.0 ms MTP drafts + **~0.3 ms host**; prose 1.94-2.75 tok/round at 7.5-8.8 ms/round (257-311 tok/s vs 185-196 plain); code 4.00 tok/round, 412 tok/s | `3cda8800` |
| Nemotron verify window cost | RTX 3090 | graphs 5.52 / 5.45 / 6.61 / 11.52 ms at 1/2/4/16 rows; eager 1 row 5.81 ms, "so node gaps are not the cost". Cost tables: 4.19 → 10.96 ms (1 → 16 rows); one MTP level 0.342 ms | `3cda8800`, `3e92032f` |
| Nemotron MTP chain acceptance P(≥1..4) | RTX 3090 | prose .61-.77 / .33-.58 / .16-.38 / .04-.24; code .91 / .81 / .70 / .58 | `cacde04e` |
| Flash Next MTP chain correct to depth 1-6 | GB10, code | 0.81, 0.60, 0.51, 0.38, 0.25, 0.14 | #113 |
| Flash Next per-position acceptance (vLLM log) | GB10 | code .89 .76 .64 .55 .45; prose .70 .46 .30 .19 .12; an extra draft costs ~4.8 ms | #136 (jschmied) |
| 27B + DFlash2 tree | R9700 (gfx1201, 640 GB/s) | 12-row round **37 ms**, of which matmuls 29 ms (~80 % of 639 GB/s), DeltaNet verify chain 1.3 ms, tree attention 0.8 ms; code 6.4 tok/round; 95.7 (chat) / 126.1 (code) tok/s at T=1 vs ~34 plain; 16 rows add **1.2 ms** over 12 | #100 |
| Same, at 16k context | R9700 | round 43.0 → 40.0 ms with launch cuts (1,007 → 943 launches), 2.8 tok/round; 16 rows: code +13-19 %, prose −9 % | #100 |
| 27B tokens a round | GB10, MLX 4-bit, 12-row tree | 4.0-5.2 (chat 4.2); EXL3 3-bit target only 3.0-3.3 (drafter trained on the unquantized model) | docs/recipes/qwen3.8-27b.md:95-96, 128-130 |
| Nemotron served | RTX 3090 (1.0.4, user receipt) | 350 W: code 644, prose 372 tok/s greedy; T=1: 413 / 353. 225 W: −15-20 % | #592 |
| Nemotron vs "llama.cpp's faster mode" | RTX 3090 | 252 prose / 313 code drafted, 194 plain = 1.44-1.69x | CHANGELOG.md:157. **The llama.cpp configuration is not recorded anywhere I could find** (commit `8a745bf4`, merges `f691d467`/`9cb79e05`, #592). [INFERENCE] 252/1.44 ≈ 175 and 313/1.69 ≈ 185, so the baseline was probably about TensorFold's plain decode, i.e. llama.cpp without speculation. |

---

## 2. Draft-length policy: the exact rules

### 2.1 Nemotron CUDA in-round depth rule (0.6.5 `bcb8f01c`; Zig `zig/src/core/draft_depth.zig`)

**Costs.** At startup, the engine times verify windows of 1..16 rows (`verify[r]`) and one MTP level (`level`).
- The marginal row costs are pooled so they never rise with rows: `Costs.measured`, a pool-adjacent-violators pass on `verify[r+1]−verify[r]` (draft_depth.zig:14-41; Python `@py src/tensorfold/cuda/draft_depth.py`).
- `row(k) = verify[k+1] − verify[k]`.

**Rule** (draft_depth.zig:53-91). Let `run` = the running product of the head's top-1 confidences along the chain, read after each level (`cuda_drafts.zig:19-31`).
- `keep(k)`: always true for k = 1; otherwise `run^power ≥ rate · row(k)`.
- `more(k)`: `k < most` and `run^power ≥ rate · (row(k+1) + level)`.
- `rate = tokens/ms` is an EMA (weight 1/8) of tokens per round over **modeled** ms per round, `verify[rows] + levels·level`. The code comment says "never a clock, so every rank of a split model chooses alike" (draft_depth.zig:87-91). Prior: 2 tokens over a 2-row round.

**Calibration** is a fixed power: `CALIBRATION = (2.0, 2.0)  # the depth rule's power on the head's overconfident running confidence (greedy, sampled)` (`@py src/tensorfold/families/nemotron_h/cuda/__init__.py:7`; Zig `cuda_drafts.zig:139-142` `DepthRule.init(c, max_chain=15, null, 2.0)`). The per-node isotonic tables of `fit_draft_calibration.py` are not used here. Those are for DFlash trees (§2.4).

**Mechanics.**
- One CUDA graph per level. The host waits on an event after each level to read its confidence from pinned memory (`cuda_mtp.zig:222-249`).
- Graphs are captured for "levels 0 and 1 at every kept-row count, later levels at one row" (`cuda_mtp.zig:194-202`).
- Level 0 is "absorb only": the kept rows of the last window enter the head's KV.
- On the 3090 the whole MTP part of a round is ~1.0 ms for 1.6-2.6 drafts (`3cda8800`).

**Gain.** Against 0.6.4's default (`DRAFTS = 3`, `CONFIDENCE = 0.2` on the running product; diff in `bcb8f01c`): **+6 % on one and two DGX Sparks, +7 % on an RTX PRO 6000**, exact (CHANGELOG.md:215-219; #136 close-out).
- docs/recipes/nemotron-3.5.md:44-45 still describes the old 3-draft / 20 % default. That text is stale: the Zig lone CUDA path always uses the cost rule (`cuda_lone.zig:26`), and `--mtp-drafts/--mtp-confidence` are not wired into the Zig Nemotron engine (grep finds them only in `server/cli.zig` and `engine_api.zig`).

**Measuring the costs** (`zig/src/core/lanes/cost_rule.zig`, `zig/src/families/nemotron/cuda_costs.zig`):
- Fastest of 7 timed runs after one untimed run. The commit message reasons that "Noise only adds time" (`49dad8b9`).
- A width that times more than 3 % under the previous width counts as noise, and both are re-timed (at most two sweeps).
- If any entry is more than 15 % from the last table measured on this GPU and model shape, everything is timed a second time.
- The level is timed between widths, as (chain-8 − chain-1)/7 with interleaved minima. One boot had recorded 0.61 ms for a level that measures 0.34 (`3e92032f`).
- Timing runs over real text from a fixed paragraph. A repeated token underprices MoE rows: "an 11-row window measured only 1.16x a single row… against 2-2.3x on real replies" (#250).
- Results are cached per executable, GPU, driver, model shape and kernel set (`11b90251`). A 3090 boot went from 7.5 s to 5.6 s.
- Spread before and after the fix, 1-row window: 4.58-6.27 ms → 4.38-4.92 ms; level: 0.353-1.176 → 0.351-0.377 ms (`49dad8b9`).

### 2.2 Mac lane core: a between-round depth chooser (`zig/src/core/lanes/depth.zig`, a port of `@py engine/family_depth.py`)

- Per stream, an EMA of acceptance by depth (`depth_rate` 0.15) and an EMA of measured round times by draft count (`cost_rate` 0.2).
- The chosen depth maximizes `(1 + Σ_d Π p_j) / roundCost(d)`.
- It probes one level deeper every 8 rounds.
- `plain_guard`: a draft must beat a plain round by 5 %; probes back into drafting double their wait up to 128 rounds (depth.zig:7-14, 137-186).
- Measured round time includes host time. Sampled and greedy rounds are kept apart because "a sampled round raises [round time and host time] by drawing on the host a row at a time". Fixing that took greedy code after sampled prose from 144.0 to 150.6 tok/s (CHANGELOG.md:29).

### 2.3 Measured outcomes of depth policies (mostly negative)

| Policy | Result | Source |
|---|---|---|
| Fixed cap 3 + running confidence ≥ 0.2 → cost rule (power 2, up to 15) | +6-7 % (Nemotron, GB10 / RTX PRO 6000) | `bcb8f01c`, #136 |
| Between-round depth from an EMA of acceptance (Flash Next, CUDA) | code 72-73 vs 74; chat −4-7 %. "Rounds carry ~24 ms of fixed work, so shallow chains waste the round." | #250 |
| Next round's depth from last round's confidences (vLLM replay) | code −0.8 to −8.2 %, prose +1.9 % at best | #136 |
| In-round per-draft stop at τ=0.7 vs fixed depth 5 (vLLM replay) | code +4 %, prose +7.5 %; depth 7, τ 0.8: +10 % / +12.8 % | #136 |
| Expected-tokens-per-ms controller vs that gate (replay) | 1-2 % behind the gate; oracle headroom +25 % / +35 % | #136 |
| `--mtp-cost 0.06`, marginal stop, Flash Next, uncalibrated | over-drafts: kept 7-8 % where the rule assumed ~0.19 ("product overstates greedy acceptance about 2.5×") | #250 |
| Same, calibrated per depth | 0.980 of the 0.70 cut (geomean of 23 cases) | #250 |
| Look-ahead (expected tokens/ms over all remaining depths) | no cut: 0.964; with cut: 1.001-1.010 (noise); adding a fixed 4.5 ms host term made it **worse** (0.953) | #250 |
| Why the priced rules lose on Flash Next | live rounds cost **5.0 ms/draft vs 3.55 in the startup table (+40 %)**; the gap was never attributed | #250 |
| Learned calibration ratios (kept / head product), Flash Next | greedy 0.94 / 0.78 / 0.62 / 0.43 at depth 1 / 3 / 5 / 8; sampled ≥ 0.9 down to depth 5 | #250 |
| Trimming verify rows but still running the draft steps (vLLM) | slower on prose; "the gain is in the skipped draft steps" | #136 |

Lesson: a cost-priced in-round stop pays only when (a) row and level prices match live rounds (Nemotron's did; Flash Next's did not), and (b) the head's overconfidence is corrected (power 2, or per-depth kept/product ratios).

### 2.4 Trees vs chains

- **MTP trees lose on Nemotron/3090** (`cacde04e`, `zig/tests/cuda/tree_accept.zig`). An offline probe recorded the head's 8-level chain plus chains from the level-1 runners-up (top-2..4) at every position. **Runners-up hold the level-1 truth in 56-88 % of misses**, which contrasts sharply with Strata's 0/14. But "their chains decay as fast". With 4.47 → 11.76 ms windows: prose median chain 333 tok/s vs top-2×2 295 and top-4×8 154; "every tree shape predicts below chains 2-3".
- **DFlash2 trees win for the 27B.** A best-first tree of 15 nodes, ≤4 children, scored by DFlash2's unary logits plus a learned predecessor/successor edge term (`edge` 0.6, `tau` 1.5), with keyed noise (weight 0.7) on sampled requests (`zig/src/families/qwen27/dflash/selector.zig:6, 50-60`).
- **Node landing probabilities**:
  - Python: an offline isotonic table P(land | depth bin, path log-prob bin), fitted by `@py tools/fit_draft_calibration.py` from `TF_DRAFT_LOG` dumps over 16 public prompts at T=0 and T=1, PAVA-pooled and checked on held-out streams (`@py src/tensorfold/drafters/calibration.py`). The shipped `@py src/tensorfold/families/qwen3_5/dflash2_calibration.json` (M5 Max, 4-bit target): greedy depth-0 bins run from 0.037 (score < −2.2) to 0.999 (score > −0.05). Calibration is roughly depth-independent and close to e^score at the top.
  - Zig replaces the table with **online counts per log-prob bucket (0.5 wide), with e^own as a 2-pseudo-count prior**. A greedy stream reads greedy rounds only (`zig/src/native/qwen27_landing.zig:4-24`; `6d59acfb`). Chance of a node = own × parent's (`qwen27_lanes.zig:556-566`).
- **Width choice:** add nodes greedily in order of landing probability and keep the prefix that maximizes `expected / (cost(rows) + overhead_ms)`. Overhead = measured round wall time minus timed forward cost (EMA 0.2; 8 ms default) (`zig/src/core/lanes/allocate.zig:8-49`, `windows.zig:167-190`, `depth.zig:241-268`).
- **Other negatives:**
  - The MTP head as a second opinion on DFlash2 candidates: +3-12 % accepted tokens but **−6-9 % tok/s**, because it is a dependent call (#113, #136).
  - For a lone 27B stream, context copies land less often than the DFlash2 tree: 138 vs 146 tok/s, M3 Ultra (CHANGELOG.md:61).

### 2.5 Draft vocabulary and 4-bit heads

- **Nemotron's `draft_ids.txt`**: 32,768 ids. Built byte-reproducibly from CPython 3.14.5 stdlib plus repo .py/.md (10.17M tokens): "ids below 1024, then ids by frequency, then lowest unused ids" (docs/recipes/nemotron-3.5.md:57-108). The draft head is lm_head's rows for those ids.
- **`tools/draft_vocab_extend.py`** adds every id whose decoded text contains a script: cjk, hangul, kana, cyrillic, arabic, devanagari, thai. There is **no Latin-Extended option**, so Polish diacritics are not covered (tools/draft_vocab_extend.py:20-29).
- **The CJK list costs English speed.** Flash Next's 79,591-id list covered only 33-43 % of Chinese token occurrences, giving 0.22 accepted drafts/round on Chinese vs 0.56 on English. The 135,040-id CJK list reads 1.7× the head rows and cost English/code −2 to −6 % (#416, `6dff66b1`).
- **4-bit heads by default.** Nemotron ships `mtp-4bit.safetensors`. For the NVFP4 checkpoint, "The bf16 MTP head is made MLX affine-4 at load as the MLX checkpoint's is" (`5f971417`). The 27B's DFlash2 drafter is read once into 4-bit copies: −17.6 GiB, "same tokens, at the same speed" (CHANGELOG.md:9).
  - **No acceptance A/B of 4-bit vs bf16 heads exists in the repo.**
- **Drafter vs target quantization:** DFlash2 on an oQ2 target gives 2.9 rows/round vs 7.8 on a 4-bit target, 19.7 vs 43.4 tok/s (#280).

### 2.6 Sampling at T>0: keyed Gumbel is the default, not an option

- The target draw is `argmax(v − log(−log u(seed, position, id)))`, with the noise hashed from (seed, position, token id) (`zig/src/core/lanes/gpu_rule.zig:83-92`; host twin `lanes/sampling.zig`).
- Drafters use the same keyed noise:
  - DFlash2's tree adds `0.7 · noise(position, token)` to node scores (`selector.zig:56`).
  - Nemotron draws sampled drafts at `DRAFT_TAU = 0.6 ×` the request temperature (`@py …/nemotron_h/cuda/__init__.py:6`).
- Verification is an exact match against the keyed sample.
- Result: **sampled ≈ greedy**.
  - 27B/DFlash2 on R9700: code T=1 126.1 vs greedy 117.9; chat 95.7 vs 96.8 (#100).
  - Nemotron on 3090: prose T=1 352.5 vs 372.5 greedy (#592).
  - Ours: MTP T=1 81.1 vs T=0 86.3; DFlash T=1 71.9 vs 90.6 (NOTES.md:165-175).

---

## 3. Recurrent-state rollback: a lagged state replayed inside the next window (new vs Strata)

Nemotron CUDA (`zig/kernels/cuda/nemotron_mamba.cu:1-155`, `zig/src/families/nemotron/cuda_engine.zig:476-492`).

**Per-row inputs.** A window stores each row's raw conv input, conv output `XC` and `DT` in **double-buffered "parity" planes** (`RAW[parity]`, `XC[parity]`, `DT[parity]`).

**The next window's kernels do the commit.** They read `META = {pos, parity, prev_keep}`.
- **Conv** (`tf_nemo_conv`, :20-49): replays the `pk = prev_keep` kept rows from `RAW[1−parity]` through the 4-tap history, writes `BASE` (the committed history) at row `pk−1`, then processes the window's own rows.
- **Scan** (`tf_nemo_scan`, :83-155): loads the state into registers, replays the `pk` kept rows (reading the old `XC`/`DT`), **writes the state to memory only at `i == pk−1`** (:142-146), then runs the R new rows in registers and never writes their states.

**Host side.** `Engine.commit(keep)` is two integer stores, `pos += keep; prev_keep = keep` (cuda_engine.zig:488-492). There is no commit kernel, no commit graph, no snapshot copies and no host sync. Rollback = choosing `pk`.

**Serial rounds without the host.** `tf_serial_feed` (`zig/kernels/cuda/nemotron_ops.cu:6-16`) writes the sampled token into the next window's ids, `pos+1`, flips parity and sets keep = 1. Plain decode is then "one graph replay a round, queued `lookahead`=4 deep: the device feeds each token to the next round" (`cuda_decode.zig:48-61`, `cuda_engine.zig:58-59`).

**Cost per round per Mamba layer.** One state read and one state write, the same as a plain step, plus recomputing ≤16 rows of compute. Strata instead has the verify read the state, then a separate commit graph read it again, replay and write. Snapshot schemes write the state once per row.

**Other engines.**
- 27B (Metal/CUDA): "DeltaNet commits replay the accepted path; attention commits retain only its keys" (docs/recipes/qwen3.8-27b.md:25).
- 27B commit off the critical path: `4f5f387b` / #713 splits the round's command buffer into (picks + accepted rows' taps + head row: everything the host waits for) and (keep: KV rows, recurrent state, history). The keep runs behind the next draft and is waited on only before the next verify: CLI +3.7 % short, **+12.0 % at 16K** (M5 Max). Not on the served path.
- Wide copy windows (Nemotron M5, 16 → 64 rows) "keep their Mamba states every 8th row" (CHANGELOG.md:258-261). Code editing went 550 → 760 tok/s (1.4×), prose +1.6-3.3 %.

---

## 4. Host mechanics and graphs

| Mechanism | Measured | Source |
|---|---|---|
| Dedicated single-stream loop ("lone driver") vs the generic lane scheduler | GB10: story 132.9 → 137.5, code 195.8 → 203.5, facts 141.3 → 150.8, long 137.5 → 142.8 tok/s (+3.5-7 %) | `efcf970e` |
| Extending the lone driver to thinking budgets / loop guard | −3.3 to −8.1 % wall time | #778 |
| Lone driver reclaims the last lane stream | about −5 % greedy | #780 |
| Masked (grammar) windows replay graphs, captured on first use per row count and draw mode; mask bits at one fixed device address the host rewrites | 9,426 eager windows → 22 captures (~50 ms); `"draft": false` +4.4 %, drafted +1.0 % | CHANGELOG.md:40, #660 |
| Other sequences capture their own graphs on first use | fixed crashes; speed unchanged | #615 |
| Collectives inside a captured graph cost +10 µs (GB10/NCCL); split graphs at collectives; relocate one captured plan across sequences via `cuGraphExecKernelNodeSetParams` | TP2 one stream +15-21 % | #597 |
| 27B tree verify / commit / draft as CUDA graphs, padded to row buckets 4..128 (pad rows are their own roots) | GB10 (GPU-bound): 0; A40 behind a 2.1 GHz Xeon: one GPU 57-76 → 65-86, TP2 49-68 → 100-136 | #358 |
| ROCm 27B: removed ~200 launches and **3 host syncs per drafted round** (stage-timer syncs only when tracing; strided views instead of copies, 176 launches) | part of R9700 98 → 128 tok/s dev history | #100 |
| GPU-side rounds (Metal Nemotron, Flash Next `fz_accept`): the GPU accepts, keeps rows and drafts; the host "reads behind", rounds queued `ahead`=2; the depth stop on the GPU zeroes later levels' **indirect-dispatch threadgroup counts** | no isolated number found | `zig/src/families/nemotron/gpu_round.zig:1, 48-62`, `gpu_round_api.zig:4-22` |
| Host thread QoS: only Mac two-host links (`pthread_set_qos_class_self_np(.USER_INTERACTIVE)`, `MCDMA_FABRIC_QOS=1`). No CUDA pinning, spinning or priority code: waits are plain `cuEventSynchronize` | — | `flashnext/tp.zig:607`, `cuda/stream.zig:61-63`, CHANGELOG.md:53 |
| Chunked prompt fill between rounds, scheduled foreground first and then shortest-remaining | HIP fork: slowest short request 11.4 → 0.73 s behind 8k prompts | CHANGELOG.md:19, #651 |
| "CUDA: every default path verifies at least two rows a round" (the first draft is always verified, `keep(1)=true`) | — | CHANGELOG.md:610, draft_depth.zig:75 |

---

## 5. Prompt cache / retained prefixes

- **Keep at any row with no extra prompt call** (#670, CHANGELOG.md:7):
  - The prompt path is chunk-invariant: all 53 dumps plus logits are byte-equal at 17 cut patterns on GB10 and RTX PRO 6000.
  - A state inside a chunk is stored by the scan as it passes that row, into a spare buffer; K/V rows are copied once the chunk is queued.
  - Turns 2-5 started 1.7-2.8× sooner (0.09-0.11 s vs 0.15-0.30 s).
  - Cold first turns are +1-3 ms under 1,400 tokens, and unchanged from 10k tokens.
- **Where states are kept:** at the user message start, and **512 and 2,048 tokens before the end of a long system prompt** (CHANGELOG.md:7). A second turn then resumed 2,607 of 2,647 tokens, vs 2,048 on the old grid.
- **What a state holds:** only what the prompt needs: 48 MiB Mamba + 7 KiB/token of K/V (attention and MTP head), counted in **2 MiB driver pages**. That is 62 MiB at 2k tokens vs 543.7 MiB for a whole-window copy; the 16 GiB budget held 258 states instead of 30.
- **Spare buffers:** four free Mamba buffers (192 MiB) stay preallocated, because "a fresh 48 MiB allocation takes 2.1 ms on a GB10" (CHANGELOG.md:8).
- **Background warm pass** (#723): after a reply, the rendered conversation + reply + next turn's opening is prefilled in the background; the pass yields to arriving requests at each chunk.
  - TTFT −48 to −57 % at gaps ≥ 0.15 s; +28-33 % if the next message arrives within 0 s.
  - Delaying the pass by 25 ms was worse.
  - The 27B has the same pass; it steps aside and keeps what it prefilled (`924104e2`).
- **Last-turn rewind state** kept just before the latest user message: an edit/regenerate cycle took 1.7 s vs 10.9 s of prompt time (M3 Ultra, 27B) (CHANGELOG.md:118).
- **`--learn` (Mac only):** shared-prefix states on disk, under an identity of config, tensor index, shard inode/ctime, kernels, OS, chip and a 4,143-token probe's bits (about 1 s at startup).
  - A new server's first turn: 0.27 s vs 1.30 s for 9.2k tokens; two states took 213 MB on disk (docs/recipes/nemotron-3.5.md:129-137).
  - Free-disk floor and crash-safe index (CHANGELOG.md:136-137).
  - CUDA refuses `--learn` (CHANGELOG.md:21).

## 6. Loop guard and thinking budget

- **`--loop-guard`** (#210, #262), off by default:
  - Watches committed tokens only inside an open think block.
  - Fires on the 256th consecutive repeat of a cycle of period ≤ 8 whose region starts ≥ 64 tokens in, so the earliest fire is at token 321. Cost: 1.3 µs per commit.
  - The fire forces the template's think-close through the same forced-window path as the thinking budget; the model then answers (#262).
  - Motivating incident (#204): GLM looped for ~28k tokens; 11,368 rounds at 29.8 ms ≈ 5.7 min.
- **Thinking budget:** the budget's last token becomes the start of `\n</think>\n\n`. The close lands inside a drafted window and the reply stays exact (CHANGELOG.md:35). Engines that cannot enforce it refuse with 400 (CHANGELOG.md:17).

---

## 7. What is NEW relative to the Strata study (research/strata/spec-host.md)

| Topic | Strata | TensorFold (new) |
|---|---|---|
| Recurrent rollback | Verify reads state without writing; a **separate commit graph** replays n_keep rows and writes; async commit +5.6 % | **Lagged state**: the replay of kept rows is fused into the *next window's* conv/scan kernels from double-buffered per-row inputs; state written once at row pk−1; the host commit is two integers; serial rounds are fed on the device and queued 4 deep (§3) |
| Depth policy | min-p gate on the drafter's own top prob; `DraftPolicy` chooses window size *between* rounds from EMAs; online measured round times | **In-round stop priced per row**: `run^2 ≥ rate·row(k)` and `run^2 ≥ rate·(row(k+1)+level)`, with startup tables (fastest of 7, dip/drift re-time, PAVA-concave), clock-free modeled rate; +6-7 %. Plus a documented set of failures (between-round EMA, look-ahead, uncalibrated cost stop) and the cause (live cost/draft 40 % above the table) |
| Calibration | none (gate on raw q) | power 2 on the running product (Nemotron); per-depth kept/product ratios (Flash Next PR); isotonic node tables (offline) and online log-prob buckets (27B trees) |
| Trees | Top-2 hit 0/14 → don't build trees | Nemotron: runner-up hit **56-88 %**, yet trees still lose to chains on a 3090 because of row cost; DFlash2 trees win for the 27B (4.0-6.4 tok/round at 12 rows) |
| Sampling | Coupled / Gumbel drafts opt-in (+9 % Strix Halo, noise on 3060) | **Keyed Gumbel is the default sampler**; drafters add the same keyed noise; sampled ≈ greedy speed |
| Host | doorbells, spins, pinning, aux-cpus | A dedicated lone-stream loop +3.5-7 % over the generic scheduler; GPU-side rounds with indirect-dispatch early stop (Metal); graphs for masked windows; sync audit (3 timer syncs per round in production) |
| Prompt cache | checkpoints at turn boundaries / 16K, message-boundary, parking | state at any row with no extra call; marks 512/2048 before the system prompt's end; K/V up to prompt length in 2 MiB pages; preallocated spare buffers; background warm pass of the reply; rewind state; disk-learned prefixes keyed by identity |
| Copy windows | lookup-chain ≤ 8 | copy windows grow 16 → 64 rows while landing whole, with Mamba states every 8th row: file rewrite **3.7×** (Flash Next CUDA, #319), code edit 1.4× (M5) |
| Exactness | batch-invariant kernels opt-in (`STRATA_IQ_MT_MIN`) | row-invariance is a hard contract, checked at load and in CI (`check-kernels` 1..16 rows byte-equal, `c787dd2f`) |
| Not new | MTP KV absorb of kept rows only, reduced draft vocab per script, 4-bit head, a TP collective note | same conclusions; TensorFold adds no 4-bit vs bf16 acceptance A/B and **no MTP attention window** (head chunks cover the full context, `gpu_round.zig:463`) |

---

## 8. Transfer to our setup (ranked)

Baseline: 35.7 ms/step = verify ~31 ms (incl. ~3.2 ms of gaps at ~972 kernels) + ~4.7 ms outside verify (MTP chain ~1.2-2.5 ms plus host). Row cost ~1.4 ms/extra column (roadmap B1 hypothesis); MTP level ~0.3 ms (roadmap B3: 4 draft graphs 1.17 ms wall).

### T1. Lagged GDN state: replay kept rows inside the next verify's GDN/conv kernels (S4, B11, A5)

- **Mechanism.** §3. In each GDN layer the verify kernel takes `pk` (the previous window's kept rows) and their stored per-row inputs from a parity buffer: post-conv q/k/v, g, beta, and raw conv inputs (~20 KB per row per layer in bf16; 48 layers × 16 rows × 2 parities ≈ 31 MB `[INFERENCE]`). It replays them in registers, writes the state once at row pk−1, then computes the R window rows without writing state.
- **TensorFold gain.** Not isolated: it is the base design of every Nemotron CUDA number.
- **Why it applies.** Our GDN state is ~3 MiB fp32 per layer × 48 ≈ 144 MiB `[INFERENCE: 48 v-heads × 128 × 128 × 4 B, the same as Flash Next's SO_ROW, flashnext/replay.zig]`. Per-row snapshots at T=5 write ~720 MB (≈0.75 ms at 960 GB/s, though the Infinity Cache absorbs part; roadmap B11 bounds it at ≤ 0.8 ms). A5's "5 snapshot cpys" in the conv path also disappear (5 × 48 = 240 kernels × 3.3 µs ≈ 0.8 ms of gaps).
- **Expected gain.** −0.8 to −1.6 ms/step → **+2.3 to +4.6 %**. It also makes rollback free for any width (K4).
- **Effort.** High (3-5 days). New variants of the GDN op and ssm_conv taking (state, prev inputs, pk); `pk` as a device-side graph input so graphs aren't rebuilt. The hybrid memory module must keep a "pending window" instead of per-cell snapshots (`[INFERENCE]` locations: `ggml/src/ggml-cuda/gated_delta_net.cu`, `ssm-conv.cu`, `src/llama-memory-recurrent.cpp`/`-hybrid.cpp`, the qwen35 graph builder).
- **Risk.** Medium: llama.cpp's seq_rm/checkpoint semantics; prompt-cache checkpoints must flush the pending window.

### T2. Cost-priced verify width, drafting max levels in one graph (K4; supersedes the failed p-cum attempt)

- **Mechanism.**
  - Keep drafting all levels in one graph: levels are cheap for us (~0.3 ms vs 1.4 ms per row, the opposite ratio from Flash Next/GB10).
  - Then trim the verify width with TensorFold's rule `keep(k): (Πp)^2 ≥ rate·row(k)`, where `rate` = EMA of tokens per modeled ms and row costs come from a startup table (fastest of 7, PAVA, drift check). This needs no per-level host sync.
  - Price from live rounds or check the table against them (the #250 lesson).
- **TensorFold gain.** +6-7 % (Nemotron, GB10 / RTX PRO 6000, against cap 3 + floor 0.2).
- **Why limited now.** Our rows are cheap relative to the round: 1.4/29.3 ≈ 4.8 % per row vs Nemotron/3090's ≈ 11 %. With rate = 3.16/35.7 = 0.0885 tok/ms the bar is `Πp ≥ √(0.0885·1.4) = 0.35`; at n ≤ 5 that is roughly what a p-cum gate does. That fits our null result (80.5 vs 80.3, NOTES.md:179).
- **Where it pays.** Combined with K4 at 9-16 columns: code and recall chains stay above 0.35 for many levels (Nemotron code chain .91/.81/.70/.58). If rows got to ~0.5 ms (R9700 WMMA: 0.3-0.7 ms/row), the bar drops to `Πp ≥ 0.21`.
- **Expected gain.** Mixed chat 0 to +2 %; code/edit +10-20 % only once wide columns are cheap (R9700 16 vs 12 rows: code +13-19 %, prose −9 % without a rule; the rule removes the prose loss) `[INFERENCE]`.
- **Effort.** Low-medium: the rule is ~100 LOC in common/speculative or our MTP loop; the startup table ~1 day.
- **Risk.** Low for exactness; medium for mispricing (table vs live).

### T3. A cheap multi-row verify GEMM is the real K4 enabler (K1/K4)

- **Mechanism.** R9700 (#100): the decode matmul is WMMA on 4-bit words repacked into 16-output tiles, with persistent blocks, a K split fixed by weight shape, the last block reducing in order, and **up to 32 rows sharing each weight read**. Stacked `[gate|up]`, `[qkv|z|b|a]`, `[q|k|v]` cut launches (1,007 → 943).
- **Measured.** 12-row round 37 ms vs ~29 ms plain (34 tok/s) at 640 GB/s; 16 rows only +1.2 ms more.
- **Applies.** gfx1100 has WMMA. Our MMVQ costs ~1.4 ms per extra column, with an MMQ cliff at n=8 (roadmap B1).
- **Expected.** If 9-16 columns cost ~0.5 ms each, a 12-row verify ≈ 31 + 7×0.5 ≈ 34.5 ms vs ~41 ms with MMVQ `[INFERENCE]`. That is the precondition for T2 and T4.
- **Owner.** Kernel slice; listed here as the dependency.

### T4. DFlash2 trees with calibrated node probabilities and keyed noise (alternative drafter path; B10)

- **Mechanism.** Best-first tree of 15 nodes (≤ 4 children, edge term, tau 1.5). Node chance = an online bucketed landing rate × parent chance. Width chosen by expected tokens / (cost + overhead). Keyed Gumbel noise is shared with the target sampler.
- **TensorFold numbers.** 4.0-5.2 tok/round at 12 rows (GB10); R9700 chat 95.7 / code 126 at T=1, i.e. **already above our 88-90 on a slower card**, with T=1 ≈ greedy.
- **Why we can't take it directly.** llama.cpp has no tree verify for hybrid recurrent models (tree attention mask + GDN per-path states; TensorFold's 0.6.2 GDN tree kernel "takes 8-35% less time", CHANGELOG.md:295-296).
- **Expected.** If T1 + T3 land, a 12-16 row tree could add +10-20 % on EN and close the T=1 gap `[INFERENCE]`. Polish stays weak (drafter not trained on PL; #280 shows acceptance tracks the drafter's training distribution).
- **Effort.** Very high. **Risk.** High.

### T5. Keyed-Gumbel target sampler plus coupled MTP drafts (T>0 only)

- **Mechanism.**
  - The target samples with `argmax(logit/T + g(seed, pos, id))`, noise hashed per (seed, position, token).
  - The MTP draft at position p takes `argmax(draft_logit/T' + g(seed, p, id))` over its top-k, with T' ≈ 0.6·T as in Nemotron.
  - Verify by exact match.
  - Output is an exact sample, reproducible per seed and independent of drafting.
- **Gain.** TensorFold: T=1 within 0-5 % of greedy (27B R9700; Nemotron 3090). Strata: +5-7 pt acceptance, +9 % Strix Halo.
- **Ours.** T=1 81.1 vs T=0 86.3 → up to +6 % at T=1. Our "probabilistic" mode was rejection sampling, which also gave nothing in Strata.
- **Effort.** Low-medium: llama.cpp sampler chain (`src/llama-sampling.cpp`, common/sampling) plus the MTP draft sampler; 1-2 days.
- **Risk.** Low (exactness by construction). Interacts with grammar and penalties.

### T6. Lean single-stream host loop plus a sync audit (K3)

- **Mechanism.** TensorFold's lone driver beats its own generic scheduler by +3.5-7 % (GB10). #100 found three stage-timer syncs per round in the production path.
- **Applies.** llama-server's slot/batch/sampler machinery runs per step. A fixed spec loop needs per step: verify launch, a 1-word readback, rollback (free with T1), MTP graph launch.
- **Expected.** Our ~4.7 ms outside verify includes ~1.2-2.5 ms of MTP. If host and sync overhead is 1-2 ms, halving it gives +1.5-3 % `[INFERENCE]`.
- **Effort.** Medium. Measure first: rocprof timeline of gaps between verify end and the MTP graph, and the speculative example vs the server.
- **Overlap.** K3, A10. GPU-side acceptance (§4: rounds queued ahead, the GPU writes the next window's input) is the extreme form; it needs device-side positions and masks in llama.cpp graphs, so it is very high effort.

### T7. Prompt-cache policy items (A1)

1. **Background warm pass.** Re-render and prefill the history right after the reply (Qwen templates strip `<think>` from history, so the live state cannot be reused). TensorFold: TTFT −48-57 % at user gaps ≥ 0.15 s. For us it hides one reply's re-prefill (e.g. 2-4k tokens ≈ 3-5 s at 660-910 t/s) during the user's reading time. Medium effort in llama-server: an idle-slot task that yields on a new request.
2. **Checkpoint marks** at the user-message start and 512/2048 tokens before the end of long system prompts, plus a rewind state before the latest user message. Low effort.
3. **Persist system-prompt states to disk** across server restarts, keyed by model hash + build. For a 15-20k agent system prompt that saves ~20 s per restart. llama-server slot save/restore exists; whether it covers GDN state for hybrids is `[INFERENCE]`, check.
4. **Size checkpoints by need, not by window:** KV up to prompt length plus ~150 MiB of GDN state, with spare buffers preallocated.

### T8. Wide copy windows with states every 8th row (A9 and K4)

- **Mechanism.** The copy window doubles 16 → 64 while copies land whole and halves after a break.
- **Gain.** Flash Next CUDA file rewrite 92 → 341 tok/s (3.7×); Nemotron M5 code edit 1.4×.
- **For us.** Agentic edits only. Needs K4 widths plus T1 or sparse snapshots (every 8th row).
- **Effort.** Medium. **Risk.** Low.

### T9. MTP prompt absorb as K/V only (S3, B6)

- **Mechanism.** TensorFold's head absorbs prompt rows through embed + norms + eh_proj + attn_norm + QKV + KV write only, skipping attention, o_proj, MLP and the head (`cuda_mtp.zig:270-293`).
- **Check.** Does our llama.cpp MTP prefill run the full MTP layer on every prompt token? `[INFERENCE]` If it does, skipping FFN and attention for prompt rows saves ~70 % of the MTP layer's prefill matmuls plus its quadratic attention: ≈ +1 % prefill short, more at 30-94k.
- **Effort.** Low-medium.
- **S3 note.** TensorFold has no MTP attention window, so it offers no evidence for or against S3.

### T10. Loop guard in think blocks

Period ≤ 8, 256 repeats, region start ≥ 64. Quality-of-life rather than speed; it prevents multi-minute runaway turns at 90 t/s. Low effort in the server.

### Not transferable or no gain for us

- Lane/shared rounds and `--parallel` (single user).
- Two-Mac QoS.
- Graph relocation across sequences.
- Collective splitting.
- `--learn` identity probe (Mac-only design).
- The 4-bit MTP head for S2: TensorFold defaults to it but publishes **no acceptance A/B**, so Strata's numbers (draft ms −13 %, tok/step flat) remain the only evidence.
- MTP self-distillation: TensorFold offers only #620's "recorder" idea: write verified rows' hidden taps plus the target's top-k per conversation to disk, so serving traffic becomes training data. That is a cheap way to collect **Polish** self-distillation data from our own server `[INFERENCE]`.

## 9. Overlap map

| Our item | TensorFold evidence |
|---|---|
| K1 MMVQ bandwidth | T3 (R9700 WMMA multi-row decode GEMM, 80 % of peak at 12 rows) |
| K2 fusion/latency audit | #100 launch cuts (stacked projections, strided views: −176 launches/round); 27B attention dispatch trims (`3262e703`, `dba7e18b`) |
| K3 host overhead | T6 (lone driver +3.5-7 %, sync audit), GPU-side rounds, device-fed serial rounds |
| K4 verify width 9-16 | T2 + T3 + T8; R9700 12 → 16 rows: code +13-19 %, prose −9 % |
| S2 4-bit MTP draft | 4-bit by default, no A/B (§2.5) |
| S3 MTP attention window | no window in TensorFold; T9 K/V-only absorb is the related prefill saving |
| S4 GDN rollback by replay | T1 (lagged state, replay fused into the next window) |
| MTP self-distillation | #280 (drafter acceptance follows the target's quantization), #620 recorder |
