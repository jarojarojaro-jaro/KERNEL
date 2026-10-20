Done. Summary:

## What changed

One file: `ggml/src/ggml-cuda/mmvq.cu` (+88 / -25).

| item | change |
|---|---|
| `MMVQ_LAUNCH_BOUNDS_OCC(nthreads, max_waves, min_blocks)` (new macro, next to `MMVQ_LAUNCH_BOUNDS`) | CUDA: `__launch_bounds__(nthreads, min_blocks > 0 ? min_blocks : 1)`; HIP: falls back to `MMVQ_LAUNCH_BOUNDS` (min_blocks ignored) |
| `mul_mat_vec_q<...>` kernel template | new trailing param `int min_blocks = 0`; launch bounds now go through the OCC macro |
| `[GGML_CUDA_MMVQ_OCC]` host helpers (new, `#if !defined(GGML_USE_HIP)`): `mmvq_occ_type`, `mmvq_occ_value`, `mmvq_occ_min_blocks` | env read once (function-local static), values 8/10/12 accepted, anything else 0; per-type overrides `GGML_CUDA_MMVQ_OCC_{Q4_K,Q5_K,Q6_K,Q8_0,IQ4_XS}`, 0 disables one type |
| `mul_mat_vec_q_switch_fusion<...>` | new trailing param `int min_blocks = 0`, forwarded to the 3 kernel launches (fused path keeps `n1_rows = 0` explicitly, i.e. today's instantiation) |
| `mul_mat_vec_q_switch_ncols_dst` | new `launch_multi` lambda; `case 4/5/6` now call it. For the 5 occ types it dispatches at runtime to the `min_blocks` 8/10/12 instance, otherwise to the 0 instance |

Nothing else touched: lanes, `vdr`, `blocks_per_iter`, rows per block, block dims, and the reduction are untouched. Env unset -> only the 0 instance is launched, and that instance is bit-identical (see check below).

## Why it should be faster

At 5 columns (MTP verify batch) the kernels run 64-thread blocks, 2 rows/block, and 119-154 registers/thread, so only 6-9 blocks (12-18 of 48 warps) fit per SM. `min_blocks` caps registers (128 / <=102 / <=85 regs for 8 / 10 / 12) so more blocks stay resident; the 16-blocks/SM hardware limit caps this at 32 warps.

## Register / spill table (ptxas `-v`, sm_86, this tree)

`ncols_dst=5` (64 thr) - the verify shape; occupancy in blocks(warps)/SM after each row:

| type | plain 0 | plain 8 | plain 10 | plain 12 | fused 0 | fused 8 | fused 10 | fused 12 |
|---|---|---|---|---|---|---|---|---|
| Q6_K | 148 6(12) | 128 8(16) | 96 **SPILL 4/4** 10(20) | 80 12(24) | 154 6(12) | 128 8(16) | 96 10(20) | 80 12(24) |
| Q5_K | 127 8(16) | 127 8(16) | 96 10(20) | 80 12(24) | 128 | 127 | 96 | 80 |
| Q4_K | 119 8(16) | 119 8(16) | 96 10(20) | 80 12(24) | 123 | 123 | 96 | 80 |
| IQ4_XS | 111 9(18) | 111 9(18) | 95 10(20) | 80 12(24) | 117 | 113 | 96 | 80 |
| Q8_0 | 80 12(24) | 80 12(24) | 72 14(28) | 72 14(28) | 88 | 88 | 88 | 80 |

`ncols_dst=4` (128 thr, 4 warps/block - the cap forces <=64/48/40 regs, K-quants spill):

| type | plain 0 | plain 8 | plain 10 | plain 12 | fused 0 | fused 8 | fused 10 | fused 12 |
|---|---|---|---|---|---|---|---|---|
| Q6_K | 126 | 64 **SPILL 144/140** | 48 **SPILL 296/332** | 40 **SPILL 428/484** | 154 | 64 **SPILL 188/140** | 48 **SPILL 352/312** | 40 **SPILL 472/472** |
| Q5_K | 115 | 64 **SPILL 8/8** | 48 **SPILL 172/176** | 40 **SPILL 292/340** | 115 | 64 **SPILL 96/60** | 48 **SPILL 232/192** | 40 **SPILL 340/344** |
| Q4_K | 105 | 64 **SPILL 48/48** | 48 **SPILL 184/204** | 40 **SPILL 284/344** | 107 | 64 | 48 **SPILL 188/164** | 40 **SPILL 268/292** |
| IQ4_XS | 96 | 64 | 48 **SPILL 88/84** | 40 **SPILL 128/124** | 101 | 64 | 48 | 40 **SPILL 140/92** |
| Q8_0 | 66 | 64 | 48 | 40 **SPILL 92/92** | 72 | 64 | 48 | 40 **SPILL 128/88** |

`ncols_dst=6` (64 thr):

| type | plain 0 | plain 8 | plain 10 | plain 12 | fused 0 | fused 8 | fused 10 | fused 12 |
|---|---|---|---|---|---|---|---|---|
| Q6_K | 164 | 128 | 96 | 80 **SPILL 96/96** | 176 | 128 | 96 | 80 **SPILL 96/56** |
| Q5_K | 135 | 128 | 96 | 80 | 143 | 128 | 96 | 80 |
| Q4_K | 128 | 128 | 96 | 80 | 132 | 128 | 96 | 80 |
| IQ4_XS | 119 | 119 | 96 | 80 | 126 | 121 | 96 | 79 |
| Q8_0 | 86 | 86 | 80 | 80 | 94 | 94 | 94 | 80 |

All default (mb=0) numbers reproduce the brief's table. Only spills are flagged; everything else has 0 spill stores/loads.

## Verification performed (no GPU)

- Object compiles for sm_86 with the prepared dir; no new warnings. Compile time `nice -n 19 ninja -C build-sm86 -j 4 ...mmvq.cu.o`: **83.63 s -> 95.69 s** (+14.4%); object 5,395,880 -> 6,318,296 B; ptxas entry functions 722 -> 812 (+90 = 5 types x 3 ncols x 3 values x plain/fused, nothing else instantiated).
- **Bit-exactness of the unset path**: compiled `HEAD:mmvq.cu` and the new file to PTX with the identical nvcc command; all 468 pre-existing `mul_mat_vec_q` instances are textually identical after normalizing the mangled name (extra `Li0E`) and the global `$L__BB<n>_` label counter. `.minnctapersm 1` and `.maxntid` unchanged for the default instances; occ instances carry `.minnctapersm 8/10/12` with unchanged `.maxntid` (64 or 128 threads).
- **Host env logic** extracted verbatim into a scratch g++ test and exercised: unset -> 0; 8/10/12 -> that value; 7 -> 0; per-type override wins; override 0 disables one type; non-listed types (Q4_0, IQ4_NL) -> 0.

## Exact env values to test on the 3090

```
GGML_CUDA_MMVQ_OCC=8      # only Q6_K moves at n5 (148->128 regs, 6->8 blocks); others already <=8 blocks
GGML_CUDA_MMVQ_OCC=10     # all five types ~96 regs, 10 blocks; Q6_K plain spills 4 B
GGML_CUDA_MMVQ_OCC=12     # all five types ~80 regs, 12 blocks, no spills at n5
GGML_CUDA_MMVQ_OCC=12 GGML_CUDA_MMVQ_OCC_Q6_K=8      # per-type mix
GGML_CUDA_MMVQ_OCC=12 GGML_CUDA_MMVQ_OCC_Q8_0=0      # disable one type
```
Greedy md5 must match the unset run for every value.

## How to verify

```
cd /home/jaro/wt/nv-3090-occ
nice -n 19 ninja -C build-sm86 -j 4 ggml/src/ggml-cuda/CMakeFiles/ggml-cuda.dir/mmvq.cu.o
nvcc_cmd=$(ninja -C build-sm86 -t commands ggml/src/ggml-cuda/CMakeFiles/ggml-cuda.dir/mmvq.cu.o | tail -1)
sh -c "$(echo "$nvcc_cmd" | sed 's#-o ggml/src/ggml-cuda/CMakeFiles/ggml-cuda.dir/mmvq.cu.o#-o /tmp/occ-mm.o#' | sed 's#-MD -MT [^ ]* -MF [^ ]*##') -Xptxas -v" 2>/tmp/occ-ptxas.txt
```

Caveat worth knowing before GPU A/B: the env also covers `ncols_dst=4` (128-thread blocks), where the cap forces 64/48/40 regs and the K-quants spill 8-484 B. If the engine ever runs a 4-token batch through these kernels, expect a regression there; the 5-token verify path is spill-free at 8 and 12. `git diff --stat`: `1 file changed, 88 insertions(+), 25 deletions(-)`. Nothing committed, no GPU used.
