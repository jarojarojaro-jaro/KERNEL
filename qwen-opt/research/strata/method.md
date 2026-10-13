# Strata: how the author measures, decides and fails (methodology + negative results)

Repo: ~/research/Strata (paths below are relative to its root). 1892 commits 2026-09-24..2026-10-12, 49 tags, HEAD `a0116b27`.
Niko1221 wrote 1150 commits; the rest are community PRs, mostly ported by hand by the owner. The owner force-pushed a
history cleanup once (owner comment on #832), so hashes are post-rewrite.

## 0. TL;DR, the author's operating rules

- **Every claim is a measurement, with what it was measured on.** AGENTS.md:22-23 ("measured numbers with what they were measured on, no claims without a measurement"), AGENTS.md:30-35 (a new feature is opt-in, the default path stays byte-identical to the last release; change a default only where you measured it faster; compare against a same-day run).
- **Speed and numerics are tested separately.** A speed change should be bitwise ("same tokens") and sit behind a kill switch (`STRATA_X=0`). A numerics change is judged by teacher-forced KL against the default, next to a run-to-run KL floor.
- **A/B means interleaved whole-engine pairs on one day, alternating order, medians, plus a count of pairs faster** (e.g. "+15.6%, 5/5"). It is never a comparison with an old number.
- **Defaults follow a threshold.** A setting has to win by ≥3% (MMVQ_IL table emit rule, calibrate.py MIN_GAIN, DraftPolicy margin 0.03). If it loses on any measured box, it stays opt-in.
- **Negative results are kept, not deleted.** Very few reverts (4 in history). A failed idea usually stays as an opt-in flag with its numbers in DETAILS.md, as a checked-in bench ("measured negative"), or as a code comment that says why it does not pay.
- **Everything is per-card and per-platform.** The same switch can be +6% on one box and -21% on another (STRATA_ADAPT_OVERLAP). The answer is arch tables and opt-in flags, not one global default.

## 1. Pre-public development: oracle first, numbered rounds, a ledger

The first public commit `01529aaa` (2026-09-24) is already 50,165 lines in 219 files, and it includes the paper and `bench/results/2026-09-24-final/estimates.md`. The earlier history survives only in code comments:
- **Numbered iteration rounds.** 48 comments cite them: "round 2" (nsys table), 36, 169, 186, 189, 193-199, 209, 218, 282, 309, 320, 330-331. Examples: src/kernels/cuda/gr.cu:190-206, src/kernels/cuda/router_top10.cu:28, src/program/generate.cpp:12839.
- **A decision ledger** `Memory/LEDGER.md`, with entries L1..L123+ (include/strata/kernels/s_gemv.hpp:53; src/program/generate.cpp:339,3179,5706; src/core/layer.cpp:173,368). There are also plan IDs (P0.T2, P1.S4, P2.S2, P2.T10, "Phase 3", "plan v0.3 P7", review items R2.6/R4.2h/G1), named gates ("GATE C1", generate.cpp:3179), and stage labels ("stream A, round 2", src/core/arch_defaults.cpp:39). bench_vs_llama.py says "stream 1402-h ... The caller holds the machine's GPU lock". [INFERENCE] This looks like a multi-agent / AI-assisted workflow: parallel work streams, a shared GPU lock, a ledger, reviews.
- **Oracle before engine.** `ref/load.py` (P1.S4) does FP32 dequant through gguf-py plus an independent Q2_0 decoder, "so a bug in one cannot hide behind the other". tools/canonical_xcheck.py checks in Python that the repacked form round-trips bit-exactly before any C++ exists ("the oracle before the engine ... faster to iterate").
- **Phases: correctness first, then speed.** src/kernels/cuda/s2_gemv_q8.cu:1-15: "This is the CORRECTNESS version, not the fast one ... the phase's rule is the simplest correct kernel first, and a dp4a version whose numerics are wrong would be indistinguishable from a fast one." The P2.S2 tolerance is 1e-3 for FP16 paths. The ground truth is llama.cpp, not the float64 Python transcription (gr.cu:195-197: the FP64 accumulation was replaced by FP32 "toward the oracle").
- **Residual bisection ladder.** `--dump-residual` writes one residual per layer per position, in the format `llama-debug --tensor-filter l_last` prints, "so the first layer whose sum diverges is the layer that holds the bug" (src/program/generate.cpp:396-402).
- **Fault-injection and A/B arms built into the engine options** (generate.cpp:390-392: `ple_delay_us` fault injection, `ple_sync_submit` "A/B arm"). The constants carry their measurement: "64 left the SSD half idle (32K: 303 -> 189 ms)".

## 2. Measurement tooling inventory

| Tool | What it does | Notes |
|---|---|---|
| `tools/ab_engine.py` (139 lines) | A/B of builds or env sets on one config: restarts the server per arm, alternates arm order by round, warm-up, then the same greedy fixed requests (3 short chats + 1 long word-list prompt), and reports medians over rounds | Header: "Decode numbers move run to run ... so compare medians over rounds". A V100 reporter found its 3 short chats were below his box's noise floor (COMMUNITY_BENCHMARKS.md:36-37) |
| `tools/strata_bench.py` (1017) / BENCH.bat / bench.sh | Fixed community suite: chat, 4K/16K (and `--long` 32K) prompts, a 5-turn agent session (cache reuse), `--clients N`; 3 runs each, median and range; `--compare OLD NEW` | Every prompt carries a unique tag so the cache never helps. Thinking off. Scrubs private data (COMMUNITY_BENCHMARKS.md:65-110) |
| `tools/calibrate.py` | Per-PC tuning of `--pcie-frac`, `--spec-min-p`, pool workers and adaptive-tier knobs through per-request `strata_tune` keys (no restart where possible) | `MIN_GAIN = 0.03` (calibrate.py:37), "kept only when it beats the default by more than 3% in an interleaved re-measurement"; sweeps every value in every round (d1990da1) |
| `bench/bench_vs_llama.py` | Head-to-head with llama.cpp over both OpenAI servers, same GGUF and sampler; rounds alternate engine order; peak VRAM by polling; RSS by process tree | Result: bench/results/2026-10-06-llamacpp-0.6.0 (RTX 3060: Strata 41.6 vs llama.cpp tuned 9.1 tok/s decode at 4K) |
| `src/kernels/mmvq_il_parity.cpp` `--bench --emit-table` | Bitwise check of every shape and rows choice, then timing, then a ready-to-paste per-arch table | The bench "cycles through enough copies of the weights to miss the L2 cache, as a layer's call does" (mmvq_il_parity.cpp:11); rep 0 warms and rep 1 times (l.154) |
| ~100 `*_parity` CTest targets (CMakeLists.txt) | Kernel-level bitwise or tolerance checks (gdn_parity T=1..8 memcmp, gr_parity, kv_q4/q8, qsa, rope, router_top10, sampler, spec_verify_parity, verify_batch_parity...) | spec_verify_parity.cpp:1-10: GPU probabilistic acceptance against a host reference, every row, 2..8-row windows, 3 vocab sizes |
| `STRATA_DECODE_TIMING=1` / `STRATA_VERIFY_PROFILE=1` | One log line per request: windows, tokens/window, verify split into GPU wait / CPU pool (plan, actq, jobs) / stage, plus commit and draft. A second line with per-stage GPU ms/window | DETAILS.md:299-306: the event profile "slows the decode a little: use it to compare, not to measure speed" |
| `STRATA_LOOKAHEAD_STATS=1`, `tools/replay_cache_policy.py` | Measurement only: scores a predictor (recall/precision of next-layer experts) against real routing; replays routing traces through the cache policy offline | DETAILS.md:308-313. The predictor is measured before a prefetcher is built |
| `STRATA_LOGPOS=<path>` | Teacher-forced log-prob of every prompt token; the input for KL/perplexity checks | generate.cpp:10803 |
| `STRATA_PREFILL_TIMING=1` | Prefill phases on the GPU timeline, e.g. "wait copy" | Used to locate a whole difference in one phase (AMD_HIP.md:219-223) |
| `tools/hip/tune_hipblaslt` | Per (arch, hipBLASLt version) GEMM table. Every candidate is correctness-gated (rel-L2 ≤1e-4, max-abs ≤1e-2, padding canary); the engine refuses a mismatched table | bench/results/2026-10-04-community-rx7900xtx-hipblaslt-100500/README.md |

- **Result folders** (`bench/results/<date>-<label>/`, 132 dirs) hold a README with hardware, software, exact command, method and limitations, plus per-run JSON/CSV, the driver scripts, and often a `*-control.json` (same-day control arm, e.g. `2026-10-01-0.1.31-release/control-0.1.30.json`, `runs-0.1.40.1-control.json`). `cpu-tests-review-negative-control.txt` (2026-10-03-windows-groups) is a negative control for a Windows affinity test: it shows that the test detects lost CPU-group eligibility ("error 122").
- **Prompt corpus for routing profiles**: `bench/profile_corpus.json` has 45 prompts tagged by domain (code, ...). It feeds `tools/collect_profile_traces.py` → `tools/make_profile_mix.py`. Leave-one-out held 71%/84% hit, and the result was +5..+64% decode (mean +21%) on 12 held-out prompts (INTEL.md:827-830).

## 3. The A/B protocol and decision rules (concrete)

- **Interleaved pairs, fresh engine per side, warmed, greedy, fixed prompts, medians, and "pairs faster k/n".** Stated as policy in DETAILS.md:1693-1695. Typical N: 5 rounds (route tail skip, DETAILS.md:1651), 6 pairs (opt-in list, DETAILS.md:1709-1731), 10 pairs (MMVQ_IL_TABLE.md:28-29, GR_DOWN_MAX4 `46d01366`), 12 pairs (SPEC_GUMBEL `5e4de5c7`, deferred register `16642363`).
- **Release gate** (v0.1.42 notes): "Final build against 0.1.41, default settings, 5 interleaved pairs, medians". Run on 7+ machines (3060, P100, A4000 1x/2x, R9700 two boxes, Arc B70, A750). Also 10-prompt identity runs (`mg_norepeat` 10/10) and 4,096/20,000-token residual dumps (`exact_pp`) with the answer-changing defaults switched off (DETAILS.md:1617-1618). "A few percent on a shared box or from the draft acceptance rate is noise; no machine got consistently slower." The 0.1.41 gate caught STRATA_STAGE_PIN corrupting IQ3_S decode ("48 tokens of id 0", src/core/expert_source.cpp:1233-1236), so that switch shipped opt-in.
- **The emit rule (MMVQ_IL_TABLE.md:31-32; mmvq_il_parity.cpp:193-220).** Per (quant type, ncols, row-count class): take the rows-per-warp choice whose **worst** ratio over the class's measured shapes is best, and only if that worst ratio is < 0.97, else 0 (plain kernel). Classes that disagree give 0; an unmeasured class copies its lower neighbour. The shared sm_86/sm_120 table is non-zero only where "the worse of the two cards still gains 3%" (MMVQ_IL_TABLE.md:13).
- **A/A controls and noise floors are measured and reported.** Example: `--aux-cpus` (DETAILS.md:1773-1781): the same config restarted twice moved 1.009/1.005 solo and 0.999/1.024 two-stream, and an A/A gave 0.985/0.990, against an effect of 0.888/0.917. A 7900 XTX community report used a stall-exclusion rule: a cell below 40% of the arm's best is flagged (hipblaslt-100500 README, Method). The box drift is stated, e.g. decode "inside this machine's 2.3% run drift" (7984688e; AMD_HIP.md:566).
- **Numerics changes need KL with a floor and a scale reference** (DETAILS.md:1631-1649). Teacher-forced KL of the real decode path (28 prompts, 6 languages, ~6,000 tokens, real verify windows with MTP drafts) gave 0.0058/0.0032 mean. The floor is the same engine run twice (0.0006-0.0007); the scale is Q2_0 vs IQ3_XXS (0.10). Task checks (HumanEval 82, 30 reasoning) are reported, with the caveat that "a change of 3 reasoning tasks is noise".
- **Gate for a fast-numerics kernel: its KL vs the FP16 reference must be ≤ the incumbent's.** STRATA_PF_FUSED stayed opt-in because IQ3_XXS pooled KL was 0.00388 vs MMQ 0.00340, even with +15-19% prompt speed (AMD_HIP.md:368; v0.1.42 notes).
- **A regression report gets a paired-run request plus a bisect list of bitwise kill switches.** For #1373 the owner asked for 5-6 alternating pairs in one session, A=defaults vs B=`STRATA_MMVQ_IL=0`, then one toggle at a time from a list of 7 (`STRATA_MULTI_BLOCK_ARGMAX=0`, `STRATA_ONE_TOKEN_COMMIT=0`, `STRATA_NO_MULTI_GR=1`, `STRATA_NO_BATCH_KV_STEP=1`, `STRATA_NO_NORM_ROPE=1`, ...). "All are bitwise-identical switches, so the text must not change." Meanwhile the default was flipped to opt-in (`f7610d2c`) and then the flip was reverted (`668072aa`) once the report turned out to be a measurement artifact.
- **Microbenchmarks never select a configuration alone.** "Microkernel speedups alone were not sufficient to select a configuration" (docs/AMD_HIP_PERFORMANCE.md:144-145). A770 protocol (docs/A770_SPEED_SPEC.md:403-438): save A/B configs and binary hashes, record RAM/swap/contention, separate startup, JIT and warm runs, ≥3 warmed repetitions with A/B/A/B, keep the full JSON, and "accept an optimization only if it passes correctness and wins outside ordinary run-to-run noise ... Record rejected experiments too."

## 4. Measurement pitfalls the project documented (with the evidence)

1. **Cold vs warm engine.** #1373 (Scorp1o117): the reported -20% for 0.1.40.2 came from restarting the engine per data point and measuring after 3 requests, so it measured the adaptive cache's warm-up ramp. Properly measured (one load, 10 decodes in-process, back-to-back engines) 0.1.40.2 was +12.9% (127.5 → 144.0 tok/s). The same 0.1.39 binary had swung 135 → 74.8-126.9 tok/s in one evening, which made the two-day-old baseline meaningless.
2. **Unique prompt markers change the generated text, and with it the MTP acceptance and decode speed.** #832 (Zauberio): a claimed +2.8/+3.5% for STRATA_GR_DOWN_MAX4 vanished under the stricter design: identical prompt in both arms of a pair, varied across pairs, ON/OFF ratio taken within the pair, median of paired ratios. Paired medians were 1.026/1.008/1.021 (IQ3_S) and 1.004/0.997/1.000 (Q2_0), with per-pair scatter ±10%. A **positive control** (STRATA_PF_FUSED, 1.023, 4/4 positive) showed the harness's resolution is ~2-3%. This matches the owner's own 0.97/0.97/0.99 (`46d01366`).
3. **The noise floor can exceed the effect.** src/kernels/cuda/s2_gemv_fast.cu:19-24: ~20% run-to-run variance within one config while `verify` held 97% of six cores: "further micro-optimisation ... should wait for a quiet machine rather than produce more numbers that cannot be distinguished from noise."
4. **Op count is not time.** src/kernels/cuda/router_top10.cu:20-34: a one-thread router "justified" by 5,120 ops took 3.39 ms/layer, which is 56% of a 289 ms token. It was invisible to the parity test because that test runs the kernel once.
5. **Stale conclusions get re-tested when the regime changes.** gr.cu:173-215: four accumulators showed no change while FP64 throughput was the limit (39.86 vs 39.80 ms/token). After FP32 (5.07 → 2.38 ms/token, round 282) the kernel became memory-bound, so occupancy began to matter: one block per row, 53 vs 6.7 warps/SM. "The old result is not wrong; it is about a different kernel." "A hint that does not change the timing is a claim that is not true" (an unused `#pragma unroll` was removed).
6. **Profiler overhead and broken profilers.** A770 (A770_SPEED_SPEC.md:716-761): both in-engine profilers failed in eager mode, and host-clocked stage numbers are inflated, so "the relative split is the point".
7. **Hit rate is not speed.** The faster run (102 tok/s) had the *lower* cache hit rate than the 13.7 tok/s run; the real cause was 0 MiB free VRAM (DETAILS.md:623-626). A higher `--pcie-frac` raises the hit rate even when decode gets slower (DETAILS.md:294-296).
8. **The OS counter that looks like the right instrument is not.** Windows `GPU Process Memory\Shared Usage` did not separate 13.7 from 102 tok/s runs (DETAILS.md:628-631).
9. **Fixture traps in parity tests:** NaN-unsafe comparisons (`if (rel > worst)` never fires on NaN; round 197 printed a perfect score for an all-NaN fixture, src/kernels/ple_parity.cpp:40-50). The wrong denominator in relative error reads like a wrong kernel (rounds 169/189, rope_parity.cpp:128-136, s2_gemv_q8_parity.cpp:106-118). A saturated-softmax fixture "cannot see its own trap" (qsa_parity.cpp:950-958). "A threshold that passes 62 of 64 by luck is not a threshold" (s2_gemv_q8_parity.cpp:114-117).
10. **Library/version confounds.** A 7900 XTX 128K prefill measured 926 tok/s on the ROCm 10.2 nightly because no hipBLASLt table matched version 100500, so it fell back to hipBLAS. A matching table gave 1687 (+82%) with decode unchanged (bench/results/2026-10-04-community-rx7900xtx-hipblaslt-100500/README.md).

## 5. How hypotheses are formed, and whether they held

- **Byte census first** (paper Table 1). Routed experts are 34 GB stored but 0.66 GB read per token. Dense parts are 3.5 GB per token and stay in VRAM. The n-gram table is 28.8 GB stored and ≤23 KB read per token, so it goes to SSD. Design follows bytes moved per token.
- **Time breakdown per verify window** (paper Table 5, 4K, RTX 5070 + 7600 AVX-512). Q2_0: round 34.3 ms = GPU 14.6 + CPU experts 13.4 + draft 2.0 + other 4.3; 3.23 tokens/round, 0.72 VRAM hit, CPU at 41 GB/s. Conclusions drawn from it: "balanced ... speeding up only one side cannot help by more than about a third" (Finding 1); i-quants are arithmetic-bound on the CPU (~5 GB/s/core) (F7); VRAM size matters more than GPU speed (~700 experts per GB).
  - **Later confirmation:** the next big CPU-side levers matched the model. Route tail skip gave +12.9..+15.6% where hit rate was 75-90% and ±0 at 99.7% hit. The CPU-speed-derived PCIe share gave +30% on a 3060 whose CPU outran its link (DETAILS.md:1651-1689; v0.1.42 notes). The PCIe share formula `L/(L+1.85R)` is an explicit cost model "fit to three machines, so it lands within a step of each machine's best, not on it" (DETAILS.md:1675-1680).
- **Estimates for unmeasured cards** (paper Table 6 / DETAILS.md:329-345, "±20%"): the GPU part was scaled by bandwidth, the CPU part by the hit-rate curve. One later check: a single RTX 3090 with IQ3_XXS on v0.1.26 and an AVX2-only EPYC (bench/results/2026-09-29-rtx3090-epyc-milan/matrix.md) decoded 89.2 / 90.6 / 79.3 tok/s at 4K/32K/128K against estimates of ~103 / ~89 / ~71. That is within ±20% (different CPU and engine, so [INFERENCE] it is only loosely comparable). The prompt estimates went stale: DETAILS.md:333-334 says they predate 0.1.13, which roughly doubled prompt speed. No formal reconciliation of Table 6 was found.
- **MTP gain estimate**: the original design said 1.1-1.7×; measured 1.6-1.8× (plain 47-57 → 82-92 tok/s at 4K), less than all-in-VRAM engines' 2.5-3× "because every extra token in the window routes to its own CPU experts" (paper F2).
- **Paper §7 "what could make it faster" and what happened:**
  - conversation state across requests: done on day 2 (`42810ee8`, community).
  - "overlap across layers, not within one" + next-layer prediction: measured first (LOOKAHEAD_STATS, `e247c611`). The prefetch slots ("Foresight", #1348) then measured net-negative everywhere (below).
  - fused 8-bit grouped prompt kernel: 0.1.13 MMQ about doubled prompt speed; 0.1.36 fused int8 tensor-core kernels added +16-22% (DETAILS.md:22-24, 317-327).
  - sampling with rejection: STRATA_SPEC_PROB (`33356f72`, `589ccc47`).
  - T-MAC-style LUT kernels: no evidence they were attempted.
- **A770 campaign as a worked example of revising a hypothesis** (docs/A770_SPEED_SPEC.md:535-761, community `27528ca5`):
  1. "GPU-reach wait 123 of 174 ms ⇒ the GPU is the bottleneck, target the IQ expert kernels."
  2. The expert kernel measured standalone was only ~24 ms/window, so it is not the bottleneck.
  3. 123+36+8 = 167 looks like serial GPU+CPU, which led to the overlap hypothesis ("do not start it blind").
  4. gputop showed the GPU ~20% busy, which "overturns the ms_wait = GPU compute reading".
  5. A stage profile showed CPU-pool flag waits plus copy/combine at ~87% of the window. Kernel work packages closed; the lever is architectural.
  Each step names its evidence and what would refute it.

## 6. Negative results catalog (what / numbers / hardware / why per author)

### Decode kernels (matvec, GEMV, MMVQ)
| What | Result | HW | Why (author) / source |
|---|---|---|---|
| BF16 GEMV on Turing tensor cores (mma m16n8k8), 3 variants + k-split sweep | 1.3-2.2× **slower** on every real shape | sm_75 | Warp kernel already bandwidth-bound (374 GB/s); "a single-token GEMV wastes 15/16 of the m16 MMA tile". Bench checked in "so this does not have to be measured twice" (`43cd140e`, Hozák Martin) |
| XMX/joint_matrix (int8 DPAS) expert dots for 1-6 rows | 1.4× and 2-3× slower; one variant hung the GPU | Arc B70 | "At 1-6 rows the grid decode and the packed-B layout cost more than the DPAS saves" (INTEL.md:427-431) |
| Stage activation `x` in shared memory for GEMV | worse in every paired comparison (59-76 vs 64-87 G w/s) | RTX 5070 | sync + copy cost more than L1/L2 hits of an already-resident 5 KB vector (src/kernels/cuda/s2_gemv_fast.cu:10-14) |
| Constant-memory code table instead of shifts/masks | neutral | RTX 5070 | s2_gemv_fast.cu:16-18 |
| IQ grid staging in single-matrix MMVQ | 10-20% slower at 3-8 columns | RTX 5070 | the grouped expert kernels keep staging (they gain) (`39841946`; iq_kernels.cu:1964) |
| Q6_K multi-col instances with more registers | 10-50% slower at 3 columns | fork measurement | register pressure (src/kernels/cuda/native_mmvq.cu:1465). **Same failure class as our fused gate+up multi-col (-8%)** |
| QSA decode attention NC=4 | slower on V100 | sm_70 | "the registers cost occupancy" (qsa_decode_attn.cu:416) |
| `STRATA_GR_DOWN_MAX4` (MAX_T=4 specialized GR down) | B/A 0.97/0.97/0.99 over 10 pairs; a community +2.8% was retracted | RTX 5070 / 5070 Ti | `46d01366`, #832 |
| MMVQ_IL (interleaved q8_1 for 2-4 cols) on a 2-GPU split | reported -15%, retracted (cold-measurement artifact) | 4080S+5070Ti | #1373. Default stayed on (single-card +4.2% sm_86, +1.3-2.2% sm_120) |
| SIMD16 sub-group MMVQ / wide Q6_K | micro up to 1.45× (IQ4_XS) but 10-25% slower on large K-quants; **no engine gain** beyond noise | Arc B70 | INTEL.md:442-447 |
| GR read: 4 independent accumulators | no change (39.86 vs 39.80 ms/token) | RTX 5070 | FP64 throughput was the limit; re-test asked for after FP32 (gr.cu:173-215) |
| Single-row `resident_plan` variant | "one row: no gain, the old kernel stays" | - | verify_kernels.cu:1004 |
| `--spec-split` / splitting the verify window into 2 token groups to overlap CPU/GPU | **-7%** (85.8 vs 91.8 tok/s, 4K); A770 9.9-10.3 vs 11.7-12.6 | RTX 5070; A770 | dense weights read twice, fewer shared experts per group (paper F5; A770_SPEED_SPEC.md:254-258) |

### Launch count, fusion, streams, host overhead
| What | Result | HW | Why / source |
|---|---|---|---|
| `STRATA_FUSE_CONVAB` (conv + a/b in one launch) | "measured slower", opt-in | gfx12 | `a9917a55` (subject only) |
| Fused per-head RMSNorm+RoPE on HIP | kept off on HIP | gfx1151 | rope_parity check 6 fails (~7% of elements differ) (owner comment, #783) |
| `STRATA_LFUSE` (-4 launches per MoE layer, KV appends in one launch) | gfx1151 small win: 51.29 → 50.31 ms/window, 54.33 → 55.12 tok/s; Arc: "not worth it" | gfx1151; B70 | `b08cf3e1`; INTEL.md:831-833 |
| Shared-expert second stream (`STRATA_SH_STREAM`) | Linux 2x6900XT: off costs 5-13%; Windows RX 6800: on 12-22% slower; 4x R9700: off 13-45% faster; gfx1151 on +1.8/+6.7% | various AMD | platform-dependent. Off on HIP by default except the gfx1151 table (AMD_HIP.md:213-217; STRIX_HALO.md:98,166-171) |
| MTP drafter side stream on HIP | R9700 lost prompt speed, so not created on HIP (except gfx103x: big prompt gain in "wait copy") | R9700 / RX 6800 | AMD_HIP.md:219-226 (#1240) |
| Gating debug dump/host scan behind flags | measured **slower** | Blackwell, Windows | "a large blocking readback is also what flushes the pipeline for the sampler that follows" (generate.cpp:12836-12841, round 36) |
| `STRATA_ADAPT_OVERLAP` (copies land during the next window) | A4000 +5.5..+8.3% (6/6), P100 +4.4%; RTX 5070 Win -2.6%; **RTX 5090 Laptop -21%** (84.6 vs 106.6) | various | default reverted to opt-in everywhere (`661ff293`, #2010; DETAILS.md:1722-1733) |
| Host callbacks for the overlap's "landed" signal | ~7 ms/window on a 20-core 3060 box | RTX 3060 | pool workers occupy every CPU; replaced by a 4-byte stream-ordered copy into pinned memory (DETAILS.md:1739-1741) |
| Deferred per-layer arena registration | decode 4-10% slower, identical output | RTX 5070 Win | `16642363`; expert_source.cpp:4533-4534 |
| `STRATA_ADAPT_LAG=2` | P100 +3.5% (6/6), 5070 +0.2% (4/6), 3060 -1.3% (0/6) | - | stays opt-in (DETAILS.md:1720-1721) |
| Stager threads sleep (Windows) | 8K prompt -1.2% (10 pairs); laptop -5-6% | 5070 / 4070 laptop | stays spinning on Windows (prefill.cpp:128; DETAILS.md:1560) |
| Miss-first / hit-first group order; chains over several queues | -3% / -7%; no gain (one compute engine) | Arc B70 | INTEL.md:832-833 |
| PDL, mixer graph branches, batched Q4_0 query, PLE post-ops | all opt-in. PDL is sm_90+ only; HIP keeps ordinary launches | - | `2e4ddf6e` (#904); a Linux stall with NVML kept DF_BRANCH off |

### Speculative decoding
| What | Result | HW | Why / source |
|---|---|---|---|
| Taking the suffix/lookup draft whenever longer than the MTP's | lost 2-8% on ordinary text | RTX 5070 | a long lookup window costs much more to verify. Replaced by a learned tokens-per-ms policy (include/strata/spec/draft_policy.hpp:1-14) |
| Chaining every 3+-token lookup match after the MTP chain | +6.4% tokens/step for +7% window time (49% of chained drafts accepted) | Strix Halo, UD-IQ4_XS | a verify row costs ~9 ms of a ~61 ms window, so the policy keeps only chained tokens that pay (`5e0c43ba`) |
| Coupled draft sampling + Gumbel-max | acceptance 62.1 → 66.9 → 68.0%, **decode 43.4 / 43.3 / 42.8, within noise** | RTX 3060, T=1.0 | acceptance gain does not reach speed (`5e4de5c7`; DETAILS.md:126) |
| `--spec` other than 4 | spec 2: 33.6, spec 6: 35-37 vs 41.6-43.5 tok/s; "--spec above 4" flat on a 7900 XTX report | Arc B70; RX 7900 XTX | INTEL.md:293-294; AMD_HIP.md:241-242 |
| `--spec-min-p` (draft confidence floor) | 0.3-0.7 within noise; 0.0 clearly worse (10.4 vs 12.0 tok/s; acceptance 52% vs 68%); 0.7: 93% acceptance but fewer drafts → 11.6 | Arc B70; A770 | INTEL.md:294; A770_SPEED_SPEC.md:243-250. **Consistent with our p_min gating "no gain": the optimum is a flat plateau** |
| MTP prompt pass in groups of 8 (E-8) | reverted 19 min after landing; superseded 1.5 h later by E-9 (batched through prompt kernels: 0.9 s → 0.07 s of a 32K prompt) | - | `45d857c7` → `86c904ca` → `a402eefd`. [INFERENCE] superseded, not refuted |
| Penalized requests after exact per-row penalties | 1-11% slower | - | the draft layer guesses without penalties, so more rejections (DETAILS.md:1252-1254) |
| Route tail skip when ≥90% experts cached | acceptance 70.1 → 68.2%, decode -1-2% | V100 32GB | "the skip costs more draft acceptance than it saves" (DETAILS.md:1626-1628). **Changing numerics costs MTP acceptance** |

### Memory / tiers / KV / prefill
| What | Result | HW | Why / source |
|---|---|---|---|
| Foresight swap slots (predicted experts in VRAM slots) | 0.91-1.00× (0/6 to 4/6 pairs) | 3060, P100, 5070, 2x3090 | the smaller cache costs more than the slots return (DETAILS.md:1703-1711) |
| Expert rebalance (shrink VRAM cache to use the idle CPU) | neutral at 3200 slots, worse at 2400 (9.6 vs 10.9 tok/s) | A770 | A770_SPEED_SPEC.md:573-595 |
| K/V block cache in VRAM (`--kv-resident` sweep) | 34.05 / 34.06 / 34.21 / 34.92 tok/s for 4K-64K cells; "worth nothing per GiB" → split planner not built | P100 | docs/RESEARCH_RUNS.md:54-60 |
| KV q4_0 + Hadamard | ~4% faster at 128K but perplexity +8-12% on long documents; 8-bit stays default | RTX 5070 | DETAILS.md:86-89. **Relevant: we run q4_0 KV at 200K** |
| GDN chunked (WY) prompt recurrence forced on small GPUs | 0.73× (3060, 28 SMs), 0.87× (5070, 48 SMs), prompt time unchanged | - | needs ≥128 SMs in one wave (DETAILS.md:1697-1702) |
| Smaller prefill ring for a bigger chunk | 4K prompts 1-17% slower; Coder -12% at 32K | RTX 5070 | `56501a38` |
| 32 stager threads + 128-deep ring when pages are already cached | 4-7× slower | big-RAM box | memory copies, not page faults (DETAILS.md:1562) |
| hipBLASLt table on R9700 (1.4.1) | 0.98-1.76× per GEMM → e2e 0-3%, within noise; not shipped | R9700 | plain hipBLAS already close (AMD_HIP.md:301-304). Table rows where hipBLAS won (0.90-0.95×) were dropped in pairs (AMD_HIP.md:620-624) |
| Static 16K chunks, expanded FP16 expert tuning, 192-slot ring | "did not offer a consistent end-to-end win" | RX 7900 XTX | docs/AMD_HIP_PERFORMANCE.md:142-145 |
| Prefill CPU share | every share slower on RX 7900 GRE + 5700X3D (#1282); no gain on older GPUs | AMD; Pascal | DETAILS.md:1570; OLDER_GPUS.md:156 |
| AVX2 two-block Q2_0 unpack | bit-exact but -2.6..-4.7% (1 token), -3..-5% (2 tokens) | Ryzen 9 3900X | reverted (`a88904e5`) |
| AVX-512 gather for IQ3 grids | 3-5% slower than scalar | - | src/kernels/cpu/iq_avx512.cpp:31 |
| `STRATA_IQ_MT_MIN=1` (reproducible CPU rounding) | IQ3_S 1-3% slower → opt-in | - | `31ad9627` |
| QSA top-k dispatch by active blocks on CUDA | 64K prompts 1-3% slower → HIP-only | RTX 5070 | `01ec3ac9` |
| Batch MTP on a layer split with all experts in VRAM | -21.9% (0/5 pairs) | 2x R9700 | DETAILS.md:1256 |
| A slower 3rd card / helper GPU | slower (68/90 tok/s) | 5080+3090+2080Ti | "every extra card costs its own round per window" (MULTI_GPU.md:210,242-243) |
| Vision encoder on GPU | text 2-8% slower | - | less VRAM for the expert cache (DETAILS.md:1537-1539) |

## 7. Recurring commit-message patterns

- Stats: 1151/1892 commits have a body; average subject 94 chars; 146 owner subjects run past 150 chars. Across all messages: issue refs in 857, "tok/s" in 186, "opt-in" in 180, a bitwise/identical phrase in 142, a `STRATA_*=0` kill-switch in 105, "pairs" in 55, KL in 36; only 4 reverts.
- **Subject template:** `<area>: <plain-words change> (<switch>; <measured effect on hardware>) (#issue)`. Examples:
  - `a88904e5` "Revert #257 (AVX2 two-block Q2_0 unpack): bit-exact but not faster on an AVX2-only CPU (Ryzen 9 3900X: gate/up -2.6..-4.7% ...)"
  - `661ff293` "STRATA_ADAPT_OVERLAP: opt-in on every backend (RTX 5090 Laptop ...: 84.6 vs 106.6 tok/s decode median ..., 5 generations of 256 tokens from one build)"
  - `39841946` "#646: the single-matrix mmvq does not stage the IQ grids (10-20% slower on the RTX 5070 at 3-8 columns)"
- **Body usually states, in this order:**
  1. the mechanism in one paragraph;
  2. the equivalence claim ("bitwise the multi-column kernel's", "Same tokens", "Output is unchanged (the policy only picks which drafts to verify)");
  3. the kill switch (`STRATA_MMVQ_IL=0 keeps native_mmvq's kernels`);
  4. the test that proves it ("mmvq_il_parity checks every case bitwise for rows 1/2/4");
  5. numbers with hardware, model, N pairs, medians, before → after;
  6. what was left out ("with the IQ3_S and Q8_0 parts and the 5-8 column widths left out");
  7. credits ("Ported by hand from Eddoursul's fork (738e166, b67a291)", Co-authored-by).
  Examples: `ffac97f7`, `b08cf3e1`, `be7889ed`, `5e0c43ba`, `48d2e6ca`.
- **Unchanged parts are stated explicitly:** "Unchanged: the copy path, the gate predicates and the tokens" (`661ff293`). AGENTS.md:29 asks for "what it changes and what it leaves alone".
- **Work-package IDs in subjects:** C-1..C-4 (prompt), D-1..D-5 (prompt kernels), E-2..E-9 (decode/draft), F-1/F-2, F7, CS-T (file tier), "fork F4", "#783 PR-a..PR-k". Big external PRs are split into per-subsystem commits, each with its own kill switch (owner comment on #783).
- **Release notes** (e.g. v0.1.42) use sections Faster / Fixes / New opt-ins / Answers can differ (with KL tables) / Not fixed. Every claim has a machine table with "pairs faster".

## 8. Transfer candidates (for our dense Qwen3.8-27B, one RX 7900 XTX gfx1100, llama.cpp fork)

### 8a. Methodology practices to adopt
| Practice | Strata mechanism / evidence | Why for us |
|---|---|---|
| **Interleaved paired A/B with in-pair ratios, medians, and "k/n pairs faster"** | ab_engine.py alternating order; DETAILS.md:1693-1695; release gate of 5 pairs × 7 machines | Our K1-K5 gains will be 1-5%. Single runs on ROCm cannot resolve that (the 7900 XTX box drift was 2.3%, 7984688e) |
| **Same prompt in both arms; greedy; vary prompts across pairs, not within** | #832: a unique-marker design produced a fake +2.8% via MTP acceptance changes | Our tok/s is dominated by MTP acceptance (88-90 t/s at n=4). Any arm that changes the generated text confounds speed. Use greedy and verify identical token ids per pair |
| **Positive control + A/A control → state the harness resolution** | #832 (PF_FUSED 1.023, 4/4); aux-cpus A/A 0.985/0.990 | It tells us whether "HIP env knobs = noise" means no effect or harness too coarse. Run an A/A and a known +2% change (e.g. n=3 vs n=4) first |
| **Warm in-process repeats; never compare to old numbers** | #1373: 0.1.39 binary swung 135 → 75-127 tok/s in an evening; cold-ramp artifact | Our 88-90 t/s baseline should be re-measured in-session for every A/B |
| **Per-verify-window time breakdown as a standard log line** | STRATA_DECODE_TIMING: windows, tokens/window, verify split, commit, draft; an events-based stage profile "to compare, not to measure" | We already know ~31 ms verify, ~3.2 ms gaps and ~970 kernels. Put this in a permanent per-request line (draft ms, verify ms, gap ms, accepted/window) so every A/B reports where the ms moved |
| **Microbenchmarks L2-cold** | mmvq_il_parity cycles through enough weight copies to miss L2 (mmvq_il_parity.cpp:11) | **The 7900 XTX has a 96 MB Infinity Cache**: a single-matrix MMVQ microbench re-reading the same <96 MB weights will overstate bandwidth. K1 tuning needs weight-copy rotation larger than 96 MB |
| **3% emit rule on the worst shape; per-arch tables; never pick from a microbench alone** | MMVQ_IL_TABLE.md:31-32; AMD_HIP_PERFORMANCE.md:144 | Pins K1 decisions (rows/warp, cols, block size per quant and row class) to a reproducible rule, then confirm end to end |
| **Every speed change bitwise + kill switch; numerics changes gated by KL vs floor** | STRATA_*=0 switches; KL table with run-twice floor and Q2_0-vs-IQ3 scale (DETAILS.md:1631-1649) | Fusions (K2) should produce identical tokens; if not, report teacher-forced KL with a floor. Self-distilled MTP heads need the same acceptance + KL accounting |
| **Bitwise parity harness per fused kernel, all variants, NaN-safe, correct denominators** | ~100 parity targets; ple_parity.cpp:40-50; rope_parity.cpp:128-136 | Our existing fusions (norm-rope, GDN prologue, MMVQ epilogue) should get memcmp tests vs the unfused path. Strata found fused norm+RoPE failing parity on gfx1151 (~7% elements) |
| **Measure the predictor/opportunity before building** | LOOKAHEAD_STATS, replay_cache_policy.py; Foresight built anyway and lost | For K4 (verify width 9-16), log the accepted-length distribution and the per-width verify cost first, then compute the expected gain offline (as DraftPolicy does) |
| **Keep negatives as code: opt-in flags, checked-in benches, "named fast and is not faster" comments** | s2_gemv_fast.cu:1-5; `43cd140e` | Our gate+up fused MMVQ (-8%) and p_min/confidence-length results should stay as documented opt-ins with numbers, so they are not re-tried |
| **Ledger of rounds: each constant cites its measurement** | LEDGER L1-L123; comments with before → after | Cheap and audit-friendly for a long-running fork |
| **A regression response playbook** | owner reply on #1373: paired runs, then a list of bitwise toggles one at a time | A ready list of our kill switches makes bisecting a slowdown a matter of runs, not code reading |

### 8b. Technical ideas worth testing (mechanism · Strata gain/HW · fit for us)
| Idea | Strata mechanism & measured gain | Why / why not for us |
|---|---|---|
| **Cost-aware draft policy (tokens per ms, learned online)** | DraftPolicy: EMA of round cost per window size, plus committed tokens per MTP window, plus lookup acceptance by match-length bucket; pick the max E/cost with a 3% margin; re-probe stale sizes every 300 rounds (`48d2e6ca`). Prompt lookup became "Code edits +6-11%, other text unchanged" (RTX 5070, `bbe8944e`) | Our confidence-product draft length failed because it ignores **cost per width**. A measured-cost policy is different and could size K4 widths. Lookup/suffix drafting chained after MTP pays on agentic/code edits ("+6.4% tokens for +7% time" if taken unconditionally). Our dense verify rows are cheaper than MoE rows (each MoE row adds its own experts), so longer chains should pay more often for us [INFERENCE] |
| **Limit the MTP head's attention window (`--mtp-window`)** | MTP attends to the last 32,768 cells by default (paper §3.7); `--mtp-window 8192`: 64K output +3.5%, 32K -0.4% (gfx1151, STRIX_HALO.md:126-127) | We drop 90 → 78 t/s at 94K ctx. Part of that is draft-side attention over the full context. A windowed MTP KV is cheap to try; acceptance must be watched |
| **Interleaved q8_1 activation copy for 2-4(-8) col MMVQ + per-arch rows table** | Warp decodes each weight block once, applies it to all tokens, bitwise equal to multi-col: +4.2% sm_86, +1.3-2.2% sm_120 decode; V100 Q5_K head 2560×248,320 at 3 cols 1094 → 821 us, Q6_K 2560×12,288 68.9 → 47.9 us (bench/results/2026-10-07-v100-decode-kernels) | We already do multi-col. The transferable parts are the **interleaved activation layout** and the rows-per-warp table (1/2/4/0) emitted per row class by the 3% rule, which fits K1 |
| **Aligned loads for Q6_K (210-byte blocks)** | Two aligned 16-byte loads + shift instead of misaligned 16-byte loads: Q6_K 2560→10240 at 1/2/4/6 cols 160/145/141/101 → 493/432/331/273 GB/s; head 150 → 407 GB/s; decode 44.9 → 54 tok/s (Arc B70, INTEL.md:448-456) | Q4_K_XL / Q4_K_M carry Q6_K tensors (often output/ffn_down) [INFERENCE: check the GGUF]. llama.cpp's Q6_K vec-dot uses 2-byte-aligned int loads. Worth an L2-cold check of per-quant GB/s vs our ~700 GB/s average on gfx1100 |
| **Multi-token (exact-T) kernels to cut launches** | #783: batched K/V + indexer append, multi-token RMSNorm/pre/post ops, multi-token router, exact-T template specializations: verify window 15.10 → 13.07 ms (-13.4%), +9-10% tok/s (2x RTX 3090, all resident), 0-ULP across 25 parity tests. LFUSE -4 launches/layer on gfx1151: 51.29 → 50.31 ms/window | Directly K2/K3: at ~3.3 us per boundary × ~970 kernels, every per-token loop collapsed into one launch saves (T-1)×3.3 us per layer. Exact-T templates (compile-time T=1..8) also remove loop bounds |
| **Avoid second streams on AMD by default; measure per platform** | Shared-expert fork: -12..-22% (RX 6800 Win), off 13-45% faster (4x R9700), +5-13% (2x6900XT Linux), +1.8/+6.7% (gfx1151) | If our MTP graph or verify graph uses parallel branches on gfx1100, A/B a serialized variant |
| **hipBLASLt table keyed to (gfx1100, lib version)** | gfx1100 on ROCm 10.0 (hipBLASLt 100401): dense prefill GEMM fallback fixed, 1.7K 682 → 1,038 (+52%), 6.5K 857 → 1,524 (+78%) (RX 7900 XTX, `7984688e`); R9700: within noise | Our env-knob test was noise because our prefill is ~90% MMQ int8 WMMA. It only matters for the FP16/BF16 GEMMs left (if any). Low priority; check that no shape silently falls back |
| **KV precision caution** | q4_0+Hadamard: +4% speed but perplexity +8-12% on long docs; int8 default; K8V4 hybrid (keys 8-bit, values rotated 4-bit) | We run q4_0 KV at 200K. Consider K8V4-style asymmetric KV or a long-doc KL/ppl check vs q8_0 before K5 work [INFERENCE: depends on our FA kernel support] |
| **Draft-vocab subset built to a 99% corpus-coverage target** | tools/draft_vocab.py `--corpus --coverage 0.99`; French 0.51 → 0.60 acceptance; en 40,525 ids vs CJK 106,299 ids: English 1-2% faster with the smaller head | We use 64K. Coverage-targeted rebuilding from our own chat/code logs could shrink or retarget it |
| **Temperature-sampling acceptance tricks don't move speed** | Coupled + Gumbel drafts: +6 pts acceptance, decode flat (RTX 3060) | Skip unless sampled decoding matters |
| **Don't widen windows blindly** | `--spec` above 4 flat (7900 XTX report), spec 6 worse (Arc); spec-min-p flat 0.3-0.7 | Their MoE verify rows cost extra experts; ours are dense and cheaper per extra row, so K4 (9-16) may still pay. Use measured per-width cost (8b row 1) [INFERENCE] |
| **First prompt chunk short (TTFT)** | `STRATA_PREFILL_FIRST` 256 tokens: 2,184 tok 711 → 765 tok/s, TTFT -150 ms (Arc, INTEL.md:291) | Mostly for overlapping SSD reads; low value for us (fully on GPU) |
| **Prefill GDN chunked/WY needs a big GPU** | ≥128 SMs; 0.73× on 28 SMs, 0.87× on 48 SMs | 7900 XTX has 96 CUs; a chunked GDN prefill may need tuning before it pays [INFERENCE] |
| **Host-thread placement / pinning** | `--aux-cpus`: 0.888-0.917 off/on, solo decode 72 → 80 tok/s; host involuntary ctx switches 43.8K → 3.9K (2x RTX 3080, Xeon) | Our host overhead (K3) on an 8-core 5700X: pin the graph-launch thread and keep other threads off its core. Cheap to A/B |
