# TensorFold × Qwen3.8-27B (our exact model): engine, numbers, negative results, transfer to 7900 XTX / llama.cpp HIP

Repo `~/research/TensorFold` at HEAD `0efbd447` (v1.0.8). Paths are relative to the repo root at HEAD unless a tag or
commit is named. `py:` = branch `origin/python-0.6` (the frozen Python engine, 0.2–0.6.6). Issues and PRs are
`#N` = https://github.com/ashhart/TensorFold/issues/N (PRs resolve under the same URL). `[INFERENCE]` marks my own
arithmetic or guesses. Everything else is quoted from code, docs, commits or issue threads.

Scope: this report covers only what is new relative to Strata (`research/strata/*`) and our roadmap. Strata already
covers GDN rollback by replay (S4); this report adds tree verify on top of replay.

---

## 0. TL;DR

1. **Tree drafts over GDN are solved and shipping.** One verify forward covers a pending row plus ≤15 DFlash2 tree nodes.
   - The GDN layer runs the recurrence per node from its parent's state, held in registers for ≤16 nodes. It writes no
     per-node state.
   - The commit replays the accepted root-to-leaf path from the logged k/v/g/β into the committed state.
   - This refutes our roadmap's "Tree drafts: GDN rollback is chain-only" (`research/v2/roadmap.md:243`).
   - Their measured tree-over-chain gain: **+21–34 % tok/s** (M5 Max, sampled, Python 0.2) and **+28–30 % tokens a
     pass offline** (code 4.35→5.57).
2. **The tree only pays because their verify width curve is nearly flat.**

   | Hardware | Cost of extra verify rows |
   |---|---|
   | M5 Ultra | 1→16 rows: 21.08→23.40 ms (+11 %) |
   | M5 Max | 1→16 rows: 46.8→53.7 ms |
   | R9700 (RDNA4) | 12 verify rows stream the weights at ≈80 % of bandwidth; 16 rows cost +1.2 ms over 12 |
   | Ours (7900 XTX) | ≈ 29.3 + 1.4·k ms (k = verify columns): +3.9 % of the step per column, ≈4–5× steeper relative to the step |

   - At our slope a 16-row DFlash2 tree loses about 9 % [INFERENCE, §7.2].
   - With a flat multi-row WMMA verify kernel (K1/K4) it becomes +2–3 % for MTP side-leaves, and up to +25 % on EN code
     with a DFlash2 tree [INFERENCE].
   - **K4 is the gate; the tree is phase 2.**
3. **The flat kernel exists on RDNA4: `qmm_rocm.cu` (PR #100, jkuepker, commit `b83748e2`, unmerged).** It is a
   persistent WMMA decode matmul with these features:
   - 16-output tiles, with weights repacked once at load.
   - 4-bit nibbles become bf16 `128+q` with one AND-OR (`0x4300`). The bias is folded through the group sums.
   - The split-K is fixed by the weight shape and is reduced by the last-arriving block in the same launch.
   - Up to 32 rows share each weight read.

   Measured on R9700 (gfx1201, 640 GB/s):
   - 12-row round 37 ms, of which 29 ms is matmul at ≈80 % of 639 GB/s; DFlash2 170 tok/s on code.
   - Drafted 95.7–126.1 tok/s, against about 34 serial.
   - It uses gfx12 WMMA builtins, so it needs porting to the gfx11 layout.
4. **MTP vs DFlash2 on the 27B (TF's own data).**
   - The checkpoint's MTP head as a sequential chain gave **more** tokens a pass than the DFlash2 tree (5.33 vs 4.55).
     TF rejected it only because one MTP step cost 1.5–2.9 ms on Macs ("a sequential guess must cost under 0.5 ms").
   - A relay drafter (MTP over the tree) guessed +13–19 % more but ran slower live.
   - MTP as a second opinion on DFlash2 candidates: −6 to −9 % net.
   - These support keeping MTP as our primary drafter, and S2 (cheaper MTP steps).
5. **Things we can lift cheaply.** All are measured in TF.
   - Deferred GDN replay inside the next window's GDN kernel: Flash Next `FZ_GDN=2`, same 16/48/128 geometry.
   - Accept and commit on the device in one command buffer.
   - Commit overlapped with the next draft: +3.7 % short, +12 % at 16k.
   - In-place state when every row is accepted: +4 %.
   - A merged warp reduction in the GDN tree kernel.
   - A context-copy rule with geometric copy windows: edits 3.4×. This needs S4, because there are no host checkpoints.

---

## 1. Engine architecture for the 27B

### 1.1 Lineage

| Engine | Where | Status |
|---|---|---|
| Python/MLX lane engine 0.2–0.6.6 (Mac), Python/Triton+CUDA (GB10/RTX/R9700 fork) | `py:src/tensorfold/families/qwen3_5/`, `py:src/tensorfold/cuda/kernels/gdn.cu` | frozen (#286) |
| Native Zig `qwen27` family (Metal only) | `zig/src/families/qwen27/*`, `zig/kernels/metal/{core,qwen27}`, `zig/src/native/qwen27_*.zig` | since 1.0.3, `34c44245` (2026-10-09); excluded from 1.0.0 because slower than 0.6.6 (`CHANGELOG.md:203`) |
| Zig `qwen3_5` (2B row decoder; the 27B ran on it briefly, #520/#528/#563) | `zig/src/families/qwen3_5/*` | 2B only now |
| Zig CUDA 27B | #608 (open), #734/#746 (open) | not merged; the CUDA kernel `zig/kernels/cuda/gdn.cu` is a verbatim copy of py `gdn.cu` |
| Zig HIP (gfx1030/gfx1100/gfx1151/gfx1201) | #463 runtime, #490/#631 (Qwen3.5 on HIP, slices) | open; W7800 (gfx1100) 27B 4-bit **11.7 tok/s decode, 235 tok/s prefill** (#389 receipt): far behind our llama.cpp |

### 1.2 Model geometry they code against

From `zig/src/families/qwen27/round_plan.zig:96` and the original recipe `094f5e4d:docs/recipes/qwen3.8-27b.md`:
- **DeltaNet:** 64 layers, 48 of them GDN with nk 16, nv 48, dk = dv 128, conv taps 4. The fp32 state is 3 MiB per layer.
- **Attention:** 16 layers with 24 query heads over 4 KV heads (GQA 6), head dim 256, rotary on a quarter of each head,
  and an output gate.
- **Vocab:** 248,320.
- **Weights:** MLX 4-bit group 64, 14.4 GB read per forward. Ours is UD-Q4_K_XL at 17.6 GB.

### 1.3 A drafted round, end to end (Metal, HEAD)

**Draft.** `dflash/generation.zig:113-141`, `dflash/runtime_model.zig:112-131`, `dflash/selector.zig:81-111`
- The DFlash2 drafter (`z-lab/Qwen3.8-27B-DFlash2`) has 5 GQA layers: hidden 5120, 32 heads over 8 KV heads, head
  dim 128, MLP 17,408.
- It reads the target's hidden states ("taps") after layers 5, 19, 33, 47 and 61. Its context is a 2,048-token
  sliding window of those taps, a ring of 2048×5×5120×2 B ≈ 100 MiB (`native/qwen27_served.zig:144`).
- Block 8, so 7 drafted depths. The config is checked to be stock (`dflash/config.zig:4-24, 61`).
- Per depth it gives **top-16 candidates** plus a rank-256 low-rank "edge" score between parent token and child
  token: predecessor·projected·successor (`selector.zig:43-49`).
- **Tree search runs on the host CPU.** It is best-first and expands the highest cumulative log-probability:
  - Defaults: `nodes 15, children 4, tau 1.5, edge 0.6, noise_weight 0.7` (`selector.zig:6, 51-111`).
  - Node score = unary/T + 0.6·edge/T (+0.7·keyed Gumbel noise when sampling, Python only; see §1.6), then divided by
    tau and log-softmaxed over the 16 candidates.
- **Draft vocab:** the drafter's head is the first 98,304 ids plus 288 special ids (248,032–248,320), 98,592 columns
  copied from the target head (`dflash/runtime_head.zig:5-6`). Rationale: "99.64 % of committed tokens have ids
  below 98,304" (`094f5e4d` recipe, item 13).

**Verify.** `decode_round.zig:166-226`
- One forward covers the pending token plus the tree, at most 16 rows (`native/qwen27_lanes.zig:17-18`).
- Per-row RoPE position = parent position + 1, so siblings share a position (`round_plan.zig:92-99`).
- The CPU encodes 4 layers, commits them, then encodes the next 4, so the GPU starts early (`decode_round.zig:8-9`,
  `commit_every = 4`). In Python this "pipelined graph build" took a one-row forward from 46.6 to 38.7 ms.

**Accept and commit on the GPU, no host round trip in between.** `generation.zig:84-109`, `decode_round.zig:265-299`
- An argmax/keyed-pick matcher kernel walks the tree on the device (`kernels/metal/core/tree_round.metal`) and writes
  the accepted path.
- `keepDevice` turns that path into GDN keep metadata, replays every GDN layer, publishes the conv history and copies
  the attention K/V of path rows into place. It then gathers the accepted rows' taps for the drafter and the last
  accepted row's logits (`tree_commit.metal:1-31`).
- The host waits once and reads only the result struct.

**Tree attention.** `docs/recipes/qwen3.8-27b.md:144-146`
- Each node reads the committed keys plus its own root-to-node path.
- Committed keys use 512-key chunks fixed by absolute position, then a tail and an in-order merge, so a row's bits
  never depend on the window (`094f5e4d` recipe, Exactness section).
- "Attention commits retain only its keys" (`recipe:25`). Tree rows are written into 16 spare cache rows past
  `--context` (`CHANGELOG.md:26`), then the accepted path is compacted.

### 1.4 GDN on a tree: how the recurrence runs along branches

**Metal**, `zig/kernels/metal/core/deltanet.metal`:

| Kernel | Lines | What |
|---|---|---|
| `tf_delta_gdn_pre` | 39-126 | Conv over each row's own ancestor path, then q/k L2-norm, decay `g`, `beta` |
| `tf_delta_gdn_tree` | 139-191 | Per-node recurrence from the parent's state, producing outputs only |
| `tf_delta_gdn_post` | 329-367 | Gated RMSNorm with silu(z) |
| `tf_delta_gdn_replay` | 193-234 | Commit: re-applies the accepted path's (k, v, g, β) to the committed state |
| `tf_delta_gdn_conv_commit` | 368-389 | Rebuilds the accepted conv tail from projected rows plus ancestor indices ("without persisting every node's conv window") |
| `tf_delta_gdn_chain` / `_chain_wide` | 236-328 | All-accepted chains (plain decode, prompt chunks) |

**`gdn_pre` input mapping.** `windows[row*taps+tap]` points either into the committed conv history or into the
projection row of the ancestor `tap` hops up. `gdn_pool.zig:23-30` validates it.

**Tree kernel grid.** One SIMD-group per (stream, value head, dv column). 32 lanes × 4 floats cover dk = 128. Each
thread therefore holds a 4-float slice of one state column.

**Tree kernel, ≤16 nodes and dk 128.**
- The kernel loads the committed column once (`root`) into registers.
- It keeps **16 named float4 registers `kept0..kept15`**, one per node.
- Node *i* takes its parent's registers through a uniform `switch(parents[i])` and runs `delta_update` then
  `delta_read`.
- Nothing is written except the node's output y (`deltanet.metal:159-177`).
- Per-row cost equals a chain step (one decay, two dots, one rank-1 update over 4 floats per lane). Read traffic is
  one state read per layer: 3 MiB.

**Tree kernel, more than 16 nodes.** Each node writes its state to a **snapshot slab** (one layer at a time,
`rows × 3 MiB`) and children read it back (`deltanet.metal:178-190`). The Metal engine caps windows at 16 rows, so this
path is unused for the 27B.

**Commit by replay.** `gdn.zig:152-166` and the `replay` kernel:
- The kernel starts from the committed state (`state_slot`).
- It re-runs `delta_update` over `kept_rows` (the accepted path) using the logged k/v/decay/mixing.
- It writes `next_state`, which `publish` copies. #711 (open) proposes scanning in place when slots don't move.
- The Python engine documents the same mechanism: "each DeltaNet layer re-runs its recurrence over the kept tokens
  from the recorded start state (`kernels/gdn_capture.py`)" (`094f5e4d` recipe).

**State count and memory per stream.** `gdn_pool.zig:44-101`; `gdn_pool_gpu.zig:58-72` allocates all of these:

| Buffer | Size |
|---|---|
| Committed state + next state | 2 × 48 × 3 MiB = 288 MiB |
| Conv history | 48 × 60 KiB |
| Logs, per layer per row: q 4 KiB, k 4 KiB, v 12 KiB, decay 192 B, mix 96 B (≈20.3 KiB) | ×48 layers ×128 rows ≈ 127 MB |
| qkv projection rows | ≈126 MB |
| One-layer snapshot slab (rows × 3 MiB) | 384 MiB at 128 rows |

[INFERENCE: the sizes from the code's formulas.] **No full GDN state is stored per tree node.**

**CUDA (py, also `zig/kernels/cuda/gdn.cu:133-264`).** The same idea, generalised:
- Host side: `py:src/tensorfold/cuda/kernels/gdn.py:23-74` schedules the tree in **DFS or level order, whichever
  needs fewer live states**. It emits `(node, source, dest)` triples:
  - source −1: committed state.
  - source −2: the node just run, still in registers.
  - source ≥0: a shared-memory slot.
  - Slots are freed when the parent's last child reads them. More than 32 live states is refused.
- Instantiations: SLOTS ∈ {0,1,2,4,8,16,32} with R value rows per warp ∈ {8,4,2} (`gdn.cu:316-323`).
- Shared memory per warp: `SLOTS·R·32` float4.
- A chain-plus-leaves tree needs SLOTS ≤ 1.
- CHANGELOG 0.6.2: "The GDN tree kernel takes 8-35 % less time with the same bits" (`CHANGELOG.md:295-296`).

**Micro-tricks in `gdn.cu`.**
- **Merged reduction:** node *i*'s `q·S` read (`pend`) and node *i+1*'s `k·S` dot share **one** `spread_sum<2R>`
  butterfly (`gdn.cu:187-241`). This halves the shuffle rounds per node.
- **Double-buffered inputs:** node *i+1*'s inputs load while *i* computes (`visit(a,b)` / `visit(b,a)`,
  `gdn.cu:242-248`).
- **Fused commit:** "one launch replays every DeltaNet layer's accepted path" through a pointer table
  (`gdn.cu:266-304`). Two-Spark commit went 3.6 → 2.3 ms a round (`v0.3.3:docs/recipes/qwen3.8-27b.md`).
- **Deferred replay (Flash Next, same 16/48/128 GDN geometry):**
  - The tree kernel's `Pending` argument folds the **previous round's accepted rows into the committed state at the
    start of the next tree kernel** (`gdn.cu:121-182`; used by `py:qwen4_exp/cuda/gdn_multi.py:77`).
  - Metal `FZ_GDN=2` (`kernels/metal/decode/fn_gdn.metal:1-6`, commit `244989a3`): "keep one state a layer in place
    and replay the previous window's kept rows into it, so neither per-row states nor the round's 113 MB state copy are
    written".
  - Together with `fz_lane`: Flash Next long_8k 166.4 → 174.5 tok/s on M5 Ultra.

### 1.5 Draft-width policy

**Node chances.**
- `native/qwen27_landing.zig:4-24` keeps 16 buckets by the node's own drafter log-probability (0.5-nat buckets).
- A node's chance = `(landed + 2·e^own)/(offered + 2)`, observed only for nodes whose parent row was kept.
- Greedy rounds are kept apart (since 1.0.8, `6d59acfb`; `CHANGELOG.md:29`: M3 Ultra 144.0 → 150.6 tok/s).
- A node's path chance = its chance × its parent's chance (`qwen27_lanes.zig:559-566`).

**Width costs.**
- Measured per build and device at first start: widths 1–16, fastest of 7 runs, smoothed, drift-checked against a
  reference and re-timed when more than 15 % off (`qwen27_lanes.zig:147-181`; `core/lanes/cost_rule.zig:1-60`).
- Cached on disk keyed by build, device and shape.

**Rule.** `core/lanes/allocate.zig:8-47`, `core/lanes/windows.zig:167-201`
- Add nodes greedily, most likely first.
- Keep the prefix count that maximises `E[tokens] / (cost(width) + overhead_ms)`.
- The tree is then cut with `sanitizeTree`. Best-first ordering means a prefix is always a valid subtree.

**Fixed limits.**
- 15 drafts + 1 pending = 16 rows on Macs (`qwen27_lanes.zig:45`).
- 12 rows on GB10, raised to 16 for a lone stream (#115: code +13–14 %, chat ±1 %).

**Copy windows (`TF_QWEN27_COPIES`, shared rounds).**
- A context copy backed by ≥8 matching tokens replaces the tree.
- Such a match "existed in about 25 % of tree rounds and its next token was right 94 % of the time"
  (`094f5e4d` recipe, item 11).
- On CUDA, copy windows start at 16 and double while copies land whole, up to 128 (#115: edits 144 → 489–501 tok/s,
  3.4×).
- In 1.0.6 a lone stream got copies instead of trees and slowed down. 1.0.7 reverted it: "a copied span lands less
  often than the drafter's tree" (`CHANGELOG.md:61`).

### 1.6 Exactness contract ("verify matmul fixes reduction order by weight shape")

**Matmul.**
- For each 64-input group: tensor-op product of bf16 rows × raw 4-bit codes into fp32, then
  `acc += scale·p + bias·Σx_group`, groups in order.
- K is split into a slice count chosen from the weight shape alone, and slices are added in slice order. A row's bits
  therefore never depend on how many rows share the call (`094f5e4d` recipe, Exactness section;
  `py:qwen3_5/cuda/README.md` table).
- Stacked projections ([gate|up], [z|b|a], [k|v]) keep members as views, with the same bits.

**Cost of the contract.**
- **M5 Max:** the lane matmul's one row costs ≈1.35× MLX's vector kernel (`094f5e4d` recipe, item 1).
- **M5 Ultra (#527):**
  - The matrix kernel is bound by the tensor unit at one row: 7/8 of each 8×8 MMA is empty. It holds ≈700 GB/s at 1
    and at 8 rows alike.
  - An FP32-ALU kernel is +27 % at one stream (38.7 → 47.3–49.5 tok/s) but half at eight streams (131–138 → 68–72).
    Parked: the per-row-count switch would break drafted == serial.
- **GB10:** per-shape split tables were "3-8 % faster alone, 1.5-2 ms slower per forward" (`v0.3.3` recipe). That
  sentence is about live-vs-microbench, not the contract.

**Sampling.**
- Keyed Gumbel-max: `u = splitmix(seed, position, token)`, `argmax(logit/T + (−log −log u))` over the top-k/top-p
  set (`core/lanes/sampling.zig:43-54, 120-130`).
- In the Python engine the drafter's tree scores add `0.7 ×` the same keyed noise (`py:drafters/dflash_tree.py:20-26`).
  Weight 1.0 gave fewer tokens (`v0.3.3` CUDA "tried and rejected").
- At HEAD the Zig propose path passes no noise (`runtime_model.zig:126,130` → `selector.Options{.nodes=...}` with
  `noise = null`).

### 1.7 Prompt cache and prefix retention for the hybrid

**Mac.**
- Prompt chunks start at assistant-message and second-message boundaries that are ≥256 tokens beyond the previous
  start, else every 2,048 tokens. Prefix reuse resumes only at chunk starts, where the GDN state naturally exists
  (`recipe:26-29`; `core/prompt_cache.zig:86-88`: `min_gap 256`, `min_prompt 4096`).
- A kept state holds (`families/qwen27/snapshot.zig:1-27`):
  - all 48 GDN states and conv windows;
  - K/V rows up to the resume point;
  - the drafter's tap ring.
- Default budget 16 GiB (`CHANGELOG.md:24`).
- The rendered reply rows of the previous turn are re-run with **decode arithmetic** (`decodeChunk`,
  `generation.zig:65-72`; `decode_spans`). The resumed state therefore equals the decoded one bit for bit.

**CUDA (py).**
- The cache entry stops **one token before the prompt's end** (#65). The chat template re-renders `<think>\n` as
  `<think>\n\n` on the next turn.
- "The chunk holding that point runs its GDN chains as two launches, so the prompt's own state keeps its bits"
  (`py:qwen3_5/cuda/README.md`). This is how they get a GDN state at an arbitrary row inside a chunk: split the scan
  there.
- Editing, deleting or regenerating the last turn resumes from a state kept before the latest user message (#571;
  M3 Ultra: 10.9 s → 1.7 s of prompt time, `CHANGELOG.md:118`).

### 1.8 "The 27B's reuse check", small `--context` start (#661), checks drive the served host (#659)

**`tf-qwen27-reuse`** (`zig/tests/qwen27/reuse.zig:1`): "prompt reuse through the served host against fresh prompt
passes: each prompt's state and reply, bit for bit."
- 9/9 cases on M3 Ultra.
- On the M5 lane core one case differed in round count: 12 rounds and 51 accepted vs 13 and 50, with the same
  tokens. Trees are sized from server history (§1.5), so the check now compares rounds only on the serial loop (#659
  maintainer comment).

**#659 (`611b15d8`, `fd83a96b`).**
- The 27B checks (`served-check`, `dflash-served-check`, `lanes-check`, `lanes-run`, `reuse`) now build against
  `qwen27_served.zig`, the host the server opens.
- The dead serial host goes: −396/+67 lines.
- Contracts changed: sampled requests draft, a cancel lands at a round's end, a prompt-only request is a warm pass.
- M3 Ultra lanes-run: lane core 41.1 tok/s vs serial loop 32.6.

**#661 (`66042e3c`, `924751db`).**
- First start times every window width 1–16 in slot 0: a 192-token prompt, then ≈260 windows that each keep a row.
  At `--context` below ≈450 it hit `BadRoundPlan`.
- Fix: the timing prompt is at most context − 16, and the slot is refilled before a window that would not fit.
- `--context 256` now starts in 11.2 s on M3 Ultra (10.7 s on M5 Max).
- Width costs on M5 Ultra are unchanged at 21.08 … 23.40 ms for 1 … 16 rows.

---

## 2. Per-step time breakdowns they publish

| Hardware / engine | Breakdown | Source |
|---|---|---|
| M5 Ultra, Zig qwen3_5, one row | 25 ms GPU, of which 22.9 ms projections at ≈660 GB/s and 1.8 ms the rest; 0.2 ms CPU encode; 2.3 ms host memcpy of 151 MB of GDN state (removed: 36→38.7 tok/s) | #527, #528 |
| M5 Ultra, qwen27 (#578) | Plain round 21.5 ms one stream, 27.1 ms eight streams; projections-only one-row step 16.8 ms GPU over **321 calls** | #578 |
| M5 Ultra, qwen27 width costs | 1 row 21.08 ms … 16 rows 23.40 ms | #661 |
| M5 Max, Python 0.2 lane matmul | Forward 1/2/4/8/16 rows: 46.8/47.1/48.1/49.7/53.7 ms (MLX: 32.9/35.2/49.2/86.8/112.6); 32 rows 60-63; 64 rows 117; +1.35 ms per row past 16 | `094f5e4d` recipe |
| M5 Max, native 1.0.7 plain | 35.03 ms/token at 2k, 37.44 at 16k; mlx_lm 0.32: 30.86 tok/s | #711, #712 |
| M5 Max, native drafted CLI | 5.39 ms/token on code (≈185 tok/s), 6.02 at 16k | #713 |
| M5 Max, agent sessions 21-23k ctx | 45-55 ms rounds, 4.0-5.2 tokens a round | `094f5e4d` recipe |
| GB10 (≈240 GB/s), Python CUDA | 12-row round ≈95 ms: **83 verify, 8 draft, <1 commit**. Two Sparks: 60 ms (52 verify, 6 draft, 2 commit) | `v0.3.3` recipe |
| R9700 (gfx1201, 640 GB/s), PR #100 | 12-row round, code, 6.4 tok/round: **37 ms, of which 29 ms matmul at ≈80 % of 639 GB/s, GDN verify chain 1.3 ms, tree attention 0.8 ms** | #100 |
| R9700 at 16k | 43.0 → 41.2 ms (drafter attention split, 2.3 → 0.27 ms) → 40.0 ms (stacked input projections, K-split target 64; launches 1,007 → 943); 16 rows "accepted no more … and cost 1.2 ms a round" over 12 | #100 |
| R9700 at long context (12 rows, WMMA tree attention) | Round 40.4 / 43.0 / 44.4 / 51.9 / 61.7 ms at 3.4k / 16k / 38k / 77k / 120k; tree attention per layer 1,908 → 1,324 µs at 120k | #100 |

---

## 3. Numbers by version and hardware

### 3.1 Decode, tok/s

| Version / engine | Hardware | Drafted | Plain | Reference | Source |
|---|---|---|---|---|---|
| 0.2.0 Python, final stack | M5 Max 128 GB | HTML 152, code 126, story 66, whole-file edit 388 | MLX serial 24-25 | — | `094f5e4d` recipe |
| 0.3.3 Python CUDA | GB10, one Spark | code 49.6 s / 49.2 g; chat 45.8 s / 45.9 g | 13.1 | vLLM NVFP4 MTP=3: 17.7/15.0/17.7/17.0 | `v0.3.3` recipe |
| 0.3.3 Python CUDA | Two GB10 (TP2) | 82.4 / 58.9 / 76.2 / 71.1 | 22.5 | vLLM TP2: 33.1/30.4/31.6/30.5 | same |
| 0.3.5.1 Python | M5 Pro 64 GB | 62.8 / 45.9 / 61.2 / 56.2 (code s / chat s / code g / chat g) | 16.2-16.6 | — | `recipe:188-224`, #70 |
| 0.5.0 Python CUDA | GB10 at 128k / 96k | 18.4 → 38.9 / 23.6 → 45.9 | — | — | `CHANGELOG.md:379-382` |
| PR #100 (unmerged) | **R9700 (RDNA4)** | code 126.1 (T=1) / 117.9 (greedy); chat 95.7 / 96.8 | 33.9-34.2 | — | #100 |
| 0.6.x CUDA | RTX 4090 | 64-86 | — | — | `CHANGELOG.md:326-329` |
| 0.6.x CUDA, NVFP4 vs MLX vs vLLM | GB10 | NVFP4 47.1/38.2/47.2/38.3; MLX 57.8/50.0/53.9/50.1 | — | vLLM 23.4-25.8 | `recipe:85-93` |
| 0.6.x CUDA, EXL3 3.00bpw | GB10 | code s 83.4, chat s 44.2, code g 64.5, chat g 39.9 (12-row round 75 ms vs 84) | — | — | `recipe:118-133` |
| 1.0.3 native | M5 Max | prose 64-77, code 151 (512 tok) | 18-19.5 | mlx_lm 0.31.3: 32-33 (drafted) | `CHANGELOG.md:152-153` |
| 1.0.6 native (#578) | M5 Ultra | greedy code 199-215, chat 142-144; sampled code 225, chat 102 (was 28, plain) | 46.6 (21.5 ms round) | — | #578 |
| 1.0.7 / 1.0.8 native | M3 Ultra | greedy code 146 (fresh), 150.6 after sampled requests | 32.6 (serial loop) | — | `CHANGELOG.md:29,61`, #659 |

Two notes on the table:
- **T=1 vs greedy:** on R9700 and GB10, sampled tok/s ≈ greedy tok/s. Sampled acceptance does not collapse there,
  which is unlike our DFlash2 result.
- **Plain native vs mlx_lm (M5 Max):** native 28.5 vs mlx_lm 30.9 (#711).

### 3.2 Prefill, tok/s

| Version | Hardware | 2k | 8k | 16k | 32k | 64k | Notes |
|---|---|---|---|---|---|---|---|
| 1.0.3 native | M3 Ultra | — | 252 (mlx_lm 441) | — | 184 at 30k (mlx_lm 404) | — | `CHANGELOG.md:154` |
| native (#711 runs) | M5 Max | 1,049-1,060 | — | — | — | — | #712 text |
| Zig qwen3_5 + NAX (#563) | M5 Max | — | — | 206 → 619-627 at 16.7k | — | — | — |
| 0.3.5.1 Python | M5 Pro | — | 423 | 401 | 363 | 296 | 219 at 140k |
| 0.6.x CUDA, FP8 prompts | GB10 | 1,834 | 1,872 | 1,779 | 1,563 | 1,240 | bf16 default = 0.73-0.82× of FP8 |
| PR #100, FP8 prompt GEMM | R9700 | 1,834 | 2,121 | 2,069 | — | — | 4k chunk at 64k: 46 % attention |
| 0.6.x | RTX 4090 | 2,400-2,600 (2k-32k) | | | | | — |

Our 660-910 tok/s on the 7900 XTX is already ahead of every TF AMD path except RDNA4 FP8 (FP8 is gfx12-only). FP8
prompts cost perplexity +4.1 % vs +0.03 % for bf16 (#100 maintainer note).

### 3.3 Acceptance

| Measure | Value | Source |
|---|---|---|
| Tokens a pass, chain → tree (offline, 15 nodes) | code 4.35 → 5.57; HTML 3.33 → 4.36; story 2.89 → 3.73 | `094f5e4d` recipe, item 5 |
| Score calibration on ≈1,500 traced rounds | +6.5 % accepted | same |
| Session n-gram prior on tree scores | 4.49 → 4.62 tokens a pass | same, item 14 |
| Wider trees: 31 nodes | +7 % tokens for 1.6× matmul time | same |
| Wider trees: 127 nodes | 5.47 vs 4.57 at 15 nodes, ≈4× cost | same |
| GB10, 32/64 rows | about +1 token a round for +30-40 ms; 49.2 tok/s at 12 rows vs 44.7 at 32 and 43.7 at 64 | `v0.3.3` recipe |
| Candidate ceiling | Truth is in the top 16 for 6.5-7.0 tokens a round; no scorer picks right >75 % past depth 1 | `094f5e4d` recipe |
| Why 12-row rounds end | Half end because the whole branch was right and the tree had nothing deeper; 2/3 of misses have the truth among the 16 candidates, hence "depth before siblings" | `v0.3.3` recipe |
| MTP chain vs DFlash2 tree (27B, Mac) | 5.33 vs 4.55 tokens a pass; MTP first-draft acceptance "near 77 %" (ashhart, #266) | `094f5e4d` recipe |
| Quantized-target effect (M4 Pro) | 4-bit: 7.8 rows a round, 47/109 drafts accepted; oQ2: 2.9 rows, 31/60. Drafter acceptance is not the issue; rows got pricier | #280 |
| EXL3 3.00bpw chat | 3.0-3.3 tokens a round vs 4.2 for MLX 4-bit (DFlash2 trained on the unquantized model) | `recipe:128-130` |
| Served M5 Max (#711-#713) | "draft rounds and tokens per round" 2.88 / 8.53 / 3.20 / 8.00 for copy / arithmetic / story / code | as printed |

---

## 4. Tried and abandoned (negative results)

| Tried | Result | Source |
|---|---|---|
| MLX's quantized matmul for verify windows | Rows equal only up to 9; a 9-row check costs 4.3× a one-row step | `094f5e4d` |
| Int8 activations on the tensor units | 27 % faster per op, not faster end to end, 7× error | same |
| Wider windows and trees (31/127 nodes; GB10 32-64 rows) | Diminishing tokens, large cost; 12-16 rows is the optimum | `094f5e4d`, `v0.3.3` |
| Matmul variants faster alone | Pipelined group loop +5 % alone / −2.7 % live; per-shape split-K table 17 % faster in a microbench, rounds 53.3 → 69.3 ms live; prefetch; unpack per threadgroup 0.72-0.88×. GB10 per-shape settings 3-8 % faster alone, 1.5-2 ms slower per forward | same |
| Three bit-identical loop restructurings (prefetch, two groups, adjacent chunks) | All stuck at ≈700 GB/s: bound by tensor-unit instruction count, not memory. First A/B pass was GPU clock ramp after CPU compiles | #527 |
| FP32-ALU projection family | +27 % at 1 stream, parity at 2, half at 8; parked (#527) | #527 |
| Last-level-cache prefetch pass; async copies to threadgroup memory | Costs more than it saves; not reachable from Metal | `094f5e4d` |
| 1,024-key attention chunks | Win above 40k keys, lose at 2-20k, change bits | same |
| Keys staged in threadgroup memory | 33-45 % slower | same |
| MTP head as sequential chain | More tokens (5.33 vs 4.55) but 1.5-2.9 ms per step; needs under 0.5 ms | same |
| Relay drafter (MTP layer over the lane tree) | +13-19 % guessed tokens, 72.3 vs 76.0 tok/s live | same |
| MTP as second opinion on DFlash2 candidates in the same round | +3-12 % accepted on chat, 0-6 % on code; net −6 to −9 % (dependent MTP call before verify) | #113 |
| Fine-tuning DFlash2 on 372k target tokens | No gain | `094f5e4d` |
| Drafters from scratch (rented H200s) | 3.8-5.1 % first-token acceptance | same |
| Jacobi decoding (no drafter) | 1.07 tokens a pass | same |
| DFlash2 blocks of 26/32 positions | Fewer tokens than block 16 (5.8 vs 6.2 at 32 rows) | `v0.3.3` |
| Sampling-noise weight 1.0 in tree scores | Fewer tokens than 0.7 | same |
| `NCCL_PROTO=LL` (two Sparks) | 16-row forward 52.6 → 82.0 ms | same |
| Stacking DeltaNet gate projections (CUDA, 16 rows) | No gain. Contrast: on M5 Max the a/b projections ran at 13 GB/s over 96 dispatches, so fusing z+b+a and k+v was taken (#527, #578) | `v0.3.3`, #527 |
| Copies instead of trees for a lone stream (1.0.6) | Slower; reverted in 1.0.7 (copies land less often) | `CHANGELOG.md:61` |
| FP8 prompt activations as default | Perplexity +4.1 % vs +0.03 % bf16; bf16 default since 0.6.0 | #100 |
| ROCm WMMA/bf16 for verify on the Strix GGUF path | "changed drafted replies and were not faster" | #144 |

---

## 5. Kernel tricks (Metal-specific vs portable)

| Trick | Mechanism | Measured | Portable? |
|---|---|---|---|
| GDN tree, register-resident nodes | ≤16 nodes × float4 per lane, parent picked by a uniform switch, no state writes (`deltanet.metal:159-177`) | Enables 16-row trees at chain cost | **Yes.** RDNA3 wave32: 64 VGPRs extra per lane for 16 nodes |
| GDN tree, DFS/level slot schedule (CUDA) | Minimal live states in shared memory (`gdn.py:23-74`, `gdn.cu:133-264`) | "8-35 % less time" (0.6.2) | Yes |
| Merged q-read and k-dot reduction plus double-buffered node inputs | One `spread_sum<2R>` per node (`gdn.cu:187-248`) | Part of the 8-35 % [INFERENCE] | Yes, also for our chain kernel |
| Replay commit, one launch for all layers | Pointer table (`gdn.cu:266-304`) | 3.6 → 2.3 ms a round (two Sparks) | Yes |
| Deferred replay in the next window's GDN kernel | `FZ_GDN=2` (`fn_gdn.metal:1-6`); `Pending` in `gdn.cu:159-182` | Flash Next with `fz_lane`: 166.4 → 174.5 tok/s | Yes (this is our S4) |
| In-place chain scan when all rows are kept | #711: avoids a 288 MiB read+write per token | Plain +4.0 % at 2k, +2.6 % at 16k (M5 Max) | Yes (≈ our #30139) |
| Conv tail by ancestor index | No per-node conv window kept (`deltanet.metal:368-389`) | — | Yes |
| Device-side accept + commit | Matcher → keep metadata → GDN replay → K/V compaction → taps → head row in one command buffer, one readback (`generation.zig:84-109`) | Part of the 1.0.3 engine | Yes (HIP graph or stream) |
| Commit overlapped with next draft | Split the command buffer: picks + taps (needed by the drafter) first, keep second without waiting (#713) | +3.7 % code, **+12 % at 16k** (CLI, M5 Max) | Yes |
| Decode attention: tail fused into prefix kernel for chains; head-dim 256 split over two SIMD-groups at one row; gate in merge | #712 | +2.2-2.6 % plain | Partly (D=256 split for occupancy at small n) |
| Drafter attention ILP and wide top-k | 4-key tile load before fold; top-k over 98,592 columns split into 16 threadgroups plus merge | In #713's +3.7/+12 % | Yes |
| WMMA persistent multi-row decode matmul (RDNA4) | Repack to 16-output tiles; `0x4300` nibble→bf16(128+q); bias via group sums; fixed shape-chosen K split; last-arriving block reduces; ≤32 rows per weight read; stacked projections as views (`b83748e2:src/tensorfold/cuda/kernels/qmm_rocm.cu`) | 12-row verify matmul 29 ms at ≈80 % BW (R9700) | **Portable to gfx11 with a new WMMA layout** (#144: the gfx12 builtin fails on gfx1151) |
| `v_dot2_f32_bf16` GEMV for one row | "fastest at one row, compute bound in draft windows" (`qmm_rocm.cu` header) | — | Yes (gfx11 has dot2) |
| WMMA tree attention (RDNA4) | Block per 512-key chunk × KV head; 16-key tiles staged once for all (row, head) pairs; 4 loader waves double-buffered | 120k: 1,908 → 1,324 µs per layer | Yes (our fattn-kvq already shares GQA heads) |
| WMMA prompt attention head 256 (RDNA4) | Block per 16 query rows × KV head, a wave per query head sharing K/V tiles; `S^T = K Q^T` so P is already the A operand of P·V | 78 vs 48.9 TFLOPS (Triton) | Yes, relevant to B4 |
| hipcc tuning | 32-bit index math, register-pressure control, load ordering, stop full unroll of pipelined chunk (#406 backport) | Round at 61.5k 48.0 → 44.9 ms (−6.6 %); −10.5 % at 123k | Yes |
| Tiled weight layout | 1 KB contiguous blocks per 32-col tile × 64-input group | Mac rounds 58.2 → 49.7 ms; GB10 107-130 → 200-220 GB/s | Already the norm in llama.cpp |

---

## 6. Relation to our plan (K1-K5, S1-S4)

- **S4 (rollback by replay).** TF confirms the design and extends it:
  - (a) Trees: the replay walks `kept_rows`, which may be any root-to-leaf path.
  - (b) A one-launch commit for all 48 layers.
  - (c) Deferred replay folded into the next window's GDN kernel (Flash Next `FZ_GDN=2`).
  - (d) In-place scan when every row is accepted (#711).
  - S4 should be implemented with `kept_rows` (path indices), not a count n_keep. That makes it tree-ready at no extra
    cost.
- **K4 (verify width 9-16).** TF's whole tree gain rests on a flat width curve (§0.2). R9700's `qmm_rocm.cu` is the
  template: same vendor, wave32 WMMA, 16-output tiles, ≤32 rows per weight read. K4 should target bandwidth-bound
  verify up to 16 columns, not just 9-16 with today's slope.
- **K1 (MMVQ bandwidth).** TF's lesson (#527): at 1-2 rows an ALU/dot path wins; at ≥4 rows the matrix path holds BW.
  Their #527 hit an instruction-count ceiling (8×8 MMA with 7/8 empty at one row). For us the analogue is MMVQ (dp4a)
  for n ≤ 2 to 4 and WMMA tiles for n ≥ 4-5 [INFERENCE]. Verify always has ≥5 rows, so WMMA may beat MMVQ already at
  n=5 [INFERENCE].
- **K5 (prefill).** Nothing int8-RDNA3-specific is new. The WMMA prompt attention design (GQA tile sharing) matches
  our B4.
- **S2 (4-bit MTP draft).** DFlash2 at 4 bits: "a block costs about 7.5 ms against 12.5 at 8 bits, same acceptance"
  (Mac); GB10 drafting 19.5 → 9.6 ms a round at 4 bits, "same acceptance" (`v0.3.3`). This is direct evidence that a
  quantized drafter keeps acceptance.
- **S3 (MTP attention window).** DFlash2 is trained with a 2,048-key sliding window. GLM's DFlash2 reading only its
  window: 8 % faster at 52k (`CHANGELOG.md:350`). Neither is MTP evidence; the MTP layer was trained with full
  attention.
- **K2/K3.** TF also removes launches: ≈200 per drafted round (#100), 918 → 288 drafter kernels (`v0.3.3`), a/b and
  k/v fusion (#527). It hides CPU encode behind GPU execution (commit every 4 layers). This is the same direction as
  K2/K3; nothing new beyond device-side accept and commit.

---

## 7. Transfer to ONE 7900 XTX, llama.cpp HIP, Qwen3.8-27B UD-Q4_K_XL, MTP n=4

**Baseline** (NOTES.md:247): 36.38 ms/step, 86.4 tok/s at T=1, 3.14 tok/step. **1 ms/step ≈ 2.9 %.**

**Width model** (roadmap B1): step(k) ≈ 29.3 + 1.4·k ms, where k = verify columns (k=5 → 36.3 ✓).
- Matvec today ≈ 25 ms at ≈700 GB/s for 17.6 GB [INFERENCE: 17.6/0.7].
- Per extra MTP depth: verify +1.4 ms plus MTP step ≈1.17 ms (roadmap B3).
- Measured reach per depth (NOTES.md:199): depth 4 adds +0.26 tok, depth 5 adds +0.17 tok.

### 7.1 Ranked ideas

| # | Idea | Mechanism | TF's measured gain (hardware) | Why it does or doesn't apply here | Expected gain on our numbers | Effort | Risk | Where in llama.cpp | Overlap |
|---|---|---|---|---|---|---|---|---|---|
| **T1** | **Flat multi-row WMMA verify matmul** (port of `qmm_rocm.cu` ideas) | Persistent WMMA blocks, 16-output tiles, ≤16-32 rows per weight read, fixed split-K reduced by the last-arriving block in the same launch, stacked projections. Q4_K/Q5_K/Q6_K: int8 WMMA on q8_1 activations (our A6/q8_1 cache) instead of the bf16 `0x4300` trick | R9700: 12-row verify matmul 29 ms at ≈80 % of 639 GB/s; drafted 117-126 tok/s code vs 34 plain (#100) | Same vendor and wave32 WMMA. Compute per weight byte at 16 cols ≈ 57 FLOP/B vs 7900 XTX ≈128 FLOP/B peak, so still bandwidth-bound in principle [INFERENCE]. Our MMQ "cliff" at ≥9 cols (NOTES.md:159) shows the existing MMQ is not this kernel | At 80 % BW: 17.6 GB / 768 GB/s = 22.9 ms vs ≈25 ms → **−2.1 ms at k=5 (+6 %)**. Slope 1.4 → ≈0.3 ms/col [INFERENCE] makes k=9-16 cheap (below) | High (new kernel per quant type: Q4_K, Q5_K, Q6_K in UD; tile layout repack at load) | Med: numerics vs MMVQ (KLD gate) | `ggml/src/ggml-cuda/mmq.cuh` / new `mmwq` path chosen in `ggml_cuda_mul_mat` for 5 ≤ ncols ≤ 16 | **K1 + K4** (this is the K4 enabler) |
| **T2** | Deeper MTP chain once T1 lands | `allocate.zig` rule: maximise E[tok]/cost(k) with measured cost table | TF: MTP chain beat the DFlash2 tree on tokens (5.33 vs 4.55) but lost on 1.5-2.9 ms MTP steps | Our MTP step ≈1.17 ms; with a flat verify a depth costs ≈1.47 ms | n=5: 3.31 tok / 35.8 ms = 92.5 tok/s vs n=4 flat 91.5 (+1 %); n=6 ≈ 91.9 [INFERENCE]. Small: the head limits, as TF found (#113) | Low (host) | Low | `common/speculative.cpp`, server draft-n logic | K4, S2 (cheaper MTP step raises this) |
| **T3** | **GDN tree verify + tree attention** (side leaves on the MTP chain) | MTP top-2 at each depth: argmax continues the chain, 2nd-best becomes a leaf (no extra MTP calls). GDN kernel computes leaf from the parent state already in registers (`deltanet.metal:159-177` pattern; SLOTS ≤ 1). Commit = S4 replay of `kept_rows`. Tree KQ mask: leaf sees committed + chain ancestors | TF chain → tree: +21-34 % tok/s (Mac, sampled, Python 0.2), +28-30 % tokens offline. But that was DFlash2 (a whole top-16 lattice in one call), not MTP | MTP is sequential, so true branching needs extra MTP calls. Side leaves give a fraction of TF's gain. TF's "2/3 of misses have the truth among the 16 candidates" suggests a P(2nd = truth \| miss) of ≈0.3-0.4 [INFERENCE] | +4 cols, ≈+0.2 tok/step [INFERENCE]. Current slope: +5.6 ms → **−8 %**. After T1 (0.3 ms/col): +1.2 ms vs +6.4 % tok → **≈+3 %** | High: GDN kernel parent indices, `set_input_kq_mask` tree mask, KV placement and compaction of leaves, server accept loop | Med-high | `ggml-cuda/gated_delta_net.cu`, `src/llama-graph.cpp` (kq_mask), `llama-kv-cache.cpp`, `tools/server/server-context.cpp` | **S4** (replay with paths), **K4** (needs flat width) |
| **T4** | DFlash2 tree (EN/code-only mode) | As TF: 16 rows, best-first 15 nodes, 4 children, edge scores | Same as T3 row | Our DFlash2 ≈ MTP on EN chains, much worse on PL. A tree multiplies the EN advantage, not PL | After T1, EN code: 3.14 × 1.28 ≈ 4.0 tok / (37.6 − 4.7 + 3) ms ≈ 36 ms → **≈110 tok/s (+27 %)** [INFERENCE: DFlash2 draft ≈3 ms]. At current slope: 50 ms → 80 tok/s (**−8 %**). PL: loss. Needs language/task routing | Very high (DFlash2 tree selector + T3 infrastructure) | High | as T3 + DFlash2 drafter code | K4, S4 |
| **T5** | **Deferred / fused GDN replay** | Fold the previous verify's accepted rows into the committed state at the start of the next GDN kernel; no per-token states, no copy | Flash Next `FZ_GDN=2` with `fz_lane`: 166.4 → 174.5 tok/s (M5 Ultra, `244989a3`); qwen27 in-place chain +4 % (#711) | Same GDN geometry (nk 16, nv 48, dk 128). Strata estimated −576 MiB/step ≈ −0.6-0.7 ms | **+1.7-2 %** (Strata's estimate; TF's evidence supports the design). Tree-readiness comes free if keyed by `kept_rows` | High (memory-recurrent semantics) | Med | `gated_delta_net.cu`, `llama-memory-recurrent.cpp`, server spec checkpoint | **S4** (this is S4's best form) |
| **T6** | Geometric copy windows (n-gram drafts) once replay exists | A copy backed by ≥8 matching tokens replaces drafts; window 16 doubling to 128 while copies land whole | GB10: edits 144 → 489-501 tok/s (3.4×), code +13 % (#115); Mac edits 190 → 232 (#113) | Our roadmap rejected long n-gram verifies because of host checkpoints (`roadmap.md:244`). S4 removes them. A 128-col verify ≈ prefill ubatch cost ≈140-160 ms [INFERENCE from 554 ms/512] | Copy-heavy turns (quotes, code edits): several-fold. Chat/PL prose: ≈0 | Med (on top of A9 + S4) | Low (lossless) | `common/ngram-*`, `common/speculative.cpp`, server | S4, roadmap A9 |
| **T7** | Overlap the commit with the next draft | Issue the GDN/KV commit after the drafter's inputs; don't wait on it before the MTP draft graph | +3.7 % short, +12 % at 16k (M5 Max CLI, #713) | Our MTP draft depends on the last accepted hidden state, not on the GDN commit. HIP stream ordering needs the commit and draft graphs to be independent; that means T5/S4 first | ≈the commit time (with S4 replay ≈0.3-0.6 ms [INFERENCE]) → **+1-2 %** | Med | Low | server spec loop, graph scheduling | K3, S4 |
| **T8** | Merged-reduction GDN kernel micro-opts | One butterfly for q·S(i) and k·S(i+1); prefetch node i+1 inputs | Part of "8-35 % less" (CUDA 0.6.2) | Our GDN verify ≈1-1.5 ms/step [INFERENCE from R9700's 1.3 ms] | **−0.2-0.4 ms (+0.6-1.2 %)** [INFERENCE] | Low | Low | `gated_delta_net.cu` | K2, S4 |
| **T9** | Keyed (position-seeded) Gumbel sampling shared by target and MTP draft | Same `G(seed, pos, token)` in both samplers, so draft = argmax(log q/T + G) predicts the target's sample | R9700/GB10: sampled ≈ greedy tok/s with drafts (#100, recipe tables) | Our "probabilistic" spec sampling gave no gain (NOTES.md:175). Gumbel coupling is no better than rejection sampling for one token [INFERENCE], but it gives deterministic drafts and seeded reproducibility | 0-3 % [INFERENCE] | Low-med | Low | `common/sampling.cpp`, `common/speculative.cpp` | none |
| **T10** | Prefix draft vocab | First 98,304 ids + specials cover 99.64 % of committed tokens | — | We already use a 64k reduced head | ≈0 unless our 64k misses PL tokens: check coverage on a PL corpus | Low | Low | MTP head slicing | S1/S2 |
| **T11** | Decode attention occupancy at small n (split D=256 over 2 waves) | #712 | +2.2-2.6 % plain (M5 Max) | Our fattn-kvq handles ≤8 tokens × all GQA heads; at short ctx attention ≈ small share | ≤0.3 ms [INFERENCE] | Low-med | Low | `fattn-kvq` kernel | K2 |
| **T12** | hipcc kernel hygiene | 32-bit index math, register pressure, load order, no full unroll of pipelined loops | −6.6 % round at 61.5k, −10.5 % at 123k (R9700, #406) | Generic; apply to fattn-kvq and MMVQ instantiations | Unknown; audit item | Low | Low | our HIP kernels | K1, K2 |

### 7.2 Why trees fail today and pay after K4 (the decision arithmetic)

- **Today.** One verify column costs 1.4 ms = 3.9 % of the step. A 16-row tree adds 11 columns: +15.4 ms (+42 %). It
  would need ≥1.42× tokens a step. TF's best tree is 1.28× over chain (DFlash2, code, offline), so **a tree is a net
  loss at our slope.**
- **TF's slope.** M5 Ultra 0.155 ms/row of 21 ms (0.7 %/row); R9700 ≈0.3 ms/row of 37 ms (0.8 %/row). A 16-row tree
  costs 8-11 % for +28 % tokens.
- **After T1.** If our slope becomes ≈0.3 ms/col [INFERENCE], 16 cols cost +3.3 ms (+9 %). A DFlash2 tree pays on EN
  code (+15-27 %), MTP side-leaves ≈+3 %, and a deeper MTP chain ≈+1 %.
- **The ceiling is the drafter, not the verify.** TF's own conclusion: top-16 holds 6.5-7 tokens a round, and the
  scorer is ≤75 % right past depth 1. MTP self-distillation (B2) and S2 stay the main token-side levers.

### 7.3 Things not to transfer

- **Bit-exact row invariance.** It costs TF 20-29 % at one row on M5 (#527). We don't need drafted == serial bitwise;
  KLD gating is enough.
- **The FP8 prompt path.** gfx12 only.
- **Mac-specific items.** NAX/tensor-unit kernels and macOS 27 compile workarounds.
- **TF's own AMD engines.** The HIP Zig engine on gfx1100 runs at 11.7 tok/s; the Strix GGUF path at 25-38 tok/s
  drafted (#144). Both are below our llama.cpp, so there is no kernel to borrow except PR #100's RDNA4 WMMA design.

### 7.4 Checks the main agent should run before committing to T1/T3

1. Measure ROCm step at 5/8/12/16 columns: roadmap item 4 (`roadmap.md:271`). This confirms the 1.4 ms/col slope.
2. Prototype a Q4_K WMMA tile kernel for one shape (gate/up 17,408×5,120) at 1/5/8/16 cols and read GB/s.
   - Go if 16 cols ≥ 650 GB/s.
3. Offline only (no GPU): from MTP logs, measure how often the target token equals MTP's 2nd-best at the first
   rejected depth. This sizes T3: go if > 0.3.
4. Coverage of our 64k MTP vocab on Polish text (T10).
