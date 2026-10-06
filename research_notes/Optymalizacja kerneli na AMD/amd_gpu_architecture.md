# AMD GPU Hardware Architecture for LLM-Inference Kernel Optimization (RDNA2-RDNA5, Strix Halo/Point, CDNA3/4/5) — research notes, Oct 2026

Notes compiled 2026-10-06. Sources: LLVM AMDGPU docs (llvm.org/docs/AMDGPUUsage.html, live "latest" fetched 2026-10-06), ROCm docs "GPU hardware specifications" (fetched 2026-10-06; the fetch tool reported the page version as "ROCm 10.1.0", which I could not confirm and treat as uncertain), GPUOpen, Chips and Cheese, AMD product pages and press coverage. amd.com product pages returned HTTP 503 during this session, so some vendor numbers come from secondary sources and are flagged. Numbers marked "derived" are my own arithmetic from cited per-clock figures, not vendor-published values.

---

## 1. gfx target IDs and product mapping

### Takeaway
RDNA2 = gfx1030-1036; RDNA3 = gfx1100 (Navi31: 7900 XTX/XT/GRE, W7900/W7800), gfx1101 (Navi32: 7800 XT/7700 XT/7700), gfx1102 (Navi33: 7600/7600 XT); RDNA3.5 APUs = gfx1150 (Strix Point, Radeon 890M), gfx1151 (Strix Halo, Radeon 8060S), gfx1152 (Radeon 860M), gfx1153; RDNA4 = gfx1200 (9060/9060 XT), gfx1201 (9070/9070 XT/9070 GRE, AI PRO R9700); CDNA3 = gfx942 (MI300X/MI300A/MI325X); CDNA4 = gfx950 (MI350X/MI355X). As of Oct 2026 LLVM also has gfx1250/gfx1251 ("GFX12.5"), gfx1170-1172 ("RDNA 4m" APUs) and gfx1310 ("GFX13 (RDNA 5)"), all listed with product "TBA".

### Cited Findings
- LLVM processor table: gfx1030 = Radeon RX 6800 / 6800 XT / 6900 XT, PRO W6800, PRO V620. Runtimes are rocm-amdhsa, pal-amdhsa and pal-amdpal. — [LLVM AMDGPUUsage](https://llvm.org/docs/AMDGPUUsage.html)
- LLVM: gfx1100 = Radeon PRO W7900 (Dual Slot), W7800, RX 7900 XTX, 7900 XT, 7900 GRE. gfx1101 = RX 7800 XT, 7700 XT, 7700. gfx1102 = RX 7600 XT, 7600. gfx1103 = APU (product TBA in the table). All of these list target features `cumode` and `wavefrontsize64`. — [LLVM AMDGPUUsage](https://llvm.org/docs/AMDGPUUsage.html)
- LLVM, section "GCN GFX11.5 (RDNA 3.5)": gfx1150 = Radeon 890M (Strix Point), gfx1151 = Radeon 8060S (Strix Halo), gfx1152 = Radeon 860M, gfx1153/gfx1154 = TBA. All are APUs. — [LLVM AMDGPUUsage](https://llvm.org/docs/AMDGPUUsage.html)
- LLVM has a new section "GCN GFX11.7 (RDNA 4m)" with gfx1170, gfx1171 and gfx1172 (APUs, products TBA) and a `gfx11-7-generic` target. — [LLVM AMDGPUUsage](https://llvm.org/docs/AMDGPUUsage.html)
- LLVM, "GCN GFX12 (RDNA 4)": gfx1200 = RX 9060 / 9060 XT; gfx1201 = RX 9070 / 9070 XT / 9070 GRE. — [LLVM AMDGPUUsage](https://llvm.org/docs/AMDGPUUsage.html)
- ROCm spec table: Radeon AI PRO R9700 = gfx1201 (64 CUs); Ryzen AI Max+ PRO 395 / Radeon 8060S = gfx1151 (40 CUs). — [ROCm GPU hardware specs](https://rocm.docs.amd.com/en/latest/reference/gpu-arch-specs.html)
- LLVM: gfx942 = Instinct MI300X, MI300A (dGPU; features sramecc, tgsplit, xnack, kernarg preload). gfx950 is in the same family; its product column reads "TBA" in the LLVM table. — [LLVM AMDGPUUsage](https://llvm.org/docs/AMDGPUUsage.html)
- ROCm table: MI300X, MI325X and MI300A = gfx942; MI350X and MI355X = gfx950. — [ROCm GPU hardware specs](https://rocm.docs.amd.com/en/latest/reference/gpu-arch-specs.html)
- LLVM lists gfx1250-strict (dGPU), gfx1250 and gfx1251 (marked "APU"), all "TBA", with new features "Globally Accessible Scratch" and "Workgroup Clusters" plus `sramecc`. Note that they lack `wavefrontsize64` and `cumode`. Also listed: gfx1310 under "GCN GFX13 (RDNA 5)", a dGPU, TBA. — [LLVM AMDGPUUsage](https://llvm.org/docs/AMDGPUUsage.html)
- Generic targets: `gfx10-3-generic` (gfx1030-1036); `gfx11-generic` (gfx1100-1103 and 1150-1154), described as "Various codegen pessimizations are applied to work around some hazards". It notes "Not all VGPRs can be used on gfx1100, gfx1101, gfx1151" and that SALU float is unavailable on gfx1100-1103. Further generics: `gfx12-generic` (gfx1200, 1201; no restrictions), `gfx12-5-generic` (gfx1250/1251), `gfx13-generic` (gfx1310). — [LLVM AMDGPUUsage](https://llvm.org/docs/AMDGPUUsage.html)
- Press reports say GFX13 / gfx1310 in LLVM signals RDNA 5. AMD had not announced RDNA 5 gaming GPUs (reporting from Jan 2026), and launch expectations are mid-2027 to late 2027/2028 (rumor). — [Wccftech](https://wccftech.com/amd-adds-gfx13-to-llvm-confirming-early-support-for-rdna-5//amp/); [Digital Citizen](https://www.digitalcitizen.life/amd-rdna-5-radeon-gpus-may-not-arrive-until-late-2027/); [Profesional Review 2026-01-24](https://www.profesionalreview.com/2026/01/24/rdna-5-codigo-amd-lanzarse-mediados-2027/)

### Inferences
- The kernel-relevant consumer split is gfx1100/1101/1151 (1536 VGPRs per SIMD, so "not all VGPRs usable" under the generic target) versus gfx1102/1150/1152 (smaller register file). See section 2.
- gfx1250/1251 lack `wavefrontsize64` and add "Workgroup Clusters", Tensor DMA intrinsics (section 5) and a 512×4-byte LDS granule. This strongly suggests gfx1250 is AMD's next datacenter part (wave32-only, cluster-capable; widely assumed to be MI400/MI450-class, CDNA "5" / GFX12.5). AMD documentation does not confirm that mapping; LLVM says only "TBA".
- Products in the LLVM table: gfx1100/1101/1102 list "pal-amdpal" in the runtime column. ROCm support for them is documented separately in the ROCm compatibility matrix, which I did not check here.

### Gaps
- No official product name tied to gfx1250/gfx1251/gfx1170-1172/gfx1310 as of Oct 2026.
- RDNA2 lower SKUs (gfx1031 = 6700 XT, gfx1032 = 6600-class) are only partly listed. The ROCm spec table did not include RX 6000 rows in the fetched version.

---

## 2. Compute unit structure: SIMD width, wave32/wave64, dual-issue, registers, occupancy

### Takeaway
RDNA (gfx10/11/12) uses WGPs of 2 CUs. Each CU has 2 SIMD32s, so a WGP has 4 SIMD32s. Native wave32 is the default and wave64 is optional. RDNA3/3.5/4 add VOPD dual issue (wave32) or single-cycle wave64 execution of some ops on the doubled ALUs. CDNA (gfx942/950) is wave64 only, with 4 SIMD16s per CU running 64-wide waves over 4 cycles, 512 VGPRs per lane and a separate AccVGPR file for MFMA. Register file per SIMD: RDNA3 Navi31/32, Strix Halo and RDNA4 have 192 KB (1536 VGPRs × 32 lanes × 4 B); Navi33 has 128 KB.

### Cited Findings
- ROCm spec table, RDNA3/4 rows: "Wavefront size: 32 or 64". The VGPR file is 768 KiB for gfx1100/1101/1151/1200/1201 and 512 KiB for gfx1102 (RX 7600). SGPR file 32 KiB. LDS 128 KiB. — [ROCm GPU hardware specs](https://rocm.docs.amd.com/en/latest/reference/gpu-arch-specs.html)
- ROCm spec table, CDNA rows (MI300X/MI325X/MI300A/MI350X/MI355X): wavefront 64, VGPR file 512 KiB, SGPR file 12.5 KiB. LDS is 64 KiB on gfx942 and 160 KiB on gfx950. — [ROCm GPU hardware specs](https://rocm.docs.amd.com/en/latest/reference/gpu-arch-specs.html)
- LLVM `wavefrontsize64` feature: "When disabled native wavefront size 32 is used, when enabled wavefront size 64 is used." — [LLVM AMDGPUUsage](https://llvm.org/docs/AMDGPUUsage.html)
- LLVM `cumode` feature: "When disabled native WGP wavefront execution mode is used, when enabled CU wavefront execution mode is used." In WGP mode the waves of a work-group run on the SIMDs of both CUs of the WGP, and the WGP has a single LDS shared by them. LLVM adds: "TODO: Currently the compiler does not support WGP mode on gfx12+", so on RDNA4 "workgroup" scope maps to CU scope. — [LLVM AMDGPUUsage](https://llvm.org/docs/AMDGPUUsage.html)
- LLVM DWARF register mapping: "VGPR0-VGPR511 … when executing in wavefront 32 mode" (register-number space, gfx10+). — [LLVM AMDGPUUsage](https://llvm.org/docs/AMDGPUUsage.html)
- LLVM: "Not all VGPRs can be used on gfx1100, gfx1101, gfx1151" when compiling for gfx11-generic. These are the parts with the larger register file. — [LLVM AMDGPUUsage](https://llvm.org/docs/AMDGPUUsage.html)
- Dynamic VGPRs: GFX120* has `ENABLE_DYNAMIC_VGPR` (COMPUTE_PGM_RSRC2.DYNAMIC_VGPR) and the attribute "amdgpu-dynamic-vgpr-block-size" (0 = disabled by default). GFX125* has a dynamic VGPR mode in which "each wave allocates one VGPR chunk". — [LLVM AMDGPUUsage](https://llvm.org/docs/AMDGPUUsage.html)
- VOPD dual issue (RDNA3/3.5): a pair of independent VALU ops is encoded into one instruction. Dual issue is needed only in wave32, because wave64 naturally uses the second ALU. Peak per CU per cycle: FP32 FMA is 128 FLOPs single-issue and 256 with VOPD; packed FP16 is 256 and 512; FP64 is 4 FLOPs/CU/cycle (1/32 rate). — [ROCm Compute Profiler 3.9.0, RDNA speed-of-light](https://rocm.docs.amd.com/projects/rocprofiler-compute/en/latest/conceptual/rdna/system-speed-of-light.html)
- Chips and Cheese (2023): OpenCL code first missed full RDNA3 FP32 throughput because the compiler packed too few VOPD pairs. Forcing wave64 let the code use dual issue. — [Chips and Cheese, Microbenchmarking RDNA 3](https://old.chipsandcheese.com/2023/01/07/microbenchmarking-amds-rdna-3-graphics-architecture/) (via search summary)
- RX 7900 XTX: 96 CUs, "up to 61 TFLOPS" FP32 (a dual-issue figure). — [AnandTech](https://www.anandtech.com/show/17638) / [Wikipedia RDNA 3](https://en.wikipedia.org/wiki/RDNA_3) (via search summary)
- MI355X: 256 CUs (32 per XCD × 8 XCDs), 64 stream processors per CU, 4 matrix cores per CU, 2.4 GHz peak. — [glennklockwood.com MI355X (citing AMD brochure)](https://glennklockwood.com/garden/processors/MI355X)

### Inferences
- The register-file arithmetic is derived and consistent with ROCm. On RDNA3 Navi31/32 and RDNA4, 768 KiB per WGP / 4 SIMDs = 192 KiB per SIMD = 1536 VGPRs × 32 lanes × 4 B. On RX 7600 it is 512 KiB / 4 = 128 KiB = 1024 VGPRs. On CDNA3/4, 512 KiB per CU / 4 SIMDs = 128 KiB per SIMD = 512 regs × 64 lanes × 4 B. In wave64 that is the unified 512-entry ArchVGPR+AccVGPR budget. The ROCm table appears to quote RDNA register file and LDS per WGP and CDNA per CU.
- RDNA occupancy rule (derived): waves/SIMD ≈ min(16, floor(VGPRs_per_SIMD / VGPRs_per_wave)) for wave32. A wave can address at most 256 arch VGPRs. With 1536 VGPRs you can keep 6 wave32 waves at 256 VGPRs, 12 at 128, and 16 at 96 or fewer. On RX 7600 / gfx1150-class (1024 VGPRs) halve the high-register cases. Allocation granularity was not verified (see Gaps).
- CDNA occupancy (derived): up to 8 waves/SIMD on gfx942/950 (512 regs / 64 = 8 at 64 VGPRs+AGPRs). An MFMA-heavy GEMM using 256 regs gets 2 waves/SIMD.
- For memory-bound decode (GEMV), wave32 on RDNA lets one SIMD keep more independent waves in flight per KB of registers. For VALU-bound code, wave64 on RDNA3+ gets "free" dual-issue without relying on compiler VOPD pairing.
- On RDNA, WGP mode (the default, cumode off) lets one workgroup use the full 128 KB LDS and all 4 SIMDs. CU mode restricts a workgroup to one CU (2 SIMDs), but can improve L0 locality because each CU has its own L0.

### Gaps
- Exact VGPR allocation granularity per target (e.g. 8/16/24 VGPR blocks for wave32 on gfx11/12) and max waves/SIMD (16 on RDNA3? 8 on CDNA3?) were not confirmed from a primary source in this session. Use the ISA guide or LLVM `AMDGPUBaseInfo` for exact values.
- Strix Point gfx1150 register file size: not in the fetched ROCm table.
- RDNA4 VOPD changes, and whether RDNA4 retains wave64 single-cycle FP32: not verified.

---

## 3. Memory hierarchy, VRAM bandwidth and APU unified memory

### Takeaway
RDNA: per-CU L0 (vector), per-shader-array L1 (GL1, 256 KB on Strix Halo), GPU-wide L2 (2-8 MB), then Infinity Cache/MALL (32-96 MB) in front of GDDR6/LPDDR5X. LDS is 128 KB per WGP (≤64 KB per workgroup on GFX7-GFX12 by allocation encoding; see below). CDNA3: 64 KB LDS/CU, 4 MB L2 per XCD (32 MB total), 256 MB Infinity Cache. CDNA4 (gfx950) raises LDS to 160 KB/CU. GFX12.5 (gfx1250) has a configurable LDS/vector-cache split of up to 384 KB of LDS. Decode bandwidth: 7900 XTX 960 GB/s, 9070 XT 640 GB/s, Strix Halo 256 GB/s theoretical (~212 GB/s measured), MI300X 5.3 TB/s, MI325X 6 TB/s, MI355X 8 TB/s, MI450-class 19.6 TB/s (announced).

### Cited Findings
- ROCm table (LDS, Infinity Cache, L2): 7900 XTX 128 KiB, 96 MiB, 6 MiB. 7900 XT 128, 80, 6. 7900 GRE 128, 64, 6. 7800 XT 128, 64, 4. 7700 XT 128, 48, 4. RX 7600 128, 32, 2. 9070 XT/9070/R9700 128, 64, 8. 9060 XT 128, 32, 4. Ryzen AI Max+ 395 (8060S) 128 KiB LDS and 2 MiB L2. MI300X/MI325X 64 KiB LDS, 256 MiB IC, 32 MiB L2. MI300A 64 KiB, 256 MiB, 24 MiB. MI350X/MI355X 160 KiB, 256 MiB, 32 MiB. — [ROCm GPU hardware specs](https://rocm.docs.amd.com/en/latest/reference/gpu-arch-specs.html)
- LDS allocation granularity (COMPUTE_PGM_RSRC2.LDS_SIZE): GFX7-GFX12 roundup(lds/(128×4)), i.e. 512 B granules. GFX950 uses roundup(lds/(320×4)), i.e. 1280 B granules. GFX125* uses 512×4 = 2048 B and GFX13 uses 256×4 = 1024 B. — [LLVM AMDGPUUsage](https://llvm.org/docs/AMDGPUUsage.html)
- GFX125* has a "Desired LDS/VC split of TCP" setting. Options run from LDS=0/VC=448kB through LDS=64kB/VC=384kB, LDS=128kB/VC=320kB, 192/256, 256/192 and 320/128, up to LDS=384kB/VC=64kB. The LDS and vector L0 cache share a 448 KB pool. — [LLVM AMDGPUUsage](https://llvm.org/docs/AMDGPUUsage.html)
- RDNA cache line and request sizes: GL0 (TCP) 128-byte cacheline per cycle per CU; GL1 128-byte request/cycle/instance; GL2 128-byte request/cycle/bank; scalar cache 64-byte requests. — [ROCm Compute Profiler RDNA SoL](https://rocm.docs.amd.com/projects/rocprofiler-compute/en/latest/conceptual/rdna/system-speed-of-light.html)
- LLVM memory model (gfx10-12): vector and scalar L0 caches are per CU/WGP and not coherent with each other. They sit in front of an L1 shared by all WGPs on a shader array. In WGP mode on gfx12 a `global_inv scope:SCOPE_SE` is needed for some acquire cases. — [LLVM AMDGPUUsage](https://llvm.org/docs/AMDGPUUsage.html)
- RX 9070 XT: 64 CUs, 16 GB GDDR6 at 20 Gbps on a 256-bit bus = 640 GB/s, 64 MB Infinity Cache (3rd gen), 304 W TBP. — [Club386](https://www.club386.com/amd-confirms-radeon-rx-9070-series-specs-and-304w-tbp); [Jon Peddie](https://www.jonpeddie.com/news/amd-introduces-the-rx-9070-xt-and-rx-9070/)
- RX 7900 XTX: 960 GB/s (task brief; consistent with 24 GB GDDR6 at 20 Gbps on a 384-bit bus). — [AnandTech](https://www.anandtech.com/show/17638) (bandwidth not re-verified in this session because amd.com returned 503)
- Strix Halo GPU: two shader arrays, each with 256 KB L1, a 2 MB L2 for the GPU, and a 32 MB memory-side cache (Infinity Cache/MALL) as last-level cache. Memory is 256-bit LPDDR5X-8000. A Vulkan test gets "just under 1 TB/s" from Infinity Cache. The GPU has a 512 B/cycle path to the fabric through 8 × 64 B/cycle endpoints. Infinity Cache and DRAM latency are slightly higher than on discrete RDNA. — [Chips and Cheese, Strix Halo memory subsystem](https://chipsandcheese.com/p/strix-halos-memory-subsystem-tackling); [Chips and Cheese, Infinity Cache in Strix Halo](https://chipsandcheese.com/p/evaluating-the-infinity-cache-in)
- Strix Halo measured DRAM bandwidth is about 212-213 GB/s (Vulkan/ROCm bandwidth tests). The CPU side gets roughly half the GPU's bandwidth, so llama.cpp users offload all layers (`-ngl 99/999`). This is community data. — [Running LLMs on Strix Halo (blog)](https://tiny.write.as/kallyaleksiev/running-llms-on-strix-halo); [NixOS discourse](https://discourse.nixos.org/t/how-to-llama-on-amd-strix-halo/74363)
- AMD ROCm "RDNA3.5 system optimization" (Strix Halo): memory is UMA through GPUVM and is mapped, not physically partitioned. GART is the kernel-accessible mapping and GTT the user-process pool, defaulting to about 50% of system RAM. AMD recommends the minimum BIOS dedicated VRAM (e.g. 0.5 GB) and GTT-backed allocations: "AI frameworks work more efficiently with GTT-backed allocations". Configure TTM via `/sys/module/ttm/parameters/pages_limit` (in 4 KiB pages) using `amd-ttm` from amd-debug-tools (`amd-ttm --set <GB>`, `amd-ttm --clear`, reboot required). Kernel requirements for gfx1151: Ubuntu 24.04 HWE `6.17.0-19.19~24.04.2`+, OEM `6.14.0-1018`+, other distros Linux `6.18.4`+. — [ROCm docs: RDNA3.5 / Strix Halo system optimization](https://rocm.docs.amd.com/en/latest/how-to/system-optimization/strixhalo.html)
- The ROCm docs (7.2.x) also say `amdgpu.gttsize` "is deprecated and may not work anymore". Configure `ttm.pages_limit` and `ttm.page_pool_size` instead; the example value 27648000 pages × 4 KiB ≈ 105.5 GiB. — [ROCm docs 7.2.0 Strix Halo](https://rocm.docs.amd.com/en/docs-7.2.0/how-to/system-optimization/strixhalo.html) (via search summary)
- Community reports: about 112 GB exposed as GTT on 128 GB Strix Halo, and use of `amdgpu.gttsize=122880` (120 GiB). Some users found ROCm limited to half of memory until TTM limits were raised. — [Framework community](https://community.frame.work/t/igpu-vram-how-much-can-be-assigned/73081); [Level1Techs](https://forum.level1techs.com/t/rocm-can-only-use-half-of-the-unified-memory-on-my-strix-halo/253152)
- MI300X: 192 GB HBM3 at 5.3 TB/s. MI325X: 256 GB HBM3E at 6 TB/s, same compute as MI300X. — [glennklockwood MI325X](https://glennklockwood.com/garden/processors/MI325X); [The Register](https://www.theregister.com/2024/06/03/amd_reveals_refreshed_mi325x_with/)
- MI355X: 288 GB HBM3E at 8 TB/s; Infinity Fabric 7 × 153.6 GB/s; PCIe Gen5 x16; 1400 W. — [glennklockwood MI355X](https://glennklockwood.com/garden/processors/MI355X); [AMD MI355X brochure](https://www.amd.com/content/dam/amd/en/documents/instinct-tech-docs/product-briefs/amd-instinct-mi355x-gpu-brochure.pdf)
- MI400 series (CDNA 5, 2 nm): 432 GB HBM4 at 19.6 TB/s, 300 GB/s scale-out link, production shipments in 2H 2026. These are secondary press reports; amd.com returned 503. — [Guru3D](https://www.guru3d.com/story/amd-instinct-mi400-launches-in-2026-with-cdna-5-architecture); [TweakTown](https://www.tweaktown.com/news/108825/amds-confirms-instinct-mi400-series-ai-gpus-drop-in-2026-next-gen-instinct-mi500-in-2027/)

### Inferences
- Theoretical Strix Halo bandwidth (derived): 8000 MT/s × 256 bit / 8 = 256 GB/s, so about 212 GB/s measured is roughly 83%. For a memory-bound decode of a Q4 70B model (about 40 GB of weights), the upper bound is about 5 tok/s.
- Decode roofline intuition: bytes per token ≈ weight bytes (plus KV). Infinity Cache (64-96 MB on dGPUs) helps only for small working sets (KV of short contexts, activations, small models). LLM weights stream from DRAM.
- RDNA3/4 have 128 KB of LDS per WGP. If the per-workgroup cap is 64 KB (my understanding of HIP's `sharedMemPerBlock`, not verified here), two 64 KB workgroups can co-reside per WGP. The 9-bit LDS_SIZE field × 512 B granule could encode up to ~256 KB, so the encoding is not what sets the cap. See Gaps.
- CDNA4's 160 KB LDS (2.5× CDNA3) is the main enabler for larger FlashAttention / GEMM tiles on MI355X compared with MI300X.

### Gaps
- Exact per-workgroup LDS maximum on RDNA3/4 under HIP (64 KB vs 128 KB in WGP mode) was not confirmed from a primary source here.
- Vendor bandwidth for 7900 XTX (960 GB/s), 9060 XT (likely 320 GB/s, 128-bit) and Strix Point (128-bit LPDDR5X, about 120 GB/s): amd.com was unavailable, so these are not re-verified.
- MI300X L2 per XCD (4 MB) is implied by 32 MiB / 8 XCDs; not separately sourced.
- LDS bank count and bank-conflict rules (RDNA: 64 banks × 4 B in WGP mode? CDNA: 32 banks) were not found in a fetched primary source.

---

## 4. Matrix acceleration (WMMA / SWMMAC / MFMA), datatypes and peak throughput

### Takeaway
RDNA3/3.5 WMMA is a 16×16×16 wave-wide op (FP16/BF16/IU8/IU4 inputs) at 512 FLOPs/CU/clk for FP16/BF16/INT8 and 1024 for INT4. That is the same rate as dual-issued packed-FP16 VALU, because WMMA runs on the SIMD's own ALUs rather than a separate tensor core. Inputs must be duplicated across lane halves. RDNA4 doubles FP16/BF16 and quadruples INT8/INT4 per CU, adds FP8 E4M3 and BF8 E5M2 at the INT8 rate, adds 4:2 structured-sparse SWMMAC, and drops the input duplication. CDNA3/4 MFMA is a dedicated matrix-core path: MI300X 1307 TFLOPS FP16 and 2615 FP8 (dense); MI355X about 2.5 PF FP16, 5 PF FP8 and 10 PF MXFP4/MXFP6 (dense). Sources conflict on the dense vs sparse labels.

### Cited Findings
- GPUOpen "How to accelerate AI applications on RDNA 3 using WMMA" (published 2023-01-10, updated 2024-02-06):
  - WMMA is a cooperative 16×16×16 D = A×B + C across a wave32 or wave64.
  - A/B types: FP16, BF16, IU8, IU4. C/D types: FP32, FP16, BF16, I32.
  - Throughput per CU per clock on the 7900 XTX: FP16 512, BF16 512, IU8 512, IU4 1024 FLOPs/OPs.
  - A/B take 8 VGPRs per lane in either wave size, packed. Data must be replicated: in wave32, lanes 0-15 are duplicated into lanes 16-31.
  - C/D take 8 VGPRs (wave32) or 4 (wave64) and are unpacked. 16-bit outputs use OPSEL to pick the upper or lower half.
  - A is column-major; B, C and D are row-major.
  - Intrinsics follow `__builtin_amdgcn_wmma_<CD>_16x16x16_<AB>_w32|w64`, 12 variants.
  — [GPUOpen WMMA on RDNA 3](https://gpuopen.com/learn/wmma_on_rdna3/)
- Chips and Cheese: "RDNA 3's WMMA instructions provide the same theoretical throughput as using dot product instructions". RDNA4 adds FP8 instructions and SWMMAC (sparse). A 16×16×32 SWMMAC multiplies a 2:4-compressed sparse operand by a dense one, with a possible 2× gain (author's interpretation). RDNA4 also adds 8- and 16-bit scalar loads, splits s_waitcnt counters into finer categories, and introduces 4-bit cache-policy bits replacing GLC/SLC/DLC. — [Chips and Cheese, RDNA 4 changes in LLVM (2024-01-29)](https://chipsandcheese.com/p/examining-amds-rdna-4-changes-in-llvm)
- RDNA4 per-CU throughput vs RDNA3: FP16/BF16 doubled and INT8/INT4 quadrupled. FP8 (E4M3) and BF8 (E5M2) run at the INT8 rate, and 4:2 sparsity is supported. — [Chips and Cheese RDNA 4 coverage, via search summary](https://chipsandcheese.com/p/examining-amds-rdna-4-changes-in-llvm); [hwbusters RDNA 4 architecture](https://hwbusters.com/gpu/asrock-radeon-rx-9070-steel-legend-performance-power-analysis-noise-output/3/)
- GPUOpen "WMMA guide for AMD RDNA 4 GPUs", parts 1 and 2 (dated 2026-06-02 per fetch):
  - The intrinsics are `__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12` and `__builtin_amdgcn_wmma_i32_16x16x16_iu8_w32_gfx12`.
  - A and B are K-major, with each thread holding 8 contiguous elements. That allows 128-bit loads for FP16 and leaves no lane duplication. D is M-major. FP16, INT8 and INT4 all use this unified layout.
  - For FP8/INT8, the guide fuses two WMMAs into a 16×16×32 "double-K" op so 128-bit loads stay saturated.
  — [GPUOpen RDNA 4 WMMA part 1](https://gpuopen.com/learn/wmma-guide-amd-rdna-4-gpus-part-1/); [part 2](https://gpuopen.com/learn/wmma-guide-amd-rdna-4-gpus-part-2/)
- RX 9070 XT: 128 "AI accelerators" (2 per CU). "Peak Half Precision Throughput up to 97.3 TFLOPS". "Peak INT4 AI TOPS up to 1557 TOPS w/ sparsity". — [Club386](https://www.club386.com/amd-confirms-radeon-rx-9070-series-specs-and-304w-tbp); [Guru3D 9070 XT review](https://www.guru3d.com/review/sapphire-nitro-radeon-rx-9070-xt-review/) (via search summary)
- MI300X: 1307.4 TFLOPS peak FP16 and 2614.9 TFLOPS peak FP8 (dense; sparsity doubles both). MI325X has the same compute. — [AMD MI300 page via search](https://amd.com/en/products/accelerators/instinct/mi300.html); [glennklockwood MI325X](https://glennklockwood.com/garden/processors/MI325X)
- MI355X (from the AMD brochure as summarized): 2.4 GHz, 256 CUs, 1024 matrix cores, 2:4 structured sparsity. Figures: FP64 78.6 TF, FP32 157.3 TF, FP16/BF16 5,033 TF, FP8/INT8 10,066 TF, FP6/FP4 20,133 TF. Glenn Lockwood labels these "dense". — [glennklockwood MI355X](https://glennklockwood.com/garden/processors/MI355X). In contrast, an AMD-brochure search snippet gives "MXFP4 10.1 PF, MXFP6 10.1 PF, FP16 5 PF, FP8 10.1 PF". — [AMD MI355X brochure](https://www.amd.com/content/dam/amd/en/documents/instinct-tech-docs/product-briefs/amd-instinct-mi355x-gpu-brochure.pdf). **Conflict**: the most likely reading is dense FP16 ≈ 2.5 PF, FP8 ≈ 5 PF, MXFP4/6 ≈ 10 PF, with the higher figures being sparse (see Inferences).
- MI450/MI400 series (CDNA 5): 40 PF FP4 and 20 PF FP8, about 2× MI350. MI455X is the training/inference part; MI430X is the HPC variant. These are press reports. — [Guru3D](https://www.guru3d.com/story/amd-instinct-mi400-launches-in-2026-with-cdna-5-architecture); [Digital Citizen](https://www.digitalcitizen.life/amd-starts-sampling-mi450-ai-gpus-as-inference-demand-grows/)

### Inferences
- Derived from per-CU/clk × CUs × clock:
  - RX 7900 XTX: 512 × 96 × ~2.5 GHz ≈ 123 TFLOPS FP16/BF16 WMMA and the same for INT8 (≈123 TOPS). INT4 ≈ 246 TOPS. WMMA FP16 equals the dual-issue packed-FP16 VALU peak, so WMMA mainly saves issue slots and registers rather than adding compute.
  - RX 9070 XT: the published 97.3 TFLOPS "half precision" = 64 × 2.97 GHz × 512, the VALU dual-issue rate. The 1557 INT4 sparse TOPS implies 8192 sparse (4096 dense) INT4 ops/CU/clk. With INT8/FP8 at half of INT4 and FP16 at half of INT8, that gives dense ≈ 195 TFLOPS FP16/BF16 WMMA and ≈ 389 TOPS/TFLOPS INT8/FP8 (≈ 779 sparse). This matches "2× FP16, 4× INT8 vs RDNA3 per CU". Treat these as derived, not vendor-stated.
  - MI355X: 256 × 2.4 GHz × 4096 = 2.52 PF FP16, i.e. dense FP16 ≈ 2.5 PF (CDNA4 doubled per-CU FP16 vs CDNA3, where 1307 / (304 × 2.1 GHz) ≈ 2048). The 5,033 TF figure is therefore the sparse number, and dense FP8 ≈ 5 PF, MXFP4/6 ≈ 10 PF.
- For LLM prefill on RDNA3 the practical ceiling is about 123 TFLOPS FP16 on the 7900 XTX, with no FP8 hardware. On RDNA4, FP8 WMMA (≈389 dense on the 9070 XT) makes FP8 GEMMs worthwhile. INT8 dot/WMMA paths are the main route for quantized prefill on RDNA3.
- Because RDNA3 A/B must be duplicated across half-waves, each lane loads 16 elements for a 16×16 tile. LDS→VGPR traffic is effectively doubled, so RDNA3 WMMA kernels are often LDS-bandwidth- or register-bound. RDNA4 removes that.

### Gaps
- No primary AMD table for RDNA4 per-CU WMMA rates. In particular: whether there is INT4 WMMA dense at 4096/CU/clk, which shapes exist beyond 16×16×16 (e.g. 16×16×32 for FP8/IU4 in the gfx12 ISA), and the exact FP8 conversion instructions.
- CDNA3/CDNA4 MFMA instruction shapes and latencies (e.g. v_mfma_f32_32x32x8_f16, v_mfma_f32_16x16x32_f8, CDNA4 v_mfma_scale_f32_*_f8f6f4) were not fetched this session. Use the AMD Matrix Instruction Calculator (github.com/ROCm/amd_matrix_instruction_calculator) and the CDNA3/CDNA4 ISA PDFs.
- RDNA3.5 (gfx1150/1151) WMMA rate is presumably the same as RDNA3 per CU (40 CUs × 512 × ~2.9 GHz ≈ 59 TFLOPS FP16 for the 8060S, derived). This is not confirmed by AMD.
- Official MI355X / MI300X amd.com spec pages returned 503, so the dense/sparse labeling conflict could not be resolved from the vendor page.

---

## 5. Instruction-level features: dot products, packed math, cross-lane ops, buffer/async loads, scalar unit

### Takeaway
All RDNA2+ consumer targets have packed FP16 (v_pk_*) and dot instructions (v_dot2_f32_f16, v_dot4 and v_dot8 integer). These are the workhorses of quantized GEMV (decode) kernels. Cross-lane work uses DPP, ds_swizzle, ds_bpermute/permute and, on RDNA, v_permlane16/permlanex16. Direct global→LDS DMA ("load to LDS") exists on CDNA (gfx9xx) and is documented in LLVM. Fully asynchronous load/store-to-LDS, cluster loads and a tensor-descriptor DMA (TDM, NVIDIA-TMA-like) appear with GFX12.5 (gfx1250).

### Cited Findings
- LLVM lists dot instructions such as `v_dot8_u32_u4` and `v_dot2_f32_f16` as target-dependent; for example, some are unavailable on gfx1013. — [LLVM AMDGPUUsage](https://llvm.org/docs/AMDGPUUsage.html)
- LLVM gfx11-generic restriction: "SGPRs are not supported for src1 in dpp instructions for gfx1100-1103". "SALU floating point instructions are not available on gfx1100-1103", which implies SALU float exists on gfx1150+ (RDNA3.5) and gfx12. — [LLVM AMDGPUUsage](https://llvm.org/docs/AMDGPUUsage.html)
- LLVM DMA intrinsics "transfer data between global memory and LDS without occupying registers":
  - `llvm.amdgcn.load[.async].to.lds`
  - `llvm.amdgcn.global.load[.async].lds`
  - `llvm.amdgcn.{raw|struct}[.ptr].buffer.load[.async].lds`
  - `llvm.amdgcn.{global|cluster}.load.async.to.lds.b{8,32,64,128}`
  - `llvm.amdgcn.global.store.async.from.lds.b{8,32,64,128}`
  Tensor intrinsics `llvm.amdgcn.tensor.{load.to|store.from}.lds` use a tensor descriptor and "are asynchronous". `ds_atomic_async_barrier_arrive_b64` is an async barrier. Cluster IDs (`llvm.amdgcn.cluster.id.*`, "amdgpu-cluster-dims") apply only to targets with cluster support. — [LLVM AMDGPUUsage](https://llvm.org/docs/AMDGPUUsage.html)
- LLVM: buffer resources and "the cache swizzle support introduced in gfx942". On gfx1250 the buffer base pointer is truncated to 57 bits. — [LLVM AMDGPUUsage](https://llvm.org/docs/AMDGPUUsage.html)
- LLVM metadata `amdgpu.last.use` sets the TH_LOAD_LU temporal hint, and the nontemporal hint is TH_LOAD_NT (GFX12-style cache-policy bits). — [LLVM AMDGPUUsage](https://llvm.org/docs/AMDGPUUsage.html)
- RDNA4: 8/16-bit scalar loads, split s_waitcnt counters (separate load/store/sample/bvh/km counters) and 4-bit cache policy (TH/scope). — [Chips and Cheese, RDNA 4 in LLVM](https://chipsandcheese.com/p/examining-amds-rdna-4-changes-in-llvm)
- Kernarg preload is a gfx942/gfx950 feature, and both are "Architected flat scratch" targets. — [LLVM AMDGPUUsage](https://llvm.org/docs/AMDGPUUsage.html)

### Inferences
- For Q4/Q8 GEMV decode on RDNA, the typical inner loop is a buffer/global 128-bit load, then an unpack with v_and/v_lshr/v_perm, then v_dot4_i32_iu8 or v_dot2_f32_f16, then a wave reduction using DPP row_shr/row_bcast or permlanex16 plus ds_swizzle. Using wave32 halves the reduction depth compared with wave64.
- Exactly which DMA intrinsics lower on which targets was not tabulated in the fetched text. My understanding (unverified this session) is that `global_load_lds` / buffer-load-LDS is available on gfx9 (CDNA3; CDNA4 widens to dwordx3/x4), not on RDNA3/RDNA4, while the `.async` and tensor forms are gfx1250+.

### Gaps
- RDNA3/RDNA4 ISA availability of `v_dot4_i32_iu8`, `v_dot8_i32_iu4` and `v_dot2_f32_bf16`, plus DPP8/DPP16 limits and `v_permlane16_var` (gfx12), were not confirmed against ISA PDFs this session.
- LDS transpose loads (gfx950 `ds_read_b64_tr_b16`, gfx12 `global_load_tr`) are not verified here.

---

## 6. Key differences vs NVIDIA for kernel porting

### Takeaway
Wave size is 32 on RDNA (64 optional) but always 64 on CDNA, so `warpSize` must not be hard-coded. MI300/MI355 "shared memory" is only 64/160 KB per CU, with no async-copy / TMA equivalent until GFX12.5 (CDNA has synchronous global→LDS DMA only). RDNA3 WMMA is not an independent tensor core. Infinity Cache is a memory-side cache and does not behave like L2 for coherence. On APUs there is no PCIe copy, but GTT limits apply.

### Cited Findings
- CDNA wavefront is 64; RDNA is "32 or 64". — [ROCm GPU hardware specs](https://rocm.docs.amd.com/en/latest/reference/gpu-arch-specs.html)
- RDNA3 WMMA throughput equals dot-product/VALU throughput, so it is not an independent unit. — [Chips and Cheese](https://chipsandcheese.com/p/examining-amds-rdna-4-changes-in-llvm); [GPUOpen](https://gpuopen.com/learn/wmma_on_rdna3/)
- Async/TMA-like tensor DMA and workgroup clusters (the analogues of Hopper's cp.async.bulk/TMA and thread-block clusters) appear in LLVM for GFX12.5 targets. — [LLVM AMDGPUUsage](https://llvm.org/docs/AMDGPUUsage.html)
- Split counters and cache scopes (SCOPE_CU/SE/DEV/SYS) on GFX12; non-coherent L0 vector and scalar caches. — [LLVM AMDGPUUsage](https://llvm.org/docs/AMDGPUUsage.html)

### Inferences
- CUDA kernels that assume 48-228 KB of smem per SM need retiling for MI300X (64 KB). MI355X (160 KB) is closer to Ampere/Hopper.
- On RDNA consumer cards, half-wave (16-lane) DPP row semantics differ from CUDA `__shfl_xor` costs. Shuffles across rows of 16 need permlanex16 or ds_bpermute, which goes through LDS hardware.
- On MI300X the 8 XCDs each have their own L2. Workgroup-to-XCD round-robin dispatch means tile scheduling must be XCD-aware for L2 reuse; hipBLASLt and Triton use this remapping. This is background knowledge and not re-sourced this session.

### Gaps
- No primary source fetched on LDS bank-conflict rules (bank count and width per arch) or on how ds_read_b128 conflicts differ from NVIDIA's 32×4 B bank model.

---

## 7. Official AMD documents and reference tools

### Takeaway
The primary references are:
- LLVM AMDGPUUsage (targets, features, memory model, intrinsics)
- the ROCm GPU hardware specifications table
- GPUOpen WMMA guides (RDNA3, 2023; RDNA4 parts 1-2, 2026)
- ROCm Compute Profiler RDNA speed-of-light (per-CU peak formulas)
- the ROCm Strix Halo / RDNA3.5 system-optimization page
- AMD ISA PDFs (RDNA3, RDNA3.5, RDNA4, CDNA3, CDNA4)
- the AMD Matrix Instruction Calculator

### Cited Findings
- [LLVM AMDGPUUsage](https://llvm.org/docs/AMDGPUUsage.html): processor table, generic targets, LDS granularity, dynamic VGPR, DMA and tensor intrinsics.
- [ROCm GPU arch specs](https://rocm.docs.amd.com/en/latest/reference/gpu-arch-specs.html): CUs, LDS, caches and register files per product.
- [GPUOpen: WMMA on RDNA 3](https://gpuopen.com/learn/wmma_on_rdna3/) (2023-01-10, updated 2024-02-06); [GPUOpen: WMMA guide RDNA 4 part 1](https://gpuopen.com/learn/wmma-guide-amd-rdna-4-gpus-part-1/), [part 2](https://gpuopen.com/learn/wmma-guide-amd-rdna-4-gpus-part-2/) (2026-06-02 per fetch).
- [ROCm Compute Profiler RDNA speed-of-light](https://rocm.docs.amd.com/projects/rocprofiler-compute/en/latest/conceptual/rdna/system-speed-of-light.html) (v3.9.0).
- [ROCm Strix Halo optimization](https://rocm.docs.amd.com/en/latest/how-to/system-optimization/strixhalo.html).
- [GPUOpen RDNA3 "Beyond the current gen" presentation (2023)](https://gpuopen.com/presentations/2023/RDNA3_Beyond-the-current-gen-v4.pdf).
- [AMD MI355X brochure (PDF)](https://www.amd.com/content/dam/amd/en/documents/instinct-tech-docs/product-briefs/amd-instinct-mi355x-gpu-brochure.pdf).
- Chips and Cheese deep dives: [RDNA 4 in LLVM](https://chipsandcheese.com/p/examining-amds-rdna-4-changes-in-llvm), [Strix Halo memory subsystem](https://chipsandcheese.com/p/strix-halos-memory-subsystem-tackling), [Strix Halo Infinity Cache](https://chipsandcheese.com/p/evaluating-the-infinity-cache-in), [RX 7600](https://chipsandcheese.com/p/amds-rx-7600-small-rdna-3-appears), [RDNA 3 microbenchmarks](https://old.chipsandcheese.com/2023/01/07/microbenchmarking-amds-rdna-3-graphics-architecture/).

### Inferences
- The ISA PDFs (the "RDNA3 ISA Reference Guide", "RDNA4 ISA", "CDNA3 ISA", "CDNA4 ISA" at amd.com / gpuopen.com/amd-isa-documentation) are the authoritative sources for VGPR granularity, LDS banks, DPP and the WMMA/MFMA operand layouts.

### Gaps
- ISA PDF URLs and versions were not fetched this session (amd.com was returning 503).
- The AMD Matrix Instruction Calculator was not checked for gfx950 or gfx1250 support.

---

## 8. Newer generations as of Oct 2026 (RDNA5 / CDNA5 / MI400)

### Takeaway
MI400 (CDNA 5, 2 nm; MI455X, MI430X) was announced, with 2H 2026 shipments and MI450 sampling. Consumer RDNA 5 (GFX13, gfx1310) exists only as LLVM enablement, with launch rumored for 2027+. gfx1250/1251 (GFX12.5) in LLVM carry the datacenter-style features (wave32-only, clusters, tensor DMA, up to 384 KB LDS). Their product mapping is unannounced, but most plausibly they are the MI400 family.

### Cited Findings
- MI400/MI450: CDNA 5 on 2 nm, 432 GB HBM4, 19.6 TB/s, 40 PF FP4, 20 PF FP8, 2H 2026; MI500 planned for 2027. — [Guru3D](https://www.guru3d.com/story/amd-instinct-mi400-launches-in-2026-with-cdna-5-architecture); [TweakTown](https://www.tweaktown.com/news/108825/amds-confirms-instinct-mi400-series-ai-gpus-drop-in-2026-next-gen-instinct-mi500-in-2027/); [Digital Citizen, MI450 sampling](https://www.digitalcitizen.life/amd-starts-sampling-mi450-ai-gpus-as-inference-demand-grows/)
- One aggregator says AMD "Unveils Instinct MI400 Series and CDNA 5 Architecture at Advancing AI 2026", alongside "Gorgon Halo" (next APU). This is a low-quality aggregator and is unverified. — [whatpsu.com](https://de.whatpsu.com/articles/3083-AMD-Unveils-Instinct-MI400-Series-and-Helios-Rack-CDNA-Moves-to-2nm-Alongside-ROCmai-and-Gorgon-Halo)
- GFX13 (RDNA 5) gfx1310 is in LLVM. It is a dGPU that keeps `wavefrontsize64` and `cumode`, with LDS granule 256×4 B. — [LLVM AMDGPUUsage](https://llvm.org/docs/AMDGPUUsage.html); [Wccftech](https://wccftech.com/amd-adds-gfx13-to-llvm-confirming-early-support-for-rdna-5//amp/)
- GFX12.5: LDS/VC split up to 384 KB of LDS, dynamic VGPR chunks, async/cluster/tensor DMA, 57-bit buffer base. — [LLVM AMDGPUUsage](https://llvm.org/docs/AMDGPUUsage.html)

### Inferences
- The "UDNA" unification (one ISA for consumer and datacenter) is not visible as a single target yet: gfx1250 (datacenter-like) and gfx1310 (RDNA 5) are separate LLVM families as of Oct 2026.

### Gaps
- No primary AMD spec sheet for MI455X could be fetched (503). Per-CU matrix rates, LDS size and wave size for MI400 are not officially confirmed here.
- No reliable source found for RDNA 5 matrix/WMMA capabilities or for the gfx1170-1172 ("RDNA 4m") products.
