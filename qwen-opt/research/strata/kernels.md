# Strata: GPU decode/verify kernels and the HIP backend — what they do, how they were found, what transfers

Scope: `src/kernels/cuda/*` (the same .cu files compile for CUDA, wave32 HIP and wave64 gfx906), `include/strata/hip_compat/`
(wave32 RDNA shim) and `include/strata/platform/hip_compat/` (gfx906-only wave64 shim), `src/core/verify.cpp` (window
graph), docs/AMD_HIP*.md, and the history (clone at `a0116b27`, 2026-10-12) plus open PR #2231 (gfx1100, 2026-10-13).
Paths are repo-relative; `file:N` = line. Measured numbers are quoted from commit messages / code comments / docs;
anything not observed there is marked [INFERENCE].

Our geometry (read from `~/models/Qwen3.8-27B-UD-Q4_K_XL.gguf` header): GDN `ssm.time_step_rank`=48 v-heads, 16 k-heads,
state 128 — **identical GDN geometry to Strata's model (h_v 48, S 128)**, so their GDN kernel timings are directly
comparable per layer. Per-token weight bytes by type: Q5_K 7.38 GiB, IQ4_XS 2.91, Q4_K 2.85 (0.68 of it token_embd),
Q6_K 2.67 (995 MiB of it `output.weight` 5120x248320), Q8_0 0.12 (ssm_alpha/beta, some ssm_out/attn_v), Q3_K 0.11.

---

## 0. TL;DR

- Strata's decode is one captured graph **per window size T** (`verify.cpp:2172` `exec_[T]`), inputs (tokens, positions,
  commit count) read by the graph's first kernels from **pinned mapped host memory** (`verify.cpp:606,887-896,1990`),
  so no graph update / memcpy node per step. Commit of accepted tokens is a second captured graph launched
  **asynchronously** (`verify.cpp:2494-2522`).
- GDN speculative rollback uses **no per-token state snapshots**: the window computes all T outputs from the untouched
  state (read-only, `__ldg`), and the commit graph **replays** the recurrence for the `n_keep` accepted tokens from the
  saved post-conv q/k/v + gate/beta (`verify_kernels.cu:396-463`, `verify.cpp:1993-2006`). One-token windows write the
  state directly (CUDA default, HIP opt-in, `352cad8f`). Our fork writes up to K full-state snapshots per verify
  (`~/wt/k1/ggml/src/ggml-cuda/gated_delta_net.cu:183-195`) — this is the biggest *structural* difference for us.
- Matvec: llama.cpp's MMVQ arithmetic, restructured into **load (weight-only, once per row/block) / apply (per column)**
  traits (`native_mmvq.cu:818-1020`), then an **interleaved-q8_1** 2-4 column kernel where one warp owns 1/2/4 whole
  rows, no LDS cross-warp reduction, and one 16-byte load fetches the same int of every column (`native_mmvq.cu:1310-1546`,
  `q8_1_il.cuh`). Rows-per-warp is a **per-arch table** by (type, ncols, n_out class); a gfx1100 table measured
  in-engine exists only in PR #2231. Lossless **plane repacks** of 2-byte-aligned formats (Q6_K head, Q8_0) for aligned
  non-temporal dword loads (`native_mmvq.cu:1684-1960`).
- Launch-count reduction is done by (a) batching per-token kernels over the window, (b) **producers writing their
  consumer's q8_1 image** (and the interleaved copy), (c) **grid-concatenated "pair" launches** of two same-input
  matrices (no extra registers), (d) folding waits into copies, (e) deleting nodes nobody needs (self-commit, dead
  stores). They also *add* launches where parallelism pays (GDN split into recurrence + norm kernels).
- RDNA specifics: `__builtin_amdgcn_sudot4` (gfx11/12) / `sdot4` (gfx103x) for dp4a, `v_perm_b32` for `__byte_perm`,
  SWAR byte ops (+15% decode R9700), DPP `row_xmask` + `permlanex16` instead of `ds_bpermute` (hipcc in ROCm 10.0 does
  **not** do this by itself), volatile + `__threadfence_system` for stores to mapped memory, `wall_clock64()*10` = ns.
- Measured gfx1100 decode-path wins (PR #2231, RX 7900 XTX): +11.7% chat / +14.3% agent decode from many small
  bitwise fixes (GDN out-norm 9.3→2.0 µs/layer, argmax 12→5.6 µs, MTP row select 12→2.2 µs, dependent launch ≈2.7 µs).
- Their decode-half "speed switches" tuned on Strix Halo (gfx1151, UMA) measured **−4% on a discrete gfx1201**
  (#1478) and are kept gfx1151-only: wins are platform-specific; each switch needs an in-engine A/B on the target card.

---

## 1. How the author works on kernels (process)

- **Bitwise is the default bar.** A switch becomes a default only if it reproduces the old bits; anything that changes
  rounding is opt-in and gated by KL. Examples: arch defaults list only "exact" switches (`src/core/arch_defaults.cpp:35-57`);
  the multi-column "UPSTREAM" layout (llama.cpp's faster, differently-reduced one) stays off "until timed on an idle GPU
  (plan rule: default only what is measured)" (`native_mmvq.cu:1150-1154`); fused norm+RoPE is CUDA-only until its
  parity test passes on AMD hardware (`088e8a82`).
- **Bitwise proofs instead of tolerance.** Router fast path (`a2be1670`): tree sum instead of 512 serial FP64 adds is
  used only when the float bracket `tree*(1±2^-40)` maps to one float; otherwise the serial sum runs — exact by
  construction, 39→9-12 µs/call on RDNA4. Multi-warp-sum transpose (`s26_tsum.cuh:1-7`): same pairs as the butterfly,
  fp add commutes ⇒ same bits.
- **Compiler-level bit traps documented**: HIP `__fmul_rn` is a plain product ⇒ `#pragma clang fp contract(off)` in
  quantizers (`docs/AMD_HIP.md:652-655`, `iq_kernels.cu:1539-1545`); switching a shuffle to DPP let clang contract
  `x*x + shfl` into an FMA (PR #2231 `add_nc`); hipcc on gfx1151 rounded differently when a shuffle sat inside a
  divergent branch (`verify_kernels.cu:307-308`); a 128-thread rewrite differed by 1 ulp in ~7% outputs, so the norm kernel
  kept the old code shape (`verify_kernels.cu:333-335`).
- **Validation harnesses**: per kernel `*_parity` tests with memcmp (`src/kernels/*_parity.cpp`, e.g.
  `mmvq_il_parity.cpp`, `gdn_parity.cpp` T=1..8, `kv_steps_parity.cpp`, `verify_parity.cpp`, `sampler_parity` per path);
  HIP-only tests in `tests/hip/` (`intrinsics.cpp` dp4a/SWAR on random operands, `handoff.cpp` mapped-memory rings,
  `router_fast.cpp` 65,536 rows); end-to-end greedy token ids over fixed prompt sets (e.g. "S25's 18 prompts") and
  teacher-forced KL (PR #2231: 2,557 positions, KL 0.0000).
- **Measurement discipline**: paired/interleaved A/B, medians, fresh process per arm; in-graph **GPU stage stamps**
  (`gpu_stamp_kernel`, `verify_kernels.cu:1320-1347`: `wall_clock64()*10` on gfx10.3/11/12) behind `STRATA_VERIFY_PROFILE`;
  `STRATA_DUMMY_NODES=k` adds k empty nodes per layer to measure node cost (`verify.cpp:1075-1078`) → "~2.4 µs per
  dependent kernel in a gfx1201 graph whatever it does" (`verify.cpp:225-228`), ~2.7 µs on gfx1100 (PR #2231);
  `STRATA_VERIFY_NODES` dumps the graph's nodes/edges (`7fc02cb5`).
- **Microbench vs engine**: benches rotate over enough weight copies to miss L2 (`mmvq_il_parity.cpp:11`,
  `fused_gr_bench.cpp:4-6`), yet PR #2231 found the IL bench "back-to-back launches at full clock favours 2 and 4 rows a
  warp by 20-60% over what the engine sees" — the gfx1100 table was taken from **rocprofv3 kernel times inside a 4K
  decode**, forcing each rows count. A wrong table entry cost −15% decode at 128K on an RTX 4090 (#1842).
- **Every optimization is an env switch** (`STRATA_*`, kill switch for defaults, opt-in for experiments), so A/B is
  env-only on one binary; per-arch tables (`kIlArch`, `arch_defaults.cpp`, hipBLASLt tables) carry them per card.
- **Sources**: many kernels are ports from contributors' forks/PRs (Eddoursul "F4/F7", stuchapin909 #783, #262, #540),
  split "per piece" and re-verified bitwise. Research rounds are labelled S23-S27 / "143-amdk" on gfx1151 (Aurora box);
  the notes file `aurora_s23.md` is referenced but not public.

---

## 2. Verify-window execution model (graph, sync, commit)

- **Graph per T**: `Verifier::capture(T)` captures the whole 48-layer window once per T, instantiates (evicting older
  graphs if VRAM is short, `3bcfd8f3`) and `cudaGraphUpload`s it (`verify.cpp:1846-1971`); `run()` launches `exec_[T]`
  (`verify.cpp:2172`). Paper: "one captured CUDA graph per window size, so the host never waits on a synchronizing
  driver call". Exact-T template instantiations remove dynamic loop bounds (T=1..8) in GDN a/b, BF16 GEMV, HC kernels
  (`ae3b249f`, PR #783).
- **Inputs via mapped memory**: tokens/steps/positions staged by the host into `cudaHostAllocMapped` buffers and copied
  on-GPU by `copy_i32_from_mapped` as the graph's first nodes (`verify.cpp:606,887-896`). Commit count `n_keep` and
  positions likewise (`verify.cpp:1990, 2501-2503`). ⇒ one graph replays forever, no parameter update.
- **CPU↔GPU sync (MoE-specific)**: per layer the GPU "rings" a doorbell (volatile store of a sequence word into mapped
  memory + payload), the host spins (`_mm_pause`, `verify.cpp:2203-2231`), runs CPU experts, raises flags; GPU spin
  kernels `wait_flag_ge` (1 thread, `strata_spin_pause` = `s_sleep 1` on AMD) gate dependents (`verify_kernels.cu:1051-1054`).
  With every expert resident ("all-resident" graph, `be7889ed`) none of this is in the graph — the regime that matches
  our dense model. On HIP the ring store must be volatile **and** followed by `__threadfence_system()`: "on RDNA4 a
  plain store to mapped pinned memory stays in the GPU's L2 until the stream is synchronized" (0/100 rings seen
  without; `elementwise.cu:206-215`, `docs/AMD_HIP.md:283-284`).
- **End of window**: blocking `cudaStreamSynchronize` — "a cudaStreamQuery poll here cost IQ3_S ~3% decode"
  (`verify.cpp:2280-2288`).
- **Commit graph** (`capture_commit`, `verify.cpp:1973-2043`): per GDN layer `gdn_conv_commit` + state replay; per
  attention layer indexer append; launched **without host sync** when `set_commit_async` (next window queues behind it
  on the same stream; drafter on its own stream reads only final rows) (`verify.cpp:2494-2522`).
- **One-token window self-commit** (`352cad8f`, F7): a T=1 window always keeps its token, so its GDN kernel writes the
  state (n_keep=1) and the conv kernel writes its history; no commit graph. CUDA default; HIP opt-in
  (`STRATA_ONE_TOKEN_COMMIT=1`, `verify.cpp:204-206, 277-291`).
- **MTP drafter**: teacher-forced chain as one asynchronous launch with events per output (`8ba583fe`); the draft
  round graph runs the draft layer's "front" (embedding, fc, K/V append) over T cells once and only the rest for the
  last accepted row (`ca833116`, `copy_row_to_first`).
- **Graph branches**: `STRATA_DF_BRANCH` forks a/b+z beside qkv+conv inside the graph (`verify.cpp:1117-1153`), opt-in.
  On HIP cross-stream event dependencies are expensive: shared-expert fork off = 62.9 t/s vs 43.4 on (R9700),
  42.5→56.4 (RX 6800 Windows) (`verify.cpp:184-191`); only UMA gfx1151 gains (+1.8/+6.7%).
- **Host function vs stream write** (PR #2231): `cudaLaunchHostFunc` reaches the GPU 15.0 µs after the copies end;
  `hipStreamWriteValue32` 6.7 µs (gfx1100). Host thread affinity matters (#1975: callback thread inheriting the host's
  core: 142.8→207.8 t/s on a 5090, DETAILS.md:1735-1739).

---

## 3. Dense matvec (MMVQ) — `src/kernels/cuda/native_mmvq.cu`

### 3.1 Single column (llama.cpp transcription)
- 128-thread blocks (4 warps × 32), one row per block (4 rows for small K), each thread walks blocks `kbx = tid/T`
  stride `BPI`, VDR per format; cross-warp sum via LDS `partial[3][...]` + `__syncthreads`, then XOR-tree
  (`native_mmvq.cu:249-816`). Same as old llama.cpp mmvq "nwarps=4". Note: llama.cpp's RDNA path (our fork) uses
  its own nwarps/rows table; ours already has DPP reductions (`~/wt/k1/.../mmvq.cu:702-711`).

### 3.2 Multi-column 2-8 ("plan v0.3 P3", `native_mmvq.cu:818-1307`)
- Each format split into `Traits::load(block, iqs)` (codes, unpacked 6-bit scales, `dm`) and `Traits::apply(W, q8_1 ptr,
  iqs)` (activation loads + the original `*_q8_dot_impl` expression). `load` once per (row, block), `apply` per column
  ⇒ "adding columns adds only activation work", each column bitwise = single-column call.
- Two rows per block for any K (`2715a752`, #783 PR-h; kill switch `STRATA_NO_MMVQ_ROWS2`), `__launch_bounds__(NW*32,
  ROWS<=2?4:1)`. The "UPSTREAM" llama.cpp layout (4 warps for 2-4 cols, 2 warps 5-8, 2 rows/block) is kept as an
  opt-in (different reduction order).
- `SmallTraits` for Q4_0/Q5_0/Q8_0/IQ4_NL "decoded-once" (`native_mmvq.cu:1025-1155`).
- **PAIR** (`STRATA_LFUSE`, `native_mmvq.cu:1162-1176, 2406-2441`): one launch, blocks `[0,n_out/ROWS)` compute matrix 1,
  blocks beyond compute matrix 2 (same input, same shape, same per-thread code) — horizontal fusion with **zero extra
  registers**; used for shared-expert gate+up (Q8_0). Also the 1-row shared-expert gate GEMV rides as an extra block of
  the router GEMV launch (`b08cf3e1`). LFUSE total: −4 launches/MoE layer, −(T−1)/attention layer (KV append for all
  tokens, K and V in one 3D grid `blockIdx.z = 2*token + K/V`, `kv_q8.cu:28-31`): gfx1151 51.29→50.31 ms/window
  (−1.9%), 54.33→55.12 t/s.
- **TSUM** (`s26_tsum.cuh`, `2a1c54e7`): a warp ending with P = NCOLS×ROWS sums does one transposed butterfly — at
  offset 16 each lane keeps half its values and adds the partner's copy of that half, etc. — P−1+(5−log2 P) moves
  instead of 5P, moves = `permlanex16` (offset 16) and DPP `row_xmask` (`update_dpp(...,0x160+O,...)`) on AMD. Bitwise.
  Applied to multi MMVQ, packed kernels, BF16 rows GEMV, HC read, experts. gfx1151 engine: 54.21→52.10 ms/window,
  51.31→53.73 t/s.
- **PDL** prefetch of the first weight block before `pdl_wait` (`native_mmvq.cu:1182-1206`) — CUDA sm_90+ only; HIP has no
  PDL equivalent (and `__restrict__` interplay cost P40 half its decode, #1469).

### 3.3 Interleaved activations, 2-4 columns (fork F4, `ffac97f7`, CUDA; HIP port in PR #2231)
- **Layout** (`include/strata/kernels/native_mmvq.hpp:137-140`, `q8_1_il.cuh:16-65`): CP = 2 (2 cols) or 4 (3-4),
  zero-padded; `bm[nb][8][CP]` (block-major int32), `pm[8][nb][CP]` (position-major, for IQ4_XS whose lanes read the
  same int of consecutive blocks), `d[nb][CP]` floats (`__low2float(ds)`). One `int4` load = int p of block b of all
  4 columns; one `float4` = their scales. Written by a tiny `native_q8_1_interleave_kernel` (`native_mmvq.cu:1534-1546`)
  or, in PR #2231 (`STRATA_MMVQ_IL_PLAIN`), **by the producer** (the HC read writes it beside its q8_1 images) so no
  extra launch.
- **Kernel** `native_mmvq_il_kernel<I, NC, R>` (`native_mmvq.cu:1453-1504`): 128-thread blocks of 4 independent warps,
  each warp owns R rows (1/2/4) and walks *all* K: lane l's chunk m is what thread 32(m%4)+l of the exact layout did,
  sums kept as `acc[4][R][NC]` ("four virtual warps") added in warp order, then one `warp_sum` ⇒ bitwise equal to the
  exact multi-column kernel, **no LDS, no `__syncthreads`**. Weight block decoded once per (row,chunk), applied to NC
  columns. Grid-stride loop kept although each warp gets one group: "without it ptxas gives several instances fewer
  registers (Q6_K at 3 columns 10-50% slower)" (`native_mmvq.cu:1464-1465`).
- **Q3_K trick** (`native_mmvq.cu:1407-1421`): `__vsubss4(vil, vih)` replaced by `vil | (hbit*252)` — the high-bit
  offset never saturates, so OR gives the same bytes; scales and signed values done once for all columns.
- **Rows tables** by (ggml type, ncols 2-4, n_out class <2048/<4096/<8192/<12288/≥12288[/≥65536 in #2231]), 0 = plain
  kernel; rule "≥3% faster than native_mmvq on every measured shape of the class, else 0" (`docs/MMVQ_IL_TABLE.md`,
  `native_mmvq.cu:2539-2607`): shared sm_86+sm_120, sm_70, sm_60 (compute-bound Pascal: 4 rows win 15-35%), sm_86 with
  Q3_K. Override `STRATA_MMVQ_IL_ROWS="type:ncols:r0,..,r4"`; `mmvq_il_parity --bench --emit-table` prints a table.
- **gfx1100 table (PR #2231, in-engine rocprofv3, ROCm 10.2)**: `kIlRows_110` — IQ4_XS: 1 row only for ≥12288 (2 cols),
  ≥8192 (3-4 cols); Q4_K: 2 rows at 4096-8191, 1 at 8192-12287, 2/1 above; Q5_K: mostly 1 row ≥8192; Q6_K 2/1. Classes
  <4096 rows: 0 (plain kernel) everywhere. **Plain-column variant (no interleave copy) never beat native_mmvq in the
  engine** (`kIlpRows_110` all zeros).
- Measured elsewhere: RTX 4070 bench IQ4_XS 2560x10240 T=4 51.3→34.7 µs (rows1) (#1842 comment); V100 Q5_K head at 3
  cols 1094→821 µs; A4000 Q3_K 2560x10240 at 4 cols 120→70 µs (`195d3791`). Bad table on 4090: −15% decode (#1842).

### 3.4 Packed (planar) weight copies, HIP opt-in (`native_mmvq.cu:1684-1960`)
- **Q8_0** (`96f4065a`): GGUF 34-byte blocks leave every int 2-byte aligned (`load_int_b2` = two 16-bit loads). Load-time
  lossless repack into a `qs` plane (row-major int8) + `d` plane (fp16); each thread reads one aligned 8-byte run with
  `__builtin_nontemporal_load`; **640 persistent workgroups** grid-striding rows with double-buffered LDS partials.
  Eligible 1024≤n_in≤4096, n_out≥2048 (6144→2560 was +2-4% standalone but −3% in-engine; <2048 rows lose). gfx1151:
  +10-12% per call, engine 40.06 vs 39.77 t/s (8K), +2.3% in arch_defaults. Costs +1.87 GiB (GGUF copy kept for prefill).
- **Q6_K heads** (`5cf0079b`): 210-byte blocks ⇒ 2-byte aligned ints. Planes ql(128B)/qh(64B)/scales(16B)/d(2B) per
  block, aligned non-temporal dword loads, same thread ownership/order ⇒ bitwise. gfx1151 self-test medians: main head
  (248320x2560) 1 col 2420→2300 µs, 2 cols 2563→2455, **4 cols 2973→2975 (no gain: "not bandwidth-bound there")**; draft
  head (106299 rows) 1 col ~1335→~954 µs, 4 cols ~1650→~1340. +497 MiB/+213 MiB. Grid 320-20480 flat.
- Both default only on gfx1151; part of the "decode half" that lost 4% on a discrete R9700 (#1478).

### 3.5 Expert-kernel layouts with transferable ideas (`iq_kernels.cu`)
- `row_dot2/row_dotn`: a 32-lane warp computes 2..N rows in one loop — "two independent load chains in flight"
  (`iq_kernels.cu:2833-2886`); EXPERT_V2: 4 interleaved rows/warp, activation rows + IQ3_S grid table staged in LDS,
  non-temporal weight loads (`iq_kernels.cu:2006-2070`). 16-lane / 8-lane sub-warp row dots so all lanes are busy for
  short K (`iq_kernels.cu:989-1085`). gfx1100 rows-per-block autotune of these kernels: **null result (≤1%)** (PR #744).

---

## 4. GDN decode / verify — `src/kernels/cuda/verify_kernels.cu`, `fused_gdn.cu`, `gdn.cu`

Per GDN layer of a window (`verify.cpp:1113-1182`): [q8_1 quantize unless producer wrote it] → qkv MMVQ(-IL) →
`gdn_conv_l2_multi` → `gdn_ab_multi` → z MMVQ → `gdn_step_norm_multi` (recurrence + gated RMSNorm [+q8_1]) →
[quantize] → out MMVQ. ≈6-8 launches.

- **Conv + SiLU + L2 norm in one kernel** (`verify_kernels.cu:35-72`): block = 128 channels (one head), y = token row;
  window `[hist(3) | x_0..x_t]`, L2 over the head via shuffles + 4-entry LDS. `commit` flag writes the history
  (T=1 self-commit). Conv commit for n_keep is a separate 1-thread-per-channel kernel (`:74-89`).
- **a/b projections** (`:91-149`): BF16 weights, one warp per output row (2 rows/64-thread block), `uint4` weight load
  unpacked once and applied to all T tokens (`acc[MAX_T]`), softplus(·+dt)·A and sigmoid fused; exact-T instantiations
  1..6 (`ae3b249f`). Conv+ab in one launch (`STRATA_FUSE_CONVAB`, `:151-167`) **measured −0.3% on gfx1201** (the a/b
  chain is longer) → opt-in.
- **Recurrence state layout**: `state[(rg*32 + r) * h_v + head][S]` — thread (col, rg) holds 32 state rows of one column
  in registers (`RPG = S/RG = 32`, `RG = 4`), consecutive columns = consecutive lanes (coalesced). Per token: k/q row of
  the head staged in LDS (double-buffered next token's k/q, `ae3b249f`), `kv = Σ s[r]·k[r]` per row group → 4-way LDS
  reduce → `delta = (v − g·kv)·β`, `s = g·s + k·delta`, `o = Σ s·q` → LDS reduce (`:239-325`).
- **Grid sizing is the latency knob**: original one 512-thread block per head = 32-48 blocks "read the 2 MB state of a
  layer at ~60 GB/s" (~36 µs/launch at T=1 on gfx1151, +4 µs per row) (`e3c3d6ba`). `gdn.cu:17-31` documents the same
  lesson: 24 blocks ⇒ 0.28 ms/layer for 12.6 MB "that a 643 GB/s card should do in 0.020 ms". **Split**
  (`STRATA_GDN_SPLIT`, `:327-393`): 4 blocks of 32 columns per head (192 blocks × 128 threads), the head-wide output
  norm moved to a second kernel (`gdn_out_norm_kernel`, `:464-497`). gfx1151 (h_v 48 = ours): window 30.1→26.7 µs at
  4 rows, 23.8→23.2 at 2; commit 44.1→39.1 µs (1 row), 60.8→46.1 (6 rows); engine 49.45→50.1 t/s. T=1 keeps the fused
  kernel ("no gain").
- **Rollback = replay, not snapshots**: window kernel `ALL_OUT=true` reads state with `__ldg` and never writes it
  (`:259-269, 321-324`); commit graph replays `n_keep` (read from device memory written from mapped host memory)
  tokens with `gdn_state_replay_kernel` (`:396-463`): gate/β/v of every row prefetched, next row's k/q loaded during the
  current row; 44.5→39.1 µs (1 row), 53.8→42.9 (4 rows) on gfx1151. Saved per-token inputs: post-conv qkv `h_L_`,
  `gate_L_`, `beta_L_` per GDN layer (tiny vs 3 MiB state). Lineage: ninfer's "replayssm-gdn" (paper ref 7).
  Cost model per GDN layer per step: window reads state (1 pass) + commit reads+writes (2 passes) = 3 passes of 3 MiB
  regardless of T; + 2 launches/layer in the commit graph.
- **Producer-written q8_1** (`STRATA_QFUSE`, `22abb92d`, `:221-237`): the warp holding 32 output columns quantizes them
  (XOR-tree amax and sum, contraction off) into the out-projection's q8_1 blocks; harness GDN step+quantize 23.1→20.5 µs
  (1 row), 32.6→27.0 (4); engine flat (~0).
- **gfx1100 out-norm** (PR #2231 `STRATA_GDN_NORM128`, default on): the S×RG=512-thread norm kernel had 3 idle row
  groups; 128 threads + DPP/permlanex16 butterflies (`gx<M>`) → **9.3→2.0 µs per layer** bitwise.
- **Prompt GDN** (not decode, for K5): gfx11/12 defaults `GDN_HEAD/GDN_PP=2/GDN_CONVL2/GDN_NOY` (4 lanes per column, 2
  columns per lane, conv+L2 fused, no dead FP32 store): +0.8-1.8% prompt R9700 (#1478 maintainer), +4-8% (reporter).
  Chunk-parallel **WY form on gfx1100 lost badly** (fp32 folds 144x slower; rocWMMA 16x16x16 6x slower per layer-chunk,
  prefill −39..−40%) — PR #888/#1296, rejected.

---

## 5. Attention decode and KV (Strata's attention is sparse QSA; only the mechanics transfer)

- `qsa_decode_attn.cu`: split-K over selected cells — grid (64-cell chunk, kv head, query), per-chunk max/exp-sum/acc
  partials, then `attn_merge_kernel` (2 launches) (`:118-280, 522-546, 628-702`). KV formats int8 / rotated q4_0
  (FWHT-256, `kv_q4.cu:22-60`) / hybrid K8V4 (`3597c47f`: 816 vs 1,056 B/cell, 3090 decode 82-97 vs 75 t/s).
- Score phase: 12 shuffle reductions per cell made it ~53 µs/layer at T=1 on gfx1151, +32 µs per window row;
  `STRATA_ATTN_LANECELL` = one cell per thread for 3 heads, sequential butterfly order in registers (`8b30b1d5`).
- RDNA2: shuffles compile to `ds_bpermute_b32` sharing the LDS pipe with q reads; 8 cells/step + DPP exchanges took
  ds_bpermute count to 0 and prompt +7.4..+12.2% on RX 6900 XT although occupancy fell 9→6 waves/SIMD; "ROCm 10.0's
  hipcc does not turn an xor shuffle into DPP on its own" (`6126f8db`,
  `bench/results/2026-10-04-rdna2-pre75-attention/README.md:6-39,73-78`).
- KV append for all window tokens in one launch per pool (`44ffa86c`, `kv_append_q8_steps`/`kv_append_q4_steps`).

## 6. Head, argmax, sampling

- Multi-block argmax: up to 128 blocks × 4,096 logits per row, the **row's last block** (atomic counter) merges — one
  launch, no second kernel (`verify_kernels.cu:712-788`, `3e4aa1d6`). PR #2231 enables it on HIP: 12.0→5.6-6.0 µs a pick;
  and issues 4 (argmax) / 16 (exp-sum) loads per thread before using them: "one at a time the 1,024 sums' 243 loads each
  are a chain of memory round trips (31 µs a call ... 9.4 µs with sixteen)"; top-prob 12.3→9.4 µs; MTP row select over
  40 blocks 12→2.2 µs.
- Sampler (`05d4cb11`): split top-k — 4,096-logit blocks, per-warp top-k in registers, block merge, 1 warp per row tail;
  exact same list as the one-block reference.
- Head q8_1 interleaved once per window, then IL MMVQ for T≥2 (`verify.cpp:1771-1777`).

## 7. Launch-count reduction catalogue (with gains)

| technique | where | measured |
|---|---|---|
| per-token kernels batched over T | `4a50d4ce`, PR #783 | 2x3090 window 15.10→13.07 ms (−13.4%, whole #783 set) |
| producer writes consumer's q8_1 | QFUSE `22abb92d`, HC up `a9917a55` | harness −11..17%; engine ~0 (gfx1151) |
| producer writes interleaved copy | PR #2231 `MMVQ_IL_PLAIN` | part of +11.7% (not isolated) |
| pair launch / extra block | LFUSE `b08cf3e1` | −1.9% window (gfx1151) |
| KV append T tokens × K/V one launch | `44ffa86c`, `b08cf3e1` | in LFUSE |
| wait folded into following copy | `7fc02cb5`, PR #2231 | −2 nodes/layer; the whole gfx12 node-cut merge (HC norm from registers + folded waits + HC up owning q8_1 groups + hits in combine) +1.6-2.0% decode (`331b591b`) |
| memcpy node → copy kernel | `2e4ddf6e` (`copy_rows_strided`) | keeps chain kernel→kernel |
| one-token self-commit | `352cad8f` | removes commit graph for T=1 |
| draft front once | `ca833116` | — |
| conv+ab one launch | `a9917a55` | **−0.3% (slower)** |
| GDN split (adds a launch) | `e3c3d6ba`, `22abb92d` | +1.3% t/s |

## 8. HIP compat layer and RDNA tricks

- `include/strata/hip_compat/` (wave32, gfx1030/1100-1102/1150/1151/1200/1201): CUDA names → HIP; `intrinsics.hpp`:
  `__dp4a` → `__builtin_amdgcn_sudot4(true,a,true,b,c,false)` (v_dot4_i32_iu8, gfx11/12) / `sdot4` (gfx103x) / SDWA asm
  (gfx1012) (`:17-54`); `__byte_perm` → `__builtin_amdgcn_perm` (HIP's own indexes a private byte array = scratch
  traffic) (`:56-63`); SWAR `__vsub4/__vsubss4/__vcmpne4` (`:65-96`) — together +15% decode R9700, +5-7% 9070 XT
  (`600d7307`); full-mask-only shuffles (trap otherwise), `__syncwarp` = fence+wave_barrier on HIP<7, `__nanosleep` →
  `s_sleep 1`. `include/strata/platform/hip_compat/strata_hip.h` is the separate gfx906 wave64 shim (a CUDA warp = half
  wavefront).
- DPP: `__builtin_amdgcn_update_dpp(old, v, 0x160+M, 0xf, 0xf, false)` = row_xmask M∈{1,2,4,8};
  `__builtin_amdgcn_permlanex16(v, v, 0x76543210, 0xfedcba98, false, false)` = xor 16.
- Startup arch check vs compiled archs, wave32 required (`docs/AMD_HIP.md:141-144`); WMMA only in prefill/prompt
  attention (`v_wmma_f32_16x16x16_f16`, `v_wmma_i32_16x16x16_iu8`).
- Platform facts: dependent kernel ≈2.4 µs (gfx1201) / ≈2.7 µs (gfx1100) inside a graph; host function 15 µs vs
  stream write 6.7 µs; cross-stream events in a graph cost more than a small branch saves on discrete RDNA; 1 in ~10
  HIP starts gives a different greedy token somewhere ("not yet explained", `docs/AMD_HIP.md:370-371`); KFD userptr
  queue suspensions under host memory reclaim (`docs/AMD_HIP.md:244-268`).
- q8_1 finite clamp (#606, `include/strata/kernels/q8_1_finite.hpp:1-9`): fp16 `sum` of a block overflows (>65504) with
  one massive activation → inf·0 = NaN → one repeated token; same defect as ggml-org/llama.cpp#23606. Clamp to ±65504,
  bitwise for finite blocks.

## 9. Dropped / negative results relevant to us

- Decode-half switches (Q8/Q6 packed, MMVF_ROWS, LANECELL, EXPERT_V2, TSUM, LFUSE, GDN_SPLIT, QFUSE) together −4% on
  discrete gfx1201 (#1478); SH_STREAM −2% there.
- Plain-column IL never beat native in-engine on gfx1100 (PR #2231). IL bench overstated 2/4-row gains 20-60%.
- Q8 packed for 6144→2560 (+2-4% standalone, −3% in engine); <2048 rows lose.
- Q6 packed head at 4 columns: 0% on gfx1151.
- Conv+ab fusion −0.3%; GDN split at T=1 no gain; replay prefetch "with outputs lost (register pressure)"
  (`verify_kernels.cu:396-399`).
- gfx1100 rows-per-block autotune of expert/iq kernels: ≤1% (PR #744). GDN WY chunked prefill: −40% (PR #888).
- Graph-internal stream forks on HIP: large losses (R9700, RX 6800).
- hipBLASLt tables per (arch, version) matter for prefill, decode unchanged (docs/AMD_HIP.md:535-630).

## 10. Compared with our llama.cpp fork

| item | Strata | ours (from task context + quick look at `~/wt/k1`) | new for us? |
|---|---|---|---|
| graph per verify width | yes, inputs via mapped host mem | MTP chain as one graph; verify via ggml graph | input-via-mapped-memory, async commit [INFERENCE: check whether our verify graph is updated per step] |
| GDN rollback | replay on commit, no snapshots | K full-state snapshots per verify (`gated_delta_net.cu:183-195`) | **yes** |
| GDN grid | 4 blocks/head split, norm separate | `num_warps` shrinks to fill CUs (`gated_delta_net.cu:227-237`) | partially |
| multi-col MMVQ | load/apply traits, 2 rows/block, IL 2-4 cols, per-arch table | 2-8 cols, weights unpacked once/thread, DPP reductions | IL layout, TSUM, per-class rows table measured in-engine |
| same-input matrices | PAIR grid concat | gate+up fused per-thread failed (−8%, registers) | **grid concat is different and avoids registers** |
| q8_1 by producers | GDN norm, HC read (+IL copy) | q8_1 written by producers | IL copy by producer |
| Q6_K/Q8_0 planar repack | opt-in, gfx1151 | GGUF layout | yes |
| small serial kernels | NORM128, multi-block argmax, unrolled scans | ? | audit |
| q8_1 inf clamp | yes | ? | check |

---

## Transfer candidates (dense Qwen3.8-27B, one RX 7900 XTX, verify ~31 ms incl. ~3.2 ms gaps)

1. **GDN verify by replay instead of per-token snapshots** — mechanism: window GDN kernel reads state read-only and
   saves per-token post-conv q/k/v + g/β (T×(10240+96) floats/layer); after acceptance a replay kernel advances the
   state by `n_keep` tokens (Strata `verify_kernels.cu:396-463`); better for us: **fold the replay into the next
   window's GDN kernel** (replay previous n_keep, write committed state, then compute new outputs read-only) and/or one
   replay launch for all 48 layers. Strata gain: commit 39-46 µs/layer, window 23-27 µs/layer on gfx1151 with h_v 48
   (our geometry); no end-to-end isolate. Why for us: our fork writes up to T full 3 MiB snapshots per layer → at T=5
   ≈5 writes + 1 read = 864 MiB/verify (~0.9-1.2 ms) vs 2-3 passes (288-432 MiB) [INFERENCE ~1.5-3% of step]; needs
   changes in llama.cpp's recurrent-state rollback, so medium effort.
2. **Grid-concatenated "pair/triple" launches for same-input projections** — blocks beyond matrix 1 compute matrix 2
   with the unchanged per-thread code (`native_mmvq.cu:2406-2441`): qkv+z(+α/β Q8_0) in GDN layers, q+k+v in attention
   layers (k/v are only 1024 rows: latency-bound launches), ffn_gate+ffn_up (needs a two-type dispatch where types
   differ per layer). Strata: LFUSE −1.9% window (gfx1151). Why: our gate+up attempt failed on registers; this keeps
   registers identical and saves ~3.3 µs per removed node → 2-3 nodes × 64 layers ≈ 0.4-0.6 ms [INFERENCE].
3. **Audit and fix latency-bound small kernels on gfx1100** — idle row groups, one-block kernels, single-load chains:
   out-norm 9.3→2.0 µs/layer, argmax 12→5.6 µs, top-prob 31→9.4 µs with 16 loads in flight, row copy 12→2.2 µs
   (PR #2231, RX 7900 XTX). Why: our GDN gated RMSNorm runs 48×/verify and head/draft argmax every step; rocprofv3
   pass over kernels <20 µs is cheap; directly the same hardware.
4. **Q6_K output-head planar repack** (ql/qh/scales/d planes, aligned non-temporal dword loads, persistent grid) —
   Strata gfx1151: main head −5% at 1 col, 0% at 4 cols; draft head −28% at 1 col. Why: our head is Q6_K 995 MiB (largest
   single read, ~1.4 ms/verify at 700 GB/s) and the MTP reduced head is a row subset; uncertain at 5 columns (Strata saw
   no gain at 4); +~1 GB VRAM unless prefill reads the planes too — test only the head first.
5. **TSUM transposed butterfly for the NCOLS×ROWS final sums** (`s26_tsum.cuh`) — P−1+(5−log2 P) DPP moves instead of
   5P. Strata gfx1151: 54.21→52.10 ms/window (applied broadly). Why: we already use DPP (`~/wt/k1/.../mmvq.cu:702-711`),
   so the remaining gain is the move count only — small (<1%) but cheap; beware FMA contraction changing bits.
6. **In-engine measurement tooling** — in-graph `wall_clock64()*10` stamp kernels per stage, `DUMMY_NODES`-style node
   cost probe, rows/variant tables chosen from rocprofv3 times inside real decode (bench overstated 20-60%), rotating
   weight copies > 96 MB Infinity Cache in microbenches. Why: directly addresses K1 tuning risk (a wrong table cost −15%
   on a 4090).
7. **Interleaved q8_1 activation copy written by the producer** (`q8_1_il.cuh`; producer-written in PR #2231) —
   one `int4` load serves 4 columns. Strata gfx1100: only 1-2 rows/warp classes ≥4096 rows win ≥3%; plain-column variant
   never wins. Why: our MMVQ already shares weight unpack across columns; gain likely small at T=5, could matter more for
   K4 (9-16 columns, CP=8) — measure in-engine before investing.
8. **Host-overhead pattern for K3**: per-T graph replay with all per-step inputs in pinned mapped memory read by the
   first kernel, commit graph queued async on the same stream, copy kernels instead of memcpy nodes, no in-graph stream
   forks on HIP, `hipStreamWriteValue32` (6.7 µs) instead of host functions (15 µs), blocking sync instead of polling
   (polling cost 3%), pin the host thread and keep runtime/callback threads off it. Why: same HIP runtime behaviour;
   the value depends on how much per-step graph update our fork does [INFERENCE: check].
9. **q8_1 scale/sum finite clamp** (`q8_1_finite.hpp`) — bitwise for finite blocks; prevents NaN→repeated-token at
   massive activations (llama.cpp#23606). Why: zero cost correctness guard for every q8_1 producer we fused.
10. **Non-temporal weight loads** (`__builtin_nontemporal_load`) in MMVQ — keeps KV/activations/state in L2/IC. Strata
    uses it in packed kernels only (no isolated number). Why: cheap experiment on our 96 MB IC; sign unknown.
11. **Q3_K/Q6_K byte tricks** — Q3_K `__vsubss4` → OR (`native_mmvq.cu:1407-1421`); SWAR/`v_perm` gave +15% decode on
    R9700 (i-quants). Why: our `__vsubss4` uses `__builtin_elementwise_sub_sat` (codegen unchecked) and Q6_K is 17% of
    bytes; only matters if multi-column MMVQ is ALU-bound at T=5 — check ISA first. Q3_K share is 0.7% of bytes: skip.

Not transferable: doorbells/CPU experts, expert cache/PCIe share, router top-10, QSA indexer/select, PLE/hyper-connection
kernels (model-specific), PDL (CUDA sm_90+), MoE-motivated draft gating (`--spec-min-p 0.70` +10% on 7900 XTX MoE, PR #744
— consistent with our null result: dense verify cost is nearly flat in T).
