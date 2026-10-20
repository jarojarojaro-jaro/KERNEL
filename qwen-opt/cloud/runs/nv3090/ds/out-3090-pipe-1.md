Implementation complete, compiled and verified at PTX/ptxas level. Only `ggml/src/ggml-cuda/mmvq.cu` touched, nothing committed.

## What changed

**1. `mmvq_pipe_depth_nv()`** (new, after `mmvq_n1_rows_nv`, ~line 1432)
Reads `GGML_CUDA_MMVQ_PIPE` once (`static`): `1` -> depth 1, `>=2` -> depth 2, unset/`0`/other -> off. Same pattern as the `[GGML_CUDA_MMVQ_N1_ROWS]` env helper.

**2. `mul_mat_vec_q` kernel** (template now `<type, ncols_dst, has_fusion, small_k, halve_iters, bias_only, n1_rows, c_pipe = 0>`)
- `r3_pipeline` is today's exact condition (`!has_gate_fusion && mmvq_r3_pipeline(type, ncols_dst) && table_id == RDNA3`); `use_pipeline = use_multi && mmvq_has_xraw(type) && (r3_pipeline || c_pipe > 0)`; `pipe_depth = r3_pipeline ? 1 : c_pipe`. With `c_pipe == 0` this is bit-for-bit today's expression, RDNA3 behaviour unchanged.
- Pipeline loop generalised to a `pipe_depth` ring: `mmvq_xraw<type> w[pipe_depth][rows]`, prologue loads `pipe_depth` slices at `xoff_at(d)`, each iteration issues the load of `kbx + pipe_depth*blocks_per_iter` (clamped by `min(..., kbx_last)`) before unpacking/dotting `w[0]`, then rotates.
- Gate extension per brief: when `has_gate_fusion && use_gate`, `wg`/`wgn` slices are loaded and dotted with the same `vec_dot_q_multi_xs` into `tmp_gate`, using the same `yoff`; `xs` storage is reused so no extra unpacked registers. Bias/GLU epilogue untouched.
- All array indices are compile-time constants after unrolling (depth is a template param), so ptxas keeps the ring in registers.

**3. `mul_mat_vec_q_switch_fusion`** (template now `..., int n1_rows = 0, int c_pipe = 0>`)
Runtime instance selection under `#if !defined(GGML_USE_HIP)`, guarded by `if constexpr (c_pipe == 0 && c_ncols_dst >= 2 && mmvq_has_xraw(type))`: depth 1/2 recurses into `<..., 1>` / `<..., 2>`, otherwise today's call. The three launches forward `c_pipe`. HIP builds instantiate nothing new.

Instances emitted: 4 xraw types x ncols 2..8 x {plain, bias-fused} x depth {1,2} = **112 new kernels** (468 -> 580 `mul_mat_vec_q` instances).

## Why it should be faster
The generic loop issues weight loads, then waits, then unpacks/dots. Here a whole iteration of Q4_K/Q5_K/Q6_K/IQ4_XS raw slices (`mmvq_load_xraw`) is in flight during the previous iteration's q8_1 loads, `mmvq_unpack_x` ALU and `dp4a` chain, so DRAM latency is covered by work already present; `=2` keeps a second slice in flight at the cost of registers. Same warps/rows/thread mapping, so grid and occupancy are untouched.

## Bit-exactness (5 lines)
1. `mmvq_load_xraw` reads the same address (clamped to the row's last block) and `mmvq_unpack_x` converts it identically; only the issue point moves in the instruction stream.
2. Each iteration calls `vec_dot_q_multi_xs` once per accumulator with the same `yc`, `yoff`, `kqs`, so the same products are added to the same `tmp[j][r]` / `tmp_gate[j][r]`.
3. Iteration sequence (`kbx = kbx_start; kbx += blocks_per_iter`) and therefore the float addition order are unchanged; rotation copies packed bytes only.
4. A prefetch past the row end re-reads the row's last block, exactly like the existing code; loop bounds unchanged, that slice is never unpacked.
5. Machine-level check: every pre-existing kernel's PTX body is identical to baseline modulo symbol names / basic-block labels (see verification).

## Diff summary
`git diff --stat`: `ggml/src/ggml-cuda/mmvq.cu | 121 ++++++++++----- (104 insertions, 17 deletions)`. Kernel loop hunk (abridged):

```
-    constexpr bool use_pipeline = use_multi && mmvq_has_xraw(type) && !has_gate_fusion && mmvq_r3_pipeline(...) &&
-                                  table_id == MMVQ_PARAMETERS_RDNA3_0;
+    constexpr bool r3_pipeline = !has_gate_fusion && mmvq_r3_pipeline(type, ncols_dst) &&
+                                 table_id == MMVQ_PARAMETERS_RDNA3_0;
+    constexpr bool use_pipeline = use_multi && mmvq_has_xraw(type) && (r3_pipeline || c_pipe > 0);
+    constexpr int pipe_depth = r3_pipeline ? 1 : c_pipe;
     if constexpr (use_pipeline) {
+        const auto xoff_at = [&](const int step) {
+            return uint32_t(min(kbx_start + step*blocks_per_iter, kbx_last)) * bs;
+        };
-        mmvq_xraw<type> w[rows_per_cuda_block];
+        mmvq_xraw<type> w[pipe_depth][rows_per_cuda_block];
+        [[maybe_unused]] mmvq_xraw<type> wg[pipe_depth][rows_per_cuda_block];
...
-            const uint32_t xoff_next = uint32_t(min(kbx + blocks_per_iter, kbx_last)) * bs;
+            const uint32_t xoff_next = xoff_at(pipe_depth);
             ...
-                xs[r] = mmvq_unpack_x<type>(w[r], kqs);
+                xs[r] = mmvq_unpack_x<type>(w[0][r], kqs);
             }
             vec_dot_q_multi_xs<...>(xs, yc, yoff, kqs, tmp);
+            if constexpr (has_gate_fusion) { if (use_gate) { /* unpack wg[0], dot tmp_gate */ } }
+            /* rotate: w[d-1] = w[d]; w[pipe_depth-1] = wn; same for wg */
```

## Registers / spills (nvcc `-Xptxas -v`, sm_86; `base -> PIPE=1 -> PIPE=2`)

| type | cols | variant | base | =1 | =2 | spills |
|---|---|---|---|---|---|---|
| Q4_K | 4 | plain/fused | 105/107 | 114/121 | 128/131 | 0 |
| Q4_K | 5 | plain/fused | 119/123 | 127/128 | 143/151 | 0 |
| Q4_K | 6 | plain/fused | 128/132 | 141/149 | 156/165 | 0 |
| Q5_K | 4 | plain/fused | 115/115 | 127/128 | 150/157 | 0 |
| Q5_K | 5 | plain/fused | 127/128 | 140/146 | 164/168 | 0 |
| Q5_K | 6 | plain/fused | 135/143 | 153/159 | 175/182 | 0 |
| Q6_K | 4 | plain/fused | 126/154 | 128/134 | 147/152 | 0 |
| **Q6_K** | **5** | **plain/fused** | **148/154** | **149/155** | **166/168** | **0** |
| Q6_K | 6 | plain/fused | 164/176 | 161/168 | 188/192 | 0 |
| IQ4_XS | 4 | plain/fused | 96/101 | 127/128 | 137/145 | 0 |
| IQ4_XS | 5 | plain/fused | 111/117 | 139/145 | 149/155 | 0 |
| IQ4_XS | 6 | plain/fused | 119/126 | 151/156 | 161/167 | 0 |

No spills anywhere (all `0 bytes spill stores/loads`, 0 stack). ncols 5 Q6_K bias-fused (the 17408-block launch from nsys, 154 regs) is 155 regs at `=1`, +1. `=2` costs 14-26 regs; ncols 7-8 at `=2` reach 199-214 regs, expected to lose residency - treat `=2` as an experiment, `=1` as the default candidate. Full 2..8 table reproducible with `/tmp/regtable.py /tmp/pipe-ptxas-base.txt /tmp/pipe-ptxas.txt`.

Finding worth knowing: for `ncols_dst > 1` the only fused instance the dispatch builds is `bias_only = true` (the pair/bias launch), so `has_gate_fusion` is compile-time false in every emitted multi-column kernel, including the nsys "gate-fused" 154-reg one. The gate pipelining is implemented as asked but currently lands in no emitted instance (it would take a gate-fused multi instance to exercise it); no null `xr_gate` is read.

## Verification performed (CPU only)
1. `nice -n 19 ninja -C build-sm86 -j 4 ggml/src/ggml-cuda/CMakeFiles/ggml-cuda.dir/mmvq.cu.o` -> OK. Compile time (same command, cold object): **85.78 s baseline -> 101.30 s after** (+18%, from the 112 new kernels). Warnings identical to baseline: only the pre-existing `#177-D` for `mmvq_max_waves_per_eu` and `use_tsum`, no new ones.
2. ptxas resource log for both trees: `/tmp/pipe-ptxas.txt` (new), `/tmp/pipe-ptxas-base.txt` (baseline), via
   `ninja -C build-sm86 -t commands <obj> | tail -1`, add `-Xptxas -v`, stderr to the file. All 468 pre-existing `mul_mat_vec_q` instances have identical registers/stack/spills to baseline.
3. Env-off identity proof: compiled baseline and patched TUs with `-keep`, compared PTX bodies (`/tmp/ptxcmp.py`, normalising symbol names, `$L__BB` labels, `__local_depot`, `_INTERNAL_..._cu`): all 468 `mul_mat_vec_q` and 247 other kernel bodies identical; the only 7 differing kernels are `mul_mat_vec_q_wmma` (untouched code) differing solely in an embedded `__LINE__` constant (2985 -> 3072). New bodies = exactly 112, all `mul_mat_vec_q`, i.e. the pipe kernels.
4. Probe artifacts removed (`git status` = only `mmvq.cu` modified). No GPU, no server, no benchmarks run.

## Exact env values to test on the card
- `GGML_CUDA_MMVQ_PIPE` unset or `0`: today's kernels; md5 must match the installed build exactly (proven identical PTX/ptxas for the selected instances).
- `GGML_CUDA_MMVQ_PIPE=1`: depth 1 - intended candidate for the 5-column verify (Q6_K fwd/up/gate-pair 17408 blocks, 155 regs vs 154).
- `GGML_CUDA_MMVQ_PIPE=2`: depth 2 - registers +14..26, watch Q5_K/Q6_K ncols 7-8 (>=199 regs) for residency loss.
Suggested gate: same seed/prompt set, greedy, md5 of the verify logits/outputs must be identical for all three settings; then nsys kernel times of the shapes in the brief's table (expect the largest effect on the K=5120 launches that sit at ~550 GB/s, plus the LM-head-free ffn_down launches if they progress).

Limitation: `=2` and all perf claims are structurally argued only; no GPU measurement was possible under the constraints.

