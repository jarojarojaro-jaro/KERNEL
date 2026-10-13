# Strata: prefill and prompt path, attention, and KV design

Repo: ~/research/Strata (Niko1221/Strata). Paths are relative to the repo root. `[INFERENCE]` marks my reasoning, not something measured in the repo.
Strata's model context: 48 layers = 36 GDN + 12 QSA (sparse attention: 2 KV heads, hd 256, G=12 q-heads per KV head, **top-k ≈2,051 cells per query**), MoE 512x top-10. Because prompt/decode attention reads a bounded set of cells, Strata's "attention vs context" behaviour does **not** carry over to our full-attention layers. Its GEMM, GDN, kernel-engineering and methodology lessons do.

---

## 1. How the author works on the prefill path

- **Default output must stay byte-identical; anything that changes rounding is opt-in and gated by KL.** Examples: `STRATA_PREFILL_BF16X2` defaulted back to 0 (7d746a08); chunks >8192 opt-in "because the chunk size changes the tokens" (da95ad29, PR #282 comment); `STRATA_HIP_WMMA` never auto-enabled, "the output bits change" (src/program/generate.cpp:4603-4608); fused int8 prompt experts on gfx12 became default only after a 96-prompt KL check matched MMQ (docs/DETAILS.md:1982).
- **KL noise floor:** changing only the chunk size (8192→6144) on an unchanged engine gives 89.8% top-1 / KL 0.33 at 32K. Every rounding change is judged against that floor (bench/results/2026-09-28-prefill-speed/README.md "Quality"). In 732a3f4c: "the model amplifies any FP32-level change (v1 vs v2 of this kernel, same accuracy, another summation order, differ as much as old vs new)".
- **`STRATA_PF_SWITCH_MIN_T=4096`:** rounding-level fast paths apply only to chunks ≥N tokens, so short prompts keep the default numerics (src/prefill/prefill.cpp:318-321; docs/STRIX_HALO.md:102-116).
- **Whole-engine A/B decides, not microbenchmarks.** "Microkernel speedups alone were not sufficient to select a configuration" (docs/AMD_HIP_PERFORMANCE.md:142-145). "cuBLAS grouped GEMMs for the experts (faster in isolation, slower inside the engine: 770 vs 790)" (2026-09-28-prefill-speed/README.md:18). Method: interleaved arms, a fresh process per arm, the first fresh prompt after load discarded (docs/AMD_HIP.md:626-630), and `cache_n=0` enforced (tools/hip/bench_prefill.py).
- **Per-phase GPU timeline (`STRATA_PREFILL_TIMING=1`):** events are recorded on the compute stream, and the gap between two marks is charged to the phase that was waiting (src/prefill/prefill.cpp:1959-1962). This is how they found prompt attention was 25.6–27.7% of gfx1100 prefill (PR #786).
- **Bitwise kernel work as a discipline:**
  - `STRATA_HCD_EXACT` reproduces hipBLASLt solution 1176/1177's k-order (StaggerU included) in a custom WMMA kernel, so it stays bitwise (203ec5cd).
  - GDN kernels are rewritten while keeping the same per-element op order (kernels.cu:1065-1073).
  - The 1-ulp hunt in `STRATA_GDN_NOY` reproduces the compiler's `v_fma_mixlo_f16` (9668e324).
- **Rejections are kept as evidence:**
  - WY-chunked GDN on gfx1100 shipped opt-in with parity harnesses even though it lost (PR #888).
  - The `--prefill auto:32768` A/B was flat on 7900 XTX at 38K (bench/results/2026-10-06-community-rx-7900-xtx/README.md, "Prefill setting").
  - "Not worth trying (measured flat): `--kv-resident` changes, a prefill chunk above 32768, `--spec` above 4" (docs/AMD_HIP.md:241-242).

---

## 2. Chunked prefill: sizes and measured effects

The chunk is Strata's "ubatch". It is large: 8192 by default, up to 32768. On MoE the main reason is that every chunk re-streams every non-resident expert over PCIe.

| Change | Measured (hardware) | Ref |
|---|---|---|
| 2048 → `--prefill auto` (largest of 8192/6144/4096 that fits in borrowed cache slots) | Q2_0 32K prompt: chunk 4096 791, 6144 878, 8192 973 tok/s (RTX 5070 12 GB). The whole 0.1.13 package: Q2_0 572→1,290, IQ3_S 383→1,208 tok/s | DETAILS.md:317-327; 2026-09-28-prefill-speed |
| auto list up to 32768 (PR #282, sergiywith) | RTX 5090, IQ2_XS 32K: 4×8192 5,513–5,687 → 1×32768 6,231–6,615 tok/s (+15%); experts streamed ~40,000 → ~18,300. RTX 4080S 32 GB IQ3_S: 32K 2466/2856/2935 and 64K 2246/2642/2809 tok/s at 8192/16384/32768. Shipped opt-in (`auto:N`) | PR #282; da95ad29 |
| 7900 XTX (gfx1100) | static 16K chunks gave "no consistent end-to-end win" (docs/AMD_HIP_PERFORMANCE.md:142). Windows 7900 XTX, 38K: auto:32768 vs auto ≈1,630 vs 1,540 (one run each, "within noise"). #1389 (7900 XTX, 74K): `--prefill auto:32768` +23%; a chunk >32768 flat | docs/AMD_HIP.md:238-242 |
| gfx12 default 16384 | bare `--prefill auto` may take 16384 on gfx12 Linux | cf09057a; DETAILS.md:1984 |
| Experts stream from 1024-token chunks (was 2048) | +17–28% on 1–4K prompts, same output | 3e3d69b4 |
| Auto chunk = bisection on a 256-token grid; chunk and ring as one VRAM budget | one ring slot ≈0.53 tok/s vs one chunk token ≈0.05 tok/s (2x3060 + 2x5060, 120K prompt) → "the largest chunk that still leaves the ring full" | 8fef4f1f (Gopi) |
| `STRATA_PREFILL_EQUAL=1` (#693) | equal-size chunks instead of full chunks plus a short tail (changes rounding) | DETAILS.md:269 |
| Short prompt parts (≤`--short-read`, default 64 tokens) go through the decode verify windows | the batched path had ~300 ms fixed cost + ~180 ms refill per run (one-word message ~1.4 s TTFT) | 470b3d7c |
| `STRATA_PREFILL_CPU_SHARE` (0.1.41 default on CUDA, chunks <1024) | 512 tok −28..−34%, 1000 tok −20..−26% prompt time (3060/P100/5070); every share was slower on RX 7900 GRE + 5700X3D under ROCm (#1282), so auto-off there | DETAILS.md:1564-1587 |

Takeaway [INFERENCE]: Strata's chunk gains are mostly about MoE streaming amortization. For a dense model fully in VRAM, chunk size only affects GEMM tile efficiency and per-ubatch fixed cost. It also matters if the GEMM path has a per-ubatch weight dequant (§4).

---

## 3. Expert streaming over PCIe ring buffers (MoE-only; brief)

- Mechanism: at chunks ≥`stream_all_min` (1024), every non-resident expert streams in a fixed order through a VRAM ring borrowed from the expert cache. The next layer's experts arrive during the current layer's attention. A dedicated host thread issues the stream (8baae071 D-5). Lent cache slots are refilled with queued copies and one wait (68072d30).
- Ring sizing (src/prefill/prefill.cpp:199-251):
  - Q2_0 8192 chunk: 96 slots 1,153 vs 384 slots 1,294 tok/s.
  - With 1/3 unpinned (host copies): 96 slots 1,216 vs 256 slots 1,070.
  - With fused experts: 512 vs 384 slots +19–22%/+11–12%; 1024 slots 4K 1,605 vs 1,512.
- **Sized in bytes since 0.1.39b (#583):** budget = slots × Q2_0 blob (1,382,400 B). The reason: a slot is a whole blob, so a 384-slot ring on Q8_0 was 1,912 MiB and pinned an 8 GB card at 1,024-token chunks. With bytes, that rig went chunk 1,024→6,144 and prefill 87→402 tok/s. RTX 5070 32K: IQ3_XXS +18.5%/+9%, Coder +3%. Shrinking the ring from 6,144-token chunks upward measured slower (Coder −12%), so the old ring is kept there (DETAILS.md:1880-1893).
- HIP: `STRATA_PREFILL_RING=96` in the measured gfx1100 config (docs/AMD_HIP_PERFORMANCE.md:20). With `STRATA_HIP_WMMA`, a 96-slot ring is forced. 9070 XT 4K: 718 (384 slots) → 1,211 tok/s (prefill.cpp:280-286). A 192-slot ring was rejected on gfx1100 (AMD_HIP_PERFORMANCE.md:142).
- Lend coverage (#1389, 7900 XTX): with 6201/6201 lendable slots RAM-backed, 74K prefill ran at 2,583 tok/s (`wait copy` 0.2%). With 5093/6202 it was 1,810 tok/s (`wait copy` 36.8%) (docs/AMD_HIP.md:227-237).
- Not applicable to us: our weights are fully resident.

---

## 4. Dense projections: dequant+hipBLAS(Lt) vs int8 MMQ

### Path order on HIP (src/prefill/gemm.cu)
- `Gemm::f16` (675-728): `STRATA_PF_GEMM` → `STRATA_WMMA_GEMM` (#313) → `f16_io_` (RDNA2 FP16-out) → **tuned hipBLASLt** → `hipblasGemmEx` (FP16 in, FP32 out, COMPUTE_32F).
- `Gemm::native` (819-871): the GGUF weight is dequantized to an FP16 scratch (row-sliced if too big), then `f16`. `STRATA_DENSE_MMQ=1` → `native_mmq` (730-794): q8_1-quantize X, then one `mul_mat_q` per 1024-row chunk. It requires `K % 256 == 0`. Reason: llama.cpp MMQ loads 256-value K chunks and reads past a partial row, past the tensor end. On a 640-wide tensor this produced a NaN column that zeroed the output (PR #820).
- Default: MoE experts use llama.cpp MMQ (HIP builds `-DSTRATA_PREFILL_MMQ=ON`). Dense GGUF projections use dequant→FP16 + hipBLASLt.

### Measurements

| Comparison | Result | HW | Ref |
|---|---|---|---|
| Dense MMQ vs dequant + plain hipBLAS (no Lt kernels on gfx1030) | 4K 436→757, 8K 448→774 tok/s (+73%). rocprof: dense GEMMs were 68% of prefill GPU time at ~25% of fp32-acc rate; MMQ ~7x faster on those shapes | RX 6900 XT gfx1030, ROCm 7.2.3 | PR #820 (merged as 43881f14) |
| Dense MMQ vs **tuned hipBLASLt** | weighted 528.91 → 529.96 tok/s (+0.2%, noise) | Radeon 8060S gfx1151 | bench/results/2026-10-05-community-gfx1151/prefill-ab.md |
| Tuned hipBLASLt table vs plain hipBLAS | 4.2K/8.8K: 250.9 → 528.9 weighted (2.11x) | gfx1151 | same |
| same, gfx1100, ROCm 10.0.0 (hipBLASLt 1.4.1 = 100401) | 370 tok 319→371 (+16%), 1,670 tok 682→1,038 (+52%), 6,471 tok 857→1,524 (+78%) | 7900 XTX + 9800X3D | PR #766; docs/AMD_HIP.md:554-559 |
| same, gfx1100, ROCm 10.2 nightly (100500) | 131K prompt 926 → 1,687 tok/s (+82%), decode unchanged | 7900 XTX + 7900X | PR #755/#745; bench/results/2026-10-04-community-rx7900xtx-hipblaslt-100500 |
| same, 100200 (pinned ROCm at the time) | "+42–59% prompt speed on the 7900 XTX" | 7900 XTX | 5cb4ff28; PR #121 comment |
| Small-T expert GEMM rows added (f16 N1280 K2560, T 1..1873) | 26-row table → 642 fallbacks / 642 launches. Adding 17 bucket rows: 710.5 → 937.5 tok/s (+31.9%) at 3,151 tok | 7900 XTX, ROCm 10.0 | a45783c7 (PR #1289) |
| Tuned table on RDNA4 R9700 (1.4.1) | 0.98–1.76x per GEMM but only 0–3% end to end, so no table was shipped. Own R9700 table 1.15x geomean per GEMM, +0.8% e2e | R9700 | docs/AMD_HIP.md:301-306, 607-618 |
| R9700 with hipBLASLt 1.2.2 | 32K prompt 638 → 1,177 tok/s with the table | R9700 | docs/AMD_HIP.md:307-310 |

Reading [INFERENCE]: on gfx1100/1151, *untuned* hipBLAS(Lt) FP16 is the problem, not FP16 itself. With version-matched solution ids, the FP16 path ties dense MMQ (gfx1151). Strata dequantizes once per 8K–32K-token chunk, so the dequant pass is amortized. With a 512-token ubatch it would not be (see Transfer T1).

### hipBLASLt tuning table: calibration and version pinning
- Tool: tools/hip/tune_hipblaslt.cpp (420 lines).
  - Shapes/cases: `--case dtype,T,N,K,ldy` or `--shapes-file`. Default T buckets {4096, 8192} (line 53); 32 MiB workspace (the engine's own, gemm.cu:440-446).
  - Per case: time the `hipblasGemmEx` baseline (OP_T/OP_N, COMPUTE_32F). Then `hipblasLtMatmulAlgoGetHeuristic` with up to **16** candidates (MAX_ALGOS, line 69). Skip candidates needing more workspace.
  - **Accuracy gate** per candidate: rel-L2 ≤1e-4, max-abs ≤1e-2, finite, padding canary 123456.25 written outside `ldy` (lines 70-72). Reject on any write past N.
  - Timing: 2 warmups + 3 reps (line 67); keep the lowest mean. Output rows are `dtype N K ldy T solution_id`, stamped `STRATA_HIPBLASLT_TUNING_V1 <arch> <version>` (tools/hip/gfx1100-hipblaslt-100100.txt:1-2).
- Runtime (src/prefill/gemm.cu:186-345; src/prefill/hipblaslt_tuning.hpp:110-123):
  - Refuse a table whose arch/version ≠ the running `hipblasLtGetVersion`.
  - Lookup = exact (dtype, N, K, ldy) + **nearest T bucket** (ties → smaller bucket).
  - `getAlgosFromIndex(solution_id)` must return that same id, and `matmulIsAlgoSupported` must accept the actual T/beta. Otherwise fall back to hipBLASEx.
  - Per-call cache. `STRATA_HIPBLASLT_VERBOSE=1` prints `launches=… fallbacks=…` and the unique fallback shapes.
- Setup pins the table by arch **and** installed hipBLASLt version, read from `hipblaslt-version.h` (setup.py:2599-2627). "A table's solution ids are valid only for that pair, and the engine refuses any other table" (docs/AMD_HIP.md:42-45). "Another 1.5.0 build could number its solutions differently" (docs/AMD_HIP.md:579-585).
- gfx1100 tables: 100100, 100200, 100202, 100401 (43 rows), 100500 (tools/hip/).
  - Winners collapse to a few kernels: 100100 bf16 → 541/542, f16 → 1147; 100500 bf16 1034–1036, f16 2106.
  - 100202: "Four shapes at T=4096 produce non-finite output in every hipBLASLt solution", so those rows are absent (PR #170).
- Calibration gotchas (docs/AMD_HIP.md:597-630):
  - The first case of a fresh tuner process times during clock ramp (0.31–0.63 vs 0.606–0.619 ms). Time a heavy case first.
  - Occasional 100 ms → 1.6 s stalls. gfx1150 used two passes and the lowest **median of 6** (mean-of-3 picks differed in 26 rows).
  - Drop rows where hipBLAS wins, and drop both T buckets together, because of the nearest-bucket rule.
- Dense shapes in the gfx1100 table (Strata model): f16 N×K = 512×2560, 640×2560, 2560×640, 2560×6144, 6144×2560, 10240×2560, 12288×2560; bf16 small-N router/indexer/HC shapes (N=1, 4, 48, 128, 320, 512, 2560, 10240).

### FP16 vs BF16 on RDNA
- GGUF weights → FP16 GEMMs. BF16-checkpoint weights (hyper-connections, router, indexer, SSM α/β, shared gate, PLE K/V) → BF16 GEMMs with BF16 activations (prefill.cpp:300-303).
- `STRATA_PREFILL_BF16X2` (opt-in) adds the activation's BF16 remainder as a second GEMM (~16 mantissa bits). 32K first-token KL 0.074 vs 0.072; the hyper-connection term is what matters (a86bc853).
- **gfx1030:** rocBLAS has tuned kernels only for FP16-in/**FP16-out**. HSS (FP16→FP32) 5.6 TFLOPS, BF16 ~5.3, HH 37.7 TFLOPS (N10240, T7313, K2560).
  - `STRATA_HIP_PROMPT_F16=1`: 9.4K/34.7K/105.8K prompts 439/466/461 → 744/915/926 tok/s.
  - The range check found 0 FP16 overflows over 33.7K/43.3K/32.4K tokens. It ships with `STRATA_DBG_NAN` (bench/results/2026-10-04-rdna2-fp16-prompt/README.md; docs/AMD_HIP.md:438-446; src/prefill/gemm.cu:357-370).
- FP16 safety: clamp SwiGLU products to ±65504 before the FP16 down GEMM (NaN stays NaN). Decode's q8_1 path has a ~8e6 range (c517862c, 6280f653).
- #313 review: the RDNA3 WMMA FP32 accumulate was reported to round toward zero, ≤1 ULP vs hipBLAS round-to-nearest. This is the author's claim, bounded by a parity test at 4 ULP (PR #313 body).

### Strata's own gfx11 WMMA GEMMs
- **#313 (StevenChenSE) `STRATA_WMMA_GEMM`:** 64×64×16 4-wave tile and 16×16 1-wave tile (src/prefill/wmma_gemm.cu:1-17).
  - 7900 XTX, engine 0.1.30, 4K, WMMA GEMM + WMMA attention vs a **calibrated** 100401 table: 1083.7/1308.4 vs 852.2/1176.6 tok/s (+10–27%). Plain hipblasGemmEx: 658.6/552.8.
  - 32K: 790/800 (fallback) → 1501/1484 (PR #313).
  - The GEMM half was merged in 0.1.40 (41c89b17).
- **`STRATA_PF_GEMM` (4c00d2e7, wmma_gemm.cu:304-314):** 128×256 tile (128×128 below N 1024), BK 32, 8 waves of 64×64. LDS double buffer, with the next stage prefetched into **named registers** ("arrays there went to scratch"). Grouped tile order: 8 row tiles sweep all column tiles, so the weights stream from DRAM once per group.
  - gfx1151 at M=16384: 30–33 TFLOPS vs tuned hipBLASLt 25–27. K=6144 shape only 19.4 (19.1); register-only ceiling ~50.
  - Engine on gfx1151 (8K): GDN out-proj 753 → 645/665 ms. With HC_UPMIX + PA_FAST: UD-IQ4_XS 64K 872.8/880.6 → 942.4/937.8 tok/s.
- **`STRATA_PF_PAD` (bedb8087):** a 4 KB-multiple row stride (K 2048/4096/6144 halves) "camps on the memory channels". Pad rows by +64 halves: K6144 19.1 → 35.0 TFLOPS (W alone 29.0, X alone 23.7), K2560 31.7 → 36.6 (gfx1151). Bitwise identical.
  - Engine: 8K 954/931 → 984/941, 64K 947/946 → 975/1014 tok/s.
  - The GDN `ssm_out` (K=6144) and `attn_output` (K=6144) activations are written padded (prefill.cpp:350-358).
- `STRATA_PF_HCDOWN`: two GEMMs over the same T×10240 input (N=320 + N=4) merged into one WMMA GEMM, so the input is read once. 16K: 5.75 → 3.60/3.77 ms (5eecc5de).
- 4x RX 7900 XT, 0.1.41, PF_FUSED + PF_GEMM + MIN_T 4096 + split opt-ins: prompt 756→2,052 (4K), 1,722→3,804 (32K), 2,433→4,307 (128K); decode flat (PR #1655; bench/results/2026-10-09-community-4x-rx-7900-xt). These are bundled opt-ins, not isolated.

### Fused int8 WMMA prompt experts (`STRATA_PF_FUSED`)
- gfx11: `v_wmma_i32_16x16x16_iu8`.
  - Gate and up rows are interleaved (feature f → rows 2f, 2f+1). The SwiGLU runs in the epilogue: on gfx11 the lane pair l, l+16 holds gate/up; on gfx12 one lane holds both (src/prefill/moe_fused_iq.cu:649-664).
  - The int32 dot starts from MAGIC 0x4B400000 in the C operand, so `as_float(d) − 1.5·2^23` is the exact dot. Offsets (minimums / activation sums) are folded in with integer adds (src/prefill/moe_fused.cu:4-13).
- VGPR cap: `amdgpu_waves_per_eu(8)` gave wrong results with clang 22 on gfx1100 (#1180), so the cap is off for clang ≥22 (moe_fused_iq.cu:681-689).
- R9700: kernels 1.48x/1.20x/1.14x MMQ at 4K/16K/32K; e2e +8–19%; KL 1.10x MMQ's. Became default for IQ3 packs on gfx12 (docs/AMD_HIP.md:357-369; DETAILS.md:1982).
- K-quant variant `STRATA_PF_FUSED_KQ` (Q4_K/Q5_K gate/up, Q5_1/Q8_0 down, 74408069): activation-block spare bytes hold the int8 code sums for the min term. Not measured on gfx1100.

---

## 5. Prompt attention (QSA, sparse), WMMA, FP16 hi+lo

- CUDA D-1 (732a3f4c; include/strata/kernels/qsa_prompt_attn.hpp:1-17):
  - One block per (query, KV head) walks its selected cells in 32-cell chunks with an **online softmax**: no split-K scratch, no merge kernel.
  - The 12 q-heads of a KV head + 4 zero rows form the 16-row MMA M dimension.
  - **int8 KV codes enter exactly as FP16**. Per-64 scales are applied in FP32: to each 64-dim group's q·k partial, and folded into p for p·v. Q4_0 KV: (code−8) exact as int8, scale per 32.
  - **hi+lo split:** q is pre-scaled by an exact power of two so its max ≈2^14 (lo stays out of FP16 subnormals). Then hi = fp16(x), lo = fp16(x − hi), giving ~22 bits. Two MMAs each for q·k and p·v (src/kernels/cuda/qsa_prompt_attn.cu:123-141).
  - RTX 5070: int8 4.0x (26.6 → 6.6 ms per 2,048-query chunk at 32K); attention 5,216 → 1,318 ms; prompt 1,386 → 1,646 tok/s (+18.8%); needles 15/15.
- HIP gfx12 `STRATA_HIP_WMMA` (73ba4496): R9700 4K 1,784 → 2,427, 16K 1,797 → 2,700. Own R9700 at 8.8K: 1,571 → 2,064 (+31%) (docs/AMD_HIP.md:337-351).
- **HIP gfx1100 (PR #786, xyzzing):**
  - The RDNA3 fragment layout differs from gfx12 on all three operands. A lane l holds A[l&15][0..15] (lanes 16–31 replicate), B[0..15][l&15], C/D[(2i + l>>4)][l&15]. Packing the gfx12 way compiles but fails parity at ~30x output scale (qsa_prompt_attn.cu:1134-1158).
  - Kernel: 34.05 → 8.41 ms per chunk at 32K×2048q (4.05x); 4.7–5.1x at smaller shapes. vs FP64 3.3–4.5e-6.
  - E2E (7900 XTX): +22.8% @128K (1,514 → 1,863), +17.9% @32K (1,669 → 1,968), decode flat. The qsa-attn share dropped from 26–27% to 8.4–10.6% of the GPU timeline.
  - Jlauti (7900 XTX, ROCm 10.2, 24.6K prompt): 1,581.8 → 2,060.6 tok/s (+29.5%), wall −16.3%; QSA attention 4,395 → 1,165 ms.
  - 2jztricks (7950X3D): 128K request 95.4 → 79.1 s.
  - Superseded by Strata's own gfx11 kernel in 0.1.40.
- **Rejected int8 Q (iu8 WMMA for scores):** "softmax weight delta 9.5e-2 vs a 2e-2 bound under the 12x-outlier activation class", i.e. precision-bound, not MMA-bound (xyzzing comment, PR #786).
- **`STRATA_PA_FAST` (7aaf466d):** drop the lo halves (single FP16, like normal FA). Only 138.7 → 117.8 ms (−15%) at 64K on gfx1151; rel RMS 4.8e-7 → 2.7e-4; KL within the accepted MMQ-vs-fused pair. Halving the MMA work saved only 15%, so the kernel is gather/LDS-bound [INFERENCE from the numbers].
- Decode attention (QSA): split-K over selected cells (64-cell chunks, then a log-sum-exp merge kernel). The grid is sized by capacity; the real count is read from a device `step` buffer, so one captured graph serves all KV lengths (include/strata/kernels/qsa_decode_attn.hpp:1-14; include/strata/kernels/qsa.hpp:140-160).
- `STRATA_ATTN_LANECELL` (8b30b1d5): score phase with one cell per thread instead of 12 warp reductions per cell. The old kernel cost ~53 µs per layer at T=1 and **+32 µs per extra window row** on gfx1151.
- QSA select/scorer (sparse-only, not relevant to us): exact 4-lanes-per-query scorer, 4.1x stage speedup, fresh 131K/240K requests −10.5%/−22.6% (PR #1943).

---

## 6. GDN prefill: sequential, not chunked

- Default is a **token-serial recurrence with the state in registers**, parallel over value heads × column blocks.
  - D-2 (b5347e36): 48 blocks → 192 blocks (4×32 columns per head); norm in its own kernel. Q2_0 32K GDN 5,118 → 4,264 ms.
  - The keyhead variant (one thread serves the 3 value heads that share a key head): 1.41x on a 4080S (kernels.cu:555-565).
  - Software-pipelined loads (18106b1c).
- gfx11 "Aurora" kernels, all bitwise (src/prefill/kernels.cu:1065-1080, 1183-1188, 1309-1314):
  - `STRATA_GDN_HEAD` (9a427232): 4 lanes per column, state rows in registers, partials meet via shuffles. Tokens staged in LDS 4–8 at a time with the next chunk prefetched. Old kernels needed ~4 barriers and ~3.5 µs per token-layer on the 8060S. 2048 tokens 9.8 → 6.7 ms.
  - `STRATA_GDN_PP=1` (2f510316): the **VGPR occupancy cliff**. 196 VGPRs → 7 waves/SIMD, but the 192 blocks × 4 waves need 9.6, so a second round ran. CSE kept 32 state-row addresses live; an empty asm forces rematerialization → 133 VGPRs. Two alternating state register sets remove 32 copies per token (VALU per token 178 → 131). One 16K chunk-layer 25.4 → 20.5 ms; 64K prompt 1,233.7 → 1,249.0.
  - `STRATA_GDN_PP=2`: 2 columns per lane, half the LDS reads per column.
  - `STRATA_GDN_CONVL2`: conv + q/k L2 fused, 9.13 → 6.95 ms per 16K-layer.
  - `STRATA_GDN_NOY`: skip the dead FP32 output (403 MB per 16K chunk-layer).
- **Chunked (WY / fla-style) rejected:**
  - gfx1100 (PR #888): the GDN recurrence is ~7.4% of a 128K prefill. Serial 1,318 ms at 32K. WY-fma 144x slower. WY-WMMA (rocWMMA 16³) ~6x slower per layer-chunk (~127 vs ~13.7 ms) and −39..−40% engine prefill → REJECT. "rocWMMA 16×16×16 at 64×64/64×32 shapes with 4-warp blocks does not amortize fragment traffic at S=128/HV=48."
  - CUDA `STRATA_GDN_CHUNKED` (32-token WY, #1372): only on ≥128 SMs (RTX 5090 1.8x on the recurrence; 96-token chunk 1.03x, 2048+ 1.81x, kernels.cu:726-729). RTX 3060 0.73x, RTX 5070 0.87x, prompt time unchanged (DETAILS.md:1697-1702).

---

## 7. KV formats and KV residency

- **int8 KV (default above 4–8K):** int8 codes + an fp16 scale per 64 values, 1,056 B per cell·layer. Teacher-forced vs fp16: "indistinguishable" (top-1 92–98%, KL 0.009–0.114; within ~2 SE) (bench/results/2026-09-27-kv-q4/README.md).
- **q4_0 KV + 256-pt Walsh-Hadamard rotation** of K, V and Q (PR #21), 576 B per cell·layer:
  - Document PPL +8% @1K, +12% @8K (+0.112 nats/token at 8K). KL 2.6–4.2x int8's. Code/chat near-neutral. Needles 5/5 to 262K.
  - Decode 62.4 → 67.4 tok/s at 128K, from more expert slots (MoE effect). Stays opt-in.
- **K8V4 hybrid** (int8 K + rotated q4_0 V; 3597c47f, PR #120): 23% less than int8. RTX 3090 Coder 198K: 85 → 99 tok/s (more experts in VRAM). Prompts 2–5% slower. "Scores better than 4-bit KV on long documents" (DETAILS.md:91-95).
- **Hadamard rotation of int8 KV** (`STRATA_KV_ROT=1`, f133c655): first-token KL to fp16 NVFP4 0.0066 → 0.0051 but IQ2_XS 0.0022 → 0.0054. Mixed, so opt-in.
- **KV streaming / `--kv-resident N`** (include/strata/kernels/kv_stream.hpp:1-19):
  - Authoritative K/V lives in pinned, device-mapped host memory. VRAM holds a page pool (page = 4 cells = one indexer block, 4,224 B int8), and the page table becomes a residency map.
  - On device, inside the graph: walk the selected ids, claim misses, pick victims with a CLOCK sweep, then a zero-copy copy kernel pulls the missed blocks over PCIe. Writers always write the host copy and write the slot only if it is resident, so no invalidation is needed.
  - The MTP drafter uses a static ring `block % n_slots` over its last-window cells.
  - Q2_0 262K: 50.9 → 62.6 tok/s (1,589 → 3,872 experts); ~13.7 KB RAM per token (DETAILS.md:79-84).
  - Works only because QSA reads ≤2K cells per query.
- **`STRATA_KV_PREFETCH=1`** (docs/KV_PREFETCH.md:34-47): the next attention layer's streamed KV prefix uploads on a second stream during prefill. 2x RTX 3080 20 GB, PCIe 3.0: 32K prefill −5.3% (16.99 → 16.08 s), 64K −4.1%, 8K and decode nothing. 939/1,553 ms of serial wait moved off the critical path.
- MTP drafter window: attends to the last 32,768 cells by default (src/program/generate.cpp:572; paper §3.7). `--mtp-window 8192` on gfx1151: 64K output +3.5%, 32K −0.4% (docs/STRIX_HALO.md:127-128).
- Batched MTP prompt pass (E-9, a402eefd): the drafter's KV fill over the prompt as Q8_1×Q8_0 MMQ, 0.9 s → 0.07 s of a 32K prompt, same acceptance.

### Long-context decode costs (Strata)
- Decode is nearly flat in context. 7900 XTX IQ3_S (0.1.38, hipBLASLt 100500): 65.1 / 60.4 / 64.4 / 61.8 / 59.2 tok/s at 1K / 4K / 32K / 64K / 128K (DETAILS.md:59-64).
- Prefill on the same card: 760 / 1,275 / 1,641 / 1,594 / 1,494 tok/s (DETAILS.md:40). The slight decline at 128K is the QSA scorer (PR #1943).
- At extreme depth (YaRN to 512K), MTP acceptance collapsed 0.80 → 0.06 (PR #888 note).
- Contrast with full attention: dense Qwen3.8-27B on NInfer, RTX 4090, `rk4v4-e8` KV, MTP 3 drafts: prefill 3,037 / 2,391 / 1,857 tok/s at 55.6K / 117K / 199.5K; decode 127–140 tok/s (bench/results/2026-10-04-community-4090-agents-vs-dense-27b/README.md). Same study: with 70–110K prompts re-read each turn, **prefix reuse decided agent wall time** (Strata re-read ~90% of the time without a conversation cache).

---

## 8. Rejected or flat on AMD (prefill)

- Static 16K chunks; expanded FP16 expert tuning; 192-slot ring (gfx1100) — "no consistent end-to-end win" (AMD_HIP_PERFORMANCE.md:142-145).
- WY-chunked GDN on gfx1100: −39% (PR #888).
- int8-Q attention scores: precision (PR #786 comment).
- Dense MMQ on gfx1151 with tuned Lt: +0.2% (prefill-ab.md).
- R9700 hipBLASLt 1.4.1 table: +0–3%, not shipped (AMD_HIP.md:301-306).
- `--kv-resident` changes, chunk >32768, spec >4: flat on 7900 XTX (AMD_HIP.md:241-242).
- Prefill CPU share on RX 7900 GRE + 5700X3D ROCm: every share slower (DETAILS.md:1570).
- `STRATA_MTP_SIDE_STREAM` hurt R9700 prompt speed (#1240) but helps gfx103x "wait copy" (798 vs 584 tok/s) (AMD_HIP.md:219-225).
- E-8 drafter prompt groups of 8: reverted (86c904ca).
- Intermediate HIP package without a pinned upload staging buffer: stalled on 8.8K, rejected (AMD_HIP_PERFORMANCE.md:97-101).

---

## Transfer candidates (dense Qwen3.8-27B, one 7900 XTX, llama.cpp HIP fork)

Our prefill: Q4_K/Q6_K weights, MMQ int8 WMMA ≈90% of prefill at 660–910 t/s. 27B×2 FLOP×800 t/s ≈ 43 TFLOPS effective [INFERENCE]. Context 30K–200K, ubatch 512.

| # | Idea | Mechanism | Strata's measured gain (HW) | Why or why not for us |
|---|---|---|---|---|
| T1 | **A/B dense FP16 GEMM (dequant + version-pinned hipBLASLt solution table, or own 128×256 WMMA) against MMQ, at ubatch 512/1024/2048/4096** | Dequant Q4_K/Q6_K → FP16 scratch once per ubatch, then a tuned FP16 GEMM with FP32 accumulate. Solution ids from a tuner with an accuracy gate, rows keyed by (dtype, N, K, ldy, T-bucket) | Tuned vs untuned hipBLASLt on gfx1100: +16/+52/+78% (ROCm 10.0, 0.37/1.7/6.5K tok), +82% at 131K (ROCm 10.2). Dense MMQ ≈ tuned Lt on gfx1151 (+0.2%). Own WMMA GEMM: 30–33 vs 25–27 TFLOPS (gfx1151); +10–27% over a calibrated table e2e (7900 XTX, with WMMA attention) | Our "hipBLASLt env = noise" result was expected: MMQ, not hipBLASLt, runs our prefill [INFERENCE]. The dequant costs ~4.6 B/param ≈ 124 GB/ubatch ≈ 130 ms, vs ~460 ms of GEMM at ubatch 512 (≈28%), ~7% at 2048 [INFERENCE]. Worth a per-shape microbench (FP16 hipBLASLt tuned for 100401 on ROCm 10.0 vs our MMQ) before building anything |
| T2 | **Larger ubatch (1024–4096) for long prompts** | Fewer per-ubatch fixed costs, better MMQ tile fill, and the amortization T1 needs | MoE-driven gains: 2048 → 8192 +23% (Q2_0, 5070); 8192 → 32768 +15–25% (5090, 4080S). On 7900 XTX MoE: 16K flat, auto:32768 noise at 38K, +23% at 74K | Cheap to try with `-ub`. Watch compute-buffer VRAM at 200K ctx [INFERENCE]. Use Strata's trick of applying rounding-changing paths only to big chunks (`PF_SWITCH_MIN_T` analogue) |
| T3 | **GQA FA prefill on WMMA, reading q4_0 codes directly** (K5) | One tile = the query rows × the 6 q-heads of a KV head, so each K/V tile is loaded once per KV head. q4_0 codes (−8..7) are exact in FP16/int8. The per-32 scale is applied in FP32 per (cell, group): on gfx11 the C/D lane l owns column l&15 = one cell, so it is a per-lane scalar multiply. Online softmax, no split-K merge. Use the RDNA3 fragment layout (A/B replicated across lanes 16–31, C row = 2i + l/16) | Prompt attention was 25.6–27.7% of 7900 XTX prefill (sparse, ~2K cells). WMMA kernel 4.05x; e2e +17.9% @32K, +22.8% @128K, +29.5% @24.6K | **Highest-value item at 30K–200K** [INFERENCE]: our full attention at ~100K context is ~40% of prefill FLOPs (4·24·256·ctx·16 layers per token vs 2·27e9). Avoid materializing FP16 KV copies. Expect the kernel to end up gather/LDS-bound (PA_FAST lesson): invest in K/V LDS staging and bank padding (QS = HD+8, V stride 80 B), not in MMA count. Don't quantize Q to int8 (precision rejection) |
| T4 | FP32-level accuracy via an FP16 hi+lo split | Power-of-two pre-scale to ~2^14, then hi/lo halves, 2 MMAs | Accuracy matches FP32 (3e-6 vs FP64). Costs ≤15% vs single FP16 (gfx1151) | Only if KL tests show our FA prefill is precision-limited. Standard FA already uses single FP16. Low priority |
| T5 | **Check GDN prefill kernel shape: register-resident serial recurrence vs chunked** | 192 blocks (48 v-heads × 4 column blocks), 4 lanes per column, state in VGPRs, tokens staged 4–8 at a time in LDS with prefetch. Fuse conv + L2 norm. Don't write dead FP32 outputs | Chunked WY on gfx1100: −39% e2e. Serial-kernel tuning on gfx1151: 25.4 → 20.5 ms per 16K-layer (VGPR cliff fix); conv+L2 9.13 → 6.95 ms | Same GDN geometry if our model is HK16/HV48/S128 [INFERENCE: verify config]. If our fork runs chunked delta-rule ggml ops at prefill, measure its share. Strata's data says serial-in-registers wins on 96-CU gfx1100. Also check occupancy (waves/SIMD vs blocks) in our GDN and MMQ kernels |
| T6 | **Pad 4 KB-multiple row strides** | Row stride +64 halves on FP16 weight/activation buffers whose stride is a 4 KB multiple | K=6144 GEMM 19.1 → 35.0 TFLOPS; engine +3–7% at 8–64K (gfx1151, bitwise) | Our ssm_out (48×128=6144) and attn_output (24×256=6144) have K=6144. FP16 activations are 12,288 B/row (3×4 KB); FP32 hidden 5120 is 20,480 B (5×4 KB) [INFERENCE]. Q4_K weight rows (3,456 B) are not 4 KB multiples. Probe any FP16/FP32 intermediate with such strides |
| T7 | **Version-pin and fallback-count discipline for any vendor GEMM** | Table keyed by arch + hipBLASLt version. Verbose `fallbacks=` counter. Nearest-T bucket. Correctness gate plus padding canary at tune time | A hidden 642/642 fallback of one shape cost 32% (a45783c7) | Any hipBLAS(Lt) path we keep (e.g. the FP16 MTP head, or T1) should log fallbacks per shape. ROCm 10.0 = hipBLASLt 1.4.1 (100401) |
| T8 | **Cap the MTP drafter's KV window** | The draft layer attends only the last N cells (Strata default 32,768) | `--mtp-window 8192`: 64K decode +3.5%, 32K −0.4% (gfx1151) | Directly relevant to our 88 → 78 t/s at 94K. The draft chain reads the full q4_0 KV 4 times per step. Must re-check acceptance |
| T9 | Batched MTP prompt pass | Fill the MTP head's KV over the prompt with the batched/MMQ path | 0.9 s → 0.07 s of a 32K prompt | Check that our fork doesn't fill the MTP KV token by token during prefill [INFERENCE] |
| T10 | KV format re-evaluation | int8 ≈ fp16; q4_0+Hadamard +8–12% doc PPL; K8V4 between them | Quality data only (MoE speed gains don't transfer) | Our q4_0 KV at 200K ≈ 18.4 KB/token ≈ 3.8 GB; q8_0-K + q4_0-V ≈ 27 KB/token ≈ 5.5 GB [INFERENCE]. Try if VRAM allows; may help long-context MTP acceptance. Costs ~+50% KV bytes per decode step |
| T11 | Decode/verify attention score layout | One cell per thread per head group instead of a warp reduction per (cell, head) | Removed a +32 µs per window row cost on gfx1151 | Relevant to K4 (verify width 9–16) if our verify FA scales linearly in rows |
| T12 | One graph for all KV lengths | Kernels sized by capacity; the live length read from a device buffer | Lets Strata capture the QSA layer once (qsa.hpp:140-160) | For K3: avoid graph re-capture/update per step as n_kv grows [INFERENCE about our fork's graph handling] |
| T13 | FP16 safety if moving GEMMs to FP16 | Clamp SwiGLU to ±65504; NaN counter; BF16x2 hi/lo for precision-sensitive small projections | Prevents inf → NaN on massive activations (c517862c) | Needed only for T1's FP16 down projection |
| T14 | Measurement methodology | GPU-event phase timeline in the prefill path. Interleaved arms with fresh processes, first request discarded. KL floor = a chunk-size-change KL | — | Adopt a per-op-class prefill timeline at 30K/100K/200K before choosing among T1, T3, T5 |
| ✗ | Not transferable | Expert ring/streaming, lend coverage, CPU expert share, KV streaming/`--kv-resident`, KV prefetch, sparse-QSA scorer/select | — | MoE- or sparse-attention-specific. Our dense weights and full-attention KV are fully resident and fully read |
