# TensorFold: how the author measures, decides, refuses and abandons (methodology vs Strata)

Repo `~/research/TensorFold` (ashhart), HEAD `0efbd447` = v1.0.8 (2026-10-12), 1560 commits on main (1903 on all
branches), 32 tags. Paths are relative to the repo root at HEAD. Issues and PRs: `#N` =
https://github.com/ashhart/TensorFold/issues/N (PRs redirect). GitHub Discussions are disabled (API 410).
Companion file: `local://tensorfold-issues.md` (thread table). Strata baseline:
`/home/jaro/KERNEL/qwen-opt/research/strata/method.md`. This file covers only what is **new or different** from Strata.

## 0. TL;DR: the house rules in one screen

| Rule | Where written | What it means in practice |
|---|---|---|
| **Exactness contract, not a tolerance.** Drafted == `"draft": false`, resumed == fresh, concurrent == solo, prompt rows independent of chunking, cancel/partial-accept leave valid state | CONTRIBUTING.md:29-39; #286 "House rules"; #563 owner comment | Every speed PR must show token-hash equality on all four axes. A kernel whose bits depend on row count is refused even if faster (#527, #563, #437) |
| **No precision traded for speed, ever** ("a speed or memory feature can't change the reply") | #247 owner (int8 KV refused), #144 owner (Q8_1 prompt route refused), #457 owner (fp16 P·V refused), #100 owner (FP8 prompts made opt-in: code PPL +4.1% vs +0.03% bf16) | Stricter than Strata (which accepts a numerics change if KL vs floor is ok). Numerics changes need an issue first (CONTRIBUTING.md:6) |
| **Changed reduction order needs an FP64 reference per projection class, error no worse, worst column reported** | CONTRIBUTING.md:41-46 | An aggregate (mean, L2) "must not hide a worse column". #457: fp16 P·V was *closer* in aggregate L2 but made 1.8-5.8% of output words worse → rejected; bar is "no word gets worse" |
| **Near-tie policy is explicit and narrow** | CONTRIBUTING.md:45-46; tools/zig/qwen27_margins.py:13-26 | A token divergence vs the oracle counts as a near-tie only if the same two contenders win on both sides and both top-2 margins ≤ one BF16 spacing of the top logit; anything else is a "bug" |
| **No-slower gate against the last release, on every measured length** | revert `a5f518b4` ("do not meet the no-slower gate at both required lengths"); #670 owner ("Our rule is that prompt processing is no slower than the last release, so the grid stayed until…"); CHANGELOG.md:203 (27B excluded from 1.0.0 because "paired served decode and cold-prefill measurements remain slower than Python 0.6.6") | A feature that is exact and faster on average but slower at one length waits (the 2,048-grid removal waited until a kept state cost no extra prompt call, `3f4850c0`) |
| **Release gate = ABBA visits, cross-ratio rule, steadiness check** | tools/zig/gate_cells.py:17-18 (`order base cand cand base`, `margin 0.98`, `steady 0.95`); tools/zig/gate_judge.py:127-148 | "Slower only when every cross-visit ratio < 1 and the mean ratio < 0.98"; if an arm's own visits differ by >5% the cell gets **no speed verdict** ("rerun with the machine quiet", gate_judge.py:192-194) |
| **The gate is itself tested with planted faults** | tools/zig/gate_plant.py:1 ("A stand-in native binary that must fail the gate: the Python engine with one token changed, or slowed down") | Negative control for the harness, not only for the engine |
| **Oracle self-consistency first** | tools/zig/gate_judge.py:93-103 (`python==python`: same body → same reply in every visit, "or nothing is proven") | The reference must be deterministic before it can judge |
| **Measurements live in receipts, not in source** | CONTRIBUTING.md:79-80 (one-line comments ≤120 cols, files ≤600 lines, "Measurements and history belong in a receipt or recipe, not source comments"); tools/zig/lean_check.py:1-8 | Opposite of Strata (numbers and round IDs in code comments). Negatives live in PR/issue threads, CHANGELOG "Known issues", recipes |
| **Provenance of numbers is stated** | 14 owner comments say "We have not re-run them"/"those timings are yours" (e.g. #447, #406, #457, #456) | A third-party number is quoted as theirs until the owner reproduces it; when reproduced, the owner's own (often smaller) number is published (#268: contributor −5% → owner "about 3.5% faster at 90k in our run") |
| **Narrow a change to the hardware it was measured on** | #115 owner: wider copy windows "apply only to a GB10, where they were measured, because a wider window has to be paid for with a measured verify cost on every other card" | Defaults are per platform by evidence, not by extrapolation |
| **One path per model; concurrency is the default path, not a flag** | #520/#528/#568 closed ("We'd rather keep one path per model"); #606 owner | Duplicated engines are closed even when they are faster, and their result is carried to the canonical path with credit |

## 1. Exactness and precision methodology (what is new vs Strata)

Strata: speed changes bitwise behind a kill switch; numerics changes judged by teacher-forced KL against a run-twice floor.
TensorFold goes further in four ways.

1. **Contract axes, each with a tool.**
   - drafted == plain: `bench_concurrent.py --serial`, `tf-qwen27-dflash-run --compare-plain` (#711 receipt table).
   - concurrent == solo: `bench_concurrent.py --alone` (e.g. #592: 60/60 concurrent equal solo, 20/20 solo equal plain on an RTX 3090).
   - resumed == fresh: `tf-cuda-test resume` keeps states at rows 1, 7, 1500, 2047, 2048, 2049 and the last rows, refills
     every row with another prompt, restores, compares byte for byte; "Builds that restore half the rows, or skip the conv
     taps, fail it" (#670 owner).
   - chunk invariance: "dumps of every layer's rows, the final states, the MTP head's caches and the first token were
     byte-equal at 17 cut patterns on a GB10 and an RTX PRO 6000" (CHANGELOG.md:7; #670). The test is again checked to
     fail when "a local change makes the scan's clamp depend on the chunk's rows" (#670, plotarmordev).
   - row independence inside a kernel: a row in a batch of 2..32 gives the bytes it gives alone (#621 registry rule; #463
     "a row alone equals the same row in batches of 1 to 32; repeats and runs under concurrent load give identical bits").
2. **Oracles are layered.**
   - Previous engine as token oracle: tools/zig/qwen27_gate.py:1 ("Qwen27 token oracle (Python 0.6.6) and Zig comparison
     under the GPU wrapper; the two never coexist"); tools/zig/ab_nemotron.py (prints first divergence index, sha, and
     GPU ms per step/verify/draft per prompt).
   - Framework kernels bit for bit: tools/zig/check_mlx_ops.py:1 ("Check zig/kernels/metal/ops bit for bit against MLX
     0.32.3's own kernels, three ways"), check_torch_ops.py ("by raw bytes"), check_prefill_model.py (every layer state).
   - FP64 references for each projection class (CONTRIBUTING.md:42); logprob rows "within 2e-6 of a float64 log-softmax"
     (CHANGELOG.md:117).
   - Raw-bit failures stay visible while other cells continue (tools/zig/ops_compare.py:1).
3. **"Best possible" floor for precision comparisons.** In #457 the owner compared both arms against FP64 *and* against
   "rounding the exact answer to bf16" (1.645e-3..1.658e-3 rel-L2): both arms were within ~2% of that floor, so the
   aggregate gain was meaningless; the per-word count decided (fp16 arm made 1.8-5.8% of words worse) → no switch.
4. **Teacher-forced fidelity with full top-2 records.** tools/zig/qwen27_teacher_judge.py and qwen35_fidelity.py
   (teacher-forced NLL and top-token agreement vs stock mlx-lm "including its one-row/chunked variation"); the parked FP32
   family of #527 was characterised as "top-1 agreement 0.987, mean KL 1.8e-4 over 300 teacher-forced positions" and
   compared with mlx-lm's own chunked-vs-one-row band (0.975-0.985) before being parked.

Consequence for speed work: because every row must be row-count-independent, the author rejects the classic
"different kernel for 1 row vs N rows" trick. #527 found a +27% one-stream gain (M5 Ultra 38.7 → 47.3-49.5 tok/s)
from an FP32-ALU projection for 1-2 rows, but it breaks drafted==plain/concurrent==solo, so it is **parked on a fork
branch behind `TF_QWEN_QMV`**, with the decision written into the issue header ("Findings ... (parked)").

## 2. How performance is measured and reported

| Element | TensorFold practice | Source |
|---|---|---|
| Decode rate definition | `(completion tokens − 1) / (last token time − first token time)`, first sampled token excluded, from the stream | tools/bench_openai.py:1-4, :79-81 |
| Fixed public prompts, seeds | `fibonacci-raw` (code), `gpu-chat-no-think` (prose); one warm-up, then seeds 1234.. ; median of reps; all reps kept in JSON | tools/bench_openai.py:23-27, :100-108 |
| Receipt contents | commit/version, GPU, OS, checkpoint revision, runtime libs, request params; pass/fail/skip counts; unrun platforms explained | CONTRIBUTING.md:50-52 |
| Cold prefill | exact 2k/8k/32k/64k token arrays, request bodies, cached-token counts; `--prompt-cache-gib 0`; fresh KV each | CONTRIBUTING.md:66-68; docs/cache-benchmarks.md:36-44 |
| Evidence fields per request | `prompt_tokens`, `cached_tokens`, `cache_state` (cold/reused/unverified), `complete`, `token_sha`, `output_sha256` | docs/cache-benchmarks.md:3-18; tools/bench_evidence.py:27-45 |
| "Missing is not zero" | malformed/missing usage → `unverified`, never 0; missing token hashes make an exactness comparison unverified, never a pass | tools/bench_evidence.py:7-9, :47-54; #485, #432 |
| Small differences | "When a difference is only a few percent, alternate before/after runs" | CONTRIBUTING.md:70 |
| Per-step GPU breakdown | `ab_nemotron.py` prints GPU ms per step, verify, draft, rounds, accepted drafts; server `done` line has `rounds=`, `accepted=k/n`, `sha=` | tools/zig/ab_nemotron.py:44-49; #317 logs |
| Invariant for a speed A/B | "Same `sha`, same `rounds`, same `accepted`" ⇒ only time per round differs (also used by community: #406 "fixed greedy prompt gives identical draft acceptance across runs, so only kernel time differs") | #317, #406, #627 |
| Ranges, not single numbers | median of round medians with the range of the round medians, "Every 1.0.3 round is below every 1.0.2 round" | #627 |
| Per-kernel evidence | nsys `--cuda-graph-trace=node` per-launch medians by kernel name, paired by call site | #627 |
| Thermal / clocks | "alternating runs with the chip cooled in between" (#578); per-kernel bursts ≥30 ms, shipped kernel re-measured at the end of each line (#527) | #578, #527 |
| Robust startup cost tables | "each window width keeps its fastest of seven runs, outliers are timed again"; one RTX 3090 start had recorded 0.61 ms for a step that measures 0.34 | CHANGELOG.md:159 |
| Power as a variable | community receipt at 225 W vs 350 W on an RTX 3090: decode +15-20%, +29% at a 131k prompt; "linked from the CUDA recipe" | #592; CHANGELOG.md:120 |

## 3. Measurement pitfalls documented in this repo (new relative to Strata's list)

| # | Pitfall | Evidence | Lesson |
|---|---|---|---|
| 1 | **Graph recapture appears only after the cache slots fill** | #317: a "24% regression" (GB10, 66.6 → 50.8 tok/s) bounced between "not reproducible" and "real" for three days. Root cause (Arminova): from the 6th distinct prompt on `--parallel 5`, kept prompt ends fill all slots, the graph slot swaps, each request recaptures 17-18 graphs ≈ 1.25 s. Two-prompt tests never trigger it. Fix #337: 11.95 s → 6.09 s decode for requests 6-8, same `token_sha` | Benchmark with **more distinct prompts than slots**, log captures per request (`TF_GRAPH_LOG=1`, #615) |
| 2 | **Server rate vs client wall rate** | #317: server `tok/s` showed 0.6.4 faster (52.5 vs 48.0) while client wall-clock over 128 tokens was 30-40% worse; "my controlled A/B ... was not a valid instrument" (wall-based over the whole request vs (tokens−1)/(t_last−t_first)) | Report both; fixed-overhead per request hides in "settled" rates |
| 3 | **`seconds` included prefill** | #588: native `seconds` was the whole request, so a 128k prompt's 8.6 s prefill read as a collapsing decode; after fix: `seconds` 5.65 vs 39.19 on an 8,478-token prompt | Name the span every rate divides |
| 4 | **GPU clock ramp after CPU-side work** | #527: first tile-width pass said 164 → 120 µs on the down projection; "that was clock ramp: each variant was compiled on the CPU just before its burst" | Bursts ≥30 ms, re-measure the baseline last |
| 5 | **Cold page cache masquerading as decode** | #317: first request after start decodes 46 vs 53 tok/s warm (`prefill=0.20s` vs `0.02s`) with SSD-resident tables | Warm with a long read, not a one-token probe |
| 6 | **Nondeterminism only under GPU contention** | #490 (millaguie, gfx1150): same greedy request 10/10 equal idle, 5 different replies in 10 with a second process running matmuls → `softmax_stats` race (`attention.hip:138` reads `buf[0]` before a barrier); after fix 30/30 equal idle/loaded/drafted | Determinism test **under load**, not only idle |
| 7 | **Row-count-dependent library kernel choice changes bits** | #437: MLX bf16 matmul at 2,560→384 picks its kernel by row count; 24 of 240 sixteen-row windows differed, 0 of 1,920 at 8-15 rows; bisected to layer 39's router | Check verify-width rows vs one-row execution at every width |
| 8 | **Acceptance % misread when the engine adapts draft count** | #280: reporter said DFlash2 acceptance collapses on a 2-bit target; owner: 47/109 = 43% on 4-bit vs 31/60 = 52% on oQ2, the engine simply proposed fewer drafts (2.9 vs 7.8 rows/round) because rows were dearer | Look at rows/round and time/round, not acceptance % |
| 9 | **Draft-confidence product is miscalibrated** | #250: "the head's product overstates greedy acceptance about 2.5×"; uncalibrated cost stop at 0.06 over-drafts +6.5%/+10% ms/token; at 0.15 −3.9% on code, +0.9% prose; "a live round was ~5.6 ms longer than the table, which is host time the rule does not price" | Calibrate the chain product with per-depth kept/drafted counts; price host time |
| 10 | **Aggregate error hides per-element regressions** | #457: fp16 P·V closer to FP64 in rel-L2 but worse on 1.8-5.8% of words and on the worst column in 2/5 cells | Count words worse; report worst column (CONTRIBUTING.md:44) |
| 11 | **Sharing one kernel body slows the hot path** | #770: a first version sharing one body between one-stream and multi-stream kernels "slowed a lone stream by 1.6-1.9%"; kept two copies | Keep the hot single-row kernel's code untouched; `3f4850c0` uses a second instantiation so the no-keep scan has "no check in its loop" |
| 12 | **A kernel set swap as a control arm** | #627: 1.0.3's own glue kernels vs 1.0.2's captured set via `TENSORFOLD_CUDA_KERNELS`: −1.4% code / −3.0% prose decode on GB10; nsys per launch `add_moe_norm` 3.84 → 20.0 µs, `router` 8.86 → 17.92, `topk` 3.55 → 7.94; second GB10 on 1.0.7: B vs A +0.8% / +1.9%, "B led A in every round" | Whole-set swaps isolate a subsystem end-to-end; nsys pins which kernels |
| 13 | **Harness bugs that fake measurements** | #432: `prefill_cold.py` ignored `[DONE]` and SSE errors and substituted stream-close time for a missing first token; #485: absent token hashes compared equal → false exactness pass | Validate the harness with unit tests on malformed streams (docs/cache-benchmarks.md:56-64) |
| 14 | **Run-to-run drift bigger than the effect** | #527: split-K variants 21.7-22.9 vs 22.4-22.5 tok/s, "Run-to-run drift on that machine was about 7%, so there is no signal there"; #264: "Drafted decode moves by up to about 10% between runs of the same configuration" | Kernel-level A/B (per call, same bits) before end-to-end |

## 4. How hypotheses are formed and tested (the #527 pattern)

The clearest worked example is #527 (BobClawblaw, M5 Ultra, Qwen3.8-27B 4-bit):

1. **Step breakdown first** (`tf-qwen35-bench`): one-row step = 25 ms GPU (22.9 ms projections at ~660 GB/s of 1.2 TB/s,
   1.8 ms other kernels) + 0.2 ms CPU encode + **2.3 ms CPU after the command buffer completes** → that 2.3 ms was a
   151 MB/stream host memcpy of DeltaNet states (`Cache.commit`); moving it to the GPU gave 36.0-36.3 → 38.5-38.9 tok/s
   one stream, 106-110 → 131-138 at eight (#528). jkuepker's alternative (#568) removed the copy entirely: 8-stream
   89 → 142 tok/s, bits unchanged.
2. **Ruled out by measurement, each bit-identical:** tile width (`S` ∈ {8,16,32}, `NT` ∈ {1,2,4,8} on every 27B shape:
   shipped within a few percent everywhere), three loop restructurings (prefetch, two groups/iteration, adjacent chunks:
   65.5-65.9 µs vs 65.7 shipped on the down projection).
3. **Speed-of-light ablations with kernels "whose output is wrong by design":** (a) same access pattern, no math →
   1,080 GB/s (contiguous 1,160) vs 700-770 real; (b) scales/biases replaced by constants → −3%; (c) MMA replaced by a
   scalar fma on the same registers → 65.9 → 31.6 µs. Conclusion: tensor-unit-bound (8-row time = 1-row time), not
   memory-bound, so no reordering can move it.
4. **Build the alternative, measure, characterise numerics, then park it** (FP32 family: +27% at 1 stream, parity at 2,
   half at 8; top-1 0.987, KL 1.8e-4) — the decision text explains why the contract forbids it.
5. Owner closes with a cross-check from the other side (prompt chunks: "Every bit-identical reshaping ... lost to the
   shipped kernel") and a standing invitation: "If a kernel beats `tf_lane_reg` with the same bytes, a new issue with the
   A/B is very welcome."

Other recurring patterns:
- **Measure the opportunity on real traffic before building**: #447 (plotarmordev) logged every `prefill_matmul` call
  shape and row count during cold prompts, timed all 12 tiles on those shapes at 15 row counts (1,236 cases, every tile
  bit-equal), then built a per-shape table: +4.3% at 1k, +1.0% at 8-16k, "nowhere near the 1.4-1.5x gap ... which lies
  elsewhere".
- **Measured cost models drive policy**: draft depth on Nemotron CUDA "stops where the next verify row would cost more time
  than its draft is expected to save. Window and level costs are measured at startup on each GPU" (+6-7%, CHANGELOG.md:215-219,
  `bcb8f01c`, from #136); GLM timing draft windows at load instead of a fixed table: prose 106.1 → 116.5 tok/s
  (CHANGELOG.md:79).
- **Cheap drafts in one window beat dependent second opinions**: MTP as a second opinion on DFlash2 added 3-12% accepted
  tokens on chat but "each MTP score is a dependent call before the verify, so net tok/s fell 6-9%" (#113 owner).

## 5. Decisions, refusals and abandonment: where negative results go

TensorFold has only **2 reverts in 1560 commits** (`b72b8c3c`, `a5f518b4`); Strata had 4. Negatives are recorded as:

| Channel | Example |
|---|---|
| Revert with the gate it failed | `a5f518b4`: "the corrected policy preserves output and cache state, but the paired late-fork measurements do not meet the no-slower gate at both required lengths" |
| Release exclusion with reason | CHANGELOG.md:203 (27B out of 1.0.0: equality passes, paired decode/prefill slower than Python 0.6.6) |
| "Known issues" with measured regressions | CHANGELOG.md:140-143 (GLM prose −4%: 106 vs 111 tok/s, "slower on five of six prose prompts"; 27B sampled requests plain at ~19 tok/s) |
| Issue retitled/closed with a Findings header and a parked branch | #527 ("FP32 family (parked)"), branch link, flag name, decision paragraph |
| Precision refusals with the measured reason | #247 int8 KV (−6% at 90k, −13% at 242k rounds, refused: changes the reply); #144 Q8_1 prompt route (6/16 replies differ); #457 fp16 P·V; #100 FP8 prompts opt-in (PPL +4.1% vs +0.03%) |
| Toolchain refusals | #406 Mojo kernels (R9700 −6.6%/−10.5% ms/round at 61.5k/123k, bit-identical): "keeping the HIP backend to one kernel language for now"; the tuning (32-bit index math, register pressure, load order) is to be backported to HIP |
| Frozen-line closes | 158 PRs carry an owner "frozen" comment (Python 0.6.6 frozen, #286); each says where the idea lives on the native engine and credits the author |
| "Exact but no faster" lists kept in PR text | #502 owner: "the shapes you list as exact but no faster will save the next person a day" |

The owner's reply template is consistent: restate the contributor's numbers with hardware, say whether they were
re-run ("We have not re-run them" ×14 owner comments), state the rule that applies, and name the place where the work
continues.

## 6. Community, commits, CI

- **Volume**: 552 PRs (97 MERGED, 351 CLOSED, 104 OPEN) from 112 non-owner authors; 235 issues from 121 authors; 335 of
  787 threads have a "receipt" in the body. 144 threads state AI assistance (Claude/Claude Code) explicitly.
- **Merging community PRs**: the owner rebases, re-authors to GitHub noreply addresses (personal emails and AI
  co-author trailers are removed: CONTRIBUTING.md:94-96; #286), then adds an empty-tree merge of the PR's head so GitHub
  shows it merged: `58bd07ef` "Merge #681's head (484508f94): the same change ... This keeps the PR's own head commit in the
  history, with no change to the tree." (35 such merges). Re-authored PRs show as closed (#463, #588 owner notes).
- **Provenance scan**: before landing HIP kernels the owner ran a 6-line-window copy scan (exact and with names/numbers
  blanked) against MLX, mlx-lm, vLLM, llama.cpp, FlashInfer, SGLang, aiter, ExLlamaV3 (8,186 windows for #617/#621) and
  asked about two SPDX lines from vLLM in `gdn_prefill.hip` (#617 owner).
- **No-GPU verification of GPU PRs**: without an AMD card, the owner builds the HIP test roots against stub code
  objects and checks "a planted type error in each fails as it should" (#617, #621); device receipts come from contributors.
- **CI** is host-only: `zig build test` and `zig fmt --check` on PRs (.github/workflows/no-gpu.yml,
  zig-fmt.yml); "Neither host result substitutes for an actual model/device gate" (CONTRIBUTING.md:20-25). Golden server
  corpus with an explicit list of the ten still-known differences (zig/tests/server/golden_check.zig:1-26).
- **Commit style**: subject = declarative sentence of the new behaviour, area-prefixed, with evidence in parentheses,
  avg 77.6 chars, e.g. `e0df8e31` "Nemotron prompt experts read token rows and write down rows through the pair order (no
  row copies, same bits)"; `22f41e22` "exlr8 dense: a row a simdgroup for 1-4 rows, the same sums with four times the
  simdgroups" (body: router 0.146 → 0.069 ms on M5 Max at 1 row, byte-equal check named). Bodies state mechanism, why bits
  are unchanged, the check that proves it, and per-op numbers (`e0df8e31`: 66 MB copy + 66 MB read/write dropped per layer
  per 2,048-row chunk, byte-equal on M5 Max and M3 Ultra). Phrase counts across all messages: "same bits/byte-identical/..."
  100, "refuse" 233, "tok/s" 121, "float64/FP64" 31, "median" 13, "KL" 4 (Strata: KL 36 — TensorFold rarely needs KL
  because it rejects numerics changes).
- **CHANGELOG entries are measurement paragraphs**: before/after with hardware and "every reply equals ..." per entry
  (CHANGELOG.md:7-54), plus "Known issues".

## 7. Point-by-point comparison with Strata

| Aspect | Strata (method.md) | TensorFold | New for us? |
|---|---|---|---|
| Correctness bar for speed work | bitwise + kill switch (`STRATA_X=0`) | bitwise **on four contract axes** (drafted/plain, resumed/fresh, concurrent/solo, chunk cuts), each with a tool; no kill switches needed because nothing lossy ships | Yes: drafted==plain and chunk-invariance as standing tests |
| Numerics changes | allowed if teacher-forced KL ≤ incumbent, vs a run-twice floor | essentially refused; when a reduction order changes: per-projection FP64 reference, worst column, "no word gets worse", BF16-rounded exact answer as best-possible floor | Yes: op-level FP64 + worst-column + floor |
| Tie handling | not formalised | near-tie only if same two contenders and both margins ≤ 1 BF16 spacing (qwen27_margins.py) | Yes |
| A/B protocol | interleaved pairs, medians, "k/n pairs faster", ≥3% to change a default | ABBA visits; slower iff all cross ratios < 1 and mean < 0.98; no verdict if an arm's visits spread >5% | Partly (the steadiness rule and cross-ratio rule are new) |
| Default changes | ≥3% win, per-arch tables, opt-in otherwise | no-slower than last release at every measured length; narrow to measured hardware | Similar spirit, stricter no-regression |
| Harness validation | positive control (PF_FUSED), A/A | planted-fault binary must fail the gate; oracle self-consistency; harness unit tests on malformed streams | Yes: planted faults |
| Where numbers live | code comments, DETAILS.md, bench/results folders | receipts in PRs/issues, recipes, CHANGELOG; source comments are one line, no measurements | Different (ours is closer to Strata) |
| Negative results | opt-in flags + comments ("named fast and is not faster") | closed threads with Findings headers, parked branches, Known issues, refusals; almost no reverts | Different channel, same intent |
| Hypothesis formation | byte census, per-window time breakdown | step breakdown incl. **host time after GPU completion**; speed-of-light ablation kernels (no-math, constant scales, fma-for-MMA) | Yes: ablation kernels |
| Regression handling | paired runs + list of bitwise toggles | whole-subsystem swap (kernel set via env) + per-launch nsys; "same sha/rounds/accepted" invariant | Yes: set-swap control arm |
| Cost models | DraftPolicy EMA, PCIe-share formula | startup-measured window/level costs, fastest of 7 with outlier re-timing, per build cache | Partly |
| Community | owner ports by hand | rebase + re-author + "Merge #N's head" + copy scan + credits in CHANGELOG | Not relevant to us |

## 8. Methodology lessons to adopt for our llama.cpp fork workflow

Our tools: `greedy_check.sh` (greedy outputs of two builds), `spec_sweep.sh` (5-6 prompts × 2-3 seeds, median t/s and
ms/step), `long_ctx_bench`, rocprofv3 traces, llama-perplexity KLD (batch 6 vs 512 floor ~0.0036-0.0098).
Our step: ~35.7 ms, verify ~31 ms, ~972 kernels/verify, ~3.2 ms gaps; 1 ms/step ≈ +2.9% t/s at 3.16 tok/step.

| # | Lesson (TensorFold source) | Concrete change for us | Cost | Why it matters for K1-K5/S1-S4 |
|---|---|---|---|---|
| L1 | **ABBA with a cross-ratio verdict and a steadiness gate** (gate_judge.py:127-148; gate_cells.py:17-18) | In `spec_sweep.sh`, run A B B A (or A B B A A B) builds, compute ms/step per visit; declare "slower" only if every cross ratio < 1 and mean < 0.98 (or "faster" symmetrically); if A's two visits differ by >2% (our ms/step repeat is ~0.3 ms ≈ 0.8%, NOTES.md:182) print "no verdict" | 1 h scripting | K1/K2 gains will be 1-3% (0.35-1 ms/step); the rule prevents fake wins |
| L2 | **Invariant check before trusting a speed A/B**: same `sha`, same rounds, same accepted (#317, #406, #627) | Have `spec_sweep` print token hash, n_steps and accepted drafts per prompt per arm; if they differ between arms, report ms/step only (already our practice, NOTES.md:184) and flag t/s as non-comparable | trivial | Kernel fusions that are not bitwise (A4-style) change text → t/s confounded |
| L3 | **Determinism under GPU contention** (#490) | `greedy_check.sh --stress`: same build, same prompt 10× idle and 10× with a concurrent HIP load (e.g. `llama-bench` or a rocBLAS GEMM loop in another process); any difference = race | 30 min | Our new kernels (fattn-kvq WMMA, fused rms/rope/FWHT, multi-col MMVQ with epilogues, one-graph MTP) are exactly where TensorFold contributors found a missing `__syncthreads` |
| L4 | **drafted == plain as a bug detector, with a near-tie classifier** (CONTRIBUTING.md:35,45-46; qwen27_margins.py) | Run greedy with MTP off vs on (n=4); at the first divergence, dump top-2 logits from both paths; classify near-tie if same two contenders and both margins ≤ 1 bf16 spacing (or a q8_1-scale epsilon we pick), else "bug". [INFERENCE] llama.cpp verify (5 tokens: multi-col MMVQ, kvq FA) and single-token decode use different kernels, so bit-equality is not expected; the classifier separates numeric drift from spec-path bugs (wrong KV/GDN rollback, position errors) | 2-3 h | S4 (GDN rollback by replay) and K4 (verify width 9-16) change the spec path; this catches state bugs that KLD on prefill cannot see |
| L5 | **Chunk-invariance / resume check** (#670, CHANGELOG.md:7) | For prompt cache + checkpoints: compare greedy output of (a) cold prompt, (b) same prompt resumed from a cached prefix at several cut rows (1, 511, 512, 513, n−1 with `-ub 512`) | 1-2 h | K5 prefill changes and S4 state replay must keep resumed == fresh up to our tolerance |
| L6 | **Speed-of-light ablation kernels** (#527) | For K1: build three throwaway MMVQ variants under an env flag: (a) load weights/scales in the same pattern, no dp4a, write a dummy sum; (b) dp4a on constant data with real loads removed; (c) scales replaced by constants. Compare µs per call on the 64-layer shapes with L2/Infinity-Cache-cold rotation (Strata lesson). Tells whether ~700 GB/s is pattern-, latency- or ALU-bound before tuning | 0.5 day | K1: avoids weeks of reorderings that cannot move a non-memory bound (#527 tried three) |
| L7 | **Host time after GPU completion is part of the step** (#527/#528: 2.3 ms of a 27.5 ms step) | In rocprofv3 traces measure the gap between the last kernel of verify and the first kernel of the next draft, and between draft and verify; attribute to sampling, KV/GDN bookkeeping, graph launch | 1 h | K3 host overhead; our 3.2 ms kernel-boundary gaps are inside the graph, the inter-graph host gap is a separate bucket |
| L8 | **Clock-ramp discipline for microbenchmarks** (#527) | Per-kernel bursts ≥30 ms, re-time the baseline kernel at the end of each sweep line; at our 285 W cap check that sclk is steady during the sweep | trivial | K1/K2 microbench tables |
| L9 | **Whole-set swap as a control arm + per-kernel medians** (#627) | Keep env switches that restore the previous kernel set (e.g. old MMVQ path, old FA path) for one release; on a regression run A/B with the switch, then rocprofv3 `--kernel-trace` per-kernel median by name for both builds | small | K2 fusion audit; quick bisect of a 1-3% regression |
| L10 | **Harness self-tests and planted faults** (gate_plant.py; #432, #485) | Unit-test `spec_sweep.py` parsing on truncated/malformed server output; once per harness change, run a planted build (one token changed via a debug env, or `usleep(300)` per step) and require the harness to report "different" / "slower" | 1 h | Prevents a broken harness from blessing K-items |
| L11 | **Robust cost tables: fastest of 7, re-time outliers** (CHANGELOG.md:159) | When measuring per-width verify cost for K4 (9-16 tokens), take min of ≥7 timed runs per width after warm-up and re-time outliers; store per build | trivial | K4 decisions depend on the verify cost slope; one inflated sample flips the choice (0.61 vs 0.34 ms in TensorFold's case) |
| L12 | **Op-level FP64 reference with worst-column error** for non-bitwise kernel changes (CONTRIBUTING.md:41-44; #457) | For S1 (q8_1 clamp), S2 (4-bit MTP draft) and any reduction-order change: a `test-backend-ops`-style FP64 reference per projection class (attn qkv, GDN in, ffn up/gate/down, lm_head), report max/mean/worst-column error and "% elements worse than incumbent" in addition to KLD | 0.5 day | KLD averages hide column-level damage; TensorFold rejected a change that was better on average |
| L13 | **Distinct prompts > cache slots; log graph captures** (#317, #615) | `spec_sweep` uses ≥ (slots+2) distinct prompts in sequence; log HIP graph instantiations/updates per request ([INFERENCE] llama.cpp's CUDA/HIP graph code re-captures when node params change; count them) | 1 h | K3: a recapture costs ms per request and is invisible with 2-3 prompts |
| L14 | **Report both server rate and client wall time** (#317, #588) | `spec_sweep` already uses ms/step; add client wall time for 128-token replies (agent-style short answers) | trivial | Fixed per-request costs (graph capture, MTP warm-up, prompt-cache lookup) only show in short replies |
| L15 | **Write negative results where the next attempt will look** | Keep NOTES.md "measured, no gain" rows with hardware, N, and the reason; for parked branches, record branch + env flag + one-line decision (the #527 header format) | habit | We already list p_min, DFlash, -bs, hipBLASLt negatives; add the decision rule used |
| L16 | **Power as an explicit A/B variable** (#592) | One-time ms/step at 285 W vs 303 W vs 330 W, ABBA (NOTES.md:123-136 plan) | 1 h | Gains measured at a cap may not transfer; TensorFold's 3090 receipt shows +15-20% decode from 225 → 350 W |

### Technical observations from the threads that bear on our plan (details belong to sibling reports)

| Observation (TensorFold, hardware) | Mechanism | Fit for us / arithmetic | Overlap |
|---|---|---|---|
| DeltaNet state publish copy costs ~288 MiB r+w per token on the 27B (48 layers × 3 MiB fp32/slot); removing it is bit-identical (#711 open; #568: 8 streams 89 → 142 tok/s on M5 Max; #528: one stream 36 → 38.7 on M5 Ultra) | scan writes the final state in place when the slot does not move; partial accept copies back only the kept row's state | [INFERENCE] if our GDN kernel writes its output state to a scratch tensor that is then copied into the cache (ggml cpy) each verify: 288 MiB at ~800 GB/s ≈ 0.36 ms/step ≈ +1.0% t/s; if per-draft-position snapshots are also written (5 positions × 144 MiB) ≈ 0.9 ms ≈ +2.6%. Check in a rocprofv3 trace for `cpy`/`copy` kernels sized 3 MiB × 48 | S4 (GDN rollback by replay): TensorFold #490 HIP engine already does "a draft window keeps recurrence inputs, not a state copy per row, and the keep replays them: the same bits for about 2% of the memory" |
| A state kept inside a chunk: the scan stores its fp32 state at marked rows from registers as it passes (`3f4850c0`) | second kernel instantiation with ≤16 store rows; the no-store instantiation untouched | Same idea gives S4 per-position GDN states for the accepted prefix at zero extra launches | S4 |
| Collectives/graph lesson: one captured graph per sequence and freeing graphs with the sequence; 161 graphs after minutes of traffic cost 7-10% until restart (#597) | graph cache hygiene | [INFERENCE] check that llama.cpp HIP graph cache does not grow with distinct verify/draft shapes | K3 |
| Verify-window cost is priced per hardware; wider windows only where measured (#115: GB10 12-row verify 71.7 ms vs 142.4 at 128 rows; copy token 1.1 vs 6.0 ms) | per-width cost table | K4 must be decided from our own per-width verify cost (L11) | K4 |
| Prompt-lookup/copy drafts in the same verify window as the model drafter: Flash Next file rewrite 92.4 → 341.0 tok/s (#319), 27B edits 3.4x on one Spark (#113) | copy window starts at 16 rows, doubles while copies land whole, halves after a break | Our roadmap A9 (n-gram + MTP hybrid) | A9 / spec |
| MTP as a "second opinion" on another drafter: +3-12% accepted, −6-9% net tok/s (#113) | dependent call before verify | Don't chain MTP scoring after DFlash on our box | spec |

## 9. Sources read

CONTRIBUTING.md, RUNBOOK.md, docs/cache-benchmarks.md, packaging/VALIDATION.md, zig/gate.json, tools/zig_gate.py,
tools/bench_evidence.py, tools/bench_openai.py, tools/zig/{ab_nemotron, gate_judge, gate_cells, gate_plant, qwen27_margins,
qwen27_teacher_judge, lean_check, check_*_ops headers}.py, zig/tests/server/golden_check.zig, build.zig:227-246,
.github/workflows/*.yml, CHANGELOG.md:1-219, git log statistics, ~100 threads dumped in full (see the issues file).
