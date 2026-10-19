# Verification: AMD track — uarch.md (Microarchitecture discovery: microbenchmarks, thread trace, profilers, wave-level debugging)

Verified 2026-10-17. Method: every cited URL was opened with WebFetch and compared with the claim; independent evidence was sought with WebFetch of sibling/primary pages (rocprofiler-sdk develop + overview pages, rocprof-compute "latest" page, gpuopen.com/rgp, Mesa envvars, mankier umr man page, chipsandcheese Jan-2023 article, local rocprof-trace-decoder clone at commit 7e58204 / 2026-04-10). NOTE: the WebSearch budget for this run was exhausted before this check started, so no WebSearch could be run; "independent" evidence below comes from additional primary pages fetched directly, not from search.

## Confirmed

1. **Claim:** rocprofv3 --att thread trace supports RDNA3 discrete gfx1100/gfx1101/gfx1102 in 'trace-only' mode (no --att-perfcounters), with full support (perfmon streaming) only on CDNA gfx90a/gfx942/gfx950; output stats_*.csv has per-instruction Hitcount, Latency (Stall+Execute on gfx10+), Stall and Idle columns.
   - Cited page (docs-10.1.0) table: "RDNA3 | AMD Radeon (discrete) | Trace-only | gfx1100, gfx1101, gfx1102"; Full = gfx950/gfx942/gfx90a; "trace-only architectures don't support `--att-perfcounters`". Columns: Hitcount, Latency ("Stall time + Issue time" for gfx9 or "Stall time + Execute time" for gfx10+), Stall, Idle — verbatim as in the note.
   - Independent: develop docs (same table) and the "What is ROCprofiler-SDK" page: "RDNA2-4 (gfx10-12) are trace-only and don't support `--att-perfcounters`".
   - Side note confirmed: the docs really do contradict themselves on `--att-simd-select` for Radeon (text: "SIMD ID defaulting to 3"; table: Navi 0x0), as the note says.

2. **Claim:** The rocprof-trace-decoder plugin is bundled with ROCm >= 7.13 and supports Radeon 6000/7000/9000 series plus Instinct MI200/MI300; its 0.1.6 changelog notes RDNA2/3 s_barrier wait was reported as idle and is now approximated as stall time.
   - README (web): "Users on ROCm >= 7.13 do not need to install this package separately - it is included by default."; "AMD Radeon: 6000, 7000, 9000 series"; "AMD Instinct: MI200 and MI300 series".
   - CHANGELOG 0.1.6 (local clone, HEAD 2026-04-10; the GitHub blob/raw URL returned 404 to WebFetch): "s_barrier behaved differently on RDNA2/3: The time spent waiting on s_barrier was mostly reported as idle time. It is now changed to stalled/wait time starting from the last executed instruction. This is an approximation, but will be closer to what RDNA4 and MI series reports." Also "Fixed classification of scalar prefetch (was reported as SALU)".
   - Independent: ROCprof Compute Viewer how-to: decoder "Bundled with `rocprofv3` since ROCm 7.13".

3. **Claim:** On RDNA3/RDNA4 the AUTO performance mode gates off the perfmon clock and disables PMC counter profiling; rocprofv3 requires setting STABLE_STD via 'echo profile_standard > /sys/class/drm/card<N>/device/power_dpm_force_performance_level' or 'amd-smi set --perf-level STABLE_STD'.
   - Cited page: "On RDNA3 (Navi3x) and RDNA4 (Navi4x) GPUs, the `AUTO` performance mode disables PMC profiling in some GPU hardware blocks ... the perfmon clock is gated off"; commands `sudo sh -c 'echo profile_standard > /sys/class/drm/card<N>/device/power_dpm_force_performance_level'` and `sudo /opt/rocm/bin/amd-smi set --gpu <N> --perf-level STABLE_STD`; "This is a hardware feature enablement requirement."
   - Independent: "What is ROCprofiler-SDK" page: on gfx11/gfx12 "counter collection requires a stable power state", recommends amd-smi.

4. **Claim:** PC sampling in rocprofv3 is Instinct-only: host-trap on MI200-series (gfx90a) and later, stochastic (zero-skid, with Stall_Reason such as WAITCNT/ALU_DEPENDENCY) on MI300 (gfx942) and later; no RDNA GPU is listed.
   - Cited page: table lists only MI355X/MI350X/MI350P, MI325X/MI300X/MI300A (both), MI250X/MI250/MI210 (host-trap only); MI100 excluded; no gfx11/gfx12 entries; "zero sampling skid"; Stall_Reason values ..._WAITCNT, ..._OTHER_WAIT, ..._ALU_DEPENDENCY, ..._NO_INSTRUCTION_AVAILABLE.
   - Independent: profiling-tools-selection page: "HOST_TRAP (MI200+) ... STOCHASTIC (MI300+)"; overview page: "Stochastic PC sampling requires AMD Instinct MI300-series (gfx942) or later".

5. **Claim:** rocprof-compute 3.10.0 supports counters/speed-of-light and roofline on MI350/MI300/MI200 and Strix Halo-class gfx1150-1153, but discrete RDNA (gfx1100) is not supported ('development to support Radeon (RDNA) GPUs is in progress').
   - Cited develop page: header "ROCm Compute Profiler (rocprofiler-compute) 3.10.0"; table rows MI350 (gfx950) Yes/Yes, MI300 Yes/Yes, MI200 Yes/Yes, MI100 Yes/No, Ryzen AI gfx1150/1151/1152/1153 Yes/Yes (roofline gfx1150/1152 in 3.7.0, gfx1151 in 3.8.0), MI50/MI60 No; "Development is in progress to support Radeon™ (RDNA) GPUs."
   - Independent: "latest" page (3.9.0) carries the same RDNA statement and no gfx1100 support.

6. **Claim:** Chips and Cheese's corrected RX 7900 XTX latencies (after accounting for Infinity Fabric power states) are 128.4 ns scalar / 150.3 ns vector for Infinity Cache and 221.24 ns / 234.55 ns for VRAM; earlier measurements of 161/199 ns were inflated by the fabric clocking down under sparse requests.
   - Cited article (2023-06-15): "a much lower 128.4 ns of Infinity Cache latency" (scalar, was 161 ns); "Infinity Cache latency dropped from 199 ns to 150.3 ns" (vector); VRAM 1 GB "221.24 ns and 234.55 ns"; "Navi 31 likely manages power states separately for the Infinity Fabric and shader array".
   - Independent: the Jan-2023 article carries an editor's note "(6/14/2023) We have a new article that reevaluates the cache latency of Navi 31." (minor: the note date is 6/14 vs article date 6/15; immaterial.)

7. **Claim:** RGP v2.7.1 supports OpenCL/HIP compute profiling (instruction timing) on Windows 11 only; on Linux it supports Vulkan only, and with 25.20+ drivers RDP cannot capture Vulkan apps, so RADV's MESA_VK_TRACE=rgp built-in capture is the Linux path.
   - Cited manual (v2.7.1): compute APIs OpenCL and HIP; graphics OS "Windows 11" and "Ubuntu 24.04 LTS (Vulkan only)"; compute OS Windows 11 only; with 25.20-based Linux drivers AMDVLK is dropped, RADV default, "the Radeon Developer Panel does not support capturing data from Vulkan applications"; workaround 25.10 driver or RADV built-in capture via "MESA_VK_TRACE_* environment variables".
   - Independent: gpuopen.com/rgp lists "2.7.1 (October 2026)", OSs "Windows 11" and "Linux – Ubuntu 24.04 LTS (Vulkan only)"; Mesa envvars page documents MESA_VK_TRACE=rgp and MESA_VK_TRACE_PER_SUBMIT ("can help with compute-only workloads", only with rgp).

## Refuted with corrections

8. **Claim:** ROCgdb officially supports gfx1100, gfx1101, gfx1102 (and gfx11-generic) with info agents/queues/dispatches/lanes, kernel breakpoints, wave stepping and vector/scalar register groups; the only gfx1100-specific restriction listed is that cooperative groups and CU masking are unsupported.
   - Supported-architecture list and commands/register groups: CONFIRMED (gfx1100 "Plum Bonito", gfx1101 "Wheat Nas", gfx1102 "Hotpink Bonefish", gfx11-generic; reggroups general/vector/scalar/system).
   - "Only gfx1100-specific restriction" part: REFUTED. The cited page lists at least three restrictions naming gfx1100/gfx1101/gfx1102: (a) cooperative groups / CU masking (any attempt to create such a queue while attached fails); (b) "ROCgdb cannot debug a program past a `s_sendmsg` with `MSG_DEALLOC_VGPRS`" on gfx1100, gfx1101, gfx1102, gfx1200, gfx1201 — an asynchronous exception reported after it while attached kills the wave and only the ROCm runtime reports it; (c) "For AMD GPU architectures 'gfx1100', 'gfx1101' and 'gfx1102', the AMD ROCm runtime cannot create a AMD GPU core dump". Further restrictions use the `gfx11*` wildcard. The note's line 152/168 text ("the docs give no gfx1100 limitation beyond cooperative groups/CU masking") should be corrected to list (b) and (c); (b) matters for kernel RE because compilers emit `s_sendmsg MSG_DEALLOC_VGPRS` at the end of gfx11 kernels.
   - Correction source: https://rocm.docs.amd.com/projects/ROCgdb/en/latest/ROCgdb/gdb/doc/gdb/AMD-GPU.html

## Unverifiable

- **Claim (note line 104):** list counters with `rocprofv3 --list-avail` (or `rocprofv3 -L`, `rocprofv3-avail`). The cited rocprofv3 page contains `rocprofv3 --list-avail` but neither `-L` nor `rocprofv3-avail` was found on it (first 100k chars). `rocprofv3-avail` is a real binary shipped with rocprofiler-sdk in ROCm 6.4+ to my knowledge, but it could not be confirmed from the cited source in this run; treat `-L` as unverified.
- **URL (note line 68):** https://github.com/ROCm/rocprof-trace-decoder/blob/main/CHANGELOG.md returned HTTP 404 via WebFetch (raw.githubusercontent also 404). The content was verified from the local clone (commit 7e58204, 2026-04-10), so the claim stands, but the live URL may have moved to ROCm/rocm-systems/projects/rocprof-trace-decoder.

## Other issues

- **Hallucination-risk URLs (note line 107):** https://gpuopen.com/?p=57470 and https://gpuopen.com/?p=57466, cited as "GPUOpen RDNA Counters" / "GPUOpen RDNA3 Counters". Fetching ?p=57466 resolves to the GPUOpen homepage, not a counter reference; no VALUBusy/MemUnitBusy definitions there. The note already flags "page fetch did not return the table", but the links should be replaced by the real pages (GPUOpen "RDNA Performance Counters" / "RDNA3 Performance Counters" under gpuopen.com/learn/) or dropped. Verdict: refuted as a citation (claim content about VALUBusy/MemUnitBusy meaning is plausible but unsupported by the cited URL).
- **Minor:** cited ROCgdb page refers to `info lanes` only indirectly (lane Target ID column); `info agents/queues/dispatches` are listed explicitly. Not an error.
- **Minor:** umr man page (mankier) confirms `--waves [none|uq|ring|vmid@addr.size]`, `--profiler [pixel=|vertex=|compute=]<nsamples> [ring]`, `-O halt_waves/full_shader/bits/skip_gprs`, `--ring-stream/-RS`, `--vm-read/-vr`, `--top`, `--vgpr-granularity`, and the GFX power-gating hang warning — note's umr flags are not hallucinated.
- **Minor:** RADV/ACO env vars on line 82/123/185 all appear verbatim on docs.mesa3d.org/envvars.html (MESA_VK_TRACE*, RADV_THREAD_TRACE_* with defaults 32MiB / 0xFFFFFFFF / peak, ACO_DEBUG perfinfo/liveinfo/force-waitcnt/force-waitdeps/nosched/nosched-ilp/nosched-vopd, RADV_DEBUG shaderstats/extra_md/pso_history/bo_history) — confirmed.
- **Minor:** kernel-replay flags on line 104 confirmed verbatim: "--replay-mode kernel requires --pmc and --kernel-replay-beta-enabled" and "cannot be combined with --att, PC sampling, or --spm".
