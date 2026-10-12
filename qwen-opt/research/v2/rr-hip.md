# ROCm/HIP levers on gfx1100 for batch-1 decode and spec-verify (Qwen3.8-27B, qwen35)

Scope: research only. Nothing ran on the GPU. The new measurements come from re-parsing an existing rocprofv3 trace (`~/qwen-opt/prof/rocm-mtp4-now/run_kernel_trace.csv`, 2026-10-12, build-hip, MTP n_max=4, 64k draft head, ctx 16k; log in `~/qwen-opt/prof/rocm-mtp4-now.log`). Unmarked numbers come from that trace, from code, or from the cited sources. Estimates are marked [INFERENCE].

## 0. Trace facts that set the ranking (new analysis)

Per spec step (n_max=4, median of ~150 steps; profiled step period 44.2 ms):

| segment | kernels | wall | GPU busy |
|---|---|---|---|
| verify input uploads (8× `__amd_rocclr_copyBuffer`) + 8-kernel prefix split + gap | 16 | **0.52 ms** from first upload to start of the main graph | ~0.13 ms |
| verify main graph | **2188** | **36.7–36.9 ms** | 29.8 ms |
| gap after verify | – | 0.45 ms | – |
| MTP catch-up graph (4 uploads + 32 kernels) | 36 | 0.77 ms | 0.54 ms |
| gap (CPU sampling) | – | 0.7–0.96 ms | – |
| 4 draft graphs (5–7 uploads + ~46 kernels each) | 4×53 | 4×1.17 ms | 4×0.88 ms |

**Inside the verify graph, every kernel boundary costs a near-constant ~3.2–3.4 µs of GPU idle, whatever the kernel type.** Average gap before: mmvq 3.27, rms_norm 3.23, quantize_q8_1 3.22, cpy 3.16, bin_bcast 3.29, GDN 3.31, FA tile 3.32 µs. Summed over 2188 kernels this is **7.13 ms of gaps per verify (19 % of wall)**. Matvec busy time is 24.98 ms. Every non-matvec kernel plus every gap adds up to **≈12 ms per verify**, and that 12 ms is the HIP-specific budget.

This matches an independent measurement. ROCm issue [#6409](https://github.com/ROCm/ROCm/issues/6409) (W7900 gfx1100, TheRock 7.15) measures **3.865 µs/node for a warmed 941-node hipGraph** of tiny serialized kernels, against **0.876 µs/dispatch** for RADV command-buffer replay. The issue is open and has no fix.

Cause, from CLR source ([rocvirtual.cpp, ROCm/rocm-systems](https://raw.githubusercontent.com/ROCm/rocm-systems/develop/projects/clr/rocclr/device/rocm/rocvirtual.cpp)):
- Every kernel AQL packet is built with `barrierHBits | agentScopeHBits` (`dispatchPacketHeader_`, ~L2451-2453). The barrier bit makes the CP wait for the previous packet to complete.
- The agent-scope acquire "invalidates I, K and L1" on every kernel (header comment, L70-72).
- The graph replay path already batch-copies all packets into the queue with one slot reservation and one doorbell (~L1760-1830). Host submission is therefore not the problem. The cost is CP and firmware time per packet.
- This explains why the HIP env knobs (graph batch/segment, kernarg, direct dispatch) were noise (NOTES.md:117). None of them changes the per-packet barrier and cache handling.

**Kernel count per verify layer (from the trace sequence):**

*GDN layer: 35 kernels.*
- Conv/state path:
  - qkv mmvq → `concat_non_cont` (11.8 µs!)
  - 5× `cpy_scalar` conv snapshots
  - `k_get_rows_float_vec` ssm-state gather (6.6 µs)
  - `ssm_conv`(+silu)
- q/k l2-norm and gates:
  - 2× `rms_norm<…,do_scale>` (l2norm of q and k)
  - alpha path: mmvq **9 µs** → add → softplus → mul
  - beta path: mmvq **9 µs** → sigmoid
- Recurrence and output:
  - GDN (10.6 µs)
  - gated rms_norm
  - z mmvq → silu·mul → quantize
  - out mmvq → residual add
- FFN:
  - post-norm → quantize
  - up mmvq, gate mmvq → swiglu → quantize
  - down mmvq → residual add
- Next layer prefix:
  - next attn_norm
  - conv `k_get_rows_float`
  - quantize

*Attention layer: 31 kernels.*
- Q path: q+gate mmvq → q-norm → `rope_multi` → `fwht`
- K/V path:
  - k mmvq → fwht → v mmvq
  - k-norm → rope → fwht
  - 2× `set_rows` q4_0
  - 2× `dequantize_block_q4_0`
- Attention: FA tile → combine → fwht (V un-rotation)
- Output: gate `cpy` (cont) → sigmoid·mul → quantize → o mmvq → add
- FFN tail: same as the GDN layer

`fwht` is the Hadamard rotation that llama.cpp adds automatically for quantized KV (`src/llama-kv-cache.cpp:315-360`, `llama-graph.cpp:3006-3013,3051`).

Note: the brief says "~1200 kernels per spec step". This trace has 2188 (verify) + 36 + 4×53 ≈ **2440 per step**.

---

## Ranked findings

### 1. Fuse the GDN conv/state path: CONCAT + K conv-snapshot CPYs (+ conv-state gather) into one kernel. Highest impact, HIP-agnostic, upstream-quality.
- **Evidence:** per GDN layer, `concat_non_cont` takes 11.8 µs, the 5 `cpy_scalar` take 1.7–4.0 µs each and `k_get_rows_float` takes 2.0 µs. Each also pays ~3.3 µs of gap.
  - The CPYs come from `build_conv_state`: one `ggml_cpy` per rollback slot (`src/models/delta-net-base.cpp:502-521`).
  - They cannot be merged into one ggml view. The src offset *decreases* as the slot index increases (`s_idx = base-K+t`, `s_slot = K-t`), which needs a negative stride.
  - The concat is the "transposed src1" slow path. The RDNA3.5 shared-memory transpose PR [#28303](https://github.com/ggml-org/llama.cpp/pull/28303) targets the same shape in prefill only.
- **Change:** a CUDA/HIP fusion that matches `CONCAT(conv_states, transpose(qkv))` → K × `CPY(view(concat) → conv_states_all slot)` (→ `SSM_CONV` [+ADD] + SILU). The fused SSM_CONV kernel reads both sources directly and writes the K snapshot windows (3×10240 floats each).
  - Model the matcher on `ggml_cuda_try_gdn_cache_fusion`, which already matches GDN plus non-adjacent CPY nodes and redirects writes into the cache (`ggml/src/ggml-cuda/ggml-cuda.cu:2843-2903`).
  - Put it in `ggml_cuda_try_fuse` next to the existing SSM_CONV fusions (`ggml-cuda.cu:4285-4293`). The kernel goes in `ggml/src/ggml-cuda/ssm-conv.cu`.
  - Optionally read the conv state through the `s_copy` index, which removes the conv `get_rows` too. PR [#30139](https://github.com/ggml-org/llama.cpp/pull/30139) does this at graph level.
- **Gain:**
  - −6 to −7 kernels × 48 layers = −290 to −336 kernels.
  - Gaps: 0.95–1.1 ms. Removed kernel time: concat 0.57 ms + cpy ~0.45 ms + get_rows 0.10 ms, partly re-spent inside ssm_conv (+~1 µs/layer) [INFERENCE].
  - **≈1.8–2.1 ms per verify, ≈4–5 % of the 41.8 ms step.**
  - Plain decode (n_rs_seq=0, 1 cpy) gains ~0.5 ms/token.
- **Effort:** medium (2–3 days with test-backend-ops). **Risk:** low. The order is exact copies, so output stays bitwise lossless.

### 2. GDN prologue fusion: alpha/beta projections + gate math + q/k l2-norm (+ state gather) into fewer kernels.
- **Evidence:**
  - alpha and beta are separate m=48 mmvq calls at **9.0 / 8.5 µs**, i.e. 24 workgroups on 96 CUs, latency-bound.
  - The rest of the chain: add(dt) 1.4–2.4, softplus 1.2, mul(A) 2.1, sigmoid 1.1, two l2-norm `rms_norm` 2.2 + 1.5 µs.
  - Graph sources: `src/models/qwen35.cpp:372-390` (alpha/beta chain) and `:443-444` (`build_gdn_l2_norm` = `rms_norm`+`scale`, `src/models/models.h:14-17`).
- **Upstream:** [#29187 "CUDA: Fuse GDN alpha/beta projections"](https://github.com/ggml-org/llama.cpp/pull/29187) (open draft) does exactly this for BF16/F16/F32/**Q8_0** weights in one launch: `gate=softplus(W_a x+dt)*a`, `beta=sigmoid(W_b x)`. It reports +7–13 % pp2–8 on Qwen3.8-27B on Blackwell. It is a plain CUDA kernel, so it should build for HIP [INFERENCE]. SYCL merged the equivalent chain fusion in [#29687](https://github.com/ggml-org/llama.cpp/pull/29687).
- **Additional step (not upstream):**
  - Fold the q/k l2-norm into the GDN kernel (`ggml/src/ggml-cuda/gated_delta_net.cu:7`). Each head's 128-element q/k is already loaded there, so this is a 128-wide reduction per (head, token).
  - Read the initial state through the `s_copy` index instead of the `get_rows_float_vec` copy, per PR [#30139](https://github.com/ggml-org/llama.cpp/pull/30139). That PR measures 209 µs per token on a 27B and removes a 3 MB read + 3 MB write per GDN layer.
- **Gain:**
  - Kernels: alpha/beta 6 → 1, l2 2 → 0, gather 1 → 0. That is −8 kernels × 48 = −384 kernels → 1.25 ms of gaps.
  - The m=48 pair drops from 17.5 µs to ~3–4 µs → −0.65 ms [INFERENCE].
  - Small ops removed: ~0.45 ms. Gather traffic removed: ~0.3 ms.
  - **≈2.3–2.6 ms per verify (≈5.5–6 % step).**
- **Effort:** medium. Port #29187, then extend the GDN kernel. **Risk:** low to medium. The l2-norm in-kernel reorders an fp32 reduction, so it is within kernel noise but not bitwise.

### 3. Fuse `quantize_q8_1` into its producers (rms_norm·w, swiglu, sigmoid/silu·mul).
- **Evidence:**
  - 256 quantize kernels per verify (avg 1.5 µs + 3.2 µs gap). Total ≈ 0.39 ms busy + 0.82 ms gap.
  - The local q8_1 cache (`3a05006a0`, `mmvq_q8_cache_*`, `ggml-cuda.cu:4359,4468,4495`) already removes duplicates. 4 per layer remain: post-attn norm, swiglu, gated-norm/sigmoid-gate output, next attn_norm.
- **Change:**
  - The producer kernel writes the q8_1 blocks (and the f32 output only if another consumer exists) straight into the cache slot. Mark the slot valid for `src1`.
  - Code: `ggml/src/ggml-cuda/norm.cu` (`rms_norm_f32<…,do_multiply>`), `unary.cu`/glu, `quantize.cu`. Matching goes in `ggml_cuda_try_fuse` (`ggml-cuda.cu:4260-4300`).
- **Gain:** −256 kernels → **≈1.0–1.2 ms per verify (≈2.5 %)**, plus ~0.1 ms/step on drafts [INFERENCE]. **Effort:** medium. **Risk:** low. Same arithmetic, so lossless.

### 4. Let the multi-column mmvq take the residual-ADD (bias) epilogue (ncols 2–8).
- **Evidence:**
  - Fusion is gated to `ncols_dst == 1` (`ggml-cuda.cu:1845-1848`; `mmvq.cu:1583-1596` asserts "fusion only supported for ncols_dst=1").
  - Draft graphs (n=1) therefore fuse `mmvq+add`, but verify (n=5) runs 2 separate `k_bin_bcast` residual adds per layer: 128 kernels, ~1.9 µs + 3.3 µs gap each.
  - The multi-column kernel already loads `x_biases[ncols_dst]` (`mmvq.cu:1216-1231`). Only the instantiation and dispatch gate are missing.
  - Do **not** enable the gate+up path at ncols>1. It was measured negative (NOTES.md:116, register pressure). Use a separate bias-only template flag so `tmp_gate` is not allocated.
- **Gain:** −128 kernels → **≈0.6 ms per verify (≈1.5 %)**. **Effort:** low (1 day). **Risk:** low.

### 5. HIP "any-order" launches for independent neighbours (removes the CP barrier without new kernels).
- **Evidence:**
  - AQL barrier-bit semantics: a packet with barrier=1 waits for *all* earlier packets. A packet launched with `hipExtAnyOrderLaunch` has its barrier bit cleared (CLR `rocvirtual.cpp:5125-5127`). The header logic keeps "explicit any-order" through the fence-state path (~L1649-1653).
  - API: `hipExtLaunchKernel(..., flags=hipExtAnyOrderLaunch)` in `/opt/rocm/core-10.0/include/hip/hip_ext.h:95-103`. `hip_runtime_api.h:1031` defines `hipExtAnyOrderLaunch 0x01`. Not supported on GFX9, but fine on gfx1100.
- **Candidates per verify (B independent of A):**
  - up/gate mmvq: 64
  - alpha/beta mmvq: 48, if #2 is not done
  - q-l2 / k-l2: 48, if #2 is not done
  - conv snapshot cpys: 4×48, if #1 is not done
  - K/V `set_rows`: 16
  - K/V dequant: 16
  - ssm-state `get_rows` vs `ssm_conv`: 48
  - That is ~430 barriers, of which ~150–200 remain after #1–#2.
- **Change:**
  - Add an `any_order` field to `ggml_cuda_kernel_launch_params`. In `ggml_cuda_kernel_launch` (`ggml/src/ggml-cuda/common.cuh:1724-1742`) call `hipExtLaunchKernel` under `GGML_USE_HIP`.
  - The caller (graph-compute loop, `ggml-cuda.cu:4416-4500`) sets the flag only when node i+1 reads nothing that node i writes and the two outputs do not overlap. Reuse `ggml_cuda_check_fusion_memory_ranges`-style checks (`ggml-cuda.cu:3060`).
  - **Must verify:** that stream capture keeps the flag in the graph kernel node. Check with `AMD_LOG_LEVEL=4` / `AMD_LOG_MASK` AQL logging, which prints `barrier=` per packet (`logAqlDispatchPacket`, rocvirtual.cpp ~L185).
- **Gain:** 150–430 × ~3.3 µs = **0.5–1.4 ms per verify** [INFERENCE: assumes the gap is barrier-wait dominated, which the ROCm #6409 tiny-kernel replay floor suggests]. **Effort:** low to medium. **Risk:** medium. Wrong independence analysis gives races, so it must be gated by a strict checker.
- This is not the same as `GGML_CUDA_GRAPH_OPT=1` (measured −1 %, NOTES.md:118). That path adds `cudaEventRecord`/`cudaStreamWaitEvent` per fork/join (`ggml-cuda.cu:4326-4343, 4421-4428`), which become extra barrier packets.

### 6. Attention-layer small-op trimming (16 layers).
All are lossless or within kernel noise:
- **rms_norm+mul+rope fusion:** exists only for NORMAL/NEOX rope (`ggml-cuda.cu:2821-2825, 2780-2783`). qwen35 uses `ggml_rope_multi` (`qwen35.cpp:313-323`), so it never fuses. Add an IMROPE/MROPE path to `ggml_cuda_op_rms_norm_mul_rope_fused` → −2/layer.
- **rope + fwht (q and k):** both work per 256-dim head. Append FWHT in the rope kernel → −2/layer. The V-output `fwht` can fold into the following sigmoid·mul → −1.
- **`gate = ggml_cont_2d(...)` (`qwen35.cpp:307`):** produces a 4 µs `cpy_scalar`. Unary ops on strided views are supported since [#29781](https://github.com/ggml-org/llama.cpp/pull/29781) (merged 2026-10-08, in base). Drop the cont and feed the view to `ggml_sigmoid` → −1.
- **2× `dequantize_block_q4_0` + tile FA:** superseded by the in-progress GQA q4_0 FA kernel.
- **Gain:** ~−6 to −8 kernels × 16 → **≈0.4–0.5 ms per verify**. **Effort:** low to medium.

### 7. Input uploads and split boundaries around graphs (HIP host path).
- **Evidence:**
  - Every input `set_tensor` is `cudaMemcpyAsync(H2D, cudaStreamPerThread)` followed by `cudaStreamSynchronize` (`ggml-cuda.cu:783-789`).
  - On ROCm a small pageable H2D runs as a blit kernel (`__amd_rocclr_copyBuffer`, 2.6–3.6 µs GPU each) plus a host round-trip.
  - The trace shows 8 uploads plus prefix taking 0.52 ms before verify, ~0.13 ms per draft graph (5–7 uploads) and 0.115 ms per catch-up. That is **≈1.15 ms per step**.
  - Also, every verify runs as **two** submissions: an 8-kernel prefix (layer-0 attn_norm, conv gather, quantize, qkv mmvq, concat, 3 of 5 conv cpys), then a **120–155 µs gap**, then the 2188-kernel graph. That looks like a scheduler split, with the next split's input copied by SDMA (SDMA copies do not appear in a kernel trace) [INFERENCE].
- **Change:**
  1. Diagnose the split with `GGML_SCHED_DEBUG=2` (env read at `ggml-backend.cpp:1950`), which prints splits and their inputs.
  2. Upload all graph inputs with one async copy on the compute stream from a pinned staging buffer, with no per-tensor sync. Use the backend `set_tensor_async` (`ggml-cuda.cu:2534`) from the llama input path. Related Vulkan attempt: [#30169](https://github.com/ggml-org/llama.cpp/pull/30169) (closed).
  3. Background on ROCm small D2D copies: [#28178](https://github.com/ggml-org/llama.cpp/pull/28178) found that `hipMemcpyAsync` D2D below 1 KiB goes to SDMA with an L2 flush.
- **Gain:** **≈0.5–0.9 ms per step** [INFERENCE]. **Effort:** medium; touches llama-graph input setters. **Risk:** low. Overlaps the host-side slice; coordinate.

### 8. Avoid hipGraph re-warmup when n_kv crosses a 256 boundary.
- **Evidence:**
  - Graphs are cached per first-node pointer (`common.cuh:1458-1486`) and evicted after 10 s idle (`:1468-1477`).
  - A property change resets warmup, and two eager executions follow before recapture (`ggml-cuda.cu:4577-4596`).
  - n_kv is padded to 256 (`src/llama-kv-cache.cpp:1285-1290`). So the verify graph, and the MTP draft/catch-up graphs with their own KV, change shape every 256 tokens, about every 85 steps at ~3 tokens/step.
  - Verify graph reuse via `uid` is fine (`ggml-cuda.cu:2690-2695`). Catch-up/draft got distinct keys in [#28549](https://github.com/ggml-org/llama.cpp/pull/28549), which is already in base.
- **Change:** port [#29768 "avoid repeated warmup after stable graph replay"](https://github.com/ggml-org/llama.cpp/pull/29768) (recapture immediately when ops are unchanged; +1.1 % on 5090/27B). On HIP the eager pass of 2188 launches is the expensive part [INFERENCE].
- **Gain:** ~0.1–0.4 ms per step amortized, plus smoother latency [INFERENCE]. **Effort:** low. **Risk:** low.

### 9. VRAM overclock under the 285 W cap (hardware; needs root + reboot).
- **Facts on this box:**
  - `ppfeaturemask = 0xfff7bfff`. Bit 14 (0x4000, OverDrive) is clear, so `pp_od_clk_voltage` is absent. `qwen-opt/gpu-power.sh` already documents `0xfff7ffff`.
  - `pp_dpm_mclk` top level is **1249 MHz**. GDDR6 effective = ×2 = 2498 MHz → 20 Gbps → 960 GB/s ([kernel docs, pp_od_clk_voltage](https://docs.kernel.org/gpu/amdgpu/thermal.html)).
  - FCLK DPM tops at 2301 MHz.
  - SMU13 OD exposes `OD_SCLK`, `OD_MCLK`, `OD_FCLK` and a `vo` voltage offset. Writes are `m 1 <MHz>`, `f 1 <MHz>`, `vo -N`, then `c` (same doc). Memory timing straps ("Fast Timing" in Windows Adrenalin) are not in the Linux OD interface [INFERENCE: absent from the kernel doc].
- **Evidence for headroom:** a 7900 XTX OC write-up runs memory at 2700 MHz (21.6 Gbps, 1.036 TB/s, +8 %) with Fast Timing on Windows ([Medium, opinali](https://medium.com/@opinali/overclocking-the-radeon-7900-xtx-4e963bd5cda1), search snippet). AMD lifted the 7900 GRE limit to 3000 MHz ([Tom's Hardware](https://www.tomshardware.com/pc-components/gpus/amd-lifts-memory-overclocking-limitations-on-rx-7900-gre)). No LLM-specific measurement on Linux was found.
- **Gain:**
  - Matvec is ~25 of 36.9 ms per verify, and n=1 mmvq runs at 81–88 % of peak, so it is bandwidth-bound. +8 % bandwidth → up to −1.5 to −2 ms per verify → **≈+3–5 % t/s** [INFERENCE].
  - The extra memory power under a fixed 285 W cap can pull sclk down, which slows the gap/small-op portion. Measure both.
- **Undervolt (`vo -50…-100 mV`):** the same sclk at lower power, so more headroom under the cap. It should lower junction temperature (NOTES.md:134 recorded 106 °C at prefill), which is the longevity lever. Decode speed should be flat or slightly up [INFERENCE]. Community note: on the 7900 XTX, undervolting tends to raise clocks in the same power window rather than cut power ([r/Amd thread](https://www.reddit.com/r/Amd/comments/18bev9o/7900_xt_xtx_and_their_undervolting_clocking)).
- **Also check without OD:** log `pp_dpm_fclk` and `pp_dpm_mclk` during decode at 285 W. If FCLK drops below 2301 under the cap, MALL/memory-path bandwidth drops too. `gpu-power.sh monitor` does not log FCLK yet.
  - The KFD already switches the SMU to the COMPUTE profile while compute queues are active (`amdgpu_amdkfd_set_compute_idle` → `amdgpu_dpm_switch_power_profile(..., PP_SMC_POWER_PROFILE_COMPUTE, !idle)`, [linux amdgpu_amdkfd.c:751-769](https://raw.githubusercontent.com/torvalds/linux/master/drivers/gpu/drm/amd/amdgpu/amdgpu_amdkfd.c)), so there is nothing to gain from `pp_power_profile_mode`.
- **Risk:**
  - GDDR6 instability. EDC retries hide link errors as slowdowns; data at rest has no ECC. Validate with greedy-output equality (`greedy_check.sh`) plus long runs.
  - Higher VRAM temperature.
  - The power-cap minimum readback is flaky on newer kernels ([LACT #775](https://github.com/ilya-zlobintsev/LACT/issues/775)).
- **Tools:** LACT (SMU13 OD support), `amd-smi metric -p`.

### 10. Non-temporal hints for weight streaming in mmvq (A/B experiment, small).
- **Evidence:** braidinfer gfx1100 microbenchmarks ([GFX1100_CACHE_HINTS.md](https://raw.githubusercontent.com/mcelrath/braidinfer/master/GFX1100_CACHE_HINTS.md)):
  - Repeated streaming reads: `glc=1` 1365 GB/s and `slc=1` 1369 GB/s vs 1237 GB/s default (64 MiB set, so MALL-resident).
  - **`dlc=1` (Infinity Cache non-temporal) dropped to 697 GB/s.**
  - In a hot/stream mix, `dlc=1` protects the hot set but slows the stream.
- **Applicability:** weights are 16.5 GB per forward and never reused across a forward, while activations, q8_1 and states are small. Try `slc` (`__builtin_nontemporal_load`, compiler-chosen bits) on weight loads only, in `mmvq.cu`/`vecdotq.cuh` load helpers. **Never `dlc`.** Expected 0–3 % of matvec time [INFERENCE]. **Effort:** low. **Risk:** low.

### 11. Infinity Cache (96 MB): what does and does not matter.
- **Weights:** 16.5 GB stream per forward means zero cross-step reuse. No ordering trick helps.
- **Recurrent states:** 48 × 3.15 MB = 151 MB, more than the MALL. They are evicted by the weight stream between steps.
- **What IC does absorb today:** the GDN snapshot writes. With the K=5 fused cache path, each GDN layer writes 5 × 3.15 = 15.7 MB in a 10.6 µs kernel (≈1.5 TB/s). That only works as write-back into L2/MALL, with the DRAM write-back (≈755 MB per verify ≈ 0.8 ms of 960 GB/s) overlapping the next matvecs [INFERENCE].
  - Removing it means replaying from inputs instead of snapshotting: vLLM/SGLang "ReplaySSM", and llama.cpp attempt [#29763](https://github.com/ggml-org/llama.cpp/pull/29763) (closed; bit-exact claim, constant 2 planes).
  - Low priority: ≤0.8 ms/verify, uncertain, high effort.
- **KV:** at long context the q4_0 KV per attention layer (~1152 B/token) exceeds the MALL beyond ~80k tokens. The GQA FA kernel already reads K/V once per KV head, which is the right IC behaviour.
- **Hard limits:** HIP has no software MALL residency control comparable to CUDA access-policy windows [INFERENCE: none found in the HIP 10 headers]. Do not use `dlc=1` on reused data (see #10).

### 12. Compiler/codegen (low expected value).
- **Current build:**
  - `build-hip/CMakeCache.txt`: Release `-O3 -DNDEBUG`, empty `CMAKE_HIP_FLAGS`, `GPU_TARGETS=gfx1100`, clang `/opt/rocm/core-10.0/lib/llvm`, `GGML_HIP_GRAPHS=ON`, `GGML_HIP_NO_VMM=ON`.
  - `ggml/src/ggml-hip/CMakeLists.txt` adds no AMDGPU-specific flags (lines 14-16 Debug only; 116-118 metrics only).
- **Wave size:** wave32 everywhere on RDNA (`ggml_cuda_get_physical_warp_size()` returns 64 only for GFX8/9, `common.cuh:390-394`).
  - ROCm #6409 finds HIP (wave32) vs RADV (wave64) only 1.05–1.13× apart on packed-dot microbenchmarks on gfx1100.
  - HIP *wins* the production-shaped Q4/Q6 quantize+dot rows (0.50–0.90×).
  - Wave64 is not worth porting. Upstream wave64 work ([#29534](https://github.com/ggml-org/llama.cpp/pull/29534)) is GCN FA only.
- **`__launch_bounds__`:**
  - In HIP the second parameter is `MIN_WARPS_PER_EXECUTION_UNIT`, not CUDA's min-blocks ([HIP C++ extensions](https://rocm.docs.amd.com/projects/HIP/en/docs-7.0.2/how-to/hip_cpp_language_extensions.html)).
  - mmvq uses `(nwarps*warp, 1)` (`mmvq.cu:1136`), so occupancy is unconstrained by the compiler.
  - Lever: `__attribute__((amdgpu_waves_per_eu(N)))` on the multi-column mmvq instantiations, to trade VGPRs for occupancy at n=5. Verify reaches only ~700 GB/s (17.5 GB / 24.98 ms) vs 81–88 % of peak at n=1. Expected 0–5 % matvec [INFERENCE]. Check spills with `GGML_HIP_EXPORT_METRICS=ON` (`-Rpass-analysis=kernel-resource-usage`).
- `-munsafe-fp-atomics` is irrelevant: decode kernels use no FP atomics on these paths.

### 13. Persistent kernel / megakernel. Not recommended for this stack.
- **Evidence:**
  - Hazy "No Bubbles" (Llama-1B, H100): CUDA graphs still left ~1.3 µs/launch. The megakernel reached 78 % of bandwidth, built on Hopper/Blackwell-specific infrastructure ([blog](https://hazyresearch.stanford.edu/blog/2025-05-27-no-bubbles)).
  - MPK "generates fast CUDA implementations" ([arXiv 2512.22219](https://arxiv.org/abs/2512.22219)). It does not target AMD.
  - The only gfx1100 LLM megakernel found is braidinfer ([repo](https://github.com/mcelrath/braidinfer)): a persistent cooperative kernel with **2.79 µs median persistent dispatch**, no better than the 3.3 µs hipGraph gap. It reports **Qwen3.5-27B q4 at 4.1–4.2 t/s** on one 7900 XTX, far below llama.cpp here.
- **Feasibility in ggml:** a whole-model persistent interpreter means rewriting every op as a device task with global-atomic dependency counters. Cross-workgroup sync on RDNA3 goes through L2 atomics with ~µs latency, and nothing like PDL exists on HIP.
- **Gain ceiling:** at most the ~7 ms of gaps per verify, against months of work. Fusions #1–#6 recover roughly 5–7 ms of the same 12 ms budget at a fraction of the cost.

### 14. HIP graph features: nothing to switch on.
- HIP 10 headers have `hipGraphInstantiateFlagDeviceLaunch`/`Upload`/`UseNodePriority` (`hip_runtime_api.h:1859-1868`), but **no conditional/while nodes**. A draft loop therefore cannot run on-device via graph features.
- Device launch does not change the per-node CP cost.
- The graph runtime knobs present in this libamdhip64 (`DEBUG_HIP_GRAPH_BATCH_SIZE`, `_SEGMENT_SCHEDULING`, `_CLASSIC_PATH`, `_MIN_OVERLAP`, `DEBUG_HIP_FORCE_GRAPH_QUEUES`, from `strings` on `libamdhip64.so.7.15.26333`) were already A/B'd as noise (NOTES.md:117).

---

## Summary arithmetic (verify ≈36.9 ms wall; step 41.8 ms unprofiled at n=4)

| # | lever | kernels removed per verify | est. saving per step |
|---|---|---|---|
| 1 | conv/concat/snapshot fusion | ~290–336 | 1.8–2.1 ms |
| 2 | GDN prologue (#29187 + l2 + in-place state) | ~384 | 2.3–2.6 ms |
| 3 | quantize into producers | ~256 | 1.0–1.2 ms |
| 4 | mmvq residual epilogue ncols>1 | 128 | 0.6 ms |
| 6 | attention trimming | ~100–130 | 0.4–0.5 ms |
| 5 | any-order on what remains | (barriers) | 0.5 ms |
| 7 | input upload batching + split fix | – | 0.5–0.9 ms |
| 8 | no re-warm at n_kv steps | – | 0.1–0.4 ms |

Kernel levers total ≈ −1150 kernels (2188 → ~1050). Estimated **≈6.5–7.5 ms per step [INFERENCE: assumes ~3.3 µs per removed boundary plus removed kernel time, minus fused-kernel cost]**. That takes the 41.8 ms step to ≈34–35 ms, **≈+19–22 % t/s** (74.5 → ~89–91 mixed). It also applies to plain decode (GDN parts) and to prefill (fewer launches at small ubatches). Hardware OC (#9) is independent and adds ~3–5 %.

Suggested order (value per effort): 4 → 2 (port #29187 first) → 1 → 3 → 7 → 6 → 5 → 8. Verify each step with `test-backend-ops -o GATED_DELTA_NET|SSM_CONV|CONCAT|CPY|MUL_MAT|RMS_NORM|ROPE`, greedy-output equality, and a rocprofv3 kernel trace (kernel count, gap sum).

## Avoid / does not apply
- **Disabling HIP graphs or `GGML_CUDA_GRAPH_OPT=1` (multi-stream):** measured −3 % / −1 % (NOTES.md:118). Fork/join events add barrier packets to a dispatch-bound stream.
- **HIP/CLR env knobs** (graph batch/segment/classic, kernarg, direct dispatch, wait timeout): measured noise. The cost sits in per-packet CP barrier and cache handling, not host submission.
- **gate+up fused mmvq at ncols>1:** measured −8 % (register pressure). Use a bias-only epilogue (#4).
- **Full megakernel / MPK port:** CUDA-only tooling. The gfx1100 evidence (braidinfer) shows no dispatch-latency win (2.79 µs) and poor 27B throughput.
- **Wave64 rewrite for RDNA3:** no evidence of decode gain. HIP wave32 already wins production-shaped dot kernels (ROCm #6409).
- **`dlc=1` / MALL-bypass loads on reused data:** halves bandwidth in gfx1100 microbenchmarks (braidinfer).
- **BF16/F16 rollback snapshots to cut IC/DRAM write traffic:** changes recurrent-state numerics, so it is not lossless.
- **[#29796](https://github.com/ggml-org/llama.cpp/pull/29796) "skip redundant stream synchronization":** explicitly native-CUDA only; HIP keeps unconditional sync.
- **[#27722](https://github.com/ggml-org/llama.cpp/pull/27722) (disable GDN cache fusion on HIP):** a workaround for RDNA3 *iGPU* hangs (closed). The dGPU trace shows the fused path working (`gated_delta_net_cuda<128,false,true,4>`, no state cpy). Keep it.
- **hipGraph device launch / conditional nodes for the MTP draft chain:** no conditional nodes in HIP 10. Build the unrolled draft graph instead (already planned).
- **Lowering the power cap further for speed:** decode sits at the cap. Only undervolting or OC changes the operating point, and the 272 W floor without OD gives only −4.5 % power (NOTES.md:126-127).
