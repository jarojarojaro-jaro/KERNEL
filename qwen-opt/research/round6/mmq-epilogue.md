# MMQ epilogue (RDNA3 WMMA, Q4_K/Q5_K): report

Worktree `~/wt/mmq6`, branch `opt-mmq6`, based on `c36fd2c87`. Build: `~/wt/mmq6/build`, install: `~/wt/mmq6/inst`.
Analysis artifacts (ISA, the hash tool) are in `~/wt/mmq6-tools/`.

## Commit
- `ae1ef6a97` HIP/RDNA3 MMQ: Q4_K/Q5_K scale epilogue in VOPD-pairable f32 ops, bitwise the same sums
  (`GGML_HIP_MMQ_EPI=0` turns it off). **UNMEASURED.**

## Where the cvt / fma_mix come from (base ISA, Q4_K J=128, one k01 step = 16 WMMA)
Per lane, the 8 C tiles of a k01 step hold 64 int32 accumulators (8 rows i x 8 columns j). The source does, per element,
`sum += dmA.x*dsB.x*C` then `sum += dmA.y*dsB.y`, with the scales as half2 in LDS. The compiler emits:
- 64 `v_fma_mix_f32 t, a.x(f16), b.x(f16), -0`: the product d_x*d_y, with both f16->f32 conversions folded in;
- 64 `v_cvt_f32_i32`: the int32 WMMA accumulators;
- 64 fmac (31 VOPD pairs + 2 single): `sum = fma(t, C, sum)`;
- 64 `v_fma_mix_f32 sum, a.y(f16), b.y(f16), sum`: the min/sum term with the conversions folded in;
- plus 8 address adds and 4 VOPD moves of the zero C start value.

The scale unpack (d*sc, dmin*m) happens in load_tiles, once per tile, not in the loop. The x scales were already
loaded once per k01 step and shared by the 8 y tiles. What made the epilogue expensive is that v_fma_mix and v_cvt
cannot dual-issue. Every element needs its own (i, j) product, so the operation count cannot drop without
reassociation.

## The change
- The 8 x and the J/16 y half2 scales of a k01 step are widened once to f32 (32 `v_cvt_f32_f16`). An empty asm keeps
  them opaque; without it the compiler folds them back into v_fma_mix. They are pinned in runs of 4 consecutive
  VGPRs, so the products of different pairs land in different register banks, which VOPD pairing needs.
- The WMMA accumulator starts at 0x4B400000 instead of 0. `(float)C` is then one `v_add_f32 -12582912`, which is
  VOPD-able.
- So all 4 per-element operations (mul, add, fmac, fmac) are VOPD-able.
- The k01 loop stays non-unrolled (`#pragma unroll 1`). A full unroll had made J=64 spill 307 VGPRs.
- The variant is used only for J >= 48 and non-fallback kernels:
  - J=16 got more instructions (VALU 44 -> 58);
  - J=32 was unchanged;
  - the Q5_K J=128 fallback kernel spilled 13 VGPRs.
- The switch is a kernel template parameter. `GGML_HIP_MMQ_EPI=0` therefore launches the old kernels, and their ISA
  is identical to c36fd2c87: all 64 Q4_K and 64 Q5_K kernel bodies and VGPR counts were compared; Q4_0 is untouched.
- test-backend-ops gets new cases: Q4_K/Q5_K MUL_MAT with 8192 rows and n = 48, 64, 96, 128, 512, plus one
  MUL_MAT_ID case with 64 tokens per expert. Before this, no eval case reached J >= 48 without the fallback for these
  types.

## Offline evidence (gfx1100, ROCm 10.0 clang, the build's flags, `~/wt/qwen5-tools/isa.sh`)
Inner k01 loop, base -> new:

| kernel | instructions | VALU | VGPRs | spills |
|---|---|---|---|---|
| Q4_K J=128 | 298 -> 243 | 237 -> 178 | 239 -> 240 | 0 |
| Q4_K J=96  | 234 -> 195 | 182 -> 142 | 190 -> 191 | 0 |
| Q4_K J=64  | 165 -> 149 | 126 -> 105 | 143 -> 147 | 0 |
| Q4_K J=48  | 134 -> 124 | 100 -> 88  | 123 -> 126 | 0 |
| Q5_K J=128 | 300 -> 244 | 239 -> 181 | 244 -> 245 | 0 |
| Q5_K J=96  | 238 -> 194 | 186 -> 141 | 198 -> 198 | 0 |
| Q5_K J=64  | 166 -> 148 | 127 -> 107 | 172 -> 172 | 0 |
| Q5_K J=48  | 133 -> 124 | 99 -> 88   | 161 -> 161 | 0 |

- Q4_K J=128 op mix, base: 128 fma_mix + 64 cvt_i32 + 64 fmac (35 VOPD instructions).
- Q4_K J=128 op mix, new: 32 cvt_f16 + 64 add + 64 mul + 128 fmac, in 126 VOPD instructions; 9 muls and 3 fmacs are
  left unpaired.
- The new mix has more operations than the base (304 vs 272) but fewer instructions.
- LDS does not change: Q4_K J=128 uses 38400 B, i.e. 3 blocks per WGP within 128 KiB.
- VGPRs are not the limit: 240 VGPRs allow 6 waves per SIMD, while 3 blocks x 4 waves per WGP need 3. Occupancy
  stays at 3 blocks per WGP.
- Both kernels have `amdhsa_float_denorm_mode_16_64 3` and `_32 3`.

Expected effect [INFERENCE, not measured]:
- Per 256-K iteration a wave issues 2073 -> 1605 VALU instructions against 128 WMMA. At ~32 cycles per iu8 WMMA
  (512 int8 ops/clk/CU) that is ~4096 WMMA cycles.
- If WMMA and VALU serialize on the SIMD, which fits the ~70% WMMA utilisation during vec_dot implied by round 5,
  the main loop gets ~7.6% shorter. That would be about 5% on pp4096, ~1090 -> ~1145 t/s.
- If other waves hide part of the VALU, the gain is smaller.

## Bitwise argument
Every output element keeps the same IEEE operations in the same order.
1. **Scale product (x part).** f16->f32 is exact. The product of two f16 values is exact in f32: 11+11 significand
   bits, and |a*b| lies in [2^-48, 2^32], inside the f32 normal range. So `v_mul_f32(a.x, b.x)` equals the old
   `v_fma_mix(a.x, b.x, -0)`; the signed zeros match too (+0 + -0 = +0, -0 + -0 = -0).
2. **Min/sum term (y part).** `v_fmac_f32(sum, a.y, b.y)` equals the old `v_fma_mix(a.y, b.y, sum)`: both are one
   rounding of the exact a.y*b.y + sum.
3. **Denormals.** f16 and f32 denormals are preserved in both kernels (mode 3/3). q8_1 d values can be f16-subnormal
   for tiny activations; they convert exactly in both paths.
4. **Accumulator conversion.** |C| <= 32*128*128 = 2^19 < 2^22, so:
   - the WMMA integer sum is exact with either start value (no clamp/saturation: 0x4B400000 + 2^19 < 2^31);
   - the bits 0x4B400000 + C are the float 12582912 + C (exponent 2^23, mantissa 2^22 + C);
   - `(12582912 + C) - 12582912` is exactly C, and +0 for C = 0, as `v_cvt_f32_i32` gives.
5. **Accumulation.** `sum = fma(scale product, C, sum)` is the same `v_fmac_f32`, and the k01, tile and element
   order are unchanged.
6. **Limit.** The bits could differ only in NaN payloads, i.e. if a scale is already inf/NaN, in which case the
   logits are NaN either way.

## Not done (and why)
- **x scales as float2 in LDS.** This would save 16 more cvt per k01 (~9% of the new VALU, ~2% of the loop). It
  needs a new sram layout, Q4_K/Q5_K load_tiles changes and +2 KB LDS (still 3 blocks per WGP). It is not worth that
  much invasive change before the main change is measured.
- **v_dot2acc_f32_f16** for the min/sum term. Its intermediate rounding is not specified, so it cannot be proven
  bitwise offline.
- **f16 WMMA** to avoid the int->float conversion. The f32 result would be exact, but the operands would need
  conversion and twice the registers/LDS.

## Pending GPU commands (all UNMEASURED; each first checks that no 8080 server runs)
Common environment for every block below:
```
G='[ -z "$(pgrep -f "llama-server.*--port 8080")" ] || { echo "8080 server running"; exit 1; }'
L="LD_LIBRARY_PATH=$HOME/wt/mmq6/inst/lib:/opt/rocm/core-10.0/lib"
Q=$HOME/models/Qwen3.8-27B-UD-Q4_K_XL.gguf; F=$HOME/models/lfm/LFM2.5-24B-A2B-Q5_K_M.gguf
W=$HOME/wt/lfm3-prof/wikitext-2-raw/wiki.test.raw; T=$HOME/wt/mmq6-tools
```

P1. test-backend-ops, new path and old path.
```
cd ~/wt/mmq6 && eval "$G" && for e in 1 0; do for op in MUL_MAT MUL_MAT_ID; do
  flock /tmp/gpu.lock flock /tmp/quiet.lock env GGML_HIP_MMQ_EPI=$e $L inst/bin/test-backend-ops -o $op 2>&1 | tail -3; done; done
```

P2. Bitwise prefill logits, the strongest check. FNV hash of every logits row, 2048 wikitext tokens:
- ubatch 512 gives J=128 tiles;
- ubatch 64 gives J=64.

`cmp` must succeed for both models.
```
cd $T && eval "$G" && for m in qwen lfm; do M=$Q; [ $m = lfm ] && M=$F; for ub in 512 64; do for e in 0 1; do
  flock /tmp/gpu.lock flock /tmp/quiet.lock env GGML_HIP_MMQ_EPI=$e $L ./logits_hash $M $W 2048 $ub > hash_${m}_${ub}_$e.txt; sleep 30; done
  cmp hash_${m}_${ub}_0.txt hash_${m}_${ub}_1.txt && echo "$m ub$ub BITWISE"; done; done
```

P3. Perplexity KLD, as in round 5 P7. The reference is EPI=0 of the same build, whose kernels are ISA-identical to
c36fd2c87. It must show Mean KLD 0.000000, Maximum KLD 0.000000, Same top p 100.000 % and identical PPL lines.
The kld file is ~4 GB in `$T`.
```
cd ~/wt/mmq6 && eval "$G" && P="inst/bin/llama-perplexity -m $Q -f $W -ngl 99 -fa on -ctk q4_0 -ctv q4_0 -c 4096 -b 4096 -ub 512 --chunks 4"
flock /tmp/gpu.lock flock /tmp/quiet.lock env GGML_HIP_MMQ_EPI=0 $L $P --kl-divergence-base $T/epi0.kld > $T/ppl_epi0.log 2>&1; sleep 45
flock /tmp/gpu.lock flock /tmp/quiet.lock env GGML_HIP_MMQ_EPI=1 $L $P --kl-divergence-base $T/epi0.kld --kl-divergence > $T/kld_epi1.log 2>&1
grep -E "Mean    KLD|Maximum KLD|Same top p|Final estimate" $T/ppl_epi0.log $T/kld_epi1.log
```

P4. llama-bench A/B, interleaved env, Qwen pp512/pp4096 and then LFM pp4096 (MoE Q5_K).
```
cd ~/wt/mmq6 && for r in 1 2 3; do for e in 0 1; do eval "$G"
  flock /tmp/gpu.lock flock /tmp/quiet.lock env GGML_HIP_MMQ_EPI=$e $L inst/bin/llama-bench -m $Q -p 512,4096 -n 0 -fa 1 -ctk q4_0 -ctv q4_0 -r 2 -o md | tee -a $T/bench_qwen_epi$e.md; sleep 45; done; done
for r in 1 2; do for e in 0 1; do eval "$G"
  flock /tmp/gpu.lock flock /tmp/quiet.lock env GGML_HIP_MMQ_EPI=$e $L inst/bin/llama-bench -m $F -p 4096 -n 0 -fa 1 -ctk q8_0 -ctv q8_0 -r 2 -o md | tee -a $T/bench_lfm_epi$e.md; sleep 45; done; done
```

P5. Greedy md5 (fresh server per mode, port 18433):
- qwen: plain `c4708318411479c9530911e310f865bd`, mtp `6f14e814bb6408aeea23a1dc50e96ba1`;
- lfm: `894e56e447243cf630214b4cfc1ffea6`.

These prompts are short, so the epi tiles are barely used; this is a regression check.
```
eval "$G" && flock /tmp/gpu.lock flock /tmp/quiet.lock ~/qwen-opt/fusion/greedy.sh ~/wt/mmq6/inst/bin ~/wt/mmq6/inst/lib /tmp/mmq6g qwen
eval "$G" && MODES=plain flock /tmp/gpu.lock flock /tmp/quiet.lock ~/qwen-opt/fusion/greedy.sh ~/wt/mmq6/inst/bin ~/wt/mmq6/inst/lib /tmp/mmq6l lfm
```

P6 (optional). Per-kernel time A/B. Compare the mul_mat_q<Q4_K,128> totals between the two runs.
```
cd ~/wt/mmq6 && for e in 0 1; do eval "$G"; flock /tmp/gpu.lock flock /tmp/quiet.lock env GGML_HIP_PM4=0 GGML_HIP_MMQ_EPI=$e $L \
  rocprofv3 --kernel-trace --stats -d $T/prof_epi$e -o run -- inst/bin/llama-bench -m $Q -p 4096 -n 0 -fa 1 -ctk q4_0 -ctv q4_0 -r 1; sleep 45; done
```
