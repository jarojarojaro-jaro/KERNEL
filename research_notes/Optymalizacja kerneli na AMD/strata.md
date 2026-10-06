# "Strata" on GitHub: identification and deep dive (AMD / ROCm / local LLM kernels), as of 2026-10-06

Method note: `gh search` / the GitHub REST search API is blocked in this session (403, "sessions are bound to their configured repositories"), so repo discovery used the GitHub MCP `search_repositories` tool (query `strata in:name`, sorted by stars) plus web search. The top candidate was shallow-cloned (`git clone --depth 1`, HEAD `82f46a8`, committed 2026-10-06T11:25:45+02:00) and its docs and source tree were read but not executed. Repo-scoped GitHub API calls (stars, releases, contributors) were also refused for this repo. Star and fork counts therefore come from the MCP search result, taken on 2026-10-06.

## Which GitHub "Strata" does the user most likely mean? (candidates, ranked)

### Takeaway
The user almost certainly means **Niko1221/Strata**. It is a 12-day-old, MIT-licensed C++/CUDA/HIP inference engine with about 15.6k stars that runs the 125B-parameter MoE model Qwen3.8-Flash-Next on consumer GPUs. It has a large, actively developed AMD HIP/ROCm backend (RDNA2/3/3.5/4, Strix Halo, MI50) with hand-tuned kernels. No other "Strata" repo on GitHub is related to GPU kernels, AMD or LLM inference. The only close ones are AMD-specific forks of this same project.

### Cited Findings
- **#1 (very likely): Niko1221/Strata.** Description: "Qwen3.8-Flash-Next on any consumer hardware: one-click install for Windows / Linux. Strata inference engine, OpenAI/Anthropic API on localhost, optional image input." Language C++. **15,624 stars, 1,331 forks, 327 open issues.** Created 2026-09-24, updated 2026-10-06. It is by far the most-starred repo named "Strata" on GitHub — GitHub MCP search (`strata in:name`, sort=stars), observed 2026-10-06; [repo](https://github.com/Niko1221/Strata)
- A web search for "strata github GPU kernel AMD ROCm" returns almost only this project and its AMD forks and issues: an RDNA4 R9700 benchmark issue (#178), a gfx1150 Strix Point report (#1217), docs/INSTALL.md and docs/OLDER_GPUS.md — [Issue #178](https://github.com/Niko1221/Strata/issues/178), [Issue #1217](https://github.com/Niko1221/Strata/issues/1217)
- **#2 (AMD forks of #1, plausible if the user saw a fork link):**
  - **xyzzing/Strata.** "Strata HIP for AMD gfx1100". Release v0.1.20-rocm.4 (Sept 29) is a HIP porting layer of upstream 0.1.20 for the RX 7900 XTX. It includes an "fma campaign" (explicit `__fmaf_rn`, "not a measurable decode lever") and "spec-split" (+5.7% decode, +28.2% prompt). Its IQ3_S decode was 36.7–38.1 tok/s, about 70–75% of upstream CUDA — [release](https://github.com/xyzzing/Strata/releases/tag/v0.1.20-rocm.4)
  - **jagsan-cyber/Strata.** "Radeon HIP fork of Strata: RX 9070 (gfx1201) on Windows with ROCm 10, plus RX 9060 and RX 7900. Upstream NVIDIA installer: Niko1221/Strata." — [repo](https://github.com/jagsan-cyber/Strata)
  - **Maxritz/Strata-rocm.** Its name suggests ROCm, but its description still reads "on a 8GB+ NVIDIA GPU". Its purpose is unclear (possibly a renamed or rebranded fork) — [repo](https://github.com/Maxritz/Strata-rocm)
  - Upstream credits **eddoursul/Strata**, the fork whose Unsloth UD-Q4_K_XL support upstream followed. It is a model-format fork, not AMD-specific — [HOW_IT_WORKS.md](https://github.com/Niko1221/Strata/blob/main/docs/HOW_IT_WORKS.md)
- **Unrelated "Strata" repos (ruled out):**
  - **strata-org/Strata** (Lean, 264 stars): "a unified platform for formalizing language syntax and semantics, and implementing automated reasoning applications". Formal verification and SMT, apparently Amazon-associated, with no GPU or ML relevance — [repo](https://github.com/strata-org/Strata)
  - **StanfordPL/strata** (72 stars): "Automatic inference of a formal specification of the x86_64 instruction set". This is ISA semantics for compilers and superoptimization (Stanford PL). It is compiler-adjacent but CPU-only, old and not AMD-GPU-related — GitHub MCP search
  - **ut-osa/strata** ("A Cross Media File System"), **OpenGamma/Strata** (finance analytics, 971 stars), **lgse/strata** (Rust file manager), **StrataWM/strata** (Wayland compositor), **facebookarchive/rocks-strata** (archived, Go) and several HTML5UP "Strata" themes — GitHub MCP search

### Inferences
- The project appeared 2026-09-24 and drew about 15.6k stars in under two weeks. It has an AMD HIP backend, a Strix Halo page, RDNA4 WMMA kernels and per-architecture hipBLASLt tuning tables. That matches someone asking about "AMD kernel optimization" in Oct 2026 and being told to "look at Strata on GitHub".
- If the user meant a specific AMD port, the upstream repo has since absorbed the HIP backend (docs/AMD_HIP.md), so upstream is now the canonical AMD source. The forks mostly predate that merge or target Windows.

### Gaps
- Global code search could not be run (the search API is blocked), so a tiny or private repo named "strata" in an AMD/ROCm org can't be fully excluded. The MCP repo search (6,320 hits for `strata in:name`) showed nothing in ROCm/AMD/AMD-AGI/ggml-org/gpu-mode/HazyResearch/tile-ai orgs among the top results. Org-specific queries were not run individually.
- Exact contributor count and total commit count could not be checked through the API. The README fetch reported "1,159 commits" — [repo page](https://github.com/Niko1221/Strata).

## What Niko1221/Strata is and how it works (architecture)

### Takeaway
Strata is a single-model inference engine specialised for Qwen3.8-Flash-Next (125B total parameters, a MoE with 24,576 experts and 10 active per token). It splits the work across a memory hierarchy: hot experts and dense layers on the GPU, all experts in pinned RAM computed in place by the CPU, and an n-gram (PLE) table on the SSD. It adds MTP speculative decoding and chunked prefill that streams experts over PCIe. It reuses llama.cpp/ggml quant formats and kernels but is a separate engine of about 200k lines.

### Cited Findings
- Its goal is to "run a 125-billion-parameter AI model on your own gaming PC". The model has "24,576 small specialists ('experts'). Each word needs only 10 of them." The API is OpenAI- and Anthropic-compatible at `http://127.0.0.1:8080/v1` and `/v1/messages`, with a browser UI at :8080 — [README](https://github.com/Niko1221/Strata)
- Memory tiers (technical description):
  - **GPU/VRAM** holds attention and DeltaNet mixers, gated-residual weights, routers, shared experts, the output head, the MTP draft layer and the KV cache. From 64K context only the hottest part of the KV cache stays on the GPU; the rest streams from RAM. An adaptive **expert cache** fills the remaining VRAM with the most-used experts.
  - **RAM** holds all 24,576 experts, pinned. The CPU computes non-cached experts "in place, at the same time as the GPU" using AVX-512/AVX2 kernels, plus ggml's kernels for i-quants.
  - **SSD** holds a 28.8 GB n-gram (PLE) table, read a few rows per token.
  - "Every extra GB holds ~700 more experts."

  — [docs/HOW_IT_WORKS.md](https://github.com/Niko1221/Strata/blob/main/docs/HOW_IT_WORKS.md)
- Speculation: "the model's own MTP layer drafts up to 3 tokens; one pass over all 48 layers checks them, 2.4-3.2 tokens per pass on average", giving 1.6–1.8x faster output. Prompt-lookup drafting adds up to 5 tokens on code edits, making them 6–11% faster — [HOW_IT_WORKS.md](https://github.com/Niko1221/Strata/blob/main/docs/HOW_IT_WORKS.md)
- Prefill runs in chunks of up to 8,192 tokens (32,768 opt-in), with experts streamed to the GPU over PCIe while the current layer's attention runs. Since 0.1.39b the streamed ring buffer is sized in bytes — [docs/DETAILS.md#how-it-works](https://github.com/Niko1221/Strata/blob/main/docs/DETAILS.md)
- The PLE table can be stored in IQ4_NL (default, 28.8 GB), Q4_0, Q5_x, Q8_0 (54 GB), FP8 or BF16. Measured mean per-row error is 0.53% for Q8_0 and 7.60% for IQ4_NL. On the Q2_0 model the mean KL vs BF16 is about 0.012–0.015 — [DETAILS.md](https://github.com/Niko1221/Strata/blob/main/docs/DETAILS.md)
- Source layout seen in the clone (HEAD 2026-10-06):
  - `src/kernels/cuda/` has 45 kernel files, including `native_moe.cu`, `native_mmvq.cu`, `iq_kernels.cu`, `qsa_prompt_attn.cu`, `qsa_decode_attn.cu`, `router_top10.cu`, `fused_gdn.cu` (gated DeltaNet), `kv_q4.cu` / `kv_q8.cu` / `kv_stream.cu`, `s2_gemv*.cu`, `verify_kernels.cu` and `sampler.cu`.
  - `src/kernels/cpu/` holds the CPU kernels.
  - `include/strata/platform/hip_compat/` is a CUDA→HIP compatibility layer.
  - `sycl/` is a separate Intel SYCL tree.
  - `tools/hip/` holds hipBLASLt tuning tables, `tune_hipblaslt.cpp` and `build_windows.bat`.
  - `serve/` is a Python server and web UI.
  - `third_party/ggml` is llama.cpp/ggml, MIT, pinned revision.
  - CMake project version is 0.1.40. `src/` and `sycl/` contain about 199.8k lines of .cu/.cpp/.hpp.

  — local clone of [Niko1221/Strata](https://github.com/Niko1221/Strata)
- Credits: model by Qwen; GSQ-RCO quantizations by ISTA-DASLab; Swift 1.5 by UkisAI; UD-Q4_K_XL by Unsloth. "Built with parts of llama.cpp / ggml (MIT). Ideas from Splash, ninfer and HyperQwen." The i-quant GPU dot products and dequantizers are "transcribed in `src/kernels/cuda/iq_kernels.cu`" from ggml. A paper is included at `docs/paper/Strata-Paper.pdf` — [HOW_IT_WORKS.md](https://github.com/Niko1221/Strata/blob/main/docs/HOW_IT_WORKS.md), [DETAILS.md](https://github.com/Niko1221/Strata/blob/main/docs/DETAILS.md)
- Supported models: Qwen3.8-Flash-Next in Q2_0, IQ2_XS, IQ3_XXS and IQ3_S; the "Coder" variant (half the experts removed, about 32 GB); Swift 1.5; Unsloth UD-IQ4_XS and UD-Q4_K_XL; and the OrcaRouter IQ3_XXS (manual setup) — [README](https://github.com/Niko1221/Strata)
- Secondary press: PC Watch (2026-10-02) reported 60–95 tok/s on one card, 93 tok/s on an RTX 5070 12 GB for short chats and 74 tok/s at 128K context. It described AMD RX 7900/9070 support on Linux as experimental — [PC Watch](https://pc.watch.impress.co.jp/docs/news/2145142.html)

### Inferences
- Strata is not a general kernel-generation framework or compiler. It is a hand-optimised, model-specific engine, closer to "llama.cpp specialised for one MoE" with aggressive heterogeneous CPU/GPU/SSD scheduling.
- Its relevance to AMD kernel optimization is the HIP backend's catalogue of concrete, measured kernel-level changes, summarised below. That makes it a good real-world reference for RDNA tuning.

### Gaps
- The PDF paper (`docs/paper/Strata-Paper.pdf`) was not read in detail.
- Model and quantization claims (Qwen3.8-Flash-Next, GSQ-RCO) were taken from the repo and press and not checked further.

## AMD / ROCm / Vulkan support and the HIP kernel optimizations

### Takeaway
AMD support comes through a **HIP backend** ("the same engine as on NVIDIA compiled for AMD"). It is validated on RDNA3 gfx1100/1101 and RDNA4 gfx1200/1201. RDNA2 gfx1030/1031 has community runs, Strix Halo gfx1151 is experimental, and gfx906 MI50/MI60 needs a separate wave64 build. **There is no Vulkan backend**: no Vulkan mentions in any doc. Intel is served by SYCL, not Vulkan. The AMD work is a dense source of RDNA-specific kernel tricks: dot4 intrinsics, `v_perm_b32`, WMMA on gfx11/gfx12, per-architecture and per-version hipBLASLt solution tables, a router kernel rewrite, and wave64 layouts for gfx906.

### Cited Findings
- **Backend design.** The backend "maps the CUDA-shaped runtime and BLAS calls to HIP/hipBLAS, uses RDNA2/RDNA3/RDNA4's signed integer dot instruction for quantized kernels, and supplies wave32 shuffle/packed-byte operations. CUDA-only QSA matrix instructions have an ordered FP32 fallback. Prefill supports both dequantization plus hipBLAS GEMM and opt-in HIP ggml MMQ. An optional, calibrated hipBLASLt path accelerates dense projections." It "does not claim bit-identical model answers across backends." — [docs/AMD_HIP.md](https://github.com/Niko1221/Strata/blob/main/docs/AMD_HIP.md)
- **Validated GPUs.**
  - RX 7900 XT/XTX (gfx1100) and RX 9070/9070 XT/AI PRO R9700 (gfx1201) are maintainer- or partner-validated.
  - RX 7800/7700 XT (gfx1101) and RX 9060 XT (gfx1200) are community-validated.
  - RX 6800/6900 (gfx1030) has a community run but is "not yet validated by maintainers".
  - gfx1102 builds and passes ctest, with no model run reported.
  - "Other AMD architectures and mixed AMD/NVIDIA execution in one run are not supported."

  — [AMD_HIP.md](https://github.com/Niko1221/Strata/blob/main/docs/AMD_HIP.md)
- **Install (Linux).** Run `./setup.sh --backend hip`. Setup detects the card through KFD topology and uses system ROCm 7 from `/opt/rocm` if present. Otherwise it installs ROCm into `.venv` from AMD's **TheRock** wheels (about 10 GB, no sudo), from the `gfx110X-dgpu`, `gfx120X-all` or `gfx103X-all` indexes. It then compiles the engine for the card, which takes 10–20 minutes once. Manual build: `cmake -S . -B build-hip -DSTRATA_ENABLE_HIP=ON -DSTRATA_ENABLE_CUDA=OFF -DCMAKE_HIP_ARCHITECTURES=gfx1100` — [AMD_HIP.md](https://github.com/Niko1221/Strata/blob/main/docs/AMD_HIP.md)
- **Install (Windows, since 0.1.34).** Run `START-HERE.bat`. It uses a prebuilt `strata-windows-x64-hip.zip` that bundles ROCm 10.2.0a20260930 TheRock libraries, so it needs only the Adrenalin driver and no ROCm/HIP SDK. The zip covers gfx1100, gfx1101, gfx1102, gfx1200, gfx1201, gfx1030, and gfx1151 from 0.1.40. Windows-specific workarounds:
  - The bundled `amdhip64_7.dll` is copied next to the exe, because the driver's own copy crashed on first prompt.
  - `hipMemGetInfo` ignores the WDDM budget, so the engine subtracts it. On an RX 6800 this restored decode from 30 to 41 tok/s.
  - A stale `hipErrorInvalidValue` after BF16/FP16 GEMMs on gfx1201 is cleared.

  — [AMD_HIP.md](https://github.com/Niko1221/Strata/blob/main/docs/AMD_HIP.md)
- **RDNA4 kernel facts.**
  - gfx1201 runs the same kernels as gfx1100: wave32, 64 KiB LDS per workgroup, signed dot4 `v_dot4_i32_iu8` through `__builtin_amdgcn_sudot4`.
  - On gfx1201 "a plain store to mapped pinned memory stays in the GPU's L2 until the stream is synchronized", so the CPU↔GPU handoff ring needed a volatile store.
  - Since 0.1.31 `__byte_perm` compiles to a single `v_perm_b32`, and packed-byte subtract/compare runs on four lanes at once. That gave decode +15% on the R9700 (46.0→53.0 tok/s) and +5–7% on the 9070 XT, with identical tokens.

  — [AMD_HIP.md](https://github.com/Niko1221/Strata/blob/main/docs/AMD_HIP.md)
- **Router kernel.** The MoE router (`router_top10`) on HIP drops a serial FP64 sum and block barriers, going from 39 µs to 9–12 µs per call with bit-identical ids and weights (checked on 65,536 rows). Decode went from 62.4 to 70.0 tok/s on the R9700 in one A/B. A user's repeated A/B measured +1–4% inside a 12–20% run-to-run spread (#432) — [AMD_HIP.md](https://github.com/Niko1221/Strata/blob/main/docs/AMD_HIP.md)
- **WMMA attention (RDNA4).** `STRATA_HIP_WMMA=1` (opt-in, gfx12 only, int8 KV) runs prompt QSA attention on `v_wmma_f32_16x16x16_f16`, using FP16 hi+lo halves like the CUDA tensor-core kernel. It is 7.2–7.5x faster than the portable kernel. R9700 prompts went from 1,784 to 2,427 tok/s at 4K and from 1,797 to 2,700 at 16K. It is not bitwise identical: greedy text diverges from token ~50. It needs the expert ring reduced to 96 slots, otherwise the 9070 XT regresses — [AMD_HIP.md](https://github.com/Niko1221/Strata/blob/main/docs/AMD_HIP.md)
- **hipBLASLt tuning tables.** Solution ids are valid only for one (architecture, hipBLASLt version) pair, so the engine refuses any mismatched table. Shipped tables: gfx1100 (100100/100200/100202/100401/100500), gfx1151 (100401), gfx1200 (100202) and gfx1201 (100202/100500). You can calibrate your own with the `tune_hipblaslt` target. Measured gains:
  - RX 9060 XT: prompt 1.50x at 2.4K tokens and 1.99x at 65K tokens over plain hipBLAS.
  - R9700 with hipBLASLt 1.2.2: a 32K prompt went from 638 to 1,177 tok/s.
  - R9700 with hipBLASLt 1.4.1: only 0–3%, so no table was shipped for it.
  - RX 7900 XTX with hipBLASLt 1.5.0: a 131K prompt went from 926 to 1,687 tok/s.

  — [AMD_HIP.md](https://github.com/Niko1221/Strata/blob/main/docs/AMD_HIP.md)
- **RDNA2 (gfx1030).**
  - There is no `v_dot4_i32_iu8`, so dp4a uses `__builtin_amdgcn_sdot4`, which compiles to `v_dot4c_i32_i8`. There is no WMMA.
  - rocBLAS on gfx1030 has tuned kernels only for FP16-in/FP16-out. FP16→FP32 and BF16 GEMMs ran about 6.6x slower (5.6 vs 37.7 TFLOPS). `STRATA_HIP_PROMPT_F16=1` raised prompts from 439/466/461 to 744/915/926 tok/s.
  - `STRATA_DENSE_MMQ=1` (int8 MMQ for dense projections) took an RX 6900 XT 4K prompt from 436 to 757 tok/s.
  - hipBLASLt ships no gfx1030 kernels.

  — [AMD_HIP.md](https://github.com/Niko1221/Strata/blob/main/docs/AMD_HIP.md)
- **gfx906 (MI50/MI60, Radeon VII, wave64).**
  - This is a separate opt-in build (`STRATA_HIP_GFX906=ON`). It compiles the CUDA sources as HIP via `hip_compat`, mapping a CUDA warp to half of a 64-lane wavefront.
  - Custom wave64 layouts: grouped native experts with sign handling as `dp4a(g^m,u) - dp4a(m,u)` (no byte SIMD), MMVQ with one wavefront per row and a 64-lane butterfly, and a single-wavefront router top-10. The IQ4 lookup uses llama.cpp's `v_perm_b32` sequence because HIP's `__byte_perm` became a scratch array there.
  - Each change was "checked bitwise against the layout it replaces".
  - On 2x MI50 it measured 57.7–59.3 tok/s decode, vs 26.9 tok/s tg128 for llama.cpp ROCm on the same model.
  - It needs a community ROCm image, because current ROCm dropped gfx906 libraries.

  — [AMD_HIP.md](https://github.com/Niko1221/Strata/blob/main/docs/AMD_HIP.md)
- **RDNA4 measured end-to-end** (Coder IQ1_M, 32K max context, MTP, int8 KV, ROCm 7.14):
  - R9700 32 GB: 4K prompt 982 tok/s, decode 45.5. 16K prompt 1,402 tok/s, decode 48.3.
  - RX 9070 XT 16 GB: 4K prompt 782 tok/s, decode 30.8. 16K prompt 1,235 tok/s, decode 35.4.
  - A two-card layer split did not help when one card already holds all experts.

  The README also lists RX 9070 XT Q2_0 at 60 tok/s decode and 1,160 tok/s prompt. — [AMD_HIP.md](https://github.com/Niko1221/Strata/blob/main/docs/AMD_HIP.md), [README](https://github.com/Niko1221/Strata)
- **Comparison with llama.cpp.** On an RX 9060 XT Strata measured 27.1 tok/s decode and 540 tok/s prompt (2.4K tokens). "For comparison, llama.cpp's HIP build measured 20 tok/s decode and 450 tok/s prompt on that card." — [AMD_HIP.md](https://github.com/Niko1221/Strata/blob/main/docs/AMD_HIP.md)
- **RX 7900 XTX (gfx1100) evidence.** This used opt-in HIP MMQ prefill, a calibrated hipBLASLt table (`STRATA_PREFILL_MMQ=1`, `STRATA_PREFILL_RING=96`, `STRATA_IO_THREADS=32`) and a reusable pinned staging buffer for expert uploads. Fresh-prompt prefill was 1.80–2.02x the previous HIP runtime: 4,210 tokens at 447.5 tok/s cold and 901.1 warm, decode about 55–59 tok/s. It ran on a Ryzen 9 7950X3D with 64 GB RAM and ROCm 7.1. Real quantized MMQ relative L2 error was about 0.0026 vs the FP32 reference — [docs/AMD_HIP_PERFORMANCE.md](https://github.com/Niko1221/Strata/blob/main/docs/AMD_HIP_PERFORMANCE.md)
- **Strix Halo (Ryzen AI Max, gfx1151, RDNA3.5).**
  - Status is experimental, built and measured on one maintainer box: Ryzen AI Max+ 395, 128 GB, ROCm 7.14.1 TheRock tarball for gfx1151.
  - The unified-memory free figure uses `MemAvailable` minus 6 GiB.
  - WMMA kernels exist for gfx1100/1101/1102/1150/1151. gfx1103 and gfx1152 take the portable path.
  - The box boots with `ttm.pages_limit=29360128` (112 GiB GTT) and `amd_iommu=off`.
  - Fast-config env flags: `STRATA_PF_FUSED`, `STRATA_PF_GEMM` (128x256 WMMA GEMM), `STRATA_PA_FAST`, `STRATA_HIP_WMMA`, `STRATA_SH_STREAM=1`.
  - Measured: UD-IQ4_XS at 8K about 1,293 tok/s prompt and 53.8 tok/s output. IQ3_S at 8K 1,242 prompt and 59.7 output. At 128K, 40–51 tok/s output.
  - Setup recognises Strix Halo by PCI id `1002:1586` and rejects Strix Point gfx1150, Krackan gfx1152 and Phoenix gfx1103 iGPUs.

  — [docs/STRIX_HALO.md](https://github.com/Niko1221/Strata/blob/main/docs/STRIX_HALO.md)
- **Vulkan.** A grep of every `.md` doc in the repo for "vulkan" returned no matches, and the backends are CUDA, HIP and SYCL (`sycl/` tree, docs/INTEL*.md) — local clone of [Niko1221/Strata](https://github.com/Niko1221/Strata)
- **Known AMD limits.** Images only work through the CPU encoder. About 1 in 10 HIP starts gives a greedy output that differs at some token, not yet explained. Long contexts beyond 16K and answer quality are not validated on RDNA4. Calibration is not offered by setup on AMD — [AMD_HIP.md](https://github.com/Niko1221/Strata/blob/main/docs/AMD_HIP.md)

### Inferences
- For someone optimising kernels on AMD, Strata's docs are a practical playbook:
  - Use the right dot4 intrinsic per generation (`sudot4` on gfx11+, `sdot4` on gfx103x).
  - Make sure byte-permute lowers to `v_perm_b32`.
  - Use WMMA on gfx11/gfx12 for prefill attention and GEMM.
  - Calibrate hipBLASLt per (arch, library version), since gains range from 0% to about 2x.
  - Watch library gaps such as gfx1030 rocBLAS FP16→FP32 and the absence of hipBLASLt for RDNA2.
  - Keep the large wins (expert caching and CPU overlap) at the system level.
- The AMD numbers (about 30–60 tok/s decode for a 125B MoE on 16–32 GB Radeons) show the project's main lever is memory placement and CPU/GPU overlap rather than raw kernel FLOPs. Kernel tuning gave +5–15% (decode) and up to 2x (prefill, via tables and WMMA).

### Gaps
- No independent third-party benchmark of Strata on AMD outside the repo's own issues and docs was found.
- Windows AMD: the maintainers say they have no Windows AMD card, and the ready-made zip "has not run a model on a discrete card yet" according to the docs. Status may have changed in the newest releases.

## Maturity and activity

### Takeaway
The project is very young (created 2026-09-24) and extremely active, with releases almost daily. It is MIT-licensed, popular (about 15.6k stars) and still at version 0.1.x. Expect fast churn and experimental AMD paths.

### Cited Findings
- 15,624 stars, 1,331 forks and 327 open issues as of 2026-10-06. Created 2026-09-24 — GitHub MCP search; [repo](https://github.com/Niko1221/Strata)
- License: MIT. `third_party/ggml` is MIT, the font is OFL 1.1 and the speed-projection vector is under the Qwen Community License. Model weights are not included — [HOW_IT_WORKS.md](https://github.com/Niko1221/Strata/blob/main/docs/HOW_IT_WORKS.md)
- Latest commit in the clone: 2026-10-06T11:25:45+02:00 ("serve: a tool call inside a code fence ... (#1058)"). CMake version 0.1.40 — local clone
- Recent releases:
  - v0.1.40.1 (Oct 6): server hotfix.
  - v0.1.40 (Oct 6): Strix Halo/gfx1151 with RDNA3.5 matrix-core kernels, plus hipBLASLt tables and Windows HIP fixes.
  - v0.1.39 (Oct 4): manual builds for gfx906 and gfx1012.
  - v0.1.38 (Oct 3): gfx1200/1201 tables for about 1.5–2x prompt speed.
  - v0.1.37 (Oct 2): Windows VRAM-budget fix, 31→42 tok/s on an RX 6800.

  — [Releases](https://github.com/Niko1221/Strata/releases)
- The README fetch reports about 1,159 commits — [repo page](https://github.com/Niko1221/Strata)
- Hardware requirements: NVIDIA RTX 20–50 with 12 GB+ VRAM, or the AMD cards above; minimum 32 GB RAM, 64 GB recommended; about 80 GB disk, SSD preferred — [README](https://github.com/Niko1221/Strata)

### Inferences
- Treat performance numbers as snapshot-specific. The docs themselves warn against reading a table "as a benchmark of every subsequent rebase".

### Gaps
- Number of distinct contributors was not retrieved (the API was blocked). The docs name several AMD contributors, including doplxyz, bsorensen110, ttio2tech, jhohertz, Efeisot and BlueKingMuch.

## Possible misspellings or alternative meanings

### Takeaway
Given the AMD context, the most plausible alternative is **Strix Halo** (Ryzen AI Max, gfx1151). However, Strata itself has a dedicated Strix Halo page, so both readings lead to the same repo. Other look-alikes (Stratix, StanfordPL/strata, strata-org) do not fit "AMD kernel optimization for local AI".

### Cited Findings
- Strata's docs/STRIX_HALO.md covers building and tuning on gfx1151 — [STRIX_HALO.md](https://github.com/Niko1221/Strata/blob/main/docs/STRIX_HALO.md)
- StanfordPL/strata (x86-64 ISA spec inference) and strata-org/Strata (Lean formal semantics) are compiler- or verification-adjacent but have no GPU/AMD content — GitHub MCP search; [strata-org/Strata](https://github.com/strata-org/Strata)

### Inferences
- "Stratix" is an Intel (ex-Altera) FPGA family and is unlikely in an AMD GPU context. "tritonparse" and "STRATO" have no clear connection. None were investigated further.

### Gaps
- The misspelling hypotheses were not searched individually, given the strong match for Niko1221/Strata.
