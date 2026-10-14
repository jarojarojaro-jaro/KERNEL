# LFM2.5-24B-A2B decode on RX 7900 XTX — round 4 (branch opt-lfm4, KV q8_0)

Worktree `~/wt/lfm4`, branch `opt-lfm4` from `amd-opt` 9d493cf6e, build `~/wt/lfm4/build-hip`, install
`~/wt/lfm4/inst`. Tools in `~/wt/lfm4-prof`.

## Result (interleaved, ~/llama-opt = 9d493cf6e vs ~/wt/lfm4/inst = opt-lfm4 e41c2330e, `~/wt/lfm4-prof/final.log`)

| measurement | ~/llama-opt | opt-lfm4 (inst) | change |
|---|---|---|---|
| llama-bench tg128 -r 5, 3 rounds, KV q8_0, depth 0 | 258.48 t/s, 3.869 ms/token | 294.84 t/s, 3.392 ms/token | -12.3 % ms (+14.1 % t/s) |
| same, depth 98304 | 193.40 t/s, 5.171 ms/token | 212.95 t/s, 4.696 ms/token | -9.2 % ms (+10.1 % t/s) |
| spec_sweep `lfm none` 6x3, T=1, round 1 / 2 | 259.31 / 259.13 t/s, 3.856 / 3.859 ms/step | 293.75 / 293.43 t/s, 3.404 / 3.408 ms/step | -11.7 % |
| spec_sweep `qwen mtp` 6x3, T=1 (1 round) | 101.72 t/s, 29.218 ms/step | 108.82 t/s, 27.812 ms/step | -4.8 % ms (same tok/step per class) |
| Uncensored model, llama-bench tg128, 3 rounds (same build, Q8_0 switch) | 3.933 ms/token | 3.706 ms/token | -5.8 % |

## 1. Decision measurements

### 1a. Launch boundary (chain of N dependent small kernels, gfx1100, ROCm 10.0)

`~/wt/lfm4-prof/boundary.cpp` (HIP stream / HIP graph / hipExtAnyOrderLaunch / AQL replay on an own ROCr queue) and
`~/wt/lfm4-prof/pm4.cpp` (one AMD vendor AQL packet `AMD_AQL_FORMAT_PM4_IB` pointing at a PM4 indirect buffer of N
`DISPATCH_DIRECT`s; encoding after hipfire `redline-rocr/src/pm4_gfx10.rs`). Metric: (T(1000) - T(200)) / 800, host
wall clock submit -> completion signal, median of 25. Kernels: empty 1x32, empty 1024x32, `copy2k` (8 x 256 threads,
reads 2048 floats written by the previous kernel, writes 2048 floats; ping-pong; result checked).

| method | empty 1x32 | empty 1024x32 | copy2k 8x256 | copy chain correct |
|---|---|---|---|---|
| HIP stream launches | 2.747 | 2.747 | 3.150 | |
| HIP stream, hipExtAnyOrderLaunch (no barrier bit: kernels may overlap) | 2.406 | 2.682 | 2.686 | (not dependent-safe) |
| **HIP graph (incumbent)** | **2.748** | **2.748** | **2.754** | yes |
| HIP graph of captured hipExtAnyOrderLaunch | 2.747 | 2.748 | 2.756 | (flag has no effect in a graph) |
| AQL replay, barrier, acq/rel system, kernarg host | 3.244 | 3.245 | 4.286 | yes |
| AQL replay, barrier, acq/rel system, kernarg VRAM | 3.246 | 3.245 | 3.302 | yes |
| AQL replay, barrier, acq/rel agent, kernarg host | 2.753 | 2.755 | 3.373 | yes |
| AQL replay, barrier, acq/rel agent, kernarg VRAM | 2.756 | 2.753 | 2.755 | yes (= what the HIP graph does) |
| AQL replay, barrier, acq agent rel none, VRAM | 2.755 | 2.755 | 2.754 | yes |
| AQL replay, barrier, acq none rel none, VRAM | 2.080 | 2.080 | 2.080 | **no** (stale L0/K$: 2047 of 2048 wrong) |
| AQL replay, no barrier, no fences, VRAM | 2.513 | 2.687 | 2.514 | no |
| PM4 IB, CS_PARTIAL_FLUSH + ACQUIRE_MEM GCR 0x380, kernarg host | 0.457 | 0.565 | 1.874 | yes |
| **PM4 IB, CS_PARTIAL_FLUSH + ACQUIRE_MEM GCR 0x380, kernarg VRAM** | **0.456** | **0.564** | **0.858** | yes |
| PM4 IB, same, kernarg VRAM, IB in VRAM | 0.457 | 0.574 | 0.869 | yes |
| PM4 IB, CS_PARTIAL_FLUSH + GCR 0x300 (no K$ inv), kernarg VRAM | 0.453 | 0.560 | 0.854 | yes (only VMEM consumers) |
| PM4 IB, CS_PARTIAL_FLUSH only, kernarg VRAM | 0.343 | 0.449 | 0.731 | **no** |
| PM4 IB, no boundary packets (overlap) | 0.238 | 0.346 | 0.262 | no |

Findings:
- Every AQL packet costs >= 2.08 us in the CP's AQL front end regardless of the barrier bit; the HIP graph already
  uses agent-scope fences and device kernargs (identical to the best correct AQL variant). AQL-level tricks
  (any-order, own queue, kernarg placement) cannot get below ~2.1 us; `hipExtAnyOrderLaunch` is ignored inside stream
  capture (graph timing identical).
- The PM4 IB path is 0.46-0.57 us per dependent boundary for empty kernels and 0.86 us for the copy kernel
  (kernarg in VRAM; in host memory the dependent kernarg `s_load` costs +1 us per kernel). 20 clean standalone runs
  (smoke + bench, every chain check correct, no GPU fault).
- First PM4 attempt faulted (CPF page fault, permission): the IB must be in memory allocated executable
  (`HSA_AMD_MEMORY_POOL_EXECUTABLE_FLAG`); the fault was recoverable (process killed, GPU fine).

Decision: step 2 (PM4 replay of the LFM decode graph) is GO: boundary 2.75 -> ~0.6-0.9 us.

### 1b. Per-call bandwidth ceiling (ideal read-only kernel, same bytes and grid as the hot MMVQ calls)

`~/wt/lfm4-prof/bw.cpp`: one wave per block, the block streams its bytes with 16-byte loads (lane-interleaved,
unroll 4), 48 calls per HIP graph on consecutive regions of a 1 GiB pool (every call cold w.r.t. the 96 MB Infinity
Cache), graph replayed 10x, rocprofv3 kernel durations (median, first 20 % dropped). MMVQ numbers: round 3 profile
(fast mode).

| call | bytes | grid | ideal kernel | GB/s | MMVQ today | gap |
|---|---|---|---|---|---|---|
| expert gate+up, 2 streams (gate rows + up rows) | 17.30 MB | 3072 x 32 | 21.92 us | 789 | 25.1 us (28.1 slow mode) | 3.2 us |
| same bytes, 1 stream | 17.30 MB | 3072 x 32 | 21.88 us | 791 | | |
| same bytes, 768 blocks | 17.30 MB | 768 x 32 | 20.20 us | 856 | | |
| in_proj (6144 x 2048 Q5_K) | 8.65 MB | 3072 x 32 | 12.04 us | 718 | 14.2 us (incl. conv tails) | 2.2 us |
| down Q5_K (4 x 2048 x 1536) | 8.65 MB | 4096 x 32 | 10.40 us | 832 | 12.7 us | 2.3 us |
| down Q6_K | 10.35 MB | 4096 x 32 | 12.24 us | 846 | 14.7 us | 2.5 us |
| head Q6_K (128000 x 2048) | 215 MB | 64000 x 32 | 232.6 us | 925 | 238.4 us | 5.8 us |

The MMVQ calls are within 10-20 % of a pure streaming read of their bytes with their grid; the summed gap is
~0.27 ms/token (38 x 3.2 + 29 x 2.2 + 20 x 2.3 + 17 x 2.5 + 5.8 us) and not all of it is reachable (dequant + dot
work, activations, output). The launch boundaries (305 x ~1.9 us above the PM4 cost) are worth ~2x more.
Two streams vs one stream: no difference in this process (the slow mode is per process, see section 4).

## 2. PM4 replay of the decode graph (GGML_HIP_PM4, kept)

`ggml/src/ggml-cuda/hip-pm4.{cu,cuh}`. After a graph is captured, its kernel nodes (one chain) become a tape: kernel
descriptors from the HIP-loaded code objects (`hipKernelNameRefByPtr` -> symbol `<name>.kd` in the executables of
the ROCr loader extension; descriptor via `query_host_address`), explicit kernargs from the node parameters at the
offsets of the code-object metadata (own msgpack reader of the NT_AMDGPU_METADATA note), hidden arguments as ROCclr
fills them (block counts, group sizes, grid dims, dynamic LDS; everything else fails closed); kernargs in VRAM, the IB
in executable host memory. One vendor AQL packet per token on an own ROCr queue; ordering with the HIP stream on the
host (stream sync before, bounded completion-signal wait after). Same kernels and arguments -> bitwise. Fallback to
`cudaGraphLaunch` for graphs with other node types, several streams, scratch or other implicit arguments.

- LFM: 304 dispatches per token in one tape (389 for the first, prompt-shaped graph). Qwen plain 807-919, Qwen MTP
  823 + 99 + 11 dispatches: tapes built too (greedy md5s unchanged).
- llama-bench tg128 -r 5, 3 rounds interleaved: GGML_HIP_PM4=0 3.887 ms/token (257.3 t/s) -> 3.424 ms (292.1 t/s),
  -11.9 % ms/token (commit 1153adb69).
- Timing (GGML_HIP_PM4_DEBUG=2): tape on the GPU 3197 us, stream sync before the tape 16.7 us, submit -> completion
  3221 us (24 us submit/notify latency), GPU idle between tapes 96 us of which ~56 us host work outside the backend.
- rocprofv3 does not see PM4 dispatches: per-kernel view via GGML_HIP_PM4_DEBUG=3 (`pm4trace` lines; `trace.py`), per
  dispatch = end of the previous dispatch -> end of this one (boundary packets included).

## 4. The per-process slow mode (and a fix for one kernel)

Survey (`cmp.sh`, `modes.sh`, 11 processes each, depth 0):

| path | expert gate+up (768x4 blocks) | in_proj+conv (3072 blocks) | moe down (2048) | tape / busy |
|---|---|---|---|---|
| HIP graph (rocprofv3) | 25.16 (3/11) or 28.2 (8/11) | 14.24 always | 12.7 | |
| PM4 tape (trace) | 25.5 + conv 14.4 (3/11) or 26.2 + conv 17.7 (8/11) | | 13.0 | 3184 or 3307 us |

Tests of the round-3 hypothesis (gate and up weight streams conflicting) and others:
1. Ticket counters one per 128-byte line (stride 32) for the gate+up and conv tails: modes unchanged (3/6 slow vs
   2/6) -> not atomic contention (reverted).
2. Ideal streaming read (`bw.cpp`) also has per-process modes, without any fusion or second stream: 3072-block cases
   (1 stream 21.8 / 23.9 us, in_proj bytes 12.0 / 12.9 us, 2 streams 21.7-22.8 / 23.5) while the 4096-block down
   shapes, the head and the 768-block case never change. Rotating each block's start slice: no effect.
   -> not a gate/up stream conflict; repacking gate+up per expert would not help (not built).
3. Four separately allocated 1 GiB pools in one process (`bw2.cpp`): all four in the same mode -> a process-wide
   state, not the physical placement of an allocation. (`hipDeviceMallocContiguous` allocations fail with OOM.)
4. Same bytes, different grids, one process (`bw4.cpp`, us per call in a graph incl. the 2.75 us boundary):
   1536 blocks 12.6-13.1, 2048 12.4-12.5, 2560 12.2 (all processes), 3072 13.6 or 14.6. A grid of exactly the wave
   capacity of the GPU (192 SIMDs x 16 one-wave blocks = 3072) is slow in every process and bimodal across
   processes; 2560 is the fastest and stable.
5. In the model (PM4 tape, 5 processes each): GGML_HIP_MMVQ_N1_ROWS=4 everywhere: no modes (conv 14.5, gate+up 26.56,
   tape 3319-3341 us) but slower in sum than 2 rows in fast mode (3184).
6. Kept: GGML_HIP_CONV_ROWS4 (commit 1b43bccae): the in_proj+conv MMVQ with 4 rows per block (1536 blocks):
   14.40-14.44 us in every process (was 14.4 or 17.7); llama-bench 4 rounds 3.458 -> 3.402 ms/token, per-process
   spread 3.386-3.488 -> 3.396-3.407. Bitwise.

## 6. LFM2.5-24B-A2B "Uncensored-AD" Q5_K_M (parent request)

Tensor mix (own GGUF lister `ggufls.py`): shortconv in_proj/out_proj, attn q/k/v/o, dense ffn gate/up/down and
token_embd (tied head) are Q8_0 (LFM: Q5_K, v/dense down/head Q6_K); experts: 33 layers Q5_K gate/up/down, 5 layers
Q6_K gate/up/down (LFM: gate/up all Q5_K, down 20 Q5_K + 18 Q6_K).

Kernels per token (rocprofv3, graph path): 305 for both models -> every fusion (NORM_ROUTER, INPROJ_CONV, GATE_UP_Q8,
MOE_DOWN_REDUCE, ATTN_PREP, KVQ_FWHT) also covers the Q8_0 / Q6_K tensors; nothing falls back.

Per class (graph path, 9d493cf6e + PM4 commits, one process each):

| call | LFM (type, grid, us, GB/s) | Uncensored (type, grid, us, GB/s) |
|---|---|---|
| in_proj + conv (6144 x 2048) | Q5_K, 1536 blocks (4 rows), 14.32 us, 604 GB/s | Q8_0, 6144 blocks (1 row), 25.52 us, 13.37 MB -> 524 GB/s |
| out_proj (2048 x 2048) | Q5_K, 1024 blocks, 5.16 us, 558 GB/s | Q8_0, 2048 blocks, 7.80 us, 571 GB/s |
| head (128000 x 2048) | Q6_K, 64000 blocks, 238.4 us, 903 GB/s | Q8_0, 128000 blocks, 301.1 us, 925 GB/s |
| dense ffn gate+up (2 layers) | Q5_K, 42.6 us | Q8_0, 59.0 us |
| expert gate+up | Q5_K 25.2/28.2 us (mode) | Q5_K 28.2 us x 33, Q6_K 30.0 us x 5 |
| GPU busy per token | 3244 us | 3735 us (+491 us) |

The gap is mostly bytes (Q8_0 is 1.55x the bytes of Q5_K), but Q8_0 was not in the RDNA3 multi-row n=1 MMVQ path
(1 row per block, 2x the blocks, the in_proj at 524 GB/s). Fix (bitwise, commit below): Q8_0 joins the 2-row path
(and the 4-row conv path): Uncensored llama-bench tg128 3 rounds 3.933 -> 3.706 ms/token (254.3 -> 269.9 t/s), logit
hash f74300e3142a5535 unchanged. GGML_HIP_MMVQ_N1_Q8_0=0 restores 1 row.

## 7. Further attempts (numbers)

- 3 rows per block for the expert gate+up (grid 512x4 instead of the 3072-block 768x4; q8 ticket tail generalized to
  blocks spanning two 32-row groups; bitwise, hash a7ce25b73f887fed): gate+up 25.40-25.44 us in every process (2 rows:
  25.5 or 26.2), but every other kernel got slower (down 12.92 -> 13.20, out_proj 5.44 -> 5.84, conv 14.40 -> 14.80,
  FA 8.88 -> 9.48; probably the 285 W cap: the more efficient gate+up draws more power), tape 3196-3228 -> 3248-3252
  us. Rejected (reverted).
- PM4 fences: dropping the tape's own system-scope ACQUIRE_MEM at start/end and/or agent-scope packet fences: tape
  3192-3206 us, submit->done minus tape 23 us in every variant -> not the fences (kept the safe set).
- Depth 98304 (llama-bench tg128 -r 5, 1 round, same build): GGML_HIP_PM4=0 5.201 ms/token -> PM4 4.678 ms/token
  (tapes are rebuilt on every graph recapture; nothing else changes with depth).

## 8. Not done (budget)

- Step 3 (persistent / early-start MoE layer): not built. With the PM4 replay a boundary costs ~0.5-0.9 us instead of
  2.75 us, so merging norm+router -> gate+up -> down saves at most 2 x 38 x ~0.6 us = ~45 us/token (1.4 %) plus
  whatever the early start of the weight loads overlaps of each kernel's ramp/tail; the go/no-go microbenchmark was not
  run.
- PM4 host ordering: per token 16 us stream sync before the tape + 23 us doorbell->completion latency (section 2).
  Next idea: submit the vendor packet before the inputs are ready behind a WAIT_REG_MEM on a host flag (needs the
  standalone 20-run protocol because it is a device-side wait); worth <= ~20-35 us/token.
- Step 5 leave-one-out of the patch stack via the env switches: not run. Silent-fallback detection: GGML_HIP_PM4_DEBUG=1
  prints the dispatch count of every tape (LFM 304/token; a fusion that stops applying shows up as a higher count),
  `cmp.sh`/`trace.py`/`rpgrid.py` give per-kernel+grid tables of both paths.
- Expert gate+up per-process mode (25.5 vs 26.2 us in the PM4 path, 25.2 vs 28.2 in the graph path): cause narrowed to
  a process-wide state hitting grids of exactly the wave capacity (3072 one-wave blocks); no bitwise fix found that does
  not cost elsewhere (4 rows 26.56 us, 3 rows see section 7).

## 9. Attempts in order

1. Launch-boundary microbenchmarks (1a): AQL variants >= 2.08 us, any-order flag ignored in graphs, PM4 IB 0.46-0.86 us.
2. PM4 first run: CPF permission fault (IB not executable) -> executable HSA pool; 20 clean standalone runs.
3. Bandwidth ceiling (1b): MMVQ within 10-20 % of an ideal streaming read with its grid.
4. GGML_HIP_PM4 in ggml-cuda: kept, 3.887 -> 3.424 ms/token.
5. PM4 diagnostics (DEBUG=2/3): kept (no effect on the default tape).
6. Ticket stride 32 (slow-mode hypothesis): no effect, reverted.
7. Synthetic slow-mode study: rotation no effect; per process, not per allocation; grid 3072 is the cliff.
8. GGML_HIP_CONV_ROWS4: kept, 3.458 -> 3.402 ms/token, per-process spread removed.
9. Uncensored model analysis; Q8_0 in the 2-row path: kept, Uncensored 3.933 -> 3.706 ms/token.
10. 3 rows per block for gate+up: rejected (+50 us/token elsewhere).
11. PM4 fence variants: no effect.

## 10. Commits (9d493cf6e..opt-lfm4)

- 1153adb69 HIP/RDNA3: replay a captured decode graph as one PM4 indirect buffer on an own ROCr queue (GGML_HIP_PM4)
- e5ca00ec4 HIP PM4 replay: GGML_HIP_PM4_DEBUG=2 per-launch timing, =3 per-dispatch durations
- 1b43bccae CUDA/HIP RDNA3: the shortconv in_proj MMVQ runs 4 rows per block (GGML_HIP_CONV_ROWS4)
- 2cbcf771a CUDA/HIP: GGML_HIP_PM4 and GGML_HIP_CONV_ROWS4 read through ggml_cuda_env_switch
- e41c2330e HIP/RDNA3 one-column MMVQ: Q8_0 joins the 2-row path (GGML_HIP_MMVQ_N1_Q8_0)

Verification: logit hashes LFM a7ce25b73f887fed (d0) / b47452b9380b665b (d3000) unchanged with every commit, Uncensored
f74300e3142a5535 unchanged; greedy md5 LFM 894e56e447243cf630214b4cfc1ffea6, Qwen plain c4708318411479c9530911e310f865bd,
Qwen MTP 6f14e814bb6408aeea23a1dc50e96ba1; test-backend-ops MUL_MAT 2476/2476 (one rerun: a q4_1 n=1 case failed once
at 0.000557 > 0.0005 and passes on rerun; q4_1 untouched), SHORTCONV 4/4.
Note: rocprofv3 does not see PM4 dispatches; profile the kernels with GGML_HIP_PM4=0 or use GGML_HIP_PM4_DEBUG=3.
