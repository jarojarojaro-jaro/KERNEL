# TensorFold: kernels, quantization, dispatch, and what transfers to our gfx1100 llama.cpp fork

Clone `~/research/TensorFold`, HEAD `0efbd447` (v1.0.8, 2026-10-12). Paths are repo-relative; `file:N` = line at HEAD
unless prefixed with a ref. PR heads were fetched read-only as `refs/pr/N` (e.g. `refs/pr/100:src/.../qmm_rocm.cu:139`).
Measured numbers come from commit messages, docs, CHANGELOG and issue/PR bodies. Anything I did not see stated there is
marked [INFERENCE]. Nothing was built or run.

**Where the code lives.** TensorFold 1.0.x serves Qwen3.8-27B from Zig on **Metal** (`zig/kernels/metal/{core,qwen27}`,
host in `zig/src/families/qwen27`). On **CUDA**, the 27B still runs on the **Python 0.6.x line** (`origin/python-0.6`,
`src/tensorfold/families/qwen3_5/cuda/README.md`; README.md:83). Its kernels are `src/tensorfold/cuda/kernels/{qmm.cu,
qmm_frag.cuh,gdn.cu,attention.py}`, and some are copied byte for byte into `zig/kernels/cuda/` (`gdn.cu:1`, `qmmf.cu:1`,
`lane_gemv.cu`). There are two **AMD** lines:
1. A PyTorch/ROCm port of the 27B CUDA path on an R9700 (gfx1201), PR #100 (closed, not merged). Its kernels are
   `refs/pr/100:src/tensorfold/cuda/kernels/{qmm_rocm.cu,attention_rocm.cu}`. Strix Halo GGUF is in PR #144.
2. A native Zig HIP engine on RDNA2/RDNA3 (W7800 gfx1100, V620 gfx1030): PR #490 (draft), being split into
   #607/#609/#611 (merged: build, caps table, runtime) and #617/#621/#631/#655 (open: kernels, affine tiles, Qwen3.5
   engine, RCCL).

At HEAD only a correctness kernel is in tree: `zig/kernels/hip/affine.hip:46-73`, plus the caps table
`zig/src/hip/caps.zig:41-46`.

---

## 0. TL;DR (what is new relative to Strata/kernels.md and our plan)

1. **Matrix units for the verify matvec, so extra rows are nearly free.** Every TensorFold backend runs 1-32 verify rows
   through a matrix-unit kernel that reads each weight once:
   - Metal M5 tensor ops: `lane_projection.metal:6`. M1-M4 simdgroup matrices: `simd_qmm.metal:1`.
   - CUDA `mma.m16n8k16`: `lane_gemv.cu`, `qmm_frag.cuh`.
   - gfx1201 WMMA: `refs/pr/100:.../qmm_rocm.cu:139-317`.

   Measured:
   - R9700: a 12-row verify's matmuls stream weights at **~80 % of 639 GB/s**, and **12 → 16 rows costs +1.2 ms per
     round** (~0.3 ms/row) on a 40 ms round (#100).
   - GB10 EXL3: every tensor is within 5 % from 1 to 16 rows (`docs/recipes/exl3.md`, Numbers).

   Our model is ~1.4 ms per extra verify column, plus an MMQ cliff at 9 columns that drops us to 47 t/s
   (roadmap B1, NOTES.md:159). Strata used WMMA only for prefill. **This is the most important new input for K4.**
2. **Persistent split-K without a reduce launch.** The K split is fixed by the weight's shape. The last-arriving block
   adds the slices in slice order, behind release/acquire fences and an atomic counter
   (`qmm_rocm.cu:284-309, 355-366`). Blocks are persistent and fetch the next item's weights a slab ahead
   (`qmm_rocm.cu:139-145, 181-222`), with non-temporal weight loads (`:148-160`). Same pattern on CUDA:
   `lane_gemv.cu:223` "the tile's last CTA sums slices in their original order"; EXLR8 job "sets" in `9b1aab43`.
3. **Software-pipelined weight loads are what reach ≥90 % of streaming bandwidth.**
   - M5 Ultra fz_lane: dense projections 3.32 → 2.70 ms at 1 row, **"1,032 GB/s, 96 % of a streaming read"** (`244989a3`).
   - GB10 EXL3: next k-step in flight gives +10-40 % (`38235a9c`).
   - GB10 FP8 lane matmul: pipeline stages aligned to 128-byte lines take a 12-row verify from **103 to 85 ms**
     (`docs/recipes/qwen3.8-27b.md:94-95`).
4. **Occupancy rule for decode tiles on gfx1100, measured on a W7800.** Columns per lane are chosen as the widest
   with `cols*bits ≤ 32` that still gives **≥3000 waves**. The 9B's 8-bit gate_up went 208 → 157 µs
   (514 → ~681 GB/s, computed), with no bit changes (`286840ac`, in `refs/pr/490`).
5. **Narrow matrices get more, thinner workers.**
   - One output row per simdgroup for 1-4 rows: router 0.146 → 0.069 ms (`22f41e22`).
   - Split-K over 2-4 "sets" when jobs < cores: 1.24-1.84× (`9b1aab43`, `5e449c7b`).
6. **GDN replay folded into the next window's kernel, and two reductions merged into one butterfly.**
   - CUDA `tree_kernel` first replays the previous window's kept rows from a `Pending` record and writes the
     committed state (`zig/kernels/cuda/gdn.cu:159-180`).
   - It then fuses each node's `k·s` reduction with the previous node's `q·s` output into one transposed butterfly
     (`gdn.cu:214-221`).
   - Metal has the same fold (`fn_gdn.metal:1-10`, FZ_GDN=2): "neither per-row states nor the round's 113 MB state
     copy are written" (`244989a3`).
   - The HIP engine on gfx1100 does it too: "a keep replays the kept rows' recurrence… the same bits for about 2 % of
     the memory" (`170df51e`, #490).

   Strata only *suggested* the fold. TensorFold ships it on three backends. Overlap: S4.
7. **Dispatch floor on Apple is about the same as ours.**
   - ~4.01 µs per dependent dispatch on M5 Ultra (`1fbd9ba7`).
   - A persistent grid-barrier "megakernel" lost (4.6-18 µs per phase).
   - Wins came from fewer dependent dispatches:
     - one command buffer per round: +3-5 % (`c6d5fd35`);
     - serial encoders plus inline group sums (−99 launches/step): +6 % (`3673a760`);
     - attention 7 → 4 dispatches per layer: +2.4-2.6 % (#712);
     - no 288 MiB/token GDN state publish copy: +2.6-4.0 % (#711).
8. **TensorFold's own gfx1100 kernels are not a source of speed for us.**
   - #490 W7800, 27B 4-bit: 25.8-27.7 t/s plain. That is ≈15 GB × 27.7 ≈ 420 GB/s end to end, about half of 864.
   - Matrix cores on/off changed decode by <5 %. Prefill was 639 t/s at 2k.
   - We are at 700 GB/s matvec and 660-910 t/s prefill.

   Reusable from it: the occupancy rule (item 4), the head-major KV pages (+2-3 % at 8k, `296bd68c`), and graph
   bucketing.
9. **Trellis (EXL3/EXLR8) costs speed and quality for little gain here.** On GB10, EXL3 3.00bpw reads 10.1 GB/token
   against 14.4 GB for MLX 4-bit, yet a 12-row round is only 75 vs 84 ms (−11 % for −30 % bytes). Chat acceptance
   fell from 4.2 to 3.0-3.3 tokens/round, so **chat decode was slower** (44.2 vs 49.7 tok/s); code was faster
   (83.4 vs 57.5) (`docs/recipes/qwen3.8-27b.md:118-133`). No HIP trellis kernel exists. Verdict for us: no.
10. **Numerics policy: row-invariance, not bit-exactness to an fp32 reference.** A row's bits must not depend on how
    many rows share its launch (1-128), its chunking or the graph replay. Each engine is its own serial reference.
    Accuracy is KL against an fp32/fp64 forward. Prefill arithmetic is allowed to differ from decode, so prompt-end
    states are kept and replies re-prefilled (§5).

---

## 1. Hardware-agnostic techniques (mechanism → gain → hardware → citation)

| # | Technique | Mechanism | Measured gain | HW | Citation |
|---|---|---|---|---|---|
| A1 | Matrix-unit verify matvec, rows padded to 16 | Weights decoded straight into B fragments (no LDS for weights), activations of ≤16/32 rows in LDS (`xsh[MT*16][SLAB*8+1]`, +1 pads banks), one weight read for all rows; 1 row also takes the MMA path so all row counts have the same bits | 12-row verify matmuls 29 of 37 ms at **~80 % of 639 GB/s**; 12 → 16 rows **+1.2 ms/round**; decode 98 → 128 t/s at 4k with "persistent WMMA decode, fused gate/up, launch cuts" | R9700 gfx1201 | #100 body; `refs/pr/100:.../qmm_rocm.cu:139-317` |
| A2 | Same on NVIDIA | `qmm_kernel` on weights packed at load into tensor-core fragment order; split by weight shape | 27B verify 12 rows 84 ms (MLX 4-bit, GB10) | GB10 | `src/tensorfold/families/qwen3_5/cuda/README.md` (python-0.6); `zig/kernels/cuda/lane_gemv.cu:1,223`, `qmm_frag.cuh` |
| A3 | Persistent blocks + slab-ahead prefetch across work items | Each block walks items `blockIdx.x, +gridDim.x…`; the next slab's weights (next item's first slab at item end) are loaded before this slab's MMAs, "so a short item does not pay a fresh memory latency" | part of 98 → 128 t/s above | gfx1201 | `qmm_rocm.cu:139-145,181-222`; grid = occupancy × CUs, evened over items, `:333-353` |
| A4 | Split-K fixed by shape, folded by the last arriving block | `wmma_slices`: fewest of 1,2,4,8,16 slices whose grid reaches `fill` (64 after tuning); slices write fp32 partials; `atomicAdd(counts)`; the last block adds in slice order and resets the counter. No reduce launch, deterministic | "K split target 128 → 64 blocks: every 27B projection read at 12 rows as fast or faster"; decode 16k 41.2 → 40.0 ms with stacked projections | gfx1201 | `qmm_rocm.cu:284-309,355-366`; #100 "Stacked input projections" |
| A5 | Non-temporal weight loads | `__builtin_nontemporal_load` for the weight words, "read once a step: keep L2 for x and partials" | not isolated | gfx1201 | `qmm_rocm.cu:148-160` |
| A6 | Next-group/next-tile prefetch during the current MMA | uint2 loads of the next group's codes/scales/biases during this group's tensor op | dense projections 3.32 → 2.70 ms (1 row), 3.43 → 2.78 (4 rows); **1,032 GB/s = 96 % of streaming**; engine 166.4 → 174.5 tok/s | M5 Ultra | `244989a3` |
| A7 | Coalesced warp load + shuffle hand-off for low-bit words, next k-step in flight | One warp loads a k-step's words as one run; lanes take their 2 words by shuffle | 2-bit q_proj 157 → 220 GB/s, o_proj 76 → 186, 27B 4-bit qkv 196 → 216; ≥7-bit prefetch −1-2 % so off; an earlier `cp.async` smem streaming was **3-5× slower** than per-lane cached loads | GB10 (237 GB/s streaming ceiling) | `38235a9c`; `docs/recipes/exl3.md` Numbers |
| A8 | Pipeline stages start on 128-byte lines | FP8 lane matmul stage alignment | 12-row verify **103 → 85 ms** | GB10 | `docs/recipes/qwen3.8-27b.md:94-95` |
| A9 | Stacked same-input projections as views | `[qkv|z|b|a]`, `[q|k|v]`, `[gate|up]` one matmul each, members kept as strided views (no memory added); glue kernels take row strides instead of copies | launches 1,007 → 943 per round; matmuls 30.3 → 29.2 ms; "removes about 200 kernel launches and 3 host syncs from every drafted round" (176 from views instead of copies) | gfx1201 + GB10 | #100 "Stacked input projections", "Every backend" |
| A10 | Occupancy rule for streaming decode tiles | Columns a lane takes = widest with `cols*bits ≤ 32` that still gives ≥3000 waves; "more, thinner waves" | 9B 8-bit gate_up 208 → 157 µs (514 → ~681 GB/s), qkv 112 → 83 µs, lm_head 2.2 → 1.75 ms; routed gate_up 26.5 → 23.1 µs | **W7800 gfx1100** (180 W cap) | `286840ac` (`refs/pr/490`); tile `refs/pr/621:zig/kernels/hip/tiles/stream.hpp:3` "a lane owns a 32-code chunk of a column; no LDS, lanes fold by shuffle" |
| A11 | Narrow kernels: one output row per simdgroup for 1-4 rows | Same per-row chain, 4× the simdgroups | router (256 rows) 0.146 → 0.069 ms; x projections 0.147 → 0.122 | M5 Max | `22f41e22` |
| A12 | Split-K "sets" for few, long jobs | 2 or 4 sets decode blocks s, s+S…, write per-block sums to threadgroup memory, set 0 folds in block order (bit-equal to 1 set) | gate/up at 1 row: 1.55-1.84× (M5 Max, 36 jobs), 1.37-1.50× (RTX PRO 6000), 1.24× (GB10); rule tuned to 4 sets ≤24 jobs, 2 ≤160 | M5/Blackwell/GB10 | `9b1aab43`, `5e449c7b`, `8bb6e285` |
| A13 | GDN: fold previous window's kept-row replay into the next window kernel | `Pending{k,v,g,beta,rows,counts}`: replay n kept rows on the register state, write the committed state, then run the new tree from registers/smem slots; no per-node state to global | "GDN tree kernel takes 8-35 % less time" (0.6.2, together with A14 + per-lane pointer loads + 8 value rows/warp on SM12); Metal: no per-row states and no 113 MB copy, engine +4.9 % (with A6) | RTX PRO 6000 / M5 Ultra | `zig/kernels/cuda/gdn.cu:159-180`; `fn_gdn.metal:1-10`; `60656c69`; `244989a3` |
| A14 | One transposed butterfly for two reductions | Node e's `Σ s·k` (memory term) and node e−1's `Σ s·q` (output) packed in `both[2R]`, one `spread_sum<2R>` (same as Strata TSUM) | inside the 8-35 % above | sm_120 | `gdn.cu:18-35, 214-221` |
| A15 | Tree states in registers | ≤16 tree nodes keep fp32 states in named registers (uniform switch on parent); snapshots only beyond | not isolated | Metal | `deltanet.metal:139-170` |
| A16 | No state publish copy | Chain rounds scan the state in place (`next_slot == slot`), publish copies only the conv history | **+4.0 % (2k), +2.6 % (16k)** plain decode; 288 MiB/token copy and 48 dispatches gone | M5 Max, 27B | #711 |
| A17 | Decode attention dependent-chain cuts | (a) chain rows attend in the prefix kernel (no tail kernel, no query repack); (b) merge prefetches 8 chunk partials and applies the attention output gate (gate dispatch gone); (c) a tile's two 128-wide head-dim halves on two simdgroups (few tiles at 1 row) | attention layer 7 → 4 dispatches, 5 → 3 barriers; **+2.6 % (2k), +2.4 % (16k)** | M5 Max, 27B | #712; `3262e703`, `dba7e18b`, `b8dfbb77` |
| A18 | GQA KV read once per KV head | A block scores a key for all query heads of a KV head (≤16) | 27B decode after 33k: **12.6 → 17.6 t/s**; 35B-A3B 39.7 → 69.4 | W7800 gfx1100 | `2b8852ea` |
| A19 | Head-major KV pages | A layer's pool is kv_heads runs of pages so a head's keys are one stretch | +2-3 % decode at 8k | W7800 | `296bd68c` |
| A20 | Tree attention: chunk-major, KV heads fastest, 16-key tile staged once for all (row, head) pairs; 4 loader waves double-buffered | Each key's K read together across heads/rows | 12-row round at 120k: Triton 160.4 → chunk-major 75.2 → WMMA 61.7 ms; per layer at 120k keys 1,908 → 1,324 µs | R9700 | #100 tables |
| A21 | Long-context attention on CUDA: key chunk read once for a round's rows, 16-byte loads | — | decode 128k **18.4 → 38.9** tok/s, 96k 23.6 → 45.9 | GB10 | CHANGELOG.md:379-381 |
| A22 | Wide top-k split over 16 workgroups + second merge dispatch | 15-row draft head over 98,592 columns used 15 cores before | drafted CLI **+3.7 % short, +12 % at 16k** (together with commit/draft overlap and a 4-key load-ahead in shared-context attention) | M5 Max | #713 |
| A23 | Index math and register pressure | Mojo re-implementation of the same WMMA lane matmul + tree attention, bit-identical; "most of the gain… 32-bit index math, register-pressure control, load scheduling" | **−6.6 % ms/round at 61.5k, −10.5 % at 123k**; launch overhead 1.56 µs (= hipcc) | R9700 | #406 |
| A24 | Draft windows sized by measured cost | Window/level costs timed once per build × chip × shape and cached; chains stop where the next verify row costs more than it saves | Nemotron CUDA +6-7 % | GB10, RTX PRO 6000 | `34c44245`; CHANGELOG.md:215-218 |

## 2. Metal-specific techniques

| Technique | Mechanism | Gain | Citation |
|---|---|---|---|
| M5 "tensor units" lane projection | 1-16 bf16 rows share each group's weight read; tensor product per group, then scale/bias FMAs; split-K order fixed | the default 27B decode path on M5 | `core/lane_projection.metal:6,95,233` |
| Pre-M5 simdgroup-matrix 4-bit tiles | 8-row tiles with a scalar twin for 1-2 rows sharing the same chains; nibbles masked in place against inputs pre-scaled by 2^-4s (exact) | "27B on M1-M4 decodes at 1.9 to 4x serial" (CHANGELOG.md:609); copy windows widen to **128 rows** (M3 Ultra edit 190 → 233 tok/s, CHANGELOG.md:349) | `core/simd_qmm.metal:1,21,24,124` |
| Row projection where tensor ops are slow | On M1-M4 the generated tensor-op coop kernels "run far under bandwidth"; 4 output columns a simdgroup, rows' own fp32 sums | Nemotron one-row step 8.0 → 5.0 ms, 119 → 193 tok/s (M3 Ultra) | `e473ec89`; `core/row_projection.metal:1,55` |
| Prompt matmul code unpack | 16-byte code loads, `bf16(128+q)` via OR 0x4300 in 16-byte stores, bias absorbs −128·scale, fp32 row sums | M5 Ultra 4096×24896 12.59 → 9.41 ms (66 → 89 TFLOPS); error vs fp64 **3.8e-3 → 1.1e-6** rms (the old bias term summed x in bf16) | `db78ea7b`; `core/affine_mm.metal:1` |
| Neural Engine MLP share for prompt chunks | Part of each MLP's gate/up on the ANE in fp16 planes, down partial summed on the GPU | (prefill; no isolated number) | `qwen27/mlp_ane.metal:1-42`; `34c44245` |
| One command buffer per round, GPU-side rounds | MTP absorbs kept rows and chains drafts into the next window's token slots on the GPU; host reads picks once a round | 110.7/117.8/106.7 → 114.4/123.2/112.3 tok/s; GPU busy 94-95 % | `c6d5fd35` |
| Serial dispatch encoders instead of a barrier after each launch; inline group sums | `FZ_SERIAL=1`, `FZ_FUSED_XSUM=1` (−99 pre-pass launches/step) | one row 88.0 → 93.5 tok/s; depth 3 123.2 → 128.9 | `3673a760` |
| Grid-barrier persistent kernel | Atomic spin barrier, coherent buffers | **loses**: 4.6-18 µs/phase vs 4.01 µs dependent relaunch | `1fbd9ba7` |
| Indirect command buffers with GPU-written jobs | Routed expert jobs and their threadgroup counts written on the GPU from the route, dispatched indirectly | no host round trip | `97b66fe7`; `zig/src/metal/icb.zig:1` |
| Keep-warm / residency sets | Idle ticker commits a tiny command buffer touching the residency sets | first-request latency | `83b032ff`; `zig/src/metal/keepalive.zig:1` |
| EXLR8 E4M3 rounding trick | Codebook halves XOR 0x1B60 (8 binades lower); E4M3 RNE = fp16 pattern's RNE at bit 7; one 32-bit integer rounding for two weights; next tile's words loaded ahead | layer 40 at 1 row: M5 Max 641 → 414 µs, M3 Ultra 600 → 382, RTX PRO 6000 301 → 266, GB10 907 → 861 | `51426b8e`; `core/exlr8_projection.metal:41,49` |
| Commit split from picks | Round command buffer split: picks + taps (host waits), then KV/state keep committed without wait and waited for just before the next verify | part of #713's +3.7/+12 % | #713 `4f5f387b` |

## 3. Bandwidth efficiency of 4-bit (and nearby) matvec

| Kernel | HW (peak) | Rows | Achieved | % | Citation |
|---|---|---|---|---|---|
| fz_lane DeltaNet in-proj | M5 Ultra | 1-4 | 1,032 GB/s | **96 % of measured streaming** | `244989a3` |
| EXL3 6-bit lm_head | GB10 (273; 237 streaming) | 1 / 16 | 226 / 222 GB/s | 95 % of streaming | exl3.md |
| EXL3 4-bit 27B in_proj_qkv | GB10 | 1 | 216 GB/s | 91 % of streaming | `38235a9c` |
| Nemotron 4-bit head | RTX 3090 (936) | 1 | 820 GB/s | 88 % of peak | `3cda8800` |
| Nemotron Mamba out (6.2 MB) | RTX 3090 | 1 | ~170 GB/s | latency-bound | `3cda8800` |
| WMMA verify, whole 27B matmul set | R9700 (640; 639 measured) | 12 | ~511 GB/s | ~80 % | #100 |
| HIP dot2 stream tile, 9B 8-bit gate_up | W7800 gfx1100 (864) | 1 | ~681 GB/s | ~79 % | `286840ac` |
| HIP engine 27B 4-bit end to end | W7800 | 1 | ~420 GB/s (15.1 GB × 27.7 t/s) | ~49 % | #490 table [computed] |
| **Ours** MMVQ | 7900 XTX (960) | 1 / 5 | 780-845 / ~700 GB/s | 81-88 % / 73 % | NOTES / roadmap B9 |

They state efficiency against a **measured streaming read** (639 GB/s on R9700, 237 on GB10). For K1 we need our own
denominator: a rocm-bandwidth-test or hipMemcpy D2D read on the 7900 XTX at 285 W. Our 73 % of spec may be about
80-85 % of streaming [INFERENCE].

## 4. Few-column (verify) matvec design

- **Contract:** 1-32 rows through the same kernel family. The registry refuses a path whose family changes with row
  count (#613; `refs/pr/621:zig/src/hip/tuning/gfx1100.zon:13-19`). On CUDA/Metal/gfx1201 that family is a matrix-unit
  kernel with rows padded to 16.
- **gfx1201 (#100):** `gemv_kernel` with `v_dot2_f32_bf16` is "fastest at one row, compute bound in draft windows"
  (`qmm_rocm.cu:1-2`). `wmma_kernel` (default) takes 16 or 32 rows a pass (`MT` tiles share each weight fetch, `:162-166`).
- **gfx1100 (#490/#621):** the table keeps the **dot2 stream tile up to 15 rows** and matrix cores from 16. The table
  itself says these "are the thresholds the launches kept before the registry; a measured table replaces them"
  (`gfx1100.zon:9`), and on the W7800 matrix cores on/off changed decode by <5 % (#490). So there is **no gfx1100
  evidence that WMMA beats dot products at ≤12 rows**. Their dot2 path was far from bandwidth-bound anyway (~49 % end
  to end).
- **Cost of rows:** R9700 12 → 16 rows +1.2 ms on 40 ms (#100: "16 verify rows accepted no more on this prompt and
  cost 1.2 ms a round"); `max_rows` stays 12 because 16 rows helped code (+13-19 %) and hurt prose (−9 %). GB10 EXL3
  1 → 16 rows ≤5 %. M3 Ultra copy windows up to 128 rows.

## 5. Numerics policy (vs Strata's "bitwise to previous code")

- **Row invariance is the invariant.** "Every kernel on the verify path gives a row the same bits whether it runs
  alone or as one of up to 128 rows… Serial decoding runs through the same kernels" (python-0.6
  `qwen3_5/cuda/README.md`). Tools that enforce it:
  - K split fixed by weight shape (`qmm_rocm.cu:355-366`);
  - last-block fold in slice order;
  - `-ffp-contract=off` on HIP (`affine.hip:1`; #100 maps `--fmad=false`);
  - explicit bf16 RNE with NaN kept (`affine.hip:30-36`);
  - ties to the lower token id (`bf16_topk.metal:1`; #100 replaced ROCm's unsorted `topk`).
- **Each engine is its own reference.** Bits differ between Mac, CUDA and ROCm, and can change between releases when
  error versus fp64 is no worse. Example: 1.0.3's own Nemotron kernels changed greedy tokens at near-ties
  (CHANGELOG.md:158). Example: `527a6a84` changes a fold's association.
- **Accuracy gates.**
  - HIP: KL ≤ 1e-2, top-1 ≥ 90 %, perplexity within 2 % vs fp64 (#490). 27B 4-bit on W7800: KL 1.5e-4, top-1 99.37 %.
  - Every tile is checked vs float64 at the fp32-sum error bound (#621).
  - CUDA prompts: bf16 KL **0.0031 vs FP8 0.0624** (20×, CHANGELOG.md:338-339); perplexity +4.1 % vs +0.03 %
    on code (#100 comment).
  - R9700 MLX-4bit FP8 prompts KL 0.0275 vs bf16 0.0007 (#100 comment).
- **Prefill may differ from decode.** Prompt kernels round differently, so prompt-end states are kept and the reply is
  re-prefilled on the next turn (python-0.6 `qwen3_5/cuda/README.md`).
- **Bias/group-sum precision matters.** Moving the affine bias term from bf16 to fp32 row sums cut prompt-GEMM error
  3.8e-3 → 1.1e-6 rms (`db78ea7b`). All TensorFold projections take fp32 group sums of x (`qmm_rocm.cu:4`, `xs`).
- **Strata comparison.** Strata's bar is "same bits as the old kernel", with KL-gated opt-ins. TensorFold's bar is
  "same bits regardless of batch/chunk, KL vs fp64". For us that maps to drafted == non-drafted at T=0, which llama.cpp
  does not give: 1-column MMVQ and multi-column/MMQ reduce differently [INFERENCE]. That costs correctness tests, not
  speed.

## 6. Launch/dispatch overhead strategy compared

| Platform | Floor per dependent launch | What they did | What did not work |
|---|---|---|---|
| Metal M5 Ultra | **4.01 µs/phase** (`1fbd9ba7`) | One command buffer per round; serial encoders; GPU-side rounds; ICB with GPU-written jobs; inline group sums; dispatch cuts in attention (7 → 4) | Persistent grid-barrier megakernel (4.6-18 µs/phase) |
| CUDA 3090/GB10 | Graph vs eager at 1 row 5.52 vs 5.81 ms → "node gaps are not the cost" (`3cda8800`, RTX 3090 Nemotron) | Graph per row-count/level, captured at first sight; inputs in stable buffers; Nemotron 15 draft levels, one graph each | — |
| HIP gfx1100 (#490) | not measured | Graph per bucketed round shape, captured when first met (`3bb5a43c`); the round plan uploaded as the graph's first node (`230cc8ef`); a speculative round = 2 replays (verify, drafts) | Graphs off for prefill chunks, opt-in under tp |
| gfx1201 (#100) | 1.56 µs launch (hipcc and Mojo, #406) | Views instead of copies (−176 launches/round), stacked projections, no split-K reduce launch, sync only when tracing | — |
| **Ours** | **3.2-3.4 µs** per boundary in a HIP graph | roadmap A3-A6 | megakernel listed in "Avoid" (roadmap C) |

Their megakernel result on Apple agrees with our "Avoid". What is new is the order of magnitude: Apple's floor
(~4 µs) is about ours (3.3 µs), and their whole Metal programme is dispatch-count cutting with no attempt at
persistence.

## 7. Trellis / EXL3 / EXLR8: any value for us?

**Format** (`docs/recipes/exl3.md`, "The format"):
- Weights: `W = diag(suh) H_K W_q H_N diag(svh)`, with H the 128-point Hadamard.
- W_q is 16×16 tiles of a circular bitstream. Each value is the 16 bits ending at its position, mapped by a hash
  codebook (`3inst`, `mcg`, `mul1`: one 32-bit multiply, a byte sum and one fp16 FMA).
- Decode is all ALU and no table. Input rotation runs once per call.
- EXLR8 (`docs/glm-5.3-exlr8.md`) is the same trellis decoding to E4M3, with the rounding trick in §2.

**Speed evidence:**
- GB10 EXL3 kernel at 1-16 rows: 173-226 GB/s of 237 streaming, i.e. 73-95 %. Getting 2-bit there needed the
  shuffle/prefetch rework (+40 %).
- End to end on the 27B, 3.00bpw against MLX 4-bit: round 75 vs 84 ms for 10.1 vs 14.4 GB/token. The bytes did not
  translate 1:1, because the decode costs ALU and the non-matmul time is fixed.
- On a 12-row MLX verify, GB10 matmul time is about ~84 ms − rest [INFERENCE: unknown split].

**Quality/acceptance evidence:** DFlash2 accepted 3.0-3.3 vs 4.2 tokens/round on chat with 3.00bpw. Chat decode was
44.2 vs 49.7 tok/s (slower); code was 83.4 vs 57.5 (faster). The 3.00bpw size is well below ours (~5 bpw effective
for UD-Q4_K_XL 17.6 GB).

**For our 7900 XTX:**
- **Decode speed.** A ~4.0 bpw trellis 27B (~13.5 GB [INFERENCE]) at our 700 GB/s would cut matvec by ~(17.6 −
  13.5)/0.7 ≈ 5.9 ms/step, about +17 %, *if* a HIP trellis kernel matched MMVQ's bandwidth. No such kernel exists:
  ExLlamaV3 ROCm closed at ≈15 t/s (roadmap C), and TensorFold's EXL3 kernel is CUDA-mma-only. gfx1100 has no FP8. The
  mul1 decode is ~5-6 integer/fp ops per weight [INFERENCE]; at 1-5 columns that is a large fraction of a matvec's
  VALU budget. TensorFold needed heavy tuning just to reach ExLlamaV3's level on GB10.
- **Quality.** Requantizing the trunk "changes the model" (roadmap C). The measured acceptance drop for a drafter
  trained on the unquantized model applies equally to our MTP head.
- **Verdict:** no for decode speed now. If VRAM, not speed, becomes the constraint (e.g. q8_0 KV at 200k), ik_llama.cpp's
  trellis IQ*_KT types are the in-ecosystem route, not EXL3. That is [external, not verified here].

## 8. HIP/AMD material in TensorFold, in detail

| Item | Content | Numbers | Reuse on gfx1100? |
|---|---|---|---|
| `zig/kernels/hip/affine.hip` (HEAD) | Naive bf16 × 4-bit row projection, 2 warps/block, fp32, `-ffp-contract=off` | none | no (correctness reference only) |
| `zig/src/hip/caps.zig:41-46` | gfx1030 (wave32, dot2_f16, sdot4/8, no matrix, fp16 act), gfx1100-1103 (dot2_bf16, `wmma11`, bf16), gfx1150-1153, gfx1200/1201 (`wmma12`) | — | a table, nothing new |
| #490 / #617 / #621 / #631 (open) | Full Zig HIP engine for Qwen3.5/3.6/3.8-27B: dot2/stream/K-parallel/matrix tiles, `gated_delta.hip`, `gdn_prefill.hip` (ported from vLLM by hand, SPDX dropped `5d058942`), paged attention, graphs, RCCL tp | W7800 27B 4-bit: 25.8/27.2 t/s served, 27.7 without MTP; MTP did not help 27B (27.7 → 27.2 at 2 drafts); prefill 639 (2k) / 424 (64k) with matrix cores, 394 without; tp2 41.6 t/s | occupancy rule `286840ac`, GQA-once `2b8852ea`, head-major pages `296bd68c`; the rest is slower than our fork |
| #100 (closed) | PyTorch ROCm on R9700: `qmm_rocm.cu` WMMA decode (gfx12 builtins), `attention_rocm.cu` WMMA flash prompt + tree attention, FP8 KV (256 e4m3 + power-of-two exponent per token/head, 272 vs 512 B) | DFlash2 96-126 t/s vs 34 plain; prefill 1,834-2,121 t/s (FP8 GEMM 150-158 TFLOPS); prompt attention 78 TFLOPS vs Triton 48.9; 64k round 48.7 → 46.5 ms with FP8 KV | Design yes (A1-A5, A9, A20), code no: gfx12 WMMA operand layout differs from gfx11 [INFERENCE: on gfx11 wave32 the A/B inputs are replicated across the two half-waves, so a lane holds 16 K-values, not 8] |
| #144 (closed) | Strix Halo gfx1151, GGUF UD-Q4_K_XL via "Gufo" kernels: W8A8 WMMA prefill (Q8_1 activations), Gufo decode GEMV at 1 row; verify stays on the exact kernel ("WMMA and bf16 for verify… changed drafted replies and were not faster") | prefill 193 vs 77 t/s exact (8.6k); decode 25-37 t/s drafts, 10.5 plain | confirms our llama.cpp-style W8A8 prefill; nothing new |
| #406 (proposal) | Mojo WMMA lane matmul + tree attention, bit-identical | −6.6 % / −10.5 % per round at 61k / 123k | the lesson (32-bit index math, register pressure) yes |
| Traps found | Triton buffer loads read zeros at negative offsets (`AMDGCN_USE_BUFFER_OPS=0`); Triton 3.6 miscompiles 128×256 bf16 tiles and pipelined e4m3 at few rows on gfx1201; ROCm `topk` unsorted, tie order varies; torch `topk` out-of-range index on gfx1151; expandable segments near full VRAM changed finished values | — | relevant only if we use buffer intrinsics with negative offsets |

---

## 9. Transfer to our gfx1100 HIP llama.cpp fork (ranked)

Baseline: step 35.7 ms, verify ~31 ms (incl. ~3.2 ms gaps at 3.3 µs/kernel), matvec ~700 GB/s at 5 columns.
1 ms/step ≈ +2.9 % t/s at 3.16 tok/step.

### T1. WMMA (iu8) "MMVQ-wide" kernel for 6-16 verify columns. Overlap: K4 (enabler), K1. **Highest value, high effort**
- **Mechanism:**
  - One wave owns 16 output rows. Weight blocks go global → VGPRs, unpacked to int8 B fragments (Q4_K nibbles, Q5_K
    with the high bit, Q6_K, IQ4_XS via table, Q8_0 direct). No LDS staging of weights; this is the difference from
    llama.cpp MMQ.
  - q8_1 activations of ≤16 columns go to LDS once per K-slab, padded against bank conflicts.
  - `v_wmma_i32_16x16x16_iu8` per 16-K step. Per 32-K sub-block, i32 → f32 FMA with the row's `d·scale` and the
    `dmin·m·sum` term from q8_1 `ds`.
  - Persistent grid = occupancy × 96 CUs. The next slab is prefetched before the current WMMAs (A3).
  - The K split is fixed by shape and folded by the last-arriving block (A4).
  - Non-temporal weight loads (A5; roadmap B9 says `slc`, never `dlc`).
- **TensorFold gain:**
  - R9700: 12-row verify matmuls at ~80 % of streaming; +0.3 ms per extra row from 12 → 16 (#100).
  - GB10: 1 → 16 rows ≤5 %.
  - On gfx1100 itself there is **no positive evidence** (#490's untuned table, matrix on/off <5 % in a slow engine).
- **Why it might apply:** our cliff is at 9 columns (MMQ: LDS-staged weight tiles, mmq_y=128, stream-K fixup); 47 t/s
  at n=8 (NOTES.md:159). Our per-column marginal is ~1.4 ms (roadmap B1 model) against ~0.3 ms on R9700.
  [INFERENCE] RDNA3 WMMA iu8 peak ≈ 123 TOPS. A 16-column pass over 27e9 weights is 0.86 TOP, ≈ 7 ms at peak against
  ≈ 23-25 ms of bandwidth time, so a well-pipelined kernel stays bandwidth-bound.
  The gfx11 operand replication across half-waves doubles VGPR footprint per fragment. It needs a DPP/permlane or LDS
  hand-off of weight words, or a duplicated load (2× L1/L0 traffic, same DRAM).
- **Expected:**
  - If the marginal drops from 1.4 to ~0.4 ms/column, a 12-column verify costs ≈ 31 + 7×0.4 ≈ 34 ms instead of
    ≈ 41 ms.
  - That turns roadmap B1's projected code +28 % / recall +61 % (RDNA4 rdna-boosts data) from "blocked by cost" into
    reachable. At T=1 chat, about 0 (acceptance-capped).
  - At 5 columns, a gain over today's MMVQ is possible only if WMMA frees VALU for loads [INFERENCE: measure].
- **Effort:** high. One kernel template per K-quant type in our mix plus the dispatcher.
- **Risk:** medium (VGPR pressure, occupancy, Q6_K/IQ4_XS unpack cost).
- **Where:** new `ggml/src/ggml-cuda/mmvq-wmma.cu` (or an `mmq.cuh` small-N specialization), dispatched from
  `ggml_cuda_mul_mat` for `ne11 ∈ [6,16]` under `GGML_HIP_RDNA3`.
- **Gate before investing:** microbench Q4_K 5120×17408 at 8/12/16 columns against MMVQ-8 and MMQ, rotating weight
  copies larger than 96 MB IC (Strata's warning: microbench overstated 20-60 %; measure in-engine with rocprofv3).

### T2. Software-pipelined weight fetch and occupancy rule in MMVQ. Overlap: **K1**
- **Mechanism:**
  - Load block b+1's weight ints (and scales) into registers before computing block b; explicit double buffer, not left
    to the compiler.
  - Size columns/rows per lane so the grid supplies ≥ ~1.5-2× resident waves. Their rule is cols·bits ≤ 32 and ≥3000
    waves on a 70-CU W7800 [INFERENCE: ~4,100 on 96 CUs].
  - Report efficiency against a measured streaming read.
- **TensorFold gain:**
  - W7800 gfx1100: 514 → ~681 GB/s (+32 %) on an 8-bit GEMV (`286840ac`).
  - M5 Ultra: −19 %, to 96 % of streaming (`244989a3`).
  - GB10: +10-40 % (`38235a9c`).
- **Why it applies:** multi-column MMVQ is at 73 % of peak against 81-88 % at n=1, which points to latency/ALU
  rather than DRAM. Prefetch hides the per-iteration dependency on 4-wave blocks.
- **Expected:** each +50 GB/s on ~22 ms of 5-column matvec saves ~1.5 ms/step (+4.4 %). Reaching 800 GB/s saves
  ~2.7 ms (+8 %).
- **Effort:** low-medium (`mmvq.cu` inner loop, per-type `vec_dot` split into load/apply as in Strata's traits).
  **Risk:** low (bit-identical if order is kept).

### T3. Few-job / narrow matrices: one row per wave, split-K "sets". Overlap: **K1/K2**
- **Mechanism:** for small-output matrices (ssm_alpha/beta 48×5120, attn_k/v 1024 rows, MTP small projections), give
  each output row its own wave, or split K over 2-4 wave sets folded in order. They are latency-bound.
- **TensorFold gain:** router 0.146 → 0.069 ms (M5 Max); gate/up 1.24-1.84× (M5, RTX PRO 6000, GB10).
- **Expected:** the alpha/beta pair costs 17.5 µs today (roadmap A4). 48 GDN layers × ~8 µs saved ≈ 0.4 ms
  (+1.1 %) [INFERENCE]; overlaps A4's fusion, which removes the kernel instead.
- **Effort:** low. **Risk:** low.

### T4. Fold GDN replay into the next verify's GDN kernel; one butterfly for both reductions. Overlap: **S4**
- **Mechanism:**
  - Window GDN kernel: first replay `n_keep` rows of the previous window from saved post-conv k/v/g/β, write the
    committed state once, then compute this window's T outputs from registers. No per-token snapshots (`gdn.cu:159-180`).
  - Fuse node e's `s·k` with node e−1's `s·q` into one transposed butterfly (`gdn.cu:214-221`).
- **TensorFold gain:**
  - 8-35 % GDN kernel time (sm_120, with other changes).
  - Metal: no per-row states and no 113 MB copy (+4.9 % with fz_lane).
  - #711: removing a 288 MiB/token state copy gave +2.6-4.0 % on M5 Max.
  - HIP gfx1100: same bits at ~2 % of the memory.
- **Expected:** Strata arithmetic: snapshots at T=5 are ~864 MiB/verify against 288-432 MiB. That is −0.5-0.8 ms of
  traffic plus 48 fewer launches (≈0.16 ms) → +2-3 %. The butterfly merge adds +0.3-1 % of GDN time [INFERENCE].
- **Effort:** medium-high (llama.cpp recurrent-memory rollback semantics). **Risk:** medium.
- **Where:** `gated_delta_net.cu` plus `llama-memory-recurrent.cpp`.

### T5. Attention-layer chain cuts. Overlap: **K2**
- **Mechanism:**
  - (a) Apply Qwen's attention output gate `sigmoid(gate)·o` inside the FA combine/output kernel. That removes one
    elementwise kernel per attention layer (16/step).
  - (b) Make verify rows (a chain) attend through the main FA pass with per-row causal key counts, so no separate
    tail/combine for the window's own keys [INFERENCE: check whether our q4_0 GQA FA already handles the window inside
    one pass].
  - (c) When tiles are few (short context, T=5), split head_dim 256 across two waves.
  - (d) Prefetch 8 split-K partials in the combine.
- **TensorFold gain:** +2.4-2.6 % on M5 Max (attention 7 → 4 dispatches per layer).
- **Expected:** (a) alone is 16 kernels × (3.3 µs gap + ~3 µs run) ≈ 0.1 ms (+0.3 %). (b)-(d) matter at 94k, where
  attention is ~4.8 ms/step [INFERENCE from 78 vs 88 t/s]; −10 % of that is 0.5 ms (+1.4 %).
- **Effort:** low for (a), medium for the rest. **Risk:** low.

### T6. FA kernel: 32-bit index math, register-pressure audit, load-ahead. Overlap: long-context part of **K2**, B4
- **Mechanism:** replace size_t/int64 offsets in inner loops with 32-bit (`v_mad_u64_u32` and 64-bit adds are 2-4×
  VALU). Cap VGPRs to keep ≥2 waves/SIMD. Issue K/V tile loads a tile ahead.
- **TensorFold gain:** Mojo rewrite of the same R9700 kernels: −6.6 % per round at 61k, −10.5 % at 123k.
- **Expected:** at 94k, 10-20 % of ~4.8 ms ≈ 0.5-1 ms (+1.5-3 % at long context, ~0 at short).
- **Effort:** low to audit (disassemble `fattn-*` for gfx1100), medium to fix. **Risk:** low.

### T7. Multi-block argmax/top-k for wide rows. Overlap: **K2** (Strata transfer #3 already lists it)
- **TensorFold gain:** part of +3.7 % (short) / +12 % (16k) drafted on M5 Max (#713).
- **For us:** the MTP draft argmax over the 64k reduced vocab (4×/step) and verify argmax over 248k × 5 rows. Strata
  measured 12 → 5.6 µs on the same card. That is ~0.05-0.1 ms/step (+0.2 %). Small.

### T8. Stacked projections / strided glue instead of copies. Overlap: **K2**
- **Mechanism:**
  - Grid-concatenate same-input matrices: qkv+z(+α/β), q+k+v, gate+up. This is Strata's PAIR; TensorFold uses views
    of one stacked weight.
  - Make glue kernels take strides so `ggml_cont` copies disappear.
- **TensorFold gain:** R9700 −64 launches and −1.1 ms of matmul per round (stacking plus K-split retune); −176
  launches from views.
- **For us:** UD-Q4_K_XL mixes types per tensor, so stacking is only possible where types match. Copy-elimination
  needs a trace of which `cpy/cont` nodes remain per layer.
- **Expected:** 0.3-0.6 ms (+1-2 %), consistent with roadmap A3-A5.

### T9. Numerics items. Overlap: **S1**, K5
- **S1:** TensorFold avoids the fp16 q8_1 `s` overflow by design (fp32 group sums `xs`). Their prompt-GEMM error
  dropped 3.8e-3 → 1.1e-6 rms once the bias × sum term was summed in fp32 (`db78ea7b`). Keep the S1 clamp as planned
  (zero cost). Storing `s` in fp32 would change `block_q8_1` and is not worth it [INFERENCE].
- **K5:** the evidence says lower-precision prefill *activations* cost real KL: FP8 e4m3 rows KL 0.0624 vs bf16
  0.0031; R9700 0.0275 vs 0.0007. Our q8_1 (int8 per 32 values, fp16 scale) is much finer than per-row e4m3, so no
  action. Do not adopt an FP8/INT4-activation prefill idea from any engine.
- **Drafted == serial:** our multi-column MMVQ/MMQ and 1-column MMVQ reduce in different orders, so greedy MTP output ≠
  greedy plain output at near-ties [INFERENCE]. TensorFold makes this an invariant. For us it is a testability
  question; worth a note in `greedy_check.sh` expectations, not a speed item.

### T10. Low-value or already-covered
- Head-major KV pages (+2-3 % at 8k, `296bd68c`): llama.cpp's KV is `[head_dim, n_head_kv, ctx]`, so one head's q4_0
  keys are 144-B runs with a 576-B stride. Since all 4 KV heads are read concurrently, L2 likely absorbs it
  [INFERENCE]. Check only if the FA kernel walks heads in separate passes.
- 128-byte line alignment (A8): our Q4_K 144-B blocks are row-contiguous, so the waste is at most one partial line per
  row per wave [INFERENCE: small]. Strata's planar repack (Q6_K head) remains the alignment experiment to run.
- Trellis/EXL3: no (§7).
- Metal ICB / one command buffer per round / keep-warm: our HIP-graph-per-step path already has the analogue.
  Megakernel: rejected by both TensorFold (Metal) and our roadmap.

## 10. New vs `research/strata/kernels.md`

| Topic | Strata | TensorFold | New for us? |
|---|---|---|---|
| Verify matvec on matrix units | WMMA only in prefill; dp4a IL MMVQ 2-4 cols | Matrix-unit verify on every backend; R9700 80 % at 12 rows, +0.3 ms/row | **Yes**: the K4 enabler (T1) |
| Split-K | Multi-block argmax with last-block merge | Matmul split-K fixed by shape, last-arriving block folds in order, persistent + slab-ahead | **Yes** for matmul (T1/T3) |
| Software prefetch | Grid-stride kept "for registers"; IL loads | Explicit next-group/tile prefetch: 96 % streaming (M5), +10-40 % (GB10) | **Yes** (T2) |
| Occupancy rule | Per-class rows table measured in-engine | cols·bits ≤ 32 and ≥3000 waves, measured on gfx1100 | Partly: a rule, not a table |
| GDN rollback | Replay in a separate commit graph; fold only suggested | Fold implemented (CUDA `Pending`, Metal FZ_GDN=2, HIP keep); fused double-reduction butterfly | **Yes**: confirms S4 design and measured +2.6-4 % from copy removal |
| Attention dispatch chain | Split-K merge kernels | Gate into merge, no tail kernel for chains, head-dim split across waves | **Yes** (T5) |
| FA long-context tuning | LANECELL, DPP | 32-bit index math / register pressure −6.6..−10.5 % (R9700) | **Yes** (T6) |
| Launch floor | 2.4-2.7 µs dependent kernel (HIP graph) | Metal 4.01 µs; grid-barrier megakernel loses; CUDA 3090 graph vs eager ~5 % | Confirms "Avoid megakernel" |
| Numerics | Bitwise vs old code, KL-gated opt-ins | Row-invariance across batch/chunk, KL vs fp64, prefill ≠ decode | **Yes**: different contract (T9) |
| Low-bit formats | i-quants, Q8/Q6 planar repack | EXL3/EXLR8 trellis, NVFP4/FP8 exact-in-bf16 reads | Evaluated: no (§7) |
| q8_1 inf clamp | Yes | N/A (fp32 sums) | Supports S1 as-is |
