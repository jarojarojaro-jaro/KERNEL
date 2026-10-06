# Vulkan compute as an LLM inference backend on AMD Radeon (state as of October 2026)

Method note: the llama.cpp findings come from reading the source directly. I made a sparse clone of `ggml-org/llama.cpp` at commit `5ad1c5da0ad7f6176256b823925aad19134f0263`, committed 2026-10-06, covering `ggml/src/ggml-vulkan/`, and read the git log of that directory from 2025-01-01 onward (585 commits). Source links point to the GitHub tree or PR. Line numbers refer to `ggml-vulkan.cpp` at that commit, which is 16,587 lines long. GitHub's REST and GraphQL APIs for llama.cpp were blocked in this session, so I could not read PR descriptions or discussions beyond the squash-commit messages and WebFetch summaries.

Contributor identities: "Ruben Ortlam" commits as **0cc4m**, the Vulkan backend maintainer. Commits co-authored by `0cc4m <picard12@live.de>` show the same person. "Eve" is **netrunnereve**. "Jeff Bolz" is **jeffbolznv** (NVIDIA). Commit counts on `ggml-vulkan/` since 2025-01-01: Jeff Bolz 259, Ruben Ortlam 75 (+10 more under the "0cc4m" name), Eve 16, Georgi Gerganov 14, Acly 12, Masato Nakasaka (Intel) 11, Winston Ma 10. Source: [llama.cpp git history](https://github.com/ggml-org/llama.cpp/commits/master/ggml/src/ggml-vulkan).

---

## 1. Drivers: RADV vs AMDVLK vs the proprietary (Windows) driver; ACO; env vars

### Takeaway
AMD discontinued AMDVLK on 2025-09-15 and now supports Mesa RADV (compiler: ACO) as its official open-source Linux Vulkan driver. On Linux, RADV is the reference driver for llama.cpp, and llama.cpp prefers it when several drivers expose the same GPU. The Windows proprietary driver is supported but gets several llama.cpp workarounds and loses some AMD tuning: the large coopmat tile config is off, and there are fixes for fp16 bugs on old GPUs.

### Cited findings
- **AMDVLK was discontinued on 2025-09-15.** AMD's statement says it is "unifying its Linux Vulkan driver strategy and has decided to discontinue the AMDVLK open-source project, throwing our full support behind the RADV driver as the officially supported open-source Vulkan driver for Radeon graphics adapters" — [Phoronix](https://www.phoronix.com/news/AMDVLK-Discontinued); [GamingOnLinux](https://www.gamingonlinux.com/2025/09/amdvlk-has-been-discontinued-as-amd-are-throwing-their-full-support-behind-radv/comment_id=283338).
- In May 2025, AMD announced that its packaged Radeon Software for Linux would officially support Mesa RADV and drop its proprietary OpenGL and Vulkan drivers. Valve, Google, Red Hat and others had already matured RADV, including for compute and workstation use — [Phoronix](https://www.phoronix.com/news/AMDVLK-Discontinued).
- **llama.cpp driver priority when one GPU appears under several drivers** (e.g., RADV and AMDVLK both installed): `eMesaRadv = 1`, `eAmdOpenSource (AMDVLK) = 2`, `eAmdProprietary = 3`. RADV is chosen first (lines 5315–5363) — [ggml-vulkan.cpp](https://github.com/ggml-org/llama.cpp/blob/master/ggml/src/ggml-vulkan/ggml-vulkan.cpp).
- **Proprietary-driver handling in llama.cpp:**
  - The large ("l") coopmat matmul tile is disabled on `eAmdProprietary`: `mul_mat_l = coopmat_support && driver_id != eAmdProprietary`. This comes from PR #18763 (2026-01-12, "Disable large coopmat matmul configuration on proprietary AMD driver").
  - The AMD-coopmat warptile tuning from PR #18749 applies only when `driver_id != eAmdProprietary`.
  - GCN matmul tuning (PR #13016, Eve, 2025-04-24) is also disabled on the proprietary driver.
  - An `old_amd_windows` flag (proprietary driver + GCN/RDNA1/RDNA2) changes the flash attention (FA) pipeline. It relates to "fix fp16 Flash Attention on Windows AMD RDNA2 and below" (#19921, 2026-02-26).
  - Workarounds exist for the "legacy Windows AMD driver" 16-bit `unpack8` bug: #12472 (2025-03-21) and #17285 (2025-11-15).
  - Sources: [ggml-vulkan.cpp](https://github.com/ggml-org/llama.cpp/blob/master/ggml/src/ggml-vulkan/ggml-vulkan.cpp); [PR #18763](https://github.com/ggml-org/llama.cpp/pull/18763); [PR #19921](https://github.com/ggml-org/llama.cpp/pull/19921); [PR #17285](https://github.com/ggml-org/llama.cpp/pull/17285).
- **KHR_coopmat whitelist on AMD.** For the AMD proprietary driver and AMDVLK, llama.cpp only uses `VK_KHR_cooperative_matrix` on RDNA3/RDNA4 ("Workaround for AMD proprietary driver reporting support on all GPUs"). For RADV it trusts the driver's report (line ~16264). The device blacklist dates from PR #11074 (0cc4m, 2025-01-04) — [ggml-vulkan.cpp](https://github.com/ggml-org/llama.cpp/blob/master/ggml/src/ggml-vulkan/ggml-vulkan.cpp); [PR #11074](https://github.com/ggml-org/llama.cpp/pull/11074).
- **RADV vs AMDVLK on Strix Halo, from strixhalo.wiki** (Qwen3-30B-A3B UD-Q4_K_XL):
  - Short context: RADV pp512 755.14 / tg128 85.11; AMDVLK 741.60 / 81.79.
  - At depth 130,560: RADV pp512 17.24 / tg128 12.54; AMDVLK 10.75 / 3.51.
  - So RADV holds up much better at long context — [strixhalo.wiki llama.cpp performance](https://strixhalo.wiki/AI/llamacpp-performance/).
- **Phoronix test, Radeon RX 9070 XT** on Ubuntu 24.04.3, Linux 6.17, Mesa 25.3-dev: RADV Vulkan beat llama.cpp's ROCm 6.4.3 back-end in every test run. This included tg128 on Llama-3.1-Tulu-3-8B-Q8_0 and Qwen3-8B-Q8_0, and pp512 on Qwen3-8B-Q8_0 — [Phoronix, via search summary](https://www.phoronix.com/review/llama-cpp-windows-linux/5). I could only see the search summary because the page returned 403 to WebFetch.
- **llama.cpp env vars that matter on AMD** (complete list of `GGML_VK_*` names in the source at 2026-10-06):
  - Feature switches: `GGML_VK_DISABLE_COOPMAT`, `GGML_VK_DISABLE_COOPMAT2`, `GGML_VK_DISABLE_COOPMAT2_DECODE_VECTOR`, `GGML_VK_DISABLE_INTEGER_DOT_PRODUCT`, `GGML_VK_DISABLE_DOT2`, `GGML_VK_DISABLE_BFLOAT16`, `GGML_VK_DISABLE_F16`, `GGML_VK_DISABLE_OCP_FP4`, `GGML_VK_DISABLE_MMVQ`, `GGML_VK_FORCE_MMVQ`, `GGML_VK_DISABLE_FUSION`, `GGML_VK_DISABLE_MULTI_ADD`, `GGML_VK_DISABLE_GRAPH_OPTIMIZE`, `GGML_VK_FA_SPARSE_DISABLE`.
  - Queue/submission and memory: `GGML_VK_ALLOW_GRAPHICS_QUEUE`, `GGML_VK_ASYNC_USE_TRANSFER_QUEUE`, `GGML_VK_DISABLE_ASYNC`, `GGML_VK_MAX_NODES_PER_SUBMIT`, `GGML_VK_PREFER_HOST_MEMORY`, `GGML_VK_DISABLE_HOST_VISIBLE_VIDMEM`, `GGML_VK_ALLOW_SYSMEM_FALLBACK`, `GGML_VK_FORCE_MAX_ALLOCATION_SIZE`, `GGML_VK_FORCE_MAX_BUFFER_SIZE`, `GGML_VK_SUBALLOCATION_BLOCK_SIZE`, `GGML_VK_ENABLE_MEMORY_PRIORITY`.
  - Profiling: `GGML_VK_PERF_LOGGER` (+ `_CONCURRENT`, `_FREQUENCY`), `GGML_VK_PIPELINE_STATS`, `GGML_VK_DEBUG_MARKERS`, `GGML_VK_MEMORY_LOGGER`, `GGML_VK_SYNC_LOGGER`.
  - Device selection: `GGML_VK_VISIBLE_DEVICES`.
  - Source: [ggml-vulkan.cpp](https://github.com/ggml-org/llama.cpp/blob/master/ggml/src/ggml-vulkan/ggml-vulkan.cpp).
- **Graphics queue.** The code comment reads: "Allow overriding avoiding the graphics queue because it can increase performance on RADV." By default the backend picks a compute queue without graphics. `GGML_VK_ALLOW_GRAPHICS_QUEUE` allows the graphics queue. On AMD non-GCN dGPUs (not UMA), the backend prefers a dedicated transfer queue for async copies unless the graphics queue is allowed.
  - PR #20551 (2026-03-15, "use graphics queue on AMD for slightly better performance") appears in history. The current code is opt-in via env var, so that default was changed again later — [ggml-vulkan.cpp](https://github.com/ggml-org/llama.cpp/blob/master/ggml/src/ggml-vulkan/ggml-vulkan.cpp); [PR #20551](https://github.com/ggml-org/llama.cpp/pull/20551).
  - An R9700 tuning thread, reported by an aggregator, measured `GGML_VK_ALLOW_GRAPHICS_QUEUE=1` at "+5% MoE decode, –8% dense" — [runaihome.com (aggregated)](https://runaihome.com/blog/rdna4-vulkan-vs-rocm-local-llm-benchmark-2026/).
- **RADV `VK_NV_cooperative_matrix2`.** Mesa 25.2 RADV has limited support, disabled by default, exposed only with the DriConf option `radv_cooperative_matrix2_nv` — [Phoronix](https://www.phoronix.com/news/RADV-NV-Coperative-Matrix2).

### Inferences
- On Linux the practical choice is RADV. AMDVLK is dead upstream and slower at long context in the Strix Halo data. The proprietary Windows driver is the only option on Windows, with somewhat less tuning in llama.cpp.
- The following is background knowledge that I did not re-verify with a fetched source in this session, so treat it as unconfirmed:
  - RADV compiles shaders with **ACO**, Valve's AMD compiler, by default. AMDVLK and the Windows driver use AMD's LLVM-based LLPC/PAL stack.
  - Ubuntu-style installs with both ICDs choose between them with `AMD_VULKAN_ICD=RADV|AMDVLK` or `VK_ICD_FILENAMES` / `VK_DRIVER_FILES`.
  - `RADV_PERFTEST=coop_matrix` was needed only in early Mesa versions. Current RADV exposes `VK_KHR_cooperative_matrix` on RDNA3/RDNA4 by default.
  - `vulkaninfo | grep -i coop` confirms what the driver exposes, and llama.cpp prints `matrix cores: KHR_coopmat` at startup.

### Gaps
- Mesa docs pages for RADV env vars (`RADV_PERFTEST`, `RADV_DEBUG`, `ACO_DEBUG`) were not fetched. The exact current RADV_PERFTEST flags for coop matrix are unverified.
- I found no 2026 head-to-head of the Windows proprietary driver vs RADV on the same RDNA3/4 card. The Phoronix "Windows 11 vs Linux" article returned 403.

---

## 2. Vulkan extensions that matter, and how they map to AMD hardware

### Takeaway
On AMD the key extensions are:
- `VK_KHR_cooperative_matrix`: WMMA on RDNA3/RDNA4. RDNA4 also has int8 and FP8 paths.
- `VK_KHR_shader_integer_dot_product`: dp4a-style `v_dot4_i32_i8`, used by MMQ/MMVQ and quantized-KV FA.
- `VK_EXT_subgroup_size_control`: wave32 vs wave64.
- fp16/int8 storage and arithmetic.
- `VK_KHR_shader_bfloat16` and `VK_EXT_shader_float8`: RADV exposes these only on RDNA4.
- `VK_VALVE_shader_mixed_float_dot_product`: `v_dot2_f32_f16`.

`VK_NV_cooperative_matrix2` is the NVIDIA "coopmat2" path. It is effectively unavailable on AMD; RADV support is experimental and off by default.

### Cited findings
- **How llama.cpp detects AMD architecture** (lines 40–60):
  - Subgroup min/max = 64/64 → **GCN**.
  - min 32 / max 64 → RDNA. Within RDNA:
    - `wavefrontsPerSimd == 20` → **RDNA1**.
    - `VK_EXT_shader_float8` present → **RDNA4**.
    - `integerDotProduct4x8BitPackedMixedSignednessAccelerated` → **RDNA3**.
    - Otherwise → **RDNA2**.
  - `VK_EXT_shader_float8` doubles as the RDNA4 marker, and mixed-signedness int8 dot acceleration as the RDNA3 marker — [ggml-vulkan.cpp](https://github.com/ggml-org/llama.cpp/blob/master/ggml/src/ggml-vulkan/ggml-vulkan.cpp).
- **Extensions llama.cpp checks/enables**: `VK_KHR_maintenance4`, `VK_EXT_subgroup_size_control`, `VK_KHR_cooperative_matrix`, `VK_NV_cooperative_matrix2`, `VK_KHR_shader_integer_dot_product`, `VK_KHR_shader_bfloat16`, `VK_EXT_shader_float8`, `VK_VALVE_shader_mixed_float_dot_product`, `VK_KHR_pipeline_executable_properties`, `VK_EXT_memory_priority`, and `VK_EXT_shader_64bit_indexing`, used for very large tensors (lines 4036–4442) — [ggml-vulkan.cpp](https://github.com/ggml-org/llama.cpp/blob/master/ggml/src/ggml-vulkan/ggml-vulkan.cpp).
- **Shader-side feature tests** in `vulkan-shaders/feature-tests/` probe glslc support at build time: `bfloat16.comp`, `coopmat.comp`, `coopmat2.comp`, `coopmat2_decode_vector.comp`, `float_e2m1.comp`, `float_e4m3.comp`, `integer_dot.comp`. When glslc lacks support, the CMake defines `GGML_VULKAN_COOPMAT_GLSLC_SUPPORT`, `..._COOPMAT2_...` and `..._BFLOAT16_...` stay unset (PR #13696, 2025-05-23) — [vulkan-shaders dir](https://github.com/ggml-org/llama.cpp/tree/master/ggml/src/ggml-vulkan/vulkan-shaders); [PR #13696](https://github.com/ggml-org/llama.cpp/pull/13696).
- **RDNA4 cooperative matrix in RADV.** `VK_KHR_cooperative_matrix` on GFX12/RDNA4 was merged into RADV for Mesa 25.2 — [Phoronix](https://www.phoronix.com/news/RADV-Lands-RDNA4-Coop-Matrix); [Mesa 25.2.0 release notes, 2025-08-06](https://docs.mesa3d.org/relnotes/25.2.0.html).
- **`VK_KHR_shader_bfloat16`** was added to RADV for GFX12+ in Mesa 25.2. RDNA3 (GFX11) "has precision issues with BF16", so RADV does not enable it there — [Phoronix](https://phoronix.com/news/RADV-Shader-BFloat16).
- **`VK_EXT_shader_float8`**: RADV is the first Mesa driver with it, on RDNA4/GFX12+, supporting E4M3FN and E5M2. Only conversions and coop-matrix muladd are supported, and conversions go through fp32. Shipped in Mesa 25.2 — [Phoronix](https://www.phoronix.com/news/RADV-VK_EXT_shader_float8); [Khronos proposal](https://docs.vulkan.org/features/latest/features/proposals/VK_EXT_shader_float8.html).
- **FP4/FP8 in llama.cpp.** PR #25338 (2026-07-13) uses "native e2m1 and e4m3 conversions for mxfp4/nvfp4". `GGML_VK_DISABLE_OCP_FP4` toggles this. NVFP4 type support arrived in PR #21455 (2026-04-14) — [PR #25338](https://github.com/ggml-org/llama.cpp/pull/25338); [PR #21455](https://github.com/ggml-org/llama.cpp/pull/21455).
- **`VK_VALVE_shader_mixed_float_dot_product` (fp16 dot2).** PR #24123 (0cc4m, 2026-06-09) added "`v_dot2_f32_f16` support in matrix-matrix multiplication and Flash Attention" via "valve fp16 dot2 extension", with a `dot_product_funcs.glsl` abstraction. It applies to the scalar (non-coopmat) matmul/FA paths, i.e., GPUs without WMMA. BF16 variants explicitly don't use dot2 — [PR #24123](https://github.com/ggml-org/llama.cpp/pull/24123); [dot_product_funcs.glsl](https://github.com/ggml-org/llama.cpp/blob/master/ggml/src/ggml-vulkan/vulkan-shaders/dot_product_funcs.glsl).
- **Wave32/wave64.** llama.cpp sets `VkPipelineShaderStageRequiredSubgroupSizeCreateInfoEXT.requiredSubgroupSize` per pipeline when `subgroup_size_control` is available (lines 741–745). Per-arch override tables:
  - `rdna1_pipelines` = {soft_max:64, im2col:64, argmax:64, mul_mat_vec:64, mul_mat_vec_f16:32, mul_mat_vec_f32_f16:32}.
  - `rdna2_pipelines` = {soft_max:64, im2col:64}.
  - Everything else uses `RDNA_DEFAULT_SUBGROUP_SIZE`.
  - The tables come from PR #12087 (Daniele, 2025-03-17), which also notes "disable warp 32 for RDNA3".
  - The new int8 coopmat matmul "only force[s] subgroup size 32 on AMD RDNA" (PR #27952).
  - Sources: [ggml-vulkan.cpp](https://github.com/ggml-org/llama.cpp/blob/master/ggml/src/ggml-vulkan/ggml-vulkan.cpp); [PR #12087](https://github.com/ggml-org/llama.cpp/pull/12087); [PR #27952](https://github.com/ggml-org/llama.cpp/pull/27952).

### Inferences
- The table below maps llama.cpp's AMD paths by generation, inferred from the detection and gating code above. RDNA2 and older have no matrix cores, so prompt processing (pp) relies on scalar/dot2 FMA and dp4a. RDNA3/4 get KHR_coopmat (WMMA), and since September 2026 also int8 WMMA MMQ.

| Gen | KHR_coopmat (WMMA) | int8 dot (dp4a) | BF16 / FP8 (RADV) | Notes |
|---|---|---|---|---|
| GCN (Vega/MI50) | no | yes on GCN5+ (by driver) | no | wave64 only; own warptiles |
| RDNA1 | no | partial | no | wave64 forced for some shaders |
| RDNA2 | no | yes | no | dot2 path useful |
| RDNA3 | yes (fp16 → f16/f32 acc) | yes (accelerated mixed-sign) | BF16 not exposed by RADV | int8 coopmat MMQ since 09/2026 |
| RDNA4 | yes | yes | BF16 + FP8 exposed | some quants fall back to fp16 matmul |

- The table's int8-dot cells for GCN and RDNA1 are inferred and not verified.

### Gaps
- The WMMA tile shapes RADV exposes via `vkGetPhysicalDeviceCooperativeMatrixPropertiesKHR` on RDNA3 vs RDNA4 (e.g., 16x16x16 f16, 16x16x16 i8; RDNA4 FP8/BF16 combos) were not fetched from a primary source.
- Windows proprietary driver support for BF16/FP8 extensions is unknown.
- `VK_EXT_shader_bfloat16` (the item named in the brief) does not exist as far as I can tell. The relevant extension is `VK_KHR_shader_bfloat16`.

---

## 3. llama.cpp ggml-vulkan backend internals (shaders, paths, AMD tuning, PRs)

### Takeaway
ggml-vulkan has about 170 GLSL compute shaders compiled to SPIR-V at build time by `vulkan-shaders-gen.cpp`. Specialization constants generate many variants per type, tile size, subgroup size and coopmat mode. Matmul has five families:
- `mul_mm` (scalar / coopmat1 / coopmat2 fp16)
- `mul_mmq` (int8 dot product)
- `mul_mmq_cm1` (int8 WMMA, new for RDNA3/4)
- `mul_mat_vec` (dequantize + FMA GEMV for decode)
- `mul_mat_vecq` / MMVQ (int8 dot GEMV)

Flash attention has scalar, coopmat1 and coopmat2 variants plus DP4A, decode split-phase, sparse and split-k pieces. Most AMD gains in 2025–2026 came from 0cc4m's integer-dot MMQ/MMVQ work, the FA refactors, AMD coopmat tile tuning and the September 2026 int8-coopmat matmul.

### Cited findings
**Shader inventory.** All in `ggml/src/ggml-vulkan/vulkan-shaders/` at 2026-10-06 — [dir](https://github.com/ggml-org/llama.cpp/tree/master/ggml/src/ggml-vulkan/vulkan-shaders):
- Matmul (prompt/batch):
  - `mul_mm.comp` covers scalar and KHR coopmat1 via `GL_KHR_cooperative_matrix`. Spec constants: `BLOCK_SIZE, BM, BN, WM, WN, WMITER, TM, TN, ..., ALIGNED, MmTypeA`.
  - `mul_mm_cm2.comp` is the NV coopmat2 variant.
  - `mul_mm_funcs.glsl` and `mul_mm_id_funcs.glsl` handle MoE `MUL_MAT_ID`.
  - `mul_mmq.comp` and `mul_mmq_funcs.glsl`: int8 integer-dot MMQ.
  - `mul_mmq_cm1.comp` and `mul_mmq_cm1_funcs.glsl`: int8 cooperative-matrix MMQ. It needs `GL_KHR_cooperative_matrix` and `GL_EXT_shader_explicit_arithmetic_types_int8`.
  - `mul_mat_split_k_reduce.comp`.
- Matvec (decode):
  - `mul_mat_vec.comp`, `mul_mat_vec_base.glsl` (spec constants `BLOCK_SIZE`, `NUM_ROWS`, `NUM_COLS`; uses `GL_KHR_shader_subgroup_arithmetic`), and per-type `mul_mat_vec_q{2..6}_k.comp` / `mul_mat_vec_iq*.comp`.
  - `mul_mat_vecq.comp` (`GL_EXT_integer_dot_product`, `B_TYPE block_q8_1_x4`, `K_PER_ITER` 8/16/32 per quant family).
  - `mul_mat_vec_nc.comp` / `mul_mat_vec_p021.comp` for non-contiguous KV-like views.
  - `quantize_q8_1.comp` quantizes activations for the integer paths.
- Flash attention: `flash_attn.comp` (scalar), `flash_attn_cm1.comp`, `flash_attn_cm2.comp`, `flash_attn_base.glsl`, `flash_attn_dequant.glsl`, `flash_attn_mmq_funcs.glsl` (DP4A FA for quantized KV), `flash_attn_decode_phase_1/2.comp`, `flash_attn_mask_opt.comp`, `flash_attn_sparse_compact.comp`, `flash_attn_split_k_reduce.comp`.
- Dequant: `dequant_*.comp` for every ggml type, including `q1_0`, `q2_0`, `mxfp4`, `nvfp4`, `tq1_0`/`tq2_0` and all IQ types. Shared code lives in `dequant_funcs.glsl` / `dequant_funcs_cm2.glsl`.
- Model-specific ops: `gated_delta_net.comp` (Qwen3-Next-style GDN), `ssm_scan.comp`, `ssm_conv.comp`, `wkv6/7.comp`, `topk_moe.comp`, `topk_radix_select.comp`, `lightning_indexer.comp` and `dsv4_hc_*.comp` (DeepSeek-V4-related), `fwht.comp`, `rms_norm_partials.comp`, `multi_add.comp`.

**AMD-specific tuning in `ggml-vulkan.cpp`** (2026-10-06) — [ggml-vulkan.cpp](https://github.com/ggml-org/llama.cpp/blob/master/ggml/src/ggml-vulkan/ggml-vulkan.cpp):
- Matmul warptiles:
  - On GCN with non-proprietary drivers: `m_warptile_mmq = {256, 64, 64, 32, 16, 16, 2, 2, 2, 1, 16}`.
  - On AMD with coopmat (RDNA3/4) and non-proprietary drivers: `l_warptile = {256, 128, 128, 16, warp8, 64, 2, tm_m, tn_m, tk_m, warp8}` and `l_warptile_mmq = {256, 128, 128, 32, ...}`. The code comment says "This is intentionally using tx_m values, slight performance increase" (PR #18749, 0cc4m, 2026-01-11, "Optimize Matmul parameters for AMD GPUs with Coopmat support").
  - Tile denominators: large 128×128, medium 64×64, small 32×32.
- The int8 coopmat MMQ (`use_cm1_int`) is enabled only when `coopmat_int_support && (RDNA3 || RDNA4)`. The comment reads "Some quants are not performant on RDNA4, those fall back to FP16 matmul."
- Matvec rows per workgroup:
  - GCN: `rm_stdq=2, rm_kq=4, rm_stdq_int=4`.
  - RDNA3/4: "above four columns, static 4 rows for all types bench faster than the default", and `rm_id` (MUL_MAT_ID) is fixed at 4. PR #29934 (2026-10-04) "fix rdna4 mat_vec tuning" is the most recent change.
- MMVQ heuristic `ggml_vk_should_use_mmvq`:
  - MMVQ is used for batch (n>1).
  - For n=1 on AMD: no MMVQ if k<2048, and q8_0 uses MMVQ only on GCN.
  - q6_k MMVQ is used only on Intel because of its 2-byte alignment.
  - `GGML_VK_FORCE_MMVQ` and `GGML_VK_DISABLE_MMVQ` override the heuristic.
- Scalar FA tuning:
  - On RDNA, subgroup size 32 when n_rows<4.
  - "row_split" splits the workgroup so that synchronization stays inside subgroups.
  - Occupancy-limiting trick: "On AMD RDNA, for small head sizes and big batch size the shader uses few registers, so too many subgroups get scheduled at once and end up thrashing the cache. Fix this by setting a large (unused) shmem buffer that reduces occupancy. This targets an occupancy of 4 subgroups per SIMD." It reserves about 26–30 KB on RDNA (when `maxComputeSharedMemorySize == 65536`) and targets 2 subgroups/SIMD on GCN for large head sizes.
  - FA `mask_opt` is disabled on GCN (PR #24362, 2026-07-08).
- Submission batching: `flops_cap` defaults to 200 GFLOP per submit. On small AMD GPUs it scales with CU count (GCN <32 CUs: 0.5 GFLOP×CU; RDNA <24 CUs: 2 GFLOP×CU) "to avoid driver timeout" (PR #25240, 2026-07-08).
- Partial offload: PR #19976 (2026-03-01) "improve partial offloading performance on AMD" uses the transfer queue with timeline semaphores for async copies, disabled on GCN.
- UMA (Strix Halo/APUs):
  - PR #16059 (Giuseppe Scrivano, 2025-09-21) "optimize UMA buffer operations and fix driver hangs".
  - PR #22930 (2026-06-16) "prefer host-visible memory buffers on UMA devices".
  - PR #22455 (2026-05-27) "avoid preferring transfer queue on AMD UMA devices".

**Notable 2025–2026 PRs**, in order, from git log of `ggml/src/ggml-vulkan` (each links to its PR):
- 2025-03-17 [#12087](https://github.com/ggml-org/llama.cpp/pull/12087) subgroup size tuning and the AMD arch enum (Daniele, with 0cc4m).
- 2025-04-24 [#13016](https://github.com/ggml-org/llama.cpp/pull/13016) matmul GCN tuning (Eve).
- 2025-05-01 [#12554](https://github.com/ggml-org/llama.cpp/pull/12554) bfloat16 support (jeffbolznv).
- 2025-05-09 [#13324](https://github.com/ggml-org/llama.cpp/pull/13324) scalar flash attention, which made FA work on non-NVIDIA GPUs.
- 2025-05-14 [#13506](https://github.com/ggml-org/llama.cpp/pull/13506) KHR_coopmat flash attention (coopmat1 FA, usable on RDNA3/4).
- 2025-09-01 [#14903](https://github.com/ggml-org/llama.cpp/pull/14903) integer-dot `mul_mat_vec` (MMVQ) for legacy quants. It added the `q8_1_x4` 128-bit-aligned activation blocks and subgroup-op `quantize_q8_1`, tuned for "Intel, AMD GCN and Nvidia RTX 3090" (0cc4m).
- 2025-09-07 [#15729](https://github.com/ggml-org/llama.cpp/pull/15729) larger loads in scalar/coopmat1 matmul.
- 2025-10-29 [#16536](https://github.com/ggml-org/llama.cpp/pull/16536) "MMQ Integer Dot Refactor and K-Quant support". It added q2_k–q6_k and mxfp4 MMQ, 32-bit accumulators, 4 quant blocks loaded into shmem in one step, lower register use, and MMQ for MUL_MAT_ID (MoE).
- 2025-11-29 [#16900](https://github.com/ggml-org/llama.cpp/pull/16900) MMVQ for K-quants and MUL_MAT_ID, with subgroup optimizations for `mul_mat_vec_id` and device tuning.
- 2025-12-14 [#17813](https://github.com/ggml-org/llama.cpp/pull/17813) faster q6_k matmul (Eve).
- 2026-01-07 [#18533](https://github.com/ggml-org/llama.cpp/pull/18533) more mul_mat optimizations for q4_k/q5_k/q2_k/q4_1/q5_1 (Eve).
- 2026-01-11 [#18749](https://github.com/ggml-org/llama.cpp/pull/18749) AMD coopmat matmul tile tuning.
- 2026-01-28 [#19075](https://github.com/ggml-org/llama.cpp/pull/19075) "Vulkan Flash Attention Coopmat1 Refactor". It uses coopmat for P·V, subgroup reductions, fewer barriers, and doesn't store the whole K tile in shmem.
- 2026-02-24 [#19625](https://github.com/ggml-org/llama.cpp/pull/19625) "Vulkan Scalar Flash Attention Refactor". Changes: fp16 in scalar FA, row-splitting within subgroups, Q cached in registers, fused accumulation loops, K/V staged through shmem (Nvidia only), vectorized stores, and a relaxed split_k condition. The description includes "fix amd workgroup size issue".
- 2026-03-01 [#19976](https://github.com/ggml-org/llama.cpp/pull/19976) AMD partial offload.
- 2026-04-13 [#20797](https://github.com/ggml-org/llama.cpp/pull/20797) Flash Attention DP4A shader for quantized KV cache.
- 2026-05-11 [#22589](https://github.com/ggml-org/llama.cpp/pull/22589) asymmetric FA (K≠V head dim) in scalar/mmq/cm1.
- 2026-05-30 [#23420](https://github.com/ggml-org/llama.cpp/pull/23420) FA for BF16 KV cache.
- 2026-06-09 [#24123](https://github.com/ggml-org/llama.cpp/pull/24123) `v_dot2_f32_f16` via VALVE extension.
- 2026-07-08 [#24362](https://github.com/ggml-org/llama.cpp/pull/24362) FA mask_opt off on GCN; [#25240](https://github.com/ggml-org/llama.cpp/pull/25240) submit threshold by CU count.
- 2026-09-15 [#28105](https://github.com/ggml-org/llama.cpp/pull/28105) sparse Flash Attention; 2026-10-05 [#29639](https://github.com/ggml-org/llama.cpp/pull/29639) sparse FA for quantized K/V.
- 2026-09-18/23 [#28822](https://github.com/ggml-org/llama.cpp/pull/28822), [#28415](https://github.com/ggml-org/llama.cpp/pull/28415) IQ3_S and IQ4_XS MMQ/MMV kernels.
- **2026-09-24 [#27952](https://github.com/ggml-org/llama.cpp/pull/27952) "int8 coopmat1 matmul implementation for AMD RDNA3 and RDNA4" (0cc4m).** Listed techniques: scales applied inline; coopmat values probed and accessed directly instead of going through shmem; q8_0 support; `BK_STEP` (default 2, later 4); larger workgroups; double buffering; scale preloading; "coopmat load first, then wmma"; float scales; "faster RDNA int->float conversion"; "workgroup scheduling for cache proximity"; wave32; restructuring for VGPR use; skipping inactive tiles; forcing subgroup size 32 only on AMD RDNA.
- 2026-10-04 [#29934](https://github.com/ggml-org/llama.cpp/pull/29934) fix RDNA4 mat_vec tuning.
- NVIDIA-only (coopmat2) work by jeffbolznv benefits RTX cards, not AMD: [#23541](https://github.com/ggml-org/llama.cpp/pull/23541) `GL_NV_cooperative_matrix_decode_vector` (2026-05-27), [#14934](https://github.com/ggml-org/llama.cpp/pull/14934), [#15546](https://github.com/ggml-org/llama.cpp/pull/15546).
- Graph-level work helps every vendor: graph_optimize reordering ([#17475](https://github.com/ggml-org/llama.cpp/pull/17475)), op fusion (`GGML_VK_DISABLE_FUSION`), and `multi_add`.

**Introspection built into llama.cpp:** with `VK_KHR_pipeline_executable_properties`, llama.cpp captures pipeline statistics when creating each pipeline. `GGML_VK_PIPELINE_STATS=<substring>` prints the driver stats (VGPR/SGPR counts, LDS, spills, etc.) for matching pipelines (lines 749–800). `GGML_VK_PERF_LOGGER=1` prints per-op GPU timings from timestamp queries (#13817, #17944) — [ggml-vulkan.cpp](https://github.com/ggml-org/llama.cpp/blob/master/ggml/src/ggml-vulkan/ggml-vulkan.cpp); [PR #17944](https://github.com/ggml-org/llama.cpp/pull/17944).

### Inferences
- Path selection on RDNA3/4 with RADV:
  - pp with quantized weights now uses int8 WMMA (`mul_mmq_cm1`) for supported quants. Otherwise it dequantizes to fp16 and uses fp16 WMMA (`mul_mm` coopmat1).
  - Decode (tg) uses `mul_mat_vec` (dequant+FMA) or MMVQ (dp4a) depending on quant type and k.
  - FA uses coopmat1 for prefill and scalar/decode-split for single tokens. Since #13554, scalar FA rather than coopmat2 is used when N==1.
- On RDNA2/GCN, pp is limited to scalar FMA, dot2 and dp4a, which explains the large pp gap to RDNA3/4.
- The tuning style is empirical per-arch constants (warptile tuples, rows-per-WG, subgroup-size maps, occupancy-limiting shmem), not autotuning.

### Gaps
- I could not read PR descriptions or benchmark tables, so the speedups claimed in #27952, #18749, #19075, #19625 and #24123 are unknown. The GitHub API was blocked, and only squash-commit bullet lists were available.
- I did not determine the exact value of `RDNA_DEFAULT_SUBGROUP_SIZE`.

---

## 4. Benchmarks: Vulkan vs ROCm/HIP (7900 XTX, 9070 XT, Strix Halo)

### Takeaway
Typical pattern in 2025–2026: **Vulkan (RADV) usually wins token generation (tg)** on small and medium dense models and MoE. **ROCm usually wins prompt processing (pp)** on large or dense models and at long context (rocWMMA FA). The gap shifts with each llama.cpp build, ROCm release and Mesa release, so always compare builds from the same date.

### Cited findings
- **llama.cpp Vulkan scoreboard, Discussion #10879.** Setup: Llama 2 7B Q4_0, `llama-bench -ngl 100 -fa 0,1`. All AMD rows on RADV.

| GPU | pp512 | tg128 | Build |
|---|---|---|---|
| RX 7900 XTX | 3726.99 | 182.63 | `304665f` |
| RX 7900 XTX + FA | 3889.54 | 190.92 | `304665f` |
| RX 7900 XT | 2941.58 | 123.18 | |
| RX 9070 XT | 5036.04 | 137.11 | `e9fd8dc` |
| RX 9070 XT + FA | 5048.07 | 131.54 | `e9fd8dc` |
| RX 9070 | 3164.10 | 119.71 | |
| RX 6800 XT | 1752.92 | 100.32 | |
| MI50 | 1119.55 | 108.51 | |
| MI50 + FA | 1127.37 | 117.94 | |
| Radeon Pro VII | 912.47 | 106.03 | |
| RTX 4090 (coopmat2) | 9452 | 187.97 | |
| RTX 4090 (coopmat2) + FA | 10830 | 190.10 | |
| RTX 3090 (coopmat2) | 4666 | 164.05 | |

  - Row dates are not given in the summary. Builds are identified by commit hash — [Discussion #10879](https://github.com/ggml-org/llama.cpp/discussions/10879).
  - Parallel ROCm scoreboard: [Discussion #15021](https://github.com/ggml-org/llama.cpp/discussions/15021).
- **RDNA4 aggregation** (runaihome.com, "mid-2026 commits", aggregated from community scoreboards, not measured by the site). Llama 2 7B Q4_0, Vulkan vs ROCm 7.2:

| GPU | tg Vulkan | tg ROCm | pp Vulkan | pp ROCm |
|---|---|---|---|---|
| RX 9070 XT | 137.1 | 101.3 | 5036 | 5055 |
| AI PRO R9700 | 138.8 | 98.0 | 5620 | 4773 |
| RX 9070 | 119.7 | 114.5 | 3164 | 2382 |
| RX 9060 XT | 70.5 | 67.6 | 2142 | 1480 |

  - Dense Qwen3.6-27B (Q8-class KV), from RDNA4 tuning thread #21043: "42.8 tok/s on ROCm vs 29.1 tok/s on Vulkan", a 47% ROCm advantage.
  - MoE Qwen3.5-35B-A3B: "127 tok/s stock on Vulkan, 156 tok/s tuned".
  - Tuning cited: `-ub 2048 -b 16384` (+29% MoE prefill).
  - Source: [runaihome.com](https://runaihome.com/blog/rdna4-vulkan-vs-rocm-local-llm-benchmark-2026/). This is a secondary aggregator; treat its numbers with caution.
- **Phoronix (2025, pre-ROCm 7.0).** RX 9070 XT, Mesa 25.3-dev RADV vs ROCm 6.4.3: Vulkan won all tests (tg128 and pp512 on 8B Q8_0 models) — [Phoronix](https://www.phoronix.com/review/llama-cpp-windows-linux/5) (search summary only; the article itself returned 403).
- **Strix Halo (Radeon 8060S)**, soothill.io, 2026-08-03. Qwen3-Coder-30B-A3B Q4_K_S, FA on, f16 KV, ctx 32k:

| Backend | Build | pp512 | tg128 |
|---|---|---|---|
| Vulkan | b10216 | 1115.30 | 97.73 |
| ROCm | b10085 | 1344.65 ± 29.79 | 73.65 ± 0.50 |

  - The author concludes "ROCm is 20.56% faster at prompt processing" and "24.64% slower at generation".
  - Qwen3.5-122B-A10B Q4_K_XL: ROCm pp512 339.9 / pp4096 523.0 / tg128 21.3; Vulkan 285.0 / 374.3 / 22.9.
  - Source: [soothill.io](https://www.soothill.io/blog/2026/08/03/llamacpp-vulkan-vs-rocm-strix-halo/).
- **Strix Halo, strixhalo.wiki** (Qwen3-30B-A3B UD-Q4_K_XL):
  - Short context: RADV 755/85.1, AMDVLK 742/81.8, ROCm 651/64.2, ROCm+hipBLASLt 652/64.0.
  - At depth 130,560: ROCm pp512 40.58 vs RADV 17.24. tg: RADV 12.54 vs ROCm 4.98. A tuned rocWMMA ROCm reached pp512 51.12 / tg128 13.32.
  - Flags used: `-fa 1`, `--mmap 0`, `-ngl 999`.
  - Source: [strixhalo.wiki](https://strixhalo.wiki/AI/llamacpp-performance/).
- **kyuz0 amd-strix-halo-toolboxes** (2026 state):
  - Variants: `vulkan-radv` ("Most stable and compatible. Recommended for most users and all models"), `vulkan-radv-performance` ("Strix Halo-focused flash attention"), and several `rocm-10.0*` variants plus `therock-nightly`.
  - The README says ROCm 10.0 "delivers superior performance" and advises "Always use flash attention (`-fa 1`) and no-mmap (`--no-mmap`) on Strix Halo."
  - Older benchmarks moved to `local-llm-benchmarks.dev`.
  - Source: [kyuz0/amd-strix-halo-toolboxes](https://github.com/kyuz0/amd-strix-halo-toolboxes).
- **Phoronix on Strix Halo + ROCm 7.0** — [Phoronix](https://www.phoronix.com/review/amd-rocm-7-strix-halo/3). Page not fetched; a search snippet says Vulkan pp512 gains were large there. The snippet is ambiguous, so I'm not quoting it.
- A contrarian piece argues "Vulkan beats ROCm is a myth" on tuned Strix Halo — [msbs.com](https://msbs.com/writing/tuning-llama-cpp-strix-halo/) (not fetched).
- More trackers: [llm-tracker.info Strix Halo](https://llm-tracker.info/AMD-Strix-Halo-(Ryzen-AI-Max+-395)-GPU-Performance) (lhl) and [slb350 strix-benchmarks](https://slb350.github.io/strix-benchmarks/) (not fetched).

### Inferences
- Decode is memory-bandwidth-bound. Vulkan's tg lead comes from lean GEMV kernels (`mul_mat_vec`/MMVQ with subgroup reductions, fused ops, low dispatch overhead) rather than from raw compute.
- pp is compute-bound. ROCm wins with rocBLAS/hipBLASLt and rocWMMA FA. Vulkan's int8 WMMA MMQ (#27952, Sept 2026) is aimed at this gap, so benchmarks taken before late September 2026 probably understate Vulkan pp on RDNA3/4. This is unverified because no post-#27952 benchmark was found.
- At long context ROCm FA is much stronger. The new Vulkan sparse/decode-split FA (Sept–Oct 2026) may change that, but I found no data.

### Gaps
- No verified 2026 head-to-head for the **RX 7900 XTX** with Vulkan and ROCm at the same build.
- No benchmarks after #27952 (int8 coopmat MMQ) or after the sparse-FA PRs.
- Exact dates of scoreboard rows are unknown.

---

## 5. Other Vulkan-based inference stacks

### Takeaway
On consumer AMD, llama.cpp/ggml is the main Vulkan LLM engine. LM Studio ships it as a selectable runtime, and Ollama added an experimental Vulkan backend in late 2025. MLC-LLM/TVM, ncnn, Kompute and wgpu/WebGPU (Burn, WebLLM) also target Vulkan but were not verified in this session.

### Cited findings
- LM Studio supports a llama.cpp Vulkan runtime on AMD under Linux and Windows. On Windows AMD, Vulkan is "the practical choice" — [glukhov.org 2026 guide](https://glukhov.org/llm-hosting/comparisons/amd-rocm-vs-vulkan-llm-hosting/) (secondary).
- Ollama has a Vulkan-powered backend for broader AMD coverage, including on Windows — [glukhov.org](https://glukhov.org/llm-hosting/comparisons/amd-rocm-vs-vulkan-llm-hosting/). An aggregator says `OLLAMA_VULKAN=1` enables the experimental Vulkan backend from v0.12.11 onward — [runaihome.com](https://runaihome.com/blog/rdna4-vulkan-vs-rocm-local-llm-benchmark-2026/) (secondary; not verified against Ollama release notes).
- Build flag: `-DGGML_VULKAN=ON` (vs `-DGGML_HIP=ON -DGPU_TARGETS=gfx1201` / `-DGGML_HIP_ROCWMMA_FATTN=ON` for ROCm) — [runaihome.com](https://runaihome.com/blog/rdna4-vulkan-vs-rocm-local-llm-benchmark-2026/).

### Inferences
- These are well known but were not checked this session:
  - MLC-LLM compiles TVM kernels to Vulkan SPIR-V.
  - ncnn is Tencent's Vulkan inference engine, mostly used for CNNs and mobile.
  - Kompute is a Vulkan compute framework that earlier powered GPT4All's Vulkan backend.
  - Burn and WebLLM reach AMD through wgpu/WebGPU, which maps to Vulkan on Linux.

### Gaps
- No primary sources fetched for MLC-LLM, Kompute, ncnn, Burn/wgpu or WebGPU performance on AMD in 2026. Current maintenance status is unknown.
- Ollama's Vulkan GA status as of October 2026 is unverified.

---

## 6. Writing and optimizing a Vulkan compute shader for LLM ops on AMD

### Takeaway
llama.cpp's shaders show the practical recipe:
- GLSL compiled with glslc.
- Workgroup size and tile sizes as **specialization constants** (`local_size_x_id = 0`, `constant_id` for BM/BN/BK/WM/WN/TM/TN), so one source yields many variants.
- Per-dispatch parameters in **push constants**.
- Shared memory (LDS) tiles with padding.
- Subgroup arithmetic for reductions.
- Explicit wave32/wave64 via subgroup size control.
- 128-bit vectorized loads and aligned variants.
- `GL_KHR_cooperative_matrix` for WMMA.
- `GL_EXT_integer_dot_product` for int8.

For checking registers and ISA: `VK_KHR_pipeline_executable_properties` (`GGML_VK_PIPELINE_STATS`), timestamp-query perf logging (`GGML_VK_PERF_LOGGER`) and AMD RGP.

### Cited findings (techniques visible in llama.cpp source and PRs)
- **Specialization constants for tiling.** `mul_mm.comp` declares `layout(local_size_x_id = 0)` and constants `BLOCK_SIZE`(0), `BM`(1), `BN`(2), `WM`(4), `WN`(5), `WMITER`(6), `TM`(7), `TN`(8), `ALIGNED`(11), `MmTypeA`(12). The host passes per-arch "warptile" tuples, e.g. AMD coopmat large = `{256,128,128,16,…}`. The matvec base uses `BLOCK_SIZE`, `NUM_ROWS` and `NUM_COLS` constants — [mul_mm.comp](https://github.com/ggml-org/llama.cpp/blob/master/ggml/src/ggml-vulkan/vulkan-shaders/mul_mm.comp); [mul_mat_vec_base.glsl](https://github.com/ggml-org/llama.cpp/blob/master/ggml/src/ggml-vulkan/vulkan-shaders/mul_mat_vec_base.glsl).
- **Forcing wave size.** The host attaches `VkPipelineShaderStageRequiredSubgroupSizeCreateInfoEXT` (and optionally "require full subgroups") per pipeline. RDNA int8-WMMA uses wave32. Some RDNA1/2 pipelines use wave64 — [ggml-vulkan.cpp](https://github.com/ggml-org/llama.cpp/blob/master/ggml/src/ggml-vulkan/ggml-vulkan.cpp); [PR #12087](https://github.com/ggml-org/llama.cpp/pull/12087).
- **Data layout for int8 paths.** The activation quantization `quantize_q8_1` uses subgroup ops. The `block_q8_1_x4` type with 128-bit alignment allows wide loads in MMVQ/MMQ. MMVQ processes 8 values per invocation, "similar to mul_mat_vec" (PR #14903) — [PR #14903](https://github.com/ggml-org/llama.cpp/pull/14903).
- **MMQ register and shmem engineering** (PR #16536): "Reduce mmq register use", "Load 4 quant blocks into shared memory in one step", "Pack q2_k blocks into caches of 32", "Use 32-bit accumulators" — [PR #16536](https://github.com/ggml-org/llama.cpp/pull/16536).
- **WMMA kernel engineering on RDNA** (PR #27952): read coopmat results directly instead of round-tripping through shmem, double buffering, a K-loop step of `BK_STEP=4`, scale preloading, issuing coopmat loads before the wmma, a fast int→float conversion, workgroup scheduling (swizzle) "for cache proximity", restructuring "for vgpr use", skipping inactive tiles, and wave32 — [PR #27952](https://github.com/ggml-org/llama.cpp/pull/27952).
- **Occupancy control on RDNA.** Over-subscription thrashes cache, so the scalar FA shader deliberately allocates unused shared memory to cap occupancy at about 4 waves/SIMD on RDNA and 2 on GCN — [ggml-vulkan.cpp](https://github.com/ggml-org/llama.cpp/blob/master/ggml/src/ggml-vulkan/ggml-vulkan.cpp).
- **Barrier avoidance.** FA "row_split" keeps synchronization within subgroups. The coopmat1 FA refactor moved to subgroup reductions and fewer barriers — [PR #19625](https://github.com/ggml-org/llama.cpp/pull/19625); [PR #19075](https://github.com/ggml-org/llama.cpp/pull/19075).
- **Spec constants for feature toggles** cut branches inside hot loops (FA mask/softcap as spec constants, #19309). The mask is preprocessed to skip all -inf or all-zero blocks (#19281, #17186) — [PR #19309](https://github.com/ggml-org/llama.cpp/pull/19309); [PR #19281](https://github.com/ggml-org/llama.cpp/pull/19281).
- **Wide loads.** "Use larger loads in scalar/coopmat1 matmul" (#15729); aligned and unaligned variants (`ALIGNED` constant, `l_align=128`, `m_align=64`, `s_align=32`) — [PR #15729](https://github.com/ggml-org/llama.cpp/pull/15729).
- **ISA and register statistics.** llama.cpp sets `eCaptureStatisticsKHR` and calls `getPipelineExecutableStatisticsKHR`. Set `GGML_VK_PIPELINE_STATS=mul_mmq` (for example) to print the driver-reported stats. On RADV these include VGPR/SGPR, spills, LDS and code size — [ggml-vulkan.cpp](https://github.com/ggml-org/llama.cpp/blob/master/ggml/src/ggml-vulkan/ggml-vulkan.cpp).
- **Per-op timing.** `GGML_VK_PERF_LOGGER` uses timestamp queries, with a concurrency mode in #17944 and FA details in #17443. `GGML_VK_DEBUG_MARKERS` names pipelines through `VK_EXT_debug_utils` so captures are readable — [PR #17944](https://github.com/ggml-org/llama.cpp/pull/17944).
- **Build-time robustness.** Shader compile failures now fail the build (PR #24450, by liminfei-amd, 2026-06-24, apparently an AMD engineer) — [PR #24450](https://github.com/ggml-org/llama.cpp/pull/24450).

### Inferences
- Recommended loop on AMD/RADV: write GLSL → expose tiles as spec constants → sweep tuples per arch → read `GGML_VK_PIPELINE_STATS` to keep VGPRs low enough for the target occupancy → profile with `GGML_VK_PERF_LOGGER`.
- Background knowledge, not verified this session:
  - RGP supports Vulkan captures on RADV via `MESA_VK_TRACE=rgp` and on the AMD driver natively.
  - RGA can compile Vulkan GLSL/SPIR-V offline to RDNA ISA (AMDVLK/PAL-based, so ISA may differ from ACO).
  - `RADV_DEBUG=shaders` / `ACO_DEBUG` dump ACO ISA.

### Gaps
- No GPUOpen/RGP/RGA documentation was fetched. The exact env vars for RGP capture on RADV (`MESA_VK_TRACE=rgp`, `RADV_THREAD_TRACE*`) and current RGA Vulkan support are unverified.
- The ACO vs LLVM ISA-quality comparison for llama.cpp shaders is not sourced.
