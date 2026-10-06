# AMD ROCm software stack for writing and optimizing LLM-inference GPU kernels (as of Oct 2026)

Research date: 2026-10-06. I fetched or searched 16 sources. "Background knowledge" means the claim comes from the researcher's pre-June-2026 knowledge and was NOT re-verified in this session. The report writer should present those claims as likely, not confirmed.

## 1. ROCm versions, TheRock, supported consumer GPUs, Windows, HSA_OVERRIDE_GFX_VERSION

### Takeaway
The current ROCm is **10.1.0, released 2026-10-05**. AMD went straight from 7.14 to 10.0 (2026-08-26/27), so there is no ROCm 8 or 9. Releases now ship every 6 weeks. They are built by **TheRock**, AMD's open-source build and release system, which went to production in ROCm 7.14 (2026-07-15). Officially supported consumer hardware now covers all RDNA3 desktop cards (RX 7900 XTX/XT/GRE, 7800 XT, 7700 XT, 7600), all RDNA4 cards (RX 9070 XT/GRE/9070, RX 9060 XT/9060, RX 9050) and the Ryzen AI Max/Strix Halo APUs (gfx1151, plus gfx1150/1152/1153). Windows uses the same release cadence as Linux: the "HIP SDK for Windows" was retired in favor of the ROCm Core SDK.

### Cited Findings
- **Release history:** 7.0.0 (2025-09-16), 7.0.1 (2025-09-17), 7.0.2 (2025-10-10), 7.1.0 (2025-10-30), 7.1.1 (2025-11-26), 7.2.0 (2026-01-21), 7.2.1 (2026-03-25), 7.2.2 (2026-04-14), 7.2.3 (2026-05-04), 7.2.4 (2026-05-29), 7.14.0 (2026-07-15), 7.14.1 (2026-09-02), **10.0.0 (2026-08-26)**, **10.1.0 (2026-10-05)**. There was no 7.3–7.13 production release. — [ROCm release history](https://rocmdocs.amd.com/en/latest/release/versions.html)
- **Release streams:** from 7.9 onward the 7.9+ releases were "tech preview" builds, while 7.0/7.1/7.2 were the stable series. ROCm 7.14 was declared the production release. — [Phoronix: ROCm 7.14](https://www.phoronix.com/news/AMD-ROCm-7.14)
- **The jump to ROCm 10.0** (Phoronix dates it 2026-08-27) was made to clear up that confusing versioning. 10.0 is the "first release of ROCm since shifting to a six week release cycle". It introduced "ROCm.AI" (described as AI-driven development tooling), a new ROCm CLI, "Hyperloom", production containers and Python wheels for vLLM, and local LLM fine-tuning on Ryzen AI Max. AMD also **retired the HIP SDK for Windows in favor of the ROCm Core SDK**, putting Windows on the Linux cadence. — [Phoronix: ROCm 10.0](https://www.phoronix.com/news/AMD-ROCm-10.0)
- **TheRock went to production in ROCm 7.14 (2026-07-15).** AMD calls it an "automated, open-source build and release system". It introduces a ROCm Core SDK plus optional expansion SDKs (HPC, computer vision, data science, life sciences).
  - New install options: a Runfile installer (user-selectable directories, multiple versions side by side), RPM/DEB packages, and Python wheels.
  - Hardware in 7.14: Instinct MI350/MI355X/MI300X/MI300A; Radeon RX 7000/9000; Radeon PRO W7900/W7800/R9700/R9700S/R9600/V710; Ryzen AI MAX+ PRO 495/490/485; Strix Halo and Strix Point.
  - Frameworks in 7.14: PyTorch 2.12/2.10, JAX 0.10.0, vLLM, llama.cpp, Ollama, SGLang.

  — [AMD ROCm blog: ROCm 7.14](https://rocm.blogs.amd.com/ecosystems-and-partners/rocm-7.14-blog/README.html); [Phoronix 7.14](https://www.phoronix.com/news/AMD-ROCm-7.14)
- **ROCm 10.1.0 (2026-10-05), one release for Linux and Windows.** Supported GPUs and gfx targets:

  | Family | Products | gfx target |
  |---|---|---|
  | CDNA4 | MI355X/MI350X/MI350P | gfx950 |
  | CDNA3 | MI325X/MI300X/MI300A | gfx942 |
  | CDNA2 | MI250X/MI250/MI210 | gfx90a |
  | CDNA | MI100 | gfx908 |
  | RDNA4 | RX 9070 XT/GRE/9070, RX 9060 XT/9060, RX 9050 | gfx1201 / gfx1200 |
  | RDNA3 | RX 7900 XTX/XT/GRE, 7800 XT, 7700 XT, 7600; PRO W7900/W7800/W7700 | gfx1100–1102 |
  | RDNA3 | PRO V710 | gfx1101 |
  | RDNA2 | V620 | gfx1030 |
  | RDNA3.5 APUs | Ryzen AI Max/Max+ and Strix/Gorgon/Krackan Point | gfx1151/1150/1152/1153 |

  Windows 11 25H2 is supported with Adrenalin 26.10.41.05. — [ROCm 10.1.0 release notes](https://rocm.docs.amd.com/en/latest/about/release-notes.html)
  - Caveat: the page summary lists the RX 9060 XT under both gfx1201 and gfx1200. That is a summarization artifact. Navi48 (RX 9070 class) is gfx1201 and Navi44 (RX 9060 class) is gfx1200 (background knowledge).
- **Validated framework versions for 10.1:** PyTorch 2.14.0, JAX 0.11.1, vLLM 0.29.0, SGLang 0.5.18, MIGraphX 2.18. — [ROCm 10.1.0 release notes](https://rocm.docs.amd.com/en/latest/about/release-notes.html)
- **Earlier milestones:**
  - ROCm 7.2.0 (Jan 2026) added more Radeon RDNA4 models plus MI300X/MI350 optimizations. — [Phoronix ROCm 7.2](https://www.phoronix.com/news/AMD-ROCm-7.2-Released); [7.2.2 release notes](https://rocm.docs.amd.com/en/docs-7.2.2/about/release-notes.html)
  - As of ROCm 7.1, gfx1151/gfx1150 were officially supported in the PyTorch-on-ROCm Docker images. — [search summary of rocm/pytorch Docker Hub](https://hub.docker.com/r/rocm/pytorch) (aggregated snippet; medium confidence)
  - ROCm 7.9.0 supported PyTorch 2.9.0 on Windows on supported Ryzen AI APUs. — [ROCm 7.9.0 compatibility matrix](https://rocm.docs.amd.com/en/docs-7.9.0/install/compatibility-matrix.html)
- **Before official support,** community TheRock builds provided gfx1151 and gfx110x PyTorch wheels, including Windows wheels (torch 2.7.0a0, Python 3.12). — [scottt/rocm-TheRock releases](https://github.com/scottt/rocm-TheRock/releases/v6.5.0rc-pytorch)
- **HSA_OVERRIDE_GFX_VERSION:** use "10.3.0 for RDNA2, 11.0.0 for RDNA3" to emulate a supported architecture on an unsupported GPU. "This is not supported on Windows." — [llama.cpp docs/build.md](https://raw.githubusercontent.com/ggml-org/llama.cpp/master/docs/build.md)

### Inferences
- For a local-LLM user in Oct 2026, the RX 7900 XTX, RX 9070 XT, R9700 (32 GB) and Strix Halo (gfx1151, up to 128 GB unified memory) are all first-class targets. HSA_OVERRIDE_GFX_VERSION is now mainly needed for the RX 6000 series (gfx1031/1032 → 10.3.0), lower RDNA3 mobile parts, and APUs not on the list.
- Because the 7.14→10.x versions came out through TheRock with Python wheels, the pip-installed per-gfx-family wheels (as opposed to system packages) are likely the main path for PyTorch users. Background knowledge: TheRock publishes per-family index URLs such as gfx110X-dgpu, gfx1151 and gfx120X-all. This was not re-verified in this session.

### Gaps
- I could not confirm whether the RX 6000 (gfx1030 desktop) cards are officially supported in 10.1. Only the V620 is listed.
- I did not fetch the exact contents of ROCm.AI and Hyperloom. Phoronix gives only names.
- I did not fetch the exact pip index URLs or the Windows PyTorch install flow for 10.x.

## 2. HIP programming: porting, wave32/64, intrinsics, inline asm, compile flags

### Takeaway
HIP is the CUDA-like C++ dialect, compiled by amdclang/hipcc (LLVM). The key kernel-level difference is that **CDNA (Instinct) runs wave64** with MFMA matrix cores, while **RDNA3/RDNA4 natively run wave32** (wave64 is optional) with WMMA instructions. RDNA4 adds FP8 WMMA. Code must not hard-code warpSize=32. The 10.1 release notes add only minor HIP APIs. Most detail here is background knowledge.

### Cited Findings
- **HIP additions in ROCm 10.1:**
  - `hipDeviceGetLuid` and `hipInitDevice`
  - Host-NUMA virtual memory (`hipMemLocationTypeHostNuma`)
  - Windows coarse-grained coherency (`hipExtHostRegisterCoarseGrained`)
  - Two new Core SDK libraries: hipThreads and libhipcxx (C++ standard library)

  — [ROCm 10.1.0 release notes](https://rocm.docs.amd.com/en/latest/about/release-notes.html)
- **ROCm 7.2.4** optimized HIP graph dispatch, which lowers launch latency for `hipGraphLaunch` with multi-list graph topologies. — [ROCm release notes 7.2.x via search](https://rocm.docs.amd.com/en/docs-7.2.2/about/release-notes.html)
- **Native FP8 WMMA on RDNA4** (RX 9070 XT / R9700) is being brought into vLLM, which confirms that RDNA4 has hardware FP8 matrix instructions. RDNA3 does not. — [vLLM forum: Native FP8 WMMA for RDNA4](https://discuss.vllm.ai/t/native-fp8-wmma-support-for-amd-rdna4-rx-9070-xt-r9700-in-vllm/1900)
- **Kernel-level techniques shown on MI300X** in Hugging Face's custom kernels (July 2025):
  - 128-bit coalesced loads
  - Packed FP16 instructions and exp2-based SwiGLU
  - Split-K skinny GEMM with warp specialization (producer/consumer)

  Reported speedups: RMSNorm 27–100% over vLLM's kernel, SwiGLU about 14× over torch, skinny GEMM 112–141% for M=1–8, and about 15% end-to-end latency reduction. The code is in the hf-rocm-kernels repo. — [HF blog: Creating custom kernels for the AMD MI300](https://huggingface.co/blog/mi300kernels)
- **ISA things to check** (AMD tuning guide):
  - Global loads in loops should be `global_load_dwordx4`.
  - LDS ops should use the `_b128` variants.
  - Inspect `s_waitcnt vmcnt(n)` and `lgkmcnt(n)` to see whether loads overlap with compute.

  — [ROCm MI300/MI350 workload optimization guide](https://rocm.docs.amd.com/en/latest/how-to/rocm-for-ai/inference-optimization/workload.html)

### Inferences
These points are background knowledge, not re-verified in this session:
- **Porting:** `hipify-perl` does regex translation and `hipify-clang` does AST-based translation. HIP's API mirrors CUDA (cudaMalloc→hipMalloc and so on).
- **warpSize:** use `warpSize` / `__AMDGCN_WAVEFRONT_SIZE`, not 32. Warp intrinsics take 64-bit masks on wave64. In ROCm 7.x, `warpSize` became a non-constexpr runtime value.
- **Compile:**
  - `hipcc` or `amdclang++ -x hip --offload-arch=gfx1100;gfx1201;gfx1151`
  - `-mwavefrontsize64` / `-mno-wavefrontsize64` controls the RDNA wave size.
  - `-munsafe-fp-atomics` turns float atomicAdd into hardware atomics instead of CAS loops.
  - `__launch_bounds__(threads, min_waves_per_eu)` and `__attribute__((amdgpu_waves_per_eu(...)))` control register and occupancy trade-offs.
  - `--save-temps` or `-Rpass-analysis=kernel-resource-usage` show the ISA and VGPR/SGPR/LDS/occupancy.
- **Intrinsics:**
  - Matrix: `__builtin_amdgcn_mfma_*` (CDNA), `__builtin_amdgcn_wmma_*` (RDNA3/4; RDNA4 adds `_gfx12` variants and FP8/BF8).
  - Cross-lane: `__builtin_amdgcn_ds_bpermute`, `__builtin_amdgcn_mov_dpp`, `__builtin_amdgcn_readfirstlane`.
  - Buffer: `__builtin_amdgcn_raw_buffer_load_*`.
  - Scheduling: `__builtin_amdgcn_s_waitcnt`, `__builtin_amdgcn_sched_group_barrier`.
  - Inline `asm volatile` with the AMDGCN ISA is supported.
- **Instruction set references:** the CDNA3/CDNA4 and RDNA3/RDNA4 ISA PDFs on gpuopen/amd.com.

### Gaps
- I did not fetch the current HIP porting guide or the warpSize changes from the ROCm 7.x/10.x docs. Treat the flag names above as background knowledge.

## 3. Libraries: rocBLAS, hipBLASLt, CK/CK-Tile, rocWMMA, MIOpen, rocPRIM/hipCUB, AITER, hipSPARSELt, RCCL

### Takeaway
- **Portable libraries** run on RDNA and CDNA: rocBLAS, hipBLASLt, rocPRIM/hipCUB, rocWMMA, MIOpen, and increasingly CK, which now targets RDNA3/4 for attention.
- **AITER is Instinct-only:** gfx942 and gfx950. It is AMD's main inference-kernel library (Triton + CK + hand-written ASM), and vLLM and SGLang use it on MI300/MI350.
- **Tuning** happens through hipBLASLt offline tuning (hipblaslt-bench, find_exact.py, TensileLite YAML) and PyTorch TunableOp.

### Cited Findings
- **AITER**
  - "AMD's high-performance AI operator library", a unified collection of production operators for inference and training.
  - Backends: Triton, Composable Kernel, and hand-tuned ASM. It includes GEMM+communication fused kernels.
  - Supported architectures: MI300X/MI325X (gfx942, fully supported) and MI350/MI355X (gfx950).
  - Also includes FlyDSL AOT precompilation for MoE and GEMM kernels, and an "Opus" a16w16 GEMM for gfx950.

  — [ROCm/aiter GitHub](https://github.com/ROCm/aITER); [AMD blog: AITER](https://rocm.blogs.amd.com/software-tools-optimization/aiter-ai-tensor-engine/README.html)
  - In vLLM V1, AITER provides "ROCm-specific fused kernels optimized for Instinct MI350 Series and MI300X/MI325X". — [ROCm docs: vLLM V1 performance optimization (7.2.4)](https://rocm.docs.amd.com/en/docs-7.2.4/how-to/rocm-for-ai/inference-optimization/vllm-optimization.html)
- **Composable Kernel 1.3.0 (ROCm 10.1)** adds a SPIR-V target and gfx1250 optimizations (gfx1250 is a next-generation target). In 10.1, hipBLASLt and rocBLAS get unspecified perf and feature updates. — [ROCm 10.1.0 release notes](https://rocm.docs.amd.com/en/latest/about/release-notes.html)
- **ROCm 7.14 library changes:**
  - hipBLASLt: per-batch bias stride
  - rocBLAS: SPIR-V support
  - hipSPARSE: BSR format
  - hipTensor: Windows support, RDNA3/4 GPUs, FP16/BF16

  — [AMD ROCm 7.14 blog](https://rocm.blogs.amd.com/ecosystems-and-partners/rocm-7.14-blog/README.html)
- **hipBLASLt tuning** (MI300 guide):
  - Benchmark with `hipblaslt-bench` (example FP8 command uses `HIP_FORCE_DEV_KERNARG=1 ... --cold_iters 100 --iters 1000 --rotating 256`).
  - Auto-tune with `python3 hipblaslt/utilities/find_exact.py tuning.yaml ...`.
  - TensileLite backend YAML: `ArchitectureName: gfx942|gfx950`, `AlgoMethod: "all"`, `NumElementsToValidate: 0`.
  - Avoid strides that are multiples of 512 bytes, which cause TA (Tagram) channel conflicts.

  — [ROCm workload optimization guide](https://rocm.docs.amd.com/en/latest/how-to/rocm-for-ai/inference-optimization/workload.html)
- **CK as a TorchInductor backend:** `pip install git+https://github.com/rocm/composable_kernel@develop`, then `TORCHINDUCTOR_MAX_AUTOTUNE_GEMM_BACKENDS=TRITON,ATEN,CK`. It covers matmul, addmm, scaled_mm (FP8) and conv2d. — [same guide](https://rocm.docs.amd.com/en/latest/how-to/rocm-for-ai/inference-optimization/workload.html)
- **RCCL tips:** `NCCL_MIN_NCHANNELS=112`, disable ACS on PCIe switches, `TORCH_NCCL_HIGH_PRIORITY=1`, `GPU_MAX_HW_QUEUES=2`. — [same guide](https://rocm.docs.amd.com/en/latest/how-to/rocm-for-ai/inference-optimization/workload.html)
- **rocWMMA** is used by llama.cpp for flash attention on "RDNA3+ or CDNA". There is a known rocWMMA 2.2.0 + AMD LLVM 22 compile issue on gfx9 (CDNA) devices without native fp16 support. — [llama.cpp commit: rocWMMA docs](https://cdn04132025.gitlink.org.cn/replica/llama.cpp/commit/3ffbbd5ce130859be91909e9b77d4c1962a6be2c); [llama.cpp PR #17156](https://github.com/ggml-org/llama.cpp/pull/17156)

### Inferences
- Lean on AITER and the MI300 tuning guide as references for Instinct only. On Radeon, the practical kernel stack is hipBLASLt/rocBLAS for GEMM, CK or Triton for attention, rocWMMA or raw WMMA intrinsics for hand-written kernels, and llama.cpp's own MMQ kernels for quantized matmul.
- Background knowledge, not re-verified:
  - hipSPARSELt (2:4 sparsity) and the FP8 hipBLASLt paths are tuned mostly for CDNA.
  - CK-Tile is CK's newer tile-programming API, which hosts the FMHA (flash attention) kernels.
  - rocPRIM is the ROCm primitives library and hipCUB is a CUB-compatible wrapper over it.

### Gaps
- I did not obtain an official per-library RDNA-vs-CDNA support matrix for hipSPARSELt, MIOpen or CK in 10.1.
- It is unconfirmed whether AITER has gained any RDNA4 kernels by Oct 2026. The sources found list gfx942/gfx950 only.

## 4. Triton on ROCm: AMD backend, RDNA support, tunables

### Takeaway
Triton's AMD backend is upstream and it is the main path for custom kernels in vLLM, SGLang and AITER. On MI300 the key knobs are:
- `num_stages=2` for a single GEMM; `1` for fused or non-GEMM kernels
- `waves_per_eu` to trim VGPRs to the next occupancy level
- `matrix_instr_nonkdim=16`; 16×16 MFMA usually beats 32×32
- `BLOCK_M/N/K` sized against 64 KB LDS (MI300X) or 160 KB LDS (MI350X)

AMD now also promotes **Gluon**, a lower-level Triton dialect, for layout-explicit kernels.

### Cited Findings
- **`num_stages`:** 2 for single-GEMM kernels, 1 for fused multi-GEMM or non-GEMM kernels. MI350X's 160 KB LDS (vs 64 KB on MI300X) may allow 3–4 stages. — [ROCm workload optimization guide](https://rocm.docs.amd.com/en/latest/how-to/rocm-for-ai/inference-optimization/workload.html)
- **`waves_per_eu`** example: 170 VGPRs round up to 176 in 16-VGPR granules. 3×176 = 528 > 512, so occupancy is capped at 2 waves per EU; setting `waves_per_eu=3` makes the compiler trim VGPRs. — [same guide](https://rocm.docs.amd.com/en/latest/how-to/rocm-for-ai/inference-optimization/workload.html)
- **`matrix_instr_nonkdim`** selects 16 or 32 MFMA. On MI300X, `mfma_16x16` typically beats `mfma_32x32` even for large GEMMs. — [same guide](https://rocm.docs.amd.com/en/latest/how-to/rocm-for-ai/inference-optimization/workload.html)
- **Occupancy formulas:**
  - `occ_lds = floor(65536/L)` on MI300X and `floor(163840/L)` on MI350X, where L is LDS bytes allocated.
  - Final occupancy is `min(occ_vgpr, occ_lds) × num_warps/4`.
  - Aim for at least 1024 thread blocks to fill 304 CUs (MI300X) or 256 CUs (MI350X).

  — [same guide](https://rocm.docs.amd.com/en/latest/how-to/rocm-for-ai/inference-optimization/workload.html)
- **Debug environment variables:**
  - `MLIR_ENABLE_DUMP=1` dumps the MLIR IR.
  - `AMDGCN_ENABLE_DUMP=1` dumps the AMDGCN ISA.
  - `TORCH_COMPILE_DEBUG=1` dumps Inductor-generated Triton code.
  - Inductor knobs: `mode="max-autotune"` (enables HIP graphs), `TORCHINDUCTOR_MAX_AUTOTUNE_GEMM_SEARCH_SPACE=EXHAUSTIVE`, `TORCHINDUCTOR_FREEZING=1`, `TORCHINDUCTOR_CPP_WRAPPER=1`.

  — [same guide](https://rocm.docs.amd.com/en/latest/how-to/rocm-for-ai/inference-optimization/workload.html)
- **MI350X (CDNA4) specifics:**
  - OCP FP8 format (MI300X uses FNUZ), so quantized weights must match the target GPU.
  - TF32 is emulated in software.
  - Native MXFP8/MXFP6/MXFP4 with 32-element scale blocks.
  - `kWidth=16–32` for FP8 in Triton.

  — [same guide](https://rocm.docs.amd.com/en/latest/how-to/rocm-for-ai/inference-optimization/workload.html)
- **Gluon** (block-level Triton):
  - `AMDMFMALayout(transposed=True)`, with `warps_per_cta=[2,2]` for 256×256 tiles
  - `PaddedSharedLayout([[512,16]])`, which removes LDS bank conflicts (4-way → 1-way); for FP8, `[[1024,16],[2048,32]]`
  - `DotOperandLayout(kWidth=8)` for FP16
  - A 3-stage pipeline: async_copy HBM→LDS for k+2, ds_read for k+1, MFMA for k
  - Target 384–448 VGPRs for a 4-wave 256×256 tile

  — [same guide](https://rocm.docs.amd.com/en/latest/how-to/rocm-for-ai/inference-optimization/workload.html)
- The ROCm "Optimizing Triton kernels" page is now only an index (auto-tunable configs, MLIR analysis, ISA analysis, torch.compile, occupancy). It points to the MI300/MI350 workload guide for the details. — [ROCm docs: optimizing Triton kernel](https://rocm.docs.amd.com/en/latest/how-to/rocm-for-ai/inference-optimization/optimizing-triton-kernel.html)

### Inferences
- The guide is written entirely for CDNA. Background knowledge, not re-verified:
  - On RDNA3/4 Triton lowers `tl.dot` to WMMA (wave32), and `matrix_instr_nonkdim` and MFMA-specific `kpack` don't apply.
  - `kpack` (1 or 2) controls the K-packing of MFMA operands on CDNA.
  - On RDNA, LDS is 64 KB per workgroup (WGP mode), and Triton's `num_warps` maps to wave32 waves.
- Expect Triton kernels tuned for MI300 to need re-tuning on Radeon (smaller BLOCK sizes, fewer stages).

### Gaps
- I did not find an AMD document dedicated to Triton tuning on RDNA3/RDNA4, or a status page for RDNA in the Triton AMD backend for 2026.

## 5. FlashAttention on AMD

### Takeaway
ROCm/flash-attention has two FA2 backends: **CK** (the default) and **Triton**. Both now cover RDNA3/4 for forward. The CK backend's RDNA3 support is forward-only, and RDNA4 backward requires `deterministic=False`. PyTorch SDPA uses **AOTriton**, which added official gfx950 and gfx1201 (RDNA4) support in 0.10b.

### Cited Findings
- **Backends:** ROCm flash-attention has a composable_kernel backend (default) and a Triton backend, both FA2.
  - The **CK backend** supports MI200x, MI250x, MI300x, MI355x and RDNA3/4. RDNA3 has no backward pass, and RDNA4 supports backward only with `deterministic=False`.
  - The **Triton backend** supports CDNA (MI200, MI300) and RDNA in fp16, bf16 and fp32. It covers forward and backward, causal masking, varlen, arbitrary sequence lengths and head sizes, MQA/GQA, dropout, rotary, ALiBi, paged attention and FP8.

  — [Dao-AILab/flash-attention README (ROCm section)](https://github.com/dao-ailab/flash-attention)
- **AOTriton 0.10b** includes official support for gfx950 and gfx1201. — [newreleases: ROCm/aotriton 0.10b](https://newreleases.io/project/github/ROCm/aotriton/release/0.10b)
  - The snippet calls gfx1201 the "RX 7600M XT", which is wrong: gfx1201 is Navi48 (RX 9070 series).

### Inferences
- On RDNA3 the CK backend is forward-only, so inference is fine but training is not. On Radeon, the Triton backend is the more feature-complete option, including paged attention and FP8.
- Background knowledge: the Triton backend is selected with `FLASH_ATTENTION_TRITON_AMD_ENABLE="TRUE"` at build and run time. This was not re-verified.

### Gaps
- No benchmark numbers for FA on RX 9070 XT or 7900 XTX were collected.
- The current AOTriton version (after 0.10b) and its gfx1100/gfx1151 status were not verified.

## 6. Profiling and tools

### Takeaway
The current profiler suite rests on **ROCprofiler-SDK**:
- `rocprofv3` collects traces and counters.
- **ROCm Compute Profiler** (`rocprof-compute`, formerly Omniperf; v3.9.0 in ROCm 10.1) gives speed-of-light, memory chart, roofline and per-kernel PC sampling. It is now pip-installable.
- **ROCm Systems Profiler** (`rocprof-sys`, formerly Omnitrace) gives system timelines.

roctracer and rocprof v1/v2 are no longer maintained. For RDNA consumer cards, Radeon GPU Profiler and Radeon GPU Analyzer are the complementary tools (background knowledge).

### Cited Findings
- **ROCm 10.1 profiler changes:**
  - ROCprofiler-SDK 1.4.1 adds kernel replay (beta), HIP event tracing, and reversible runtime interception.
  - ROCm Compute Profiler 3.9.0 adds interactive roofline analysis and per-kernel PC sampling.
  - **rocpd is now the default output format** across the profiler suite.
  - **roctracer and rocprof v1/v2 are no longer maintained**; users should move to ROCprofiler-SDK.
  - The `rocprof-sys-user` C APIs were removed; use ROCTx for manual ranges.

  — [ROCm 10.1.0 release notes](https://rocm.docs.amd.com/en/latest/about/release-notes.html)
- **ROCm 7.14 profiler changes:**
  - Systems Profiler gained MPI rank filtering and ROCTx region scoping.
  - Compute Profiler is distributed via pip.
  - ROCprofiler-SDK gained Address Sanitizer support.
  - **The PyTorch Profiler now uses the rocprofiler-SDK backend.**

  — [AMD ROCm 7.14 blog](https://rocm.blogs.amd.com/ecosystems-and-partners/rocm-7.14-blog/README.html)
- **AMD's recommended workflow:**
  1. PyTorch profiler → chrome trace → Perfetto, for operation-level bottlenecks.
  2. rocprof counters.
  3. rocprof-compute for automated multi-pass counter collection with speed-of-light, memory chart and roofline.

  — [ROCm workload optimization guide](https://rocm.docs.amd.com/en/latest/how-to/rocm-for-ai/inference-optimization/workload.html)

### Inferences
These points are background knowledge, not re-verified in this session:
- `rocprofv3 --kernel-trace --stats -d out -- ./app` and `--pmc SQ_WAVES ...` are the basic invocations. `rocprof-compute profile -n name -- ./app`, then `rocprof-compute analyze -p workloads/...`, gives the SOL and roofline.
- rocprof-compute's full hardware-counter analysis is mainly for CDNA (gfx90a/gfx942/gfx950), and RDNA support is partial.
- On Radeon, **RGP** (Radeon GPU Profiler) can capture compute/HIP dispatches with instruction timing ("thread trace") on RDNA. **RGA** (Radeon GPU Analyzer) compiles HIP/OpenCL offline and shows ISA, VGPR use and occupancy per gfx target.
- `hipcc --save-temps` produces `.s` ISA files. `llvm-objdump -d --offload-arch` or `roc-obj` extracts code objects.

### Gaps
- I did not verify RGP support for HIP compute on RDNA4 in 2026, or which rocprof-compute version added RDNA counters.

## 7. Inference engines on ROCm (kernel view)

### Takeaway
- On **Instinct**, vLLM (V1) and SGLang use AITER kernels: fused MoE, MLA/paged attention, FP8/FP4 GEMM and norms. vLLM 0.29 and SGLang 0.5.18 are the versions validated against ROCm 10.1.
- On **Radeon**, the most practical engine is llama.cpp's HIP backend:
  - its own MMQ quantized matmul kernels, now with WMMA paths on RDNA4
  - rocWMMA-based flash attention via `GGML_HIP_ROCWMMA_FATTN=ON` for RDNA3+/CDNA
- vLLM is gaining RDNA4 FP8 WMMA support.
- PyTorch TunableOp is the generic GEMM-tuning hook.

### Cited Findings
- Frameworks validated for 10.1: PyTorch 2.14.0, vLLM 0.29.0, SGLang 0.5.18, MIGraphX 2.18. ROCm 7.14 listed vLLM, llama.cpp, Ollama and SGLang as supported. — [ROCm 10.1 release notes](https://rocm.docs.amd.com/en/latest/about/release-notes.html); [ROCm 7.14 blog](https://rocm.blogs.amd.com/ecosystems-and-partners/rocm-7.14-blog/README.html)
- ROCm 10.0 ships production containers and Python wheels for vLLM. — [Phoronix ROCm 10.0](https://www.phoronix.com/news/AMD-ROCm-10.0)
- vLLM V1 on ROCm uses AITER fused kernels for MI300X/MI325X/MI350. — [ROCm vLLM V1 optimization docs](https://rocm.docs.amd.com/en/docs-7.2.4/how-to/rocm-for-ai/inference-optimization/vllm-optimization.html)
- There is community work on native FP8 WMMA for RDNA4 (RX 9070 XT, R9700) in vLLM. — [vLLM forum](https://discuss.vllm.ai/t/native-fp8-wmma-support-for-amd-rdna4-rx-9070-xt-r9700-in-vllm/1900)
- **PyTorch TunableOp:**
  - `PYTORCH_TUNABLEOP_ENABLED=1`
  - `PYTORCH_TUNABLEOP_TUNING=1` for the first run, which writes `tunableop_results.csv`; then `0` for inference
  - `PYTORCH_TUNABLEOP_VERBOSE=1`

  — [ROCm workload optimization guide](https://rocm.docs.amd.com/en/latest/how-to/rocm-for-ai/inference-optimization/workload.html)
- **llama.cpp HIP build:**
  - `-DGGML_HIP=ON -DGPU_TARGETS=gfx1100` (and so on)
  - On Linux, set `HIPCXX="$(hipconfig -l)/clang" HIP_PATH="$(hipconfig -R)"`.
  - On Windows, use the VS x64 Native Tools prompt with Ninja and `-DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++`.
  - `GGML_CUDA_ENABLE_UNIFIED_MEMORY=1` enables UMA; it helps iGPUs/APUs and hurts discrete GPUs.
  - `HIP_DEVICE_LIB_PATH` fixes missing device libraries.
  - `GGML_CUDA_FORCE_MMQ` and `GGML_CUDA_FORCE_CUBLAS` choose between the custom quantized kernels and FP16 BLAS (hipBLAS on ROCm).

  — [llama.cpp docs/build.md](https://raw.githubusercontent.com/ggml-org/llama.cpp/master/docs/build.md)
- **`-DGGML_HIP_ROCWMMA_FATTN=ON`** uses rocWMMA to speed up flash attention on RDNA3+/CDNA; it needs the rocWMMA headers. WMMA-MMQ kernels were enabled for RDNA4, with benchmarks comparing ROCWMMA_FATTN OFF and ON. — [llama.cpp rocWMMA docs commit #12179](https://cdn04132025.gitlink.org.cn/replica/llama.cpp/commit/3ffbbd5ce130859be91909e9b77d4c1962a6be2c); [llama.cpp PR #17156](https://github.com/ggml-org/llama.cpp/pull/17156)
  - Conflict: the current master `docs/build.md` (fetched 2026-10-06) no longer mentions GGML_HIP_ROCWMMA_FATTN. The option may have been moved, renamed or made default. This needs checking against the current CMake files.

### Inferences
- **Kernel-wise, llama.cpp on ROCm** works like this:
  - Quantized matmul (Q4_K etc.) goes through MMQ: dequantize into tiles and integer dot products, using dp4a-like `v_dot4` instructions or WMMA on RDNA3/4 and MFMA on CDNA.
  - Small-batch decode uses MMVQ (matrix-vector) kernels.
  - Attention uses its own FA kernels: a tile/vector FA path, plus the rocWMMA path when enabled.
- For a local Radeon user, the engines that matter are llama.cpp (and Ollama/LM Studio built on it) and, increasingly, vLLM on RDNA4.

### Gaps
- I did not verify the current SGLang ROCm kernel set, or the exact vLLM RDNA status (which attention backend vLLM uses on gfx1100/gfx1201 by default).

## 8. AMD optimization guides, blogs, and GPU MODE competitions

### Takeaway
The main official reference is the "AMD Instinct MI300 Series / MI350 Series workload optimization" guide on rocm.docs.amd.com, together with ROCm blog posts such as AITER and FP8 GEMM on CDNA4. AMD and GPU MODE have run two kernel competitions:
1. **2025 AMD Developer Challenge ($100K, MI300).** It produced about 110K kernels across these problems: fp8-gemm, moe, mla, all2all, gemm+reducescatter and allgather+gemm.
2. **2026 hackathon ($1.1M, MI355X).** Phase 1 (Mar 6–Apr 6, 2026) covered MXFP4 MoE, MLA decode and MXFP4 GEMM kernels; it was followed by end-to-end model speedruns.

### Cited Findings
- **2025 challenge:** GPU MODE built the infrastructure for AMD's $100K kernel competition. It ran 2 months with 30,000+ submissions from 163+ teams. The resulting dataset of about 110K kernels covers fp8-gemm, moe, mla, all2all, gemm+reducescatter and allgather+gemm on MI300. — [GPUMODE kernelbot-data README (HF)](https://huggingface.co/datasets/GPUMODE/kernelbot-data/blob/refs%2Fpr%2F9/README.md) (via search snippet)
- **Public writeups:**
  - Akash Karnatak's solutions; Fan Wenjie's technical analysis; Snektron's FP8 matmul — referenced in [gpu-mode/kernelboard PR #49](https://github.com/gpu-mode/kernelboard/pull/49/files)
  - seb-v's AMD challenge solutions, an FP8 GEMM written in HIP for MI300X — [DeepWiki: seb-v/amd_challenge_solutions](https://deepwiki.com/seb-v/amd_challenge_solutions)
  - Yotta Labs on the distributed kernels — [Yotta Labs blog (2025-10-23)](https://www.yottalabs.ai/post/optimizing-distributed-inference-kernels-for-amd-developer-challenge-2025)
- **2026 AMD x GPU MODE hackathon:** $1.1M in prizes on MI355X.
  - Phase 1 qualifiers (2026-03-06 to 04-06) were MXFP4 MoE, MLA Decode and MXFP4 GEMM kernels.
  - Track 1 was DeepSeek-R1-0528 FP4 + MTP ($350K grand prize). Track 2 was Kimi K2.5 1T FP4 ($650K grand prize).
  - Phase 2 finals ended in about May 2026.

  — [AMD: New GPU MODE Virtual Hackathon: E2E Model Speedrun](https://www.amd.com/en/developer/resources/technical-articles/2026/new-gpumode-virtual-hackathon--e2e-model-speedrun.html); [luma event](https://luma.com/cqq4mojz)
- **AMD FP8 GEMM tutorials for CDNA4 (HIP):** a blog post plus an AI Developer Hub notebook (v13.0 and v14.0 versions exist). — [ROCm blog: FP8 GEMM Optimization on CDNA4](https://rocm.blogs.amd.com/software-tools-optimization/cdna4-gemm-kernels/README.html); [AI Developer Hub notebook](https://rocm.docs.amd.com/projects/ai-developer-hub/en/latest/notebooks/gpu_dev_optimize/fp8_gemm_hip_cdna4.html)
- There is also an AMD blog on DeepSeek-R1 inference performance on MI300X. — [ROCm blog](https://rocm.blogs.amd.com/artificial-intelligence/DeepSeekR1_Perf/README.html)

### Inferences
- Common winning techniques in the 2025 FP8-GEMM track, from background knowledge of the public writeups (not re-verified here):
  - Hand-written HIP with direct MFMA intrinsics and FP8 FNUZ on gfx942
  - Double-buffered LDS with padded or swizzled layouts to avoid bank conflicts
  - Buffer loads with `s_waitcnt` scheduling
  - Applying the block scales in registers
  - Choosing tile shapes per problem shape so all 304 CUs are busy
  - Inline asm in some cases
- The MoE and MLA tracks leaned on AITER-style fused kernels.

### Gaps
- I did not fetch the winners' writeups, so I can't give specific speedups or technique lists for the 2025 or 2026 winners.
- The 2026 final results (winners, scores) were not found.
