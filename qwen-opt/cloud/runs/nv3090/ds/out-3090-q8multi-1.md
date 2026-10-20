## Report: `GGML_CUDA_MMVQ_Q8_WIDE` (env-gated, default off, bit-exact)

### Files/functions changed
Only `ggml/src/ggml-cuda/mmvq.cu` (+77/−6). `vecdotq.cuh` untouched (no new helpers needed).

1. `mmvq_xs<GGML_TYPE_Q8_0> { int v[2]; float d; }`, `mmvq_ys<GGML_TYPE_Q8_0> { int u[2]; float d; }` — falls into `mmvq_dot`'s default branch: `dp4a` over the same two ints, then `x.d * u.d * sumi`, i.e. the same `d8_0*d8_1*((float)sumi)` as `vec_dot_q8_0_q8_1_impl`.
2. `mmvq_load_x<Q8_0>`: two `get_int_b2(b->qs, iqs + l)` + `__half2float(b->d)` — byte-for-byte what `vec_dot_q8_0_q8_1` does. `mmvq_load_y<Q8_0>`: `mmvq_ld_ints<2,4>` of the two q8_1 ints + the `d` half.
3. `mmvq_q8_wide_type()` / `mmvq_q8_wide_on()` (NVIDIA-only), carrying the bit-exactness argument in the comment (same `vdr`=2/`qi`=8 → same thread→(kbx,kqs), same nwarps/rows/reduction, same ints, same float expression, same accumulation order into `tmp[j][i]`, shared epilogue).
4. `mul_mat_vec_q`: new trailing `bool q8_wide = false`; `use_q8_wide = q8_wide && type == Q8_0`; `use_multi = (mmvq_has_multi(type) || use_q8_wide) && ncols_dst >= MMVQ_MULTI_MIN_NCOLS`.
5. `mul_mat_vec_q_switch_fusion`: trailing `bool q8_wide = false`, threaded into the 3 kernel instantiations.
6. `mul_mat_vec_q_switch_ncols_dst`: before the ncols switch, NVIDIA-only dispatch for Q8_0 at 2..8 columns using exactly the generic cases' launch params (`small_k=false, halve_iters=false, n1_rows=0`), so block/rows/vdr are unchanged — only the loop body differs. Order-note: the dispatch sits after the MoE (`ids`) and >MAX_BATCH returns, so those are untouched.

### PTX finding (asked first, and it changes the premise)
nvcc **already CSEs** the Q8_0 loads across columns. Today's 5-column plain instance has exactly **25 global loads per loop iteration**: 10×`ld.global.u16` (2 rows × [4 qs halves + 1 `d`]) + 15×`ld.global.nc.u32` (5 columns × [2 qs ints + `ds`]). Nothing is reloaded per column. The new path has the **same 25 loads** (10 u16 weights + 5 u16 `d` + 10 u32 y) — so the brief's "2×VDR 16-bit loads per row, possibly again per column" does not hold, and **no load-instruction saving is available**. What the generic loop does spend is address math and int rebuild:

| n=5, per iteration | today (generic) | wide |
|---|---|---|
| loop instructions | 159 (fused 163) | **122 (fused 124)** |
| global loads | 25 | 25 |
| `add.s64` | 32 | **23** |
| `mov.b16` (u16→u32 rebuild) | 10 | **0** |
| `mul.lo.s64` / `mov.b32` | 5 / 14 | **0 / 4** |
| `dp4a` / `cvt.rn.f32` / `mul.f32` / `fma.f32` | 20/10/10/10 | 20/10/10/10 (unchanged) |

Loop-body deltas, plain/fused, 2..8 columns (PTX, sm_86): 2: 84/88→78; 3: 114/113→95/94; 4: 139/138→112/111; 5: 159/163→122/124; 6: 184/188→137/141; 7: 209/213→152/158; 8: 239/238→172/173 (−7% … −28%).

Registers (`ptxas -v`, no spills anywhere):

| cols | plain base→wide | fused base→wide |
|---|---|---|
| 4 | 66 → 64 | 72 → 72 |
| 5 | 80 → 72 | 88 → 80 |
| 6 | 86 → 72 | 94 → 88 |

The 5-column grid stays at 3 blocks/SM (72 and 80 regs alike); n4 plain at 64 regs reaches 4 blocks.

### Why wider weight loads were not done
`block_q8_0` is 34 B with `qs` at +2, and a lane's slice is 8 B at `34*i + 2 + 4*kqs`. Its offset mod 8 alternates with the block index parity (2 mod 4 for even `i`, 0 mod 4 for odd `i`), so no aligned `u32`/`int2`/vector load exists; CUDA requires natural alignment. With `vdr` pinned at 2 (required for bit-exactness) `4×u16 + 1×u16` is the minimum, which is why the load count is unchanged. The gain is instead hoisting all per-row/per-column 32-bit offsets out of the K loop and dropping the 64-bit per-load address adds and the 16→32-bit rebuild.

### Verification performed (CPU only)
- `nice -n 19 ninja -C build-sm86 -j 4 …/mmvq.cu.o` → OK, same two pre-existing warnings (`use_tsum` line 1728, `mmvq_max_waves_per_eu` line 1533), no new ones. Compile time: baseline 93.0 s; new 83.6/88.4/89.0 s; same-flags A/B on original vs new source (`/tmp/q8w-orig.sh`, `/tmp/q8w-new.sh`): 82 s each — no measurable increase despite 14 more kernels.
- Env off = identical code: 736 PTX entries vs 722 = exactly the 14 new `q8_wide=true` kernels (Q8_0 n2..8 × plain/bias-fused). All 722 pre-existing kernels are canonically identical (587 byte-identical after normalizing `$L__BB*` numbering; the remaining 135 differ only in nvcc's per-TU internal symbol hash `_INTERNAL_<hash>`, which changes with any source edit). Command: `nvcc … -ptx` from `ninja -t commands`, see `/tmp/q8w-ptx.sh`.
- Host bit-exactness (`/tmp/q8w_test/test_q8w.cpp`, uses the repo's `get_int_b2`/`get_int_b4`/`dp4a` semantics and both float expressions): 20 000 random iterations, ncols 2..8, rows 1..2, all `kqs ∈ {0,2,4,6}`, two accumulation steps, compares `tmp[j][i]` bit patterns → **0 mismatches`.

### How to verify on GPU (not run here)
- `GGML_CUDA_MMVQ_Q8_WIDE=1` on llama-server/bench for the Qwen3.8-27B UD-Q6_K_M verify window (n=5); greedy output md5 must be identical with the env unset and set (also n=4/6).
- nsys the Q8_0 launches from the brief: 2560 blocks 69.5 µs, 3072 blocks 46.5 µs, 8704 blocks 116.3 µs, pair 2×17408 226.3 µs, LM head 124160 blocks 1564 µs. Expect the biggest relative gain where the kernel is instruction-bound (small grids / low GB/s), which is what the −23% loop body targets.

Nothing committed; no GPU, no server, no benchmarks run.
