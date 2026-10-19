# NVIDIA track: legal boundaries + practical RE/optimization workflow on RTX 5060 Ti (GB206, sm_120)

Research date: 2026-10-17. All version numbers carry the date/version of the source they came from. Items marked **[UNVERIFIED]** could not be confirmed from a primary source during this research. The user's model name "Qwen3.8-27B" could not be matched to a known Qwen release name; everything below applies to any Q4_K_M GGUF model, since llama.cpp dispatches the same kernels per quant type, not per model **[UNVERIFIED model name]**.

Hardware context used throughout: RTX 5060 Ti 16 GB = GB206-300, 36 SMs, 4,608 CUDA cores, 144 5th-gen Tensor Cores, 128-bit GDDR7, 180 W TGP, PCIe Gen 5, launched 2025-04-16 at $429 (Wikipedia spec table + NVIDIA spec page, see Q4). Compute capability 12.0 (sm_120).

---

## Q1. What does the CUDA EULA permit / prohibit regarding reverse engineering (and what about translation layers / non-NVIDIA hardware)?

### Takeaway
The CUDA Toolkit EULA (v13.4, "Last updated: January 26, 2026") flatly prohibits reverse engineering, decompiling or disassembling *any portion of the SDK* (which includes cuBLAS, cuDNN-style libraries shipped in the toolkit), and separately prohibits RE of *your own compiled output* **only when the purpose is translating it to a non-NVIDIA platform**. Disassembling your own kernels with cuobjdump/nvdisasm (tools NVIDIA ships for exactly that), reading open-source kernels, microbenchmarking the hardware and publishing performance numbers are not restricted by any EULA clause found; there is no benchmarking/no-publish clause in the CUDA EULA.

### Cited Findings
- EULA version: "v13.4, Last updated: January 26, 2026" (page footer "Last updated on Oct 12, 2026") — [CUDA EULA](https://docs.nvidia.com/cuda/eula/index.html)
- Section 1.2 "Limitations", item 1 (verbatim): "You may not reverse engineer, decompile or disassemble, or remove copyright or other proprietary notices from any portion of the SDK or copies of the SDK." — [CUDA EULA §1.2](https://docs.nvidia.com/cuda/eula/index.html)
- Section 1.2 item 8 (verbatim, the "ZLUDA clause"): "You may not reverse engineer, decompile or disassemble any portion of the output generated using SDK elements for the purpose of translating such output artifacts to target a non-NVIDIA platform." — [CUDA EULA §1.2](https://docs.nvidia.com/cuda/eula/index.html)
- Section 2.1 "License Scope" (verbatim): "The SDK is licensed for you to develop applications only for use in systems with NVIDIA GPUs." — [CUDA EULA §2.1](https://docs.nvidia.com/cuda/eula/index.html)
- Section 1.2 item 4: "You may not bypass, disable, or circumvent any encryption, security, digital rights management or authentication" mechanism; item 5: "You may not use the SDK in any manner that would cause it to become subject to an open source software license." — [CUDA EULA §1.2](https://docs.nvidia.com/cuda/eula/index.html)
- Section 1.1.1 grant: "NVIDIA hereby grants you a non-exclusive, non-transferable license, without the right to sublicense" to install/use the SDK, modify sample source, and redistribute listed runtime components as object code. — [CUDA EULA §1.1.1](https://docs.nvidia.com/cuda/eula/index.html)
- The EULA contains **no clause** on benchmarking or publishing performance results; cuobjdump is mentioned only in Attachment B (Zstandard third-party notice, "Components of the driver and compiler used for binary management, including nvFatBin, nvcc, and cuobjdump"); nvdisasm has no separate license clause. — [CUDA EULA](https://docs.nvidia.com/cuda/eula/index.html)
- cuobjdump/nvdisasm are documented NVIDIA tools: cuobjdump `-sass`, `-ptx`, `-elf`, `-lelf/-xelf`, `-res-usage` (`--dump-resource-usage`), `-arch` (allowed values `sm_75` … `sm_121f`), `-fun`; nvdisasm `-g/-gi/-gp` (source line info), `-c`, `-cfg`, `-bbcfg`, `-plr` (register life ranges) with `-lrm count|narrow|wide`, `-hex`, `-json`, `-b` (raw binary). CUDA Binary Utilities v13.4. — [CUDA Binary Utilities 13.4](https://docs.nvidia.com/cuda/cuda-binary-utilities/index.html)
- History of the translation-layer clause (March 2024 news cycle): Tom's Hardware reported the wording "is not included in the documentation for CUDA versions 11.4 and 11.5, and appears to have been included from version 11.6"; it was spotted by engineer "Longhorn" in the EULA.txt installed with CUDA 11.6; sources disagree whether the online EULA carried it since 2021. Reporting tied it to ZLUDA and Chinese GPU vendors; NVIDIA made no official statement. — [Gigazine 2024-03-05](https://gigazine.net/gsc_news/en/20240305-nvidia-cuda), [OC3D](https://overclock3d.net/news/gpu-displays/nvidia-bans-the-use-of-translation-layers-on-cuda-software/), [Tom's Hardware (body not retrievable through proxy)](https://www.tomshardware.com/pc-components/gpus/nvidia-bans-using-translation-layers-for-cuda-software-to-run-on-other-chips-new-restriction-apparently-targets-zluda-and-some-chinese-gpu-makers)
- ZLUDA aftermath: AMD asked the developer to take down the AMD-funded code in Aug 2024 (AMD legal said the e-mail approval was not binding) — [The Register 2024-08-09](https://www.theregister.com/2024/08/09/amd_zluda_take_down/); project continued, two full-time developers as of Q2 2025 — [Phoronix 2025-07](https://www.phoronix.com/news/ZLUDA-Q2-2025-Update)
- NVBit (NVIDIA's binary instrumentation framework) is itself licensed under "the same End User License Agreement as the NVIDIA CUDA Toolkit" (EULA.txt in repo). — [NVBit README](https://raw.githubusercontent.com/NVlabs/NVBit/master/README.md)

### Inferences
- **Allowed (explicit or clearly within the license):** compiling your own kernels and dumping SASS with `cuobjdump -sass` / `nvdisasm` (the tools exist for that, §1.2-8 only bites if the goal is porting to non-NVIDIA hardware); reading open-source kernels (llama.cpp, CUTLASS, maxas-style assemblers); microbenchmarking GB206 with PTX/`%clock64` (the Delaware "Dissecting Blackwell" paper did exactly that on an RTX 5080, Q4); profiling with Nsight Compute; publishing numbers (no benchmark clause).
- **Grey zone:** `cuobjdump -sass libcublas.so` / `-lelf` extracting cuBLAS cubins to *study* them. The tool makes it trivial (siboehm's widely-read 2022 blog uses `cuobjdump --list-text` on cuBLAS, Q7), but §1.2-1 literally prohibits disassembling "any portion of the SDK"; cuBLAS is part of the SDK. Also grey: DocumentSASS-style extraction of hidden strings from `nvdisasm` (Q5) — it reads the tool's own internal data, which is RE of the SDK by the letter of §1.2-1.
- **Prohibited:** decompiling/disassembling cuBLAS/cuDNN/nvcc/ptxas/libcuda to reproduce them; any RE whose purpose is a translation layer for AMD/Intel/other hardware (§1.2-8, §2.1); circumventing DRM/auth (§1.2-4).
- **Practical risk for a hobbyist:** the EULA is a contract, and the only remedy named is loss of license; there is no evidence of NVIDIA pursuing individuals who read SASS of cuBLAS for learning. The *publication* risk is higher than the *reading* risk: publishing a cuBLAS kernel re-implementation derived from its SASS, or a tool that targets non-NVIDIA hardware, is where enforcement interest exists (ZLUDA precedent, though that was AMD's legal department, not NVIDIA's). Keeping to your own binaries + open-source kernels is zero-risk; privately reading library SASS is low-risk but contractually non-compliant; distributing derivatives is the line not to cross. (This is an inference, not legal advice.)

### Gaps
- Tom's Hardware article body was not retrievable through the proxy (page returned headline only), so the exact "online since 2021" vs "11.6" timing is reported from secondary outlets.
- Could not find any documented NVIDIA enforcement action against an individual for EULA §1.2-1 violations; absence of evidence, not evidence of absence.
- The EULA text for CUDA 11.4/11.5 was not diffed directly in this research.

---

## Q2. EU software directive counterpoint (brief) — does EU law override the EULA for interoperability/study?

### Takeaway
Directive 2009/24/EC Art. 6 allows decompilation without the rightholder's authorisation when "indispensable to obtain the information necessary to achieve the interoperability of an independently created computer program", and Recital 17 says contractual provisions contrary to the decompilation exception are "null and void". This exception is for *interoperability*, not for learning optimization tricks, and it does not authorise copying the decompiled expression.

### Cited Findings
- Art. 6(1): "The authorisation of the rightholder shall not be required where reproduction of the code and translation of its form within the meaning of points (a) and (b) of Article 4(1) are indispensable to obtain the information necessary to achieve the interoperability of an independently created computer program with other programs", subject to: acts performed by a licensee/lawful user; information not previously readily available; confined to the parts necessary for interoperability. — [Directive 2009/24/EC Art. 6 (legislation.gov.uk copy)](https://www.legislation.gov.uk/eudr/2009/24/article/6)
- Recital 17: "any contractual provisions contrary to the provisions of this Directive laid down in respect of decompilation or to the exceptions provided for by this Directive ... should be null and void." Recital 11: "ideas and principles which underlie any element of a program, including those which underlie its interfaces, are not protected by copyright". — [Directive 2009/24/EC full text](https://www.legislation.gov.uk/eudr/2009/24/data.htm)
- A May 2025 European Commission non-paper reads Art. 6 as authorising object-code decompilation and discusses updating the directive. — [EC non-paper 2025-05-09](https://interoperable-europe.ec.europa.eu/sites/default/files/discussion/attachment/2025-05/Non-paper%20PES%202025-05-09%20on%20updating%20Directive%202009-24-EC%20v01.pdf)

### Inferences
- Art. 5(3) of the same directive (observing/studying/testing a program's functioning while performing permitted acts, non-overridable by contract) is the article most relevant to "learn how cuBLAS schedules instructions" — it covers *observing* behaviour (e.g., profiling cuBLAS with ncu, timing it), but it is not a licence to disassemble. **[Art. 5(3) not fetched verbatim in this research — verify on EUR-Lex.]**
- For a Polish hobbyist: Polish law implements this directive (ustawa o prawie autorskim, art. 75), so an EULA clause forbidding decompilation *for interoperability* is unenforceable in PL/EU; the clause forbidding decompilation *for other purposes* (learning, cloning) stays enforceable as a contract term. **[Polish statute mapping from general knowledge — UNVERIFIED here.]**

### Gaps
- No case law located on applying Art. 6 to GPU library SASS; legal counsel needed for anything beyond private study.

---

## Q3. Driver-side legality: open-gpu-kernel-modules, GSP firmware, nouveau/NVK

### Takeaway
NVIDIA's kernel modules are open (per-file MIT; the linked module is dual MIT/GPLv2), currently at driver 615.78.08 and Turing+ only because they depend on the GSP firmware; the GSP firmware itself is a redistributable binary blob since the R535 EULA dropped the "no separation of components" language (May 2023), which is what lets nouveau/NVK use it. NVK was written "from scratch" using NVIDIA's official headers (not by decompiling the proprietary driver) and is a conformant Vulkan 1.4 driver that already supports consumer Blackwell RTX 50. The user-space CUDA stack (libcuda.so, ptxas, cuBLAS) remains proprietary and under the EULA.

### Cited Findings
- COPYING: "Except where noted otherwise, the individual files within this package are licensed as MIT" ... "when linked together to form a Linux kernel module, the resulting Linux kernel module is dual licensed as MIT/GPLv2." — [open-gpu-kernel-modules COPYING](https://raw.githubusercontent.com/NVIDIA/open-gpu-kernel-modules/main/COPYING)
- README: version 615.78.08; usable on "any Turing or later GPU"; must be paired with GSP firmware and user-space components from the matching 615.78.08 release (install the .run with `--no-kernel-modules`). — [open-gpu-kernel-modules README](https://raw.githubusercontent.com/NVIDIA/open-gpu-kernel-modules/main/README.md)
- GSP firmware licence: with the 535.43.02 beta (31 May 2023) NVIDIA engineer Andy Ritger said the EULA was overhauled: "There is no longer any language to prohibit separation of components", enabling shipping the GSP blobs in linux-firmware for nouveau; it is the same binary the open kernel driver uses. — [Phoronix 2023-05-31](https://www.phoronix.com/news/NVIDIA-GSP-Firmware-License)
- NVK origin (Collabora, 2022-10-04, Faith Ekstrand): "written almost entirely from scratch", using "NVIDIA's newly released official headers" for 3D/compute classes; the open kernel driver is a reference ("not quite documentation"); nouveau historically relied on reverse engineering, CUDA docs and "occasional scraps"; Turing+ targeted because of unified GSP firmware. — [Collabora: Introducing NVK](https://www.collabora.com/news-and-blog/news-and-events/introducing-nvk.html)
- Mesa docs: NVK supports "Kepler ... up to and including Ada (RTX 4000 series), as well as consumer Blackwell GPUs (RTX 5000 series)"; "NVK is a conformant Vulkan 1.4 implementation for all officially supported GPUs"; "requires at least a Linux 6.6 kernel". — [Mesa NVK docs](https://docs.mesa3d.org/drivers/nvk.html)
- Nsight/CUDA install docs: from CUDA 13.4 the Linux toolkit no longer bundles the driver; driver packages are `nvidia-open` / `cuda-drivers`. — [CUDA Installation Guide Linux 13.4](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/index.html)

### Inferences
- "Clean-room" is not a formal NVIDIA grant: NVK's legality rests on (a) NVIDIA publishing class headers under MIT, (b) nouveau's long-standing RE under EU/US interoperability exceptions, (c) GSP firmware being redistributable. Nothing in this covers CUDA user space: there is no open implementation of libcuda/ptxas/SASS assembler from NVIDIA.
- For the user's headless Ubuntu Server box the relevant choice is `nvidia-open` (open kernel module; GSP required on GB206 anyway) + proprietary user space; nouveau/NVK is irrelevant to CUDA kernel work (no CUDA on nouveau).

### Gaps
- No official NVIDIA or Collabora legal statement on NVK's clean-room status was found; only developer blog posts and forum comments.
- The exact licence text of the GSP firmware files in linux-firmware (LICENSE.nvidia) was not fetched.

---

## Q4. sm_120 toolchain facts: CUDA versions, driver branch, Ubuntu packages, sm_120 vs sm_100, compile flags, hardware limits of GB206

### Takeaway
sm_120 (CC 12.0) is supported from CUDA 12.8; today (2026-10) the current toolkit is CUDA 13.4 Update 2, which requires driver branch R615 for new features (any R580+ driver runs CUDA 13.x binaries via minor-version compatibility). Consumer Blackwell is a *different family* from datacenter Blackwell: sm_100f code does not run on sm_120, wgmma (Hopper) is unsupported, and tcgen05/TMEM (datacenter 5th-gen tensor core API) is not available on sm_120 — consumer Blackwell programs tensor cores via `mma.sync` (SASS HMMA/QMMA/OMMA) with new `.kind::f8f6f4` FP4/FP6/FP8 shapes. Per-SM limits on CC 12.x: 64K 32-bit registers/SM, 255 regs/thread, 128 KB unified L1/shared, max 100 KB shared per SM and 99 KB per block (opt-in).

### Cited Findings
**Toolkit/driver**
- CUDA 13.4 Update 2 release notes: "Existing CUDA 13.x applications run on drivers >=580 under CUDA minor version compatibility"; CUDA 13.4 uses driver branch R615 and new features require R615+; "Starting with CUDA 13.4 on Linux, the driver is no longer bundled with the Toolkit"; cuBLAS 13.x known issues specific to "compute capability 12.0 or 12.1" (OOB reads in strided-batched GEMM with broadcast operands; wrong GEMV results in some transposed cases); cuFFT/cuSPARSE 13.0 dropped Maxwell/Pascal/Volta. — [CUDA Toolkit Release Notes 13.4u2](https://docs.nvidia.com/cuda/cuda-toolkit-release-notes/index.html)
- Ubuntu packages: `wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb && sudo dpkg -i cuda-keyring_1.1-1_all.deb`; `apt update`; `apt install cuda-toolkit-13-4` (pinned) or `cuda-toolkit` (rolling); sub-metas `cuda-compiler-13-4`, `cuda-libraries-dev-13-4`, `cuda-tools-13-4`; driver installed separately (`nvidia-open`, `cuda-drivers`); GCC 6.x–16.x supported, Ubuntu 24.04 ships GCC 14.3. — [CUDA Installation Guide Linux 13.4](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/index.html)
- Community: PyTorch ≥ 2.7 built with CUDA 12.8 is the first with sm_120 kernels; "no kernel image is available" is the symptom of missing sm_120 cubin/PTX. — [HF sm120-field-guide](https://huggingface.co/datasets/witcheer/sm120-field-guide), [PyTorch forum](https://discuss.pytorch.org/t/request-add-cuda-sm-120-blackwell-support-for-convnextv2-fused-kernels/224904)
- "compute_120f needs CUDA 13.0 or later" and "SM100 cubins crash on SM120" (FlashInfer issue, 2025/2026). — [FlashInfer issue #2723](https://github.com/flashinfer-ai/flashinfer/issues/2723)

**sm_XX / sm_XXa / sm_XXf semantics (NVIDIA blog, 2025-05-01, CUDA 12.9)**
- Plain `sm_120`/`compute_120`: PTX runs on same-or-later CC; cubin runs on same major, same-or-higher minor. `f` suffix: "Family-specific features are guaranteed to be available in the same family of GPUs" (same major CC, equal-or-higher minor). `a` suffix: "no forward-compatibility for either PTX or a cubin". Examples: `nvcc -gencode arch=compute_100f,code=sm_100 -c kernel.cu` (`code=sm_100` and `code=sm_100f` are aliases), `nvcc -gencode arch=compute_100a,code=sm_100a`, forward-compat PTX `-gencode arch=compute_100,code=compute_100`. Macros `__CUDA_ARCH_SPECIFIC__`, `__CUDA_ARCH_FAMILY_SPECIFIC__`. sm_100f family currently = 10.0 and 10.3. — [NVIDIA blog: family-specific architecture features](https://developer.nvidia.com/blog/nvidia-blackwell-and-nvidia-cuda-12-9-introduce-family-specific-architecture-features/)
- Blog: "sm_100f code does NOT run on sm_120 devices and vice versa"; 12.x family = sm_120 (RTX 50) and sm_121. — [arnon.dk arch/gencode table](https://arnon.dk/matching-sm-architectures-arch-and-gencode-for-various-nvidia-cards/)
- NVIDIA forum answer: B200 is sm_100, RTX 5090 is sm_120; `tcgen05.ld.red` supported on neither (question-specific). — [NVIDIA forum: tcgen05.ld.red](https://forums.developer.nvidia.com/t/does-b200-5090-support-tcgen05-ld-red/363672)
- cuobjdump `-arch` accepts `sm_75` … `sm_121f` (CUDA 13.4 docs) — implying `sm_120`, `sm_120a`, `sm_120f`, `sm_121`, `sm_121f` are valid targets in 13.4. — [CUDA Binary Utilities 13.4](https://docs.nvidia.com/cuda/cuda-binary-utilities/index.html)

**Microarchitecture of consumer Blackwell (measured + whitepaper)**
- RTX Blackwell whitepaper v1.1: each SM "includes 128 CUDA Cores, one Blackwell Fourth-Generation RT Core, four Blackwell Fifth-Generation Tensor Cores, 4 Texture Units, a 256 KB Register File, and 128 KB of L1/Shared Memory"; GB202 has "384 FP64 Cores (two per SM)"; Tensor Cores add "new support for FP4 and FP6", FP4 at "double throughput of FP8". The whitepaper covers GB202/GB203/GB205 only; **GB206 is absent**. — [NVIDIA RTX Blackwell whitepaper PDF v1.1](https://images.nvidia.com/aem-dam/Solutions/geforce/blackwell/nvidia-rtx-blackwell-gpu-architecture.pdf)
- CUDA Programming Guide compute-capability tables, CC 12.x: 64K 32-bit registers per SM, 64K per block, 255 per thread; max shared memory per SM 100 KB; max per block 99 KB (opt-in via dynamic shared memory above 48 KB); unified data cache 128 KB; configurable SMEM carve-outs 0/8/16/32/64/100 KB. Feature table marks Thread Block Clusters, Distributed Shared Memory and TMA as "supported from 9.0" with no per-12.x exclusion listed; architecture-specific features require the `a` target (e.g., `compute_120a`). — [CUDA Programming Guide, Compute Capabilities (13.4)](https://docs.nvidia.com/cuda/cuda-programming-guide/05-appendices/compute-capabilities.html)
- "Dissecting the NVIDIA Blackwell Architecture with Microbenchmarks" (Jarmusch, Graddon, Chandrasekaran, U. Delaware, arXiv 2507.10789, July 2025) measured an RTX 5080 (GB203, same family as GB206): L1 128 KB/SM unified; dynamic shared max ≈ 99 KB/SM (static 48 KB); L1 hit ≈ 30–40 cycles; L2 65 MB, hit ≈ 358 cycles; global ≈ 877 cycles; register file 256 KB/SM; 4 sub-cores/SM; 2 FP64 units/SM; FP32 true latency 4 cycles. Hopper `wgmma` "not compatible with Blackwell"; `tcgen05` "yet to be supported for the arch. sm_120a"; `mma.sync` with FP4/FP6 requires the explicit `.kind::f8f6f4` qualifier; SASS mapping: FP8/FP6 → `QMMA`, FP4 with ue8m0 block scaling → `OMMA`. — [arXiv 2507.10789v2 HTML](https://arxiv.org/html/2507.10789v2)
- CUDA Binary Utilities 13.4 "Blackwell and Rubin" instruction table (CC 10.0/10.3/10.7/11.0/12.0 combined) lists new opcodes vs Hopper: `OMMA` (FP4), `QMMA` (FP8), `SPARSIFY`, `DECOMPRESS`, tensor-memory ops `LDTM`, `STTM`, `LDT`, `STT`, `UTCCP`, `UTCSHIFT`, `UTCHMMA`/`UTCIMMA`/`UTCOMMA`/`UTCQMMA`, uniform FP `UFADD`, `UFFMA`, `UF2FP`, `UI2FP`, `CREDUX`, `UREDGR`, `USTGR`, `UVIRTCOUNT`. — [CUDA Binary Utilities 13.4](https://docs.nvidia.com/cuda/cuda-binary-utilities/index.html)

**RTX 5060 Ti numbers**
- NVIDIA spec table: 4,608 CUDA cores, "759 AI TOPS" (5th-gen Tensor Cores), boost 2.57 GHz, 16 GB GDDR7, 128-bit interface, 180 W TGP, PCIe Gen 5. — [NVIDIA RTX 5060 family specs](https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5060-family/)
- Wikipedia spec table: die GB206-300, 36 SMs, 144 Tensor Cores, 36 RT cores, base 2.41 GHz, FP32 23.7 TFLOPS, FP64 0.37 TFLOPS, launched 16 April 2025, $429 (16 GB). — [Wikipedia: GeForce RTX 50 series](https://en.wikipedia.org/wiki/GeForce_RTX_50_series)

### Inferences
- 36 SM × 128 KB L1/shared = 4.5 MB aggregate L1 (matches Wikipedia's "L1 4.5 MB"); 36 SM × 256 KB = 9 MB register file. Max usable shared memory per block for your kernels on sm_120: 99 KB (must opt in with `cudaFuncSetAttribute(..., cudaFuncAttributeMaxDynamicSharedMemorySize, bytes)`).
- Memory bandwidth: 128-bit × 28 Gbps GDDR7 = 448 GB/s **[inferred: NVIDIA page does not list bandwidth or data rate; 28 Gbps is assumed from the 5090/5070 in the whitepaper]**. L2 size for GB206 **[UNVERIFIED — whitepaper omits GB206; community figure is 32 MB]**.
- FP16 tensor dense peak ≈ 94.9 TFLOPS (Wikipedia, "dense/sparse 94.9/189.8"); "759 AI TOPS" is FP4 *with sparsity* by NVIDIA's marketing convention (FP4 dense ≈ 380 TOPS) **[inference from the whitepaper's dense/sparse convention; not stated for 5060 Ti]**.
- The Binary Utilities table merges CC 10.x–12.0; the TMEM opcodes (`LDTM/STTM/UTC*`) are sm_100-family only, consistent with the Delaware paper's finding that tcgen05 is absent on sm_120a. Expect to see `HMMA`, `IMMA`, `QMMA`, `OMMA` in sm_120 SASS, never `UTCHMMA`.
- Recommended flags for your box: `-gencode arch=compute_120,code=sm_120 -gencode arch=compute_120,code=compute_120` (cubin + forward-compat PTX); use `-arch=sm_120a` only when you need architecture-specific PTX (`.kind::f8f6f4` mma, block-scaled FP4) and accept no forward compatibility; `compute_120f` requires CUDA ≥ 13.0.

### Gaps
- NVIDIA's own per-row Technical Specifications table (threads/SM, warps/SM, blocks/SM for 12.x) could not be parsed reliably from the flattened HTML — read Table 30 directly (values present are 1024/1536/2048 threads, 32/48/64 warps, 16/24/32 blocks across columns).
- NVIDIA forum thread "CUDA Toolkit 12.8 what GPU is sm_120" returned HTTP 403; sm_120a/sm_121 official definitions are therefore inferred from the 12.9 blog + cuobjdump arch list.
- No official document enumerating exactly which PTX features are *missing* on sm_120 vs sm_100 (NVIDIA points to the PTX ISA per-instruction "Target ISA Notes"); the Delaware paper is the best measured source.
- GB206 die-level specs (L2, memory clock) are absent from the whitepaper v1.1.

---

## Q5. Tooling availability on a GeForce RTX 5060 Ti (Nsight Compute, profiling permission, NVBit, CuAssembler/DocumentSASS, cuda-gdb, compute-sanitizer)

### Takeaway
Nsight Compute supports GB20x consumer Blackwell (support added in 2024.4; GB20x-specific fixes in 2025.1.1/2025.2; current version 2026.3.1); the only GeForce SKUs with *reduced* metrics are the China-market GB202 variants (5090D/5090DD/RTX 6000D), not the 5060 Ti. On Linux you must lift the performance-counter restriction (`NVreg_RestrictProfilingToAdminUsers=0` via `/etc/modprobe.d/*.conf`, or run as root); drivers R610+ move to a capabilities-based scheme. NVBit supports CC up to 12.1 (SM_120 since 1.7.4; 1.8.1 of Sep 2026 adds Blackwell fixes). CuAssembler is Pascal–Ampere only; nobody has published a working SASS assembler for sm_120 (sass-king says it is targeting SM120 but is early). cuda-gdb 13.4 works with `-g -G`.

### Cited Findings
- Nsight Compute release notes (v2026.3.1 page): Blackwell support added in 2024.4; 2025.1.1 fixed missing roofline ceilings for GB20x; 2025.2 fixed "some metrics were not listed for collection in section files for GB20x GPUs"; 2026.2 added "previously unsupported SKUs" RTX 6000D BSE (GB202-891), RTX 5090DD (GB202-240), RTX 5090D (GB202-250) with reduced metric support; 2026.3.1 added limited C2C metrics for GB20B/GB20C; Rubin support in 2026.3. — [Nsight Compute Release Notes](https://docs.nvidia.com/nsight-compute/ReleaseNotes/index.html)
- ERR_NVGPU page: profiling limited on GB202-891/240/250 until CUDA 13.3; fix = CUDA 13.3+ with R580+ driver, Nsight Compute ≥ 2026.2, Nsight Systems ≥ 2026.3; crypto-mining SKUs never supported. No other GeForce restriction listed. — [developer.nvidia.com/ERR_NVGPU](https://developer.nvidia.com/ERR_NVGPU)
- ERR_NVGPUCTRPERM page: restriction applies on "driver versions 419.17+ on Windows or 418.43+ on Linux"; permanent fix: create a `.conf` file in `/etc/modprobe.d` containing `options nvidia NVreg_RestrictProfilingToAdminUsers=0`, then (Debian/Ubuntu) `update-initramfs -u -k all` and reboot; temporary: unload modules and `modprobe nvidia NVreg_RestrictProfilingToAdminUsers=0`; "this regkey method will be removed in a future release. Drivers R610 and later use a capabilities-based system instead." — [NVIDIA ERR_NVGPUCTRPERM](https://developer.nvidia.com/nvidia-development-tools-solutions-err_nvgpuctrperm-permission-issue-performance-counters)
- Nsight Compute Profiling Guide: sampled stall metrics `smsp__pcsamp_warps_issue_stalled_<reason>` (and `_not_issued` variants; per-warp `smsp__warpidsamp_warps_issue_stalled_<reason>`); stall reasons and meanings: `long_scoreboard` (waiting on L1TEX = global/local/texture data), `short_scoreboard` (waiting on MIO = shared memory / special math), `mio_throttle` (MIO queue full: shared-mem, SFU, dynamic branch), `lg_throttle` (local/global instruction queue full), `math_pipe_throttle` (math pipe oversubscribed), `wait` (fixed-latency dependency), `barrier`, `membar`, `branch_resolving`, `dispatch_stall`, `drain`, `imc_miss`, `no_instructions` (instruction fetch/i-cache miss), `not_selected` (eligible, not chosen), `selected` (issued), `sleeping`, `tex_throttle`, plus `warpgroup_arrive`. Source page needs line info ("-lineinfo"); sections available: SpeedOfLight, MemoryWorkloadAnalysis, SchedulerStats, WarpStateStats, SourceCounters, Occupancy, LaunchStats, InstructionStats, ComputeWorkloadAnalysis; ncu locks SM clocks by default (`--clock-control none` to disable); caches flushed between replay passes (`--cache-control none`); replay modes kernel/application/range/app-range. — [Nsight Compute Profiling Guide](https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html)
- NVBit README: "SM compute capability: >= 3.5 && <= 12.1", CUDA ≥ 12.0, nvcc ≥ 10.2, GCC ≥ 8.5, Linux x86_64/aarch64; latest 1.7 "contains several breaking changes". — [NVBit README](https://raw.githubusercontent.com/NVlabs/NVBit/master/README.md)
- NVBit releases: SM_120 support added in 1.7.4; 1.8 (06 Apr [2026]) alpha TMA support for Hopper/Blackwell, Green contexts, headers updated to CUDA 13.2; 1.8.1 (29 Sep [2026]) CMake build, fixed URZ register index decoding on "Blackwell and newer" (255 instead of 63); 1.7.7.1 hotfix for `CUDA_ERROR_INVALID_SOURCE` on CUDA 13.1+. — [NVBit releases](https://github.com/NVlabs/NVBit/releases)
- CuAssembler README: supported SM60/61/70/75/80/86 ("..."), "still in its infancy"; workflow: `nvcc -cubin` → `cuasm` disassemble (uses `nvdisasm`) → edit `.cuasm` → `cuasm` assemble; needs Python 3.8+, SymPy, pyelftools; `hnvcc` hack for build substitution. No Hopper/Ada/Blackwell mention; GitHub issues list only an Ada FP8 request (#24, Apr 2024). — [CuAssembler README](https://raw.githubusercontent.com/cloudcores/CuAssembler/master/README.md), [CuAssembler issues](https://github.com/cloudcores/CuAssembler/issues)
- DocumentSASS: "an unofficial description of the CUDA SASS instruction sets" extracted from "two specific strings in nvdisasm" using an `intercept.so` on `memcpy`; pipeline `Makefile` → `example.cu` → `intercept.c` → `nvdisasm` → `strings` → `funnel.py`; tested with CUDA 11.6; last push 2025-07-18; no sm_100/sm_120 statement in README. — [DocumentSASS README](https://raw.githubusercontent.com/0xD0GF00D/DocumentSASS/main/README.md), [GitHub repo](https://github.com/0xD0GF00D/DocumentSASS)
- Commercial/academic SASS decoders covering Blackwell: JEB's SASS disassembler covers sm_70–sm_121; "EoSS: Exploring SASS" (Purdue, ASPLOS 2027) validated instruction sets Volta→Blackwell; `sass-king` project states initial focus on SM120/SM120a. — [PNF Software blog](https://pnfsoftware.com/blog/reversing-nvidia-cuda-sass-code/), [EoSS page](https://engineering.purdue.edu/tgrogers/publication/avalos-asplos-2027/), [sass-king](https://www.sourcepulse.org/projects/30169605)
- maxas (Scott Gray, Maxwell SASS assembler, ~96% SGEMM efficiency on GM204) archived read-only Jan 2023; turingas extends it to Volta/Turing. — [maxas wiki](https://github.com/NervanaSystems/maxas/wiki/Introduction), [turingas forum post](https://forums.developer.nvidia.com/t/an-open-source-sass-assembler-for-volta-and-turing-gpus/109011)
- cuda-gdb 13.4 (based on GDB 16.3 since 13.2): compile with `-g -G` ("must be passed to NVCC"), `-lineinfo` alone gives degraded stepping; commands `info cuda sms`, `info cuda warps`, `info cuda lanes`, focus `cuda kernel 0 block 1 thread 3`, `set cuda break_on_launch`, `set cuda single_stepping_optimizations`; Maxwell/Pascal/Volta deprecated in 12.8. — [cuda-gdb 13.4 docs](https://docs.nvidia.com/cuda/cuda-gdb/index.html)
- Tooling note from the REA repo the user pointed at: REA wraps `objdump` (`inspect_with_objdump`, operations `disassemble`, `symbols`, `dwarf`), Ghidra, Hopper, IDA, Rizin, GDB and Frida; nothing GPU/SASS-specific (no cuobjdump/nvdisasm integration) in the clone's docs. — local clone `/tmp/claude-0/-home-user-KERNEL/2fec5121-746d-5a8c-9207-83ad66dddd8f/scratchpad/rea_clone/rea/docs/reverse-engineering-tools.md`, [morluto/rea](https://github.com/morluto/rea)

### Inferences
- On a headless Ubuntu Server with the open kernel module, the simplest is a one-liner `echo 'options nvidia NVreg_RestrictProfilingToAdminUsers=0' | sudo tee /etc/modprobe.d/nvidia-profiling.conf && sudo update-initramfs -u -k all && sudo reboot`; alternatively run `ncu` with `sudo` and `-E PATH`. The R610+ "capabilities-based" mechanism is not yet documented on the page — expect this to change.
- Hardware counters on GeForce are the same as on RTX PRO for the SM/L1/L2 metrics; the reduced-metric list proves NVIDIA gates by SKU, and 5060 Ti is not gated.
- There is **no community SASS assembler for sm_120** today (CuAssembler stops at sm_86; sass-king early). SASS-level *editing* on Blackwell is not realistically available; SASS-level *reading* (cuobjdump/nvdisasm/ncu Source page) is fully supported. Optimization therefore happens at CUDA C++/PTX level, verified by reading SASS.
- REA can be pointed at `libggml-cuda.so` or `libcublas.so` as an ordinary ELF (host-side symbols, fatbin section `.nv_fatbin`), but decoding the embedded cubins still needs `cuobjdump -xelf` + `nvdisasm`; REA brings no SASS decoder of its own.

### Gaps
- compute-sanitizer Blackwell support was not fetched from its own release notes (it ships in `cuda-tools-13-4`; sm_120 support implied by toolkit support, **[UNVERIFIED]**).
- The capabilities-based profiling permission scheme for R610+ drivers is announced but not documented on the fetched page.
- DocumentSASS output for sm_100/sm_120 could not be confirmed without running the tool (its Makefile loops over an arch list; whether it works with CUDA 13 nvdisasm is unknown).

---

## Q6. Step-by-step workflow on RTX 5060 Ti (exact commands)

### Takeaway
A five-stage loop: (1) compile with `-lineinfo`, read SASS; (2) profile with `ncu --set full --import-source yes` and read per-SASS-line stall reasons; (3) build llama.cpp for `CMAKE_CUDA_ARCHITECTURES=120` with line info, dump SASS of `mul_mat_vec_q<GGML_TYPE_Q4_K,...>` (token generation) and `mul_mat_q<GGML_TYPE_Q4_K,...>` (prompt processing), profile them; (4) microbenchmark GB206 with PTX `%clock64` kernels and a bandwidth kernel; (5) put the same numbers next to the RX 7900 XTX. Every command below uses tool names/flags verified from the 13.4 docs; the llama.cpp kernel/function names come from current `master` sources.

### Cited Findings (what each step relies on)
- Step 1 flags/tools: `nvcc -lineinfo`, `cuobjdump -sass/-res-usage/-lelf/-xelf/-fun`, `nvdisasm -g -c -cfg -plr -lrm` (CUDA Binary Utilities 13.4). — [CUDA Binary Utilities](https://docs.nvidia.com/cuda/cuda-binary-utilities/index.html)
- Step 2: ncu sections, `--set full`, `-lineinfo` for Source page, `smsp__pcsamp_warps_issue_stalled_*`, `--clock-control`, `--cache-control`, replay modes. — [Nsight Compute Profiling Guide](https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html)
- Step 3 llama.cpp build: `-DGGML_CUDA=ON`, `-DCMAKE_CUDA_ARCHITECTURES="..."`, `-DGGML_CUDA_FORCE_MMQ` (custom quantized matmul instead of FP16 cuBLAS; less VRAM, slower at large batch), `-DGGML_CUDA_FORCE_CUBLAS`, `GGML_CUDA_FA_QUANTS`, `GGML_CUDA_ENABLE_UNIFIED_MEMORY=1`, `GGML_CUDA_MMQ_PREC` (NVFP4/MXFP4 on Blackwell use W4A8 path); HIP side: `-DGGML_HIP=ON -DGPU_TARGETS=gfx1100`. — [llama.cpp docs/build.md](https://raw.githubusercontent.com/ggml-org/llama.cpp/master/docs/build.md)
- Step 3 kernel names (mmvq.cu, current master): `__global__ mul_mat_vec_q<type, ncols_dst, has_fusion, small_k, halve_iters>` with `__launch_bounds__(calc_nwarps(...) * warp_size, 1)`; Q4_K path: `get_vec_dot_q_cuda(GGML_TYPE_Q4_K)` → `vec_dot_q4_K_q8_1`, `get_vdr_mmvq` → `VDR_Q4_K_Q8_1_MMVQ`, `blocks_per_iter = vdr * nwarps * warp_size / qi`; `calc_nwarps` for Q4_K ncols_dst=1: generic 4, Turing 2, RDNA3 1, RDNA4 8; `ggml_cuda_should_use_mmvq` batch limit for Q4_K is 5 on Blackwell/Volta, `MMVQ_MAX_BATCH_SIZE` on Ada; src1 is quantized first by `quantize_row_q8_1_cuda`; entry `ggml_cuda_mul_mat_vec_q` → `mul_mat_vec_q_switch_type` → `mul_mat_vec_q_switch_ncols_dst<GGML_TYPE_Q4_K>`; MoE variant `mul_mat_vec_q_moe`. — [llama.cpp mmvq.cu](https://raw.githubusercontent.com/ggml-org/llama.cpp/master/ggml/src/ggml-cuda/mmvq.cu)
- Step 3 kernel names (mmq.cuh, current master): `__global__ mul_mat_q<type, J, fallback, prec_src1>` with `__launch_bounds__(nthreads, occupancy)` from `ggml_cuda_mmq_get_config(...)`; `mul_mat_q_stream_k_fixup`; host picks `blackwell_mma_available(cc)` config for Blackwell else Ampere/`pascal_dp4a`; `use_mma_data_layout` true for Turing MMA (int8 `mma.sync`, `tile<16,8,int>`), otherwise dp4a; Q4_K: `ggml_cuda_mmq_load_tiles_q4_K<type,J,fallback>`, `ggml_cuda_mmq_vec_dot_q4_K_q8_1_dp4a`, MMA dot shared `ggml_cuda_mmq_vec_dot_q8_1_q8_1_mma`; constants `MMQ_TILE_NE_K=32`, `MMQ_TILE_Y_K=36`, `MMQ_ITER_K=256`, `MMQ_NWARPS=8`, `MMQ_DP4A_MAX_BATCH_SIZE=64`; shared memory via `mmq_get_nbytes_shared` and `CUDA_SET_SHARED_MEMORY_LIMIT`; stream-K grid = `nsm` blocks when tile efficiency < 90 %. — [llama.cpp mmq.cuh](https://raw.githubusercontent.com/ggml-org/llama.cpp/master/ggml/src/ggml-cuda/mmq.cuh)
- Step 4 method: PTX kernels with `%clock64`, warps/ILP sweeps, `mma.sync` with `.kind::f8f6f4`, cuBLASLt FP8 GEMM, nvidia-smi power (Delaware paper). — [arXiv 2507.10789](https://arxiv.org/html/2507.10789v2)
- Reference numbers to beat/compare (RTX 5080, same family): L2 hit ≈ 358 cycles, DRAM ≈ 877 cycles, L1 ≈ 30–40 cycles, shared max 99 KB. — [arXiv 2507.10789](https://arxiv.org/html/2507.10789v2)

### Inferences — the concrete plan (commands)
**Stage 0 — environment (Ubuntu 24.04 Server, headless)**
```bash
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb && sudo apt update
sudo apt install nvidia-open            # open kernel modules, R615 branch for CUDA 13.4 features (R580+ minimum)
sudo apt install cuda-toolkit-13-4      # nvcc, cuobjdump, nvdisasm, ncu, nsys, cuda-gdb, compute-sanitizer
echo 'options nvidia NVreg_RestrictProfilingToAdminUsers=0' | sudo tee /etc/modprobe.d/nvidia-profiling.conf
sudo update-initramfs -u -k all && sudo reboot
export PATH=/usr/local/cuda-13.4/bin:$PATH
nvidia-smi --query-gpu=name,driver_version,compute_cap --format=csv   # expect 12.0
```
**Stage 1 — first kernel, read SASS**
```bash
nvcc -O3 -lineinfo -gencode arch=compute_120,code=sm_120 -gencode arch=compute_120,code=compute_120 -o saxpy saxpy.cu
cuobjdump -res-usage saxpy                 # registers, smem, cmem per kernel
cuobjdump -sass -fun saxpy saxpy | less    # SASS with source-line comments (because of -lineinfo)
nvcc -O3 -lineinfo -arch=sm_120 -cubin -o saxpy.cubin saxpy.cu
nvdisasm -g -c -plr -lrm wide saxpy.cubin  # line info + register life ranges
nvdisasm -cfg saxpy.cubin | dot -Tsvg -o cfg.svg   # control-flow graph (graphviz)
nvcc -O3 -arch=sm_120 -ptx saxpy.cu -o saxpy.ptx   # compare PTX vs SASS
```
What to look for on sm_120 SASS: `LDG.E.128`/`STG.E.128` (vectorized global), `LDS.128` (shared), `HMMA.16816.F32` (FP16 tensor), `IMMA` (int8 dp4a-tensor path used by llama.cpp MMQ), `QMMA`/`OMMA` (FP8/FP4), `IDP4A` (dp4a), `BAR.SYNC`, `DEPBAR`, and the per-instruction control bits (stall counts/yield/barriers) that nvdisasm shows only via `-hex`/CuAssembler-style decoding.

**Stage 2 — profile and map stalls to SASS lines**
```bash
ncu --set full --import-source yes -k regex:saxpy -c 1 -o saxpy_full ./saxpy
ncu --import saxpy_full.ncu-rep --page details                     # SpeedOfLight, Occupancy, WarpStateStats...
ncu --import saxpy_full.ncu-rep --page source --print-source sass   # per-SASS-line pcsamp stall columns  [flag names: verify with ncu --help]
ncu --metrics smsp__pcsamp_warps_issue_stalled_long_scoreboard,smsp__pcsamp_warps_issue_stalled_mio_throttle,smsp__pcsamp_warps_issue_stalled_math_pipe_throttle -k regex:saxpy ./saxpy
ncu --set full --clock-control none --cache-control none -k regex:saxpy ./saxpy   # realistic clocks / warm caches
```
Reading order: SpeedOfLight (SM % vs DRAM %) → WarpStateStats (dominant stall) → Source page sorted by `stalled_long_scoreboard` (memory latency), `short_scoreboard`/`mio_throttle` (shared memory/SFU pressure), `math_pipe_throttle` (compute-bound), `not_selected`/`selected` (healthy).

**Stage 3 — llama.cpp kernels for a Q4_K_M model**
```bash
git clone https://github.com/ggml-org/llama.cpp && cd llama.cpp
cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=120 \
      -DCMAKE_CUDA_FLAGS="-lineinfo" -DCMAKE_BUILD_TYPE=Release
cmake --build build -j$(nproc)
cuobjdump -lelf build/bin/libggml-cuda.so | head           # list embedded cubins   [library file name: verify in build/bin or build/ggml/src]
cuobjdump -sass -fun mul_mat_vec_q build/bin/libggml-cuda.so | grep -E 'Function|HMMA|IMMA|IDP4A|LDG|LDS|BAR' | head -100
cuobjdump -sass build/bin/libggml-cuda.so > all.sass; grep -n 'Function : .*mul_mat_q' all.sass | head
# which kernels actually run for your model:
ncu --set full --import-source yes -k regex:mul_mat_vec_q -c 3 -o mmvq ./build/bin/llama-cli -m model-Q4_K_M.gguf -ngl 99 -n 16 -p "test"   # decode
ncu --set full --import-source yes -k regex:mul_mat_q -c 3 -o mmq  ./build/bin/llama-cli -m model-Q4_K_M.gguf -ngl 99 -n 1 -p "$(head -c 4000 somefile.txt)"   # prefill
nsys profile -o trace ./build/bin/llama-bench -m model-Q4_K_M.gguf -ngl 99 -p 512 -n 128   # timeline, kernel names/durations
```
Note for a 27B Q4_K_M model: at ~16–17 GB it does not fit 16 GB VRAM; either profile a smaller Q4_K_M model (the kernels are identical), use `-ngl` < all layers, or `GGML_CUDA_ENABLE_UNIFIED_MEMORY=1` (slow; distorts memory-bound profiles). Expect decode to be `mul_mat_vec_q<GGML_TYPE_Q4_K,1,...>` (DRAM-bandwidth bound; target is ~448 GB/s on 5060 Ti) and prefill to be `mul_mat_q<GGML_TYPE_Q4_K,J,...>` on the Turing-MMA (`IMMA`) path; `-DGGML_CUDA_FORCE_MMQ=ON` keeps cuBLAS out so everything you profile is open source.

**Stage 4 — microbenchmark GB206**
- Bandwidth: a `float4` streaming copy kernel over ≥ 1 GB, timed with cudaEvents, 5 runs; expect ≲ 448 GB/s read; compare against ncu `dram__throughput`.
- L2/L1 latency: pointer-chase kernel with `%clock64` in inline PTX, footprints 32 KB → 128 KB → 32 MB → 1 GB (the Delaware method; expect ≈30–40 / ≈358 / ≈877 cycles on this family).
- Tensor throughput: loop of `mma.sync.aligned.m16n8k16.row.col.f32.f16.f16.f32` with ILP 1–8 and 1–32 warps/SM, count FLOPs; FP8/FP4 via `mma.sync ... .kind::f8f6f4` compiled with `-arch=sm_120a`.
- Cross-check with `cublasLtMatmul` FP16 8192³ and `--set full` `sm__inst_executed_pipe_tensor` metrics.
- Keep clocks fixed: `sudo nvidia-smi -lgc <MHz>` before runs (ncu locks clocks by default anyway).

**Stage 5 — compare with RX 7900 XTX (gfx1100)**
Same llama.cpp commit, `-DGGML_HIP=ON -DGPU_TARGETS=gfx1100`, `llama-bench` with identical `-p/-n`; tokens/s per GB/s of bandwidth (960 GB/s on 7900 XTX vs ~448 GB/s on 5060 Ti) is the honest metric for decode; for prefill compare `mul_mat_q` time per token (RDNA3 WMMA vs Blackwell IMMA path). Kernel-level equivalents: `rocprofv3` / `rocprof-compute` vs `ncu`; `llvm-objdump --mcpu=gfx1100 -d` / `roc-obj` vs `cuobjdump -sass` (details in the AMD track).

### Gaps
- `ncu --page source --print-source sass` flag spelling and the exact path/name of the llama.cpp CUDA shared library were not verified against a live install (marked inline).
- Current llama.cpp `master` kernel signatures change frequently; the names above are from the 2026-10 fetch and should be re-grepped (`grep -n "__global__" ggml/src/ggml-cuda/mmvq.cu`).
- Whether the "27B" model in question fits 16 GB at Q4_K_M was not computed from an actual GGUF; the model name itself is unverified.

---

## Q7. Learning resources for SASS-level understanding (ranked)

### Takeaway
There is no official SASS manual; the best path is (1) the CUDA Binary Utilities instruction tables + Nsight Compute Profiling Guide, (2) the microbenchmark papers (Dissecting Volta/Turing/Ampere/Hopper/Blackwell), (3) GPU MODE lecture 37 "Introduction to SASS & GPU Microarchitecture", (4) siboehm's SGEMM worklog, (5) maxas/turingas/CuAssembler for how control bits and scheduling work, (6) PMPP as the textbook.

### Cited Findings
1. CUDA Binary Utilities 13.4 — the only NVIDIA instruction-set listing per architecture (opcode names and one-line meanings; no encodings/latencies). — [docs](https://docs.nvidia.com/cuda/cuda-binary-utilities/index.html)
2. Nsight Compute Profiling Guide — warp-state/stall semantics and metric names. — [docs](https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html)
3. "Dissecting the NVIDIA Blackwell Architecture with Microbenchmarks" (arXiv 2507.10789, Jul 2025; RTX 5080 vs H100; PTX `%clock64` methodology; QMMA/OMMA SASS mapping). — [arXiv](https://arxiv.org/abs/2507.10789v2); datacenter-Blackwell companion on tcgen05: [arXiv 2512.02189](https://arxiv.org/pdf/2512.02189v3)
4. GPU MODE lecture series (YouTube @GPUMODE; slides/code repo): Lecture 37 "Introduction to SASS & GPU Microarchitecture", Lecture 8 "CUDA Performance Checklist", Lecture 16 "On Hands profiling", Lecture 23 "Tensor Cores", Lecture 15/36 CUTLASS, Lecture 57 CuTe; the series recommends the PMPP textbook. — [gpu-mode/lectures README](https://raw.githubusercontent.com/gpu-mode/lectures/main/README.md)
5. Simon Boehm, "How to Optimize a CUDA Matmul Kernel for cuBLAS-like Performance: a Worklog" (Dec 2022, RTX A6000): naive → coalescing → SMEM → 1D/2D blocktiling → vectorized → autotune → warptiling, 93.7 % of cuBLAS FP32; reads PTX/SASS (`ld.shared.f32`, `LDS.128`) and uses `cuobjdump --list-text` on cuBLAS. — [siboehm.com](https://siboehm.com/articles/22/CUDA-MMM)
6. maxas wiki (Scott Gray; Maxwell SASS assembler, SGEMM ~96 % efficiency on GM204; archived Jan 2023) — the canonical explanation of control codes, register bank conflicts, dual-issue and scheduling at SASS level; turingas for Volta/Turing; CuAssembler (sm_60–sm_86) for Ampere-era control-code decoding. — [maxas Introduction](https://github.com/NervanaSystems/maxas/wiki/Introduction), [maxas SGEMM](https://github.com/NervanaSystems/maxas/wiki/SGEMM), [turingas](https://forums.developer.nvidia.com/t/an-open-source-sass-assembler-for-volta-and-turing-gpus/109011), [CuAssembler](https://raw.githubusercontent.com/cloudcores/CuAssembler/master/README.md)
7. DocumentSASS — per-arch instruction encodings & latencies pulled from nvdisasm (grey zone under EULA §1.2-1, see Q1). — [repo](https://github.com/0xD0GF00D/DocumentSASS)
8. PNF Software "Reversing Nvidia GPU's SASS code" (JEB; sm_70–sm_121 coverage) — commercial decompiler perspective. — [blog](https://pnfsoftware.com/blog/reversing-nvidia-cuda-sass-code/)
9. EoSS (Purdue, ASPLOS 2027) — systematic SASS exploration framework, Volta→Blackwell. — [page](https://engineering.purdue.edu/tgrogers/publication/avalos-asplos-2027/)
10. Modal GPU Glossary "Streaming Assembler" — short orientation on SASS vs PTX. — [glossary](https://modal.com/gpu-glossary/device-software/streaming-assembler)

### Inferences
- Ranking rationale for *this* user (headless, consumer Blackwell, llama.cpp): start with 2 + 5 (profiling-driven optimization with SASS reading), then 3 (to know what sm_120 actually has), then 4-L37 and 6 for control-code literacy; treat 7/8/9 as references, not tutorials.

### Gaps
- Books: "Programming Massively Parallel Processors" (PMPP) is referenced by GPU MODE but no edition/ISBN was verified here; "The CUDA Handbook" and NVIDIA's "CUDA C++ Best Practices Guide" were not fetched — **[UNVERIFIED as current recommendations]**.
- Older "Dissecting Volta/Turing/Ampere/Hopper" microbenchmark papers (Jia et al. 2018/2019; Luo et al. 2024) were not fetched in this research; cite from memory only with verification.
