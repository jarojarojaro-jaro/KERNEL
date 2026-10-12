# Qwen3.8-27B on RX 7900 XTX (ROCm): roadmap v2 (research 2026-10-12)

Scope: research only. Nothing was run on the GPU and nothing was built. The only new measurements are re-parses of traces and logs that already existed (`~/qwen-opt/prof/rocm-mtp4-now/run_kernel_trace.csv`, `~/qwen-opt/logs/*.log`). Code references point to `~/llama-master` (branch amd-opt, base e60eff95f). [INFERENCE] marks estimates.

Detailed reports behind this roadmap:
- `local://rr-hip.md`: HIP/RDNA3 levers, trace analysis, fusions, hardware.
- `local://rr-prefill-kv.md`: prefill, long-context attention, prompt caching.
- `local://rr-engines-drafters.md`: other engines, new drafters, n-gram/agentic methods, upstream PRs.

## 0. Arithmetic baseline used for every estimate

- **Mixed EN/PL at T=1:** 74.5 t/s at a 41.8 ms step (MTP n=4), i.e. **3.11 tokens/step**.
  - Each 1 ms saved per step gives ≈ **+2.4 % t/s** (3.11 / 40.8 ms = 76.2 t/s).
- **Long context, T=0:** 78.6 t/s at 1.7k means 3.29 tokens/step. Assuming the same tokens/step:
  - 62.4 t/s at 29.5k → 52.7 ms step (+10.9 ms).
  - 43.0 t/s at 94k → **76.4 ms step (+34.6 ms)** (`rr-prefill-kv.md` F1).
- **End-to-end (E2E):** a 94k prompt plus 1000 output tokens takes 165 s = 142 s prefill (666 t/s) + 23 s decode (NOTES.md:194).
- **New trace facts (re-parsed, `rr-hip.md` §0):**
  - The verify graph is **2188 kernels**. A whole step is ≈2440 kernels, not the ~1200 in the brief.
  - **Every kernel boundary costs a nearly constant 3.2–3.4 µs of GPU idle**, whatever the kernel. That is **7.13 ms of gaps per verify (19 % of 36.9 ms)**.
  - Matvec is 24.98 ms. Small ops plus gaps come to **≈12 ms per verify**: this is the HIP-specific budget.
  - Root cause is in CLR `rocvirtual.cpp`: every AQL packet sets the barrier bit plus an agent-scope cache invalidate (~L2451, L70-72; [rocm-systems source](https://raw.githubusercontent.com/ROCm/rocm-systems/develop/projects/clr/rocclr/device/rocm/rocvirtual.cpp)). The same is seen in [ROCm #6409](https://github.com/ROCm/ROCm/issues/6409): 3.87 µs/node hipGraph on gfx1100 vs 0.88 µs RADV.
  - This explains why the HIP env knobs were noise. **Fewer kernels is the only real lever.**
- **Prefill:**
  - One 512-token ubatch at 6.6k takes 554 ms: matmul ≈500 ms (90 %, ~50 TFLOPS int8-WMMA MMQ), GDN ≈15 ms, FA ≈14 ms, small ops ≈25 ms.
  - At 94k, FA reaches ≈26 % of prefill time (~47 TFLOPS effective) (`rr-prefill-kv.md` F6, F7).

---

## A. Ready to do next (ranked by value/effort)

| # | Item | Gain (arithmetic) | Effort | Risk | Lossless |
|---|---|---|---|---|---|
| A1 | Prompt-cache/checkpoint flags | follow-up on a 94k doc: 165 s → ≈23–25 s; conversation switch 34 s/142 s → 0.1–0.3 s | flags | low | yes |
| A2 | Extend the scope of the in-progress GQA FA kernel: n=1, MTP context, split-K | 94k: 43 → ~65–72 t/s; 30k: 62 → ~73 t/s | (in progress) | med | within noise |
| A3 | HIP kernel-count cuts, part 1: mmvq residual epilogue for ncols 2–8 | −0.6 ms → +1.5 % | 1 day | low | yes |
| A4 | Part 2: GDN prologue fusion (port PR #29187 + l2-norm in GDN + in-place state #30139) | −2.3…2.6 ms → +5.5–6.5 % | medium | low-med | within noise |
| A5 | Part 3: GDN conv path fusion (concat + 5 snapshot cpys + get_rows → ssm_conv) | −1.8…2.1 ms → +4.5–5 % | medium | low | bitwise |
| A6 | Part 4: quantize_q8_1 fused into producers + attention-layer trimming | −1.4…1.7 ms → +3.5–4 % | medium | low | yes |
| A7 | Zero-code A/Bs: `-bs`, `-ctkd/-ctvd q4_0`, `ROCBLAS_USE_HIPBLASLT=1`, `-ub 1024/2048`, CPU governor | 0.7–1.4 ms/step (`-bs`); −0.6 GB VRAM; prefill 1–4 % | hours | low | yes (see notes) |
| A8 | Upstream cherry-picks: #30103, #30329, #30139, #29768, #30198-style cont removal | −0.4…1.0 ms/step plus a correctness fix | low | low | yes |
| A9 | n-gram + MTP hybrid for code/agents (config now, `n_rs_seq` patch later) | code edits +23 % (config) … +75 % (patch); chat 0 | config / 30 LOC | low | yes |
| A10 | Host-path fixes: batched input uploads + sched split, KQ mask at long context, per-request fixed cost | −0.5…0.9 ms/step; −1…3 ms/step at 94k; −40…80 ms TTFT | medium | low | yes |
| A11 | Undervolt via OverDrive (thermal/longevity first) | junction temperature down; prefill +0–5 % under the 285 W cap [INFERENCE] | root + reboot | low-med | yes |

### A1. Prompt caching and context checkpoints: biggest E2E win, zero code
- **Facts** (`rr-prefill-kv.md` F2):
  - Prefix reuse restores the newest checkpoint at or before the LCP (server-context.cpp:3589-3591, 3726-3771).
  - Checkpoints are only taken at user-message starts spaced ≥ `-cms` apart (default 8192), at the last user message, and at n−4−ub / n−4 (server-context.cpp:3865-4062; common.h:641-644).
  - `--cache-ram` defaults to 8 GiB, which holds about 2 long conversations. One 94k conversation ≈ 1.74 GB q4_0 KV + 0.39 GB f16 MTP KV + 150 MB recurrent state + checkpoints.
  - Speculative rollback does **not** use these checkpoints (`spec_ckpt` + n_rs_seq snapshots, server-context.cpp:3351-3434), so more checkpoints cost no decode speed.
- **Add to run-llm.sh:**
  ```
  --cache-ram 32768 --ctx-checkpoints 96 -cms 2048 --slot-save-path ~/qwen-opt/slots
  ```
  - Keep `--cache-reuse 0` and `--reasoning-preserve`, and make the client send `reasoning_content` back.
- **Gain:**
  - 94k document follow-up: 142 s of re-prefill → ~0.3 s restore. E2E 165 s → ≈23–25 s.
  - Agent history edit: lost work drops from ~4.1k tokens on average (≈4.5 s) to ~1k (≈1.1 s).
  - hipEngine measured 2.79× E2E on coding-agent replay with prefix reuse ([README](https://github.com/shisa-ai/hipEngine)).
- **Verify:**
  - The log shows "restored context checkpoint".
  - Read the real checkpoint size from the `created context checkpoint … size=` line (server-context.cpp:2581).
  - Run `greedy_check.sh` on a restored follow-up against a fresh prefill.

### A2. GQA q4_0 FA (in progress): scope additions found in code
- **Floor vs measured:**
  - One forward reads ≥ L × 18,432 B of KV: 0.57 ms at 29.5k, 1.81 ms at 94k.
  - Measured step growth is +10.9 ms at 29.5k and +34.6 ms at 94k. Recoverable: ≈9.7 ms and ≈31 ms.
  - At ~75 % of bandwidth that gives **62 → ~73 t/s at 30k and 43 → ~65 t/s at 94k** (`rr-prefill-kv.md` F1).
- **Scope additions:**
  - **n=1 too.** VEC re-reads KV once per Q head: d32768 n1 is +3.6 ms ≈ 6 × 0.63 ms (NOTES.md:202; fattn.cu:713-716).
  - **The MTP draft context too.** Its blk.64 KV is f16 by default (common.h:350-351; run-llm.sh has no `-ctkd`) and takes TILE with ncols2=2 (KV read 3×), five passes per step.
  - **Split-K to 48–96 splits per KV head.** Only 4 KV heads; reuse `parallel_blocks` + `flash_attn_combine_results` (fattn-common.cuh:1191-1224, 1304-1312).
  - **16-B aligned row loads.** Each q4_0 row is 144 B and the token stride is 576 B, so no layout change is needed.
  - **Free the f16 scratch.** It reserves ≈839 MB at 204800 ctx (fattn.cu:722-756) and goes away once neither decode nor prefill converts.
- Peer `RocmFattnGqa` has been told.

### A3–A6. HIP kernel-count package (the planned "fusion" item, now concrete)
Source: `rr-hip.md` §1–8. Per-layer kernel sequences come from the trace: 35 kernels per GDN layer, 31 per attention layer. Do them in this order; the arithmetic assumes ≈3.3 µs per removed boundary plus the removed kernel time.

1. **A3. Bias/residual epilogue for multi-column mmvq.**
   - Today: fusion is gated to `ncols_dst==1` (ggml-cuda.cu:1845-1848; mmvq.cu:1583-1596). The multi-column kernel already loads `x_biases[ncols_dst]` (mmvq.cu:1216-1231).
   - Use a bias-only template flag; do **not** re-enable gate+up (measured −8 %).
   - −128 kernels → **−0.6 ms**.
2. **A4. GDN prologue fusion.**
   - Port open PR [#29187](https://github.com/ggml-org/llama.cpp/pull/29187): alpha/beta projections + softplus/sigmoid in one launch, Q8_0 supported, +7–13 % pp2–8 on Qwen3.8-27B (Blackwell).
   - Fold the q/k l2-norm (`build_gdn_l2_norm`, models.h:14-17) into `gated_delta_net.cu` (PurHur's gfx1151 fork does this: [GDN_TUNING.md](https://github.com/PurHur/llama.cpp-qwen35-rocm/blob/master/docs/GDN_TUNING.md)).
   - Read the initial state in place per [#30139](https://github.com/ggml-org/llama.cpp/pull/30139) (llama-graph.cpp:3661).
   - The m=48 alpha/beta pair costs 17.5 µs today. −384 kernels → **−2.3…2.6 ms**.
3. **A5. Conv/concat/snapshot fusion.**
   - `concat_non_cont` 11.8 µs + 5× `cpy_scalar` + conv `get_rows` → one fused SSM_CONV that writes the K snapshot windows.
   - The matcher follows the `ggml_cuda_try_gdn_cache_fusion` pattern (ggml-cuda.cu:2843-2903); the kernel goes in ssm-conv.cu; graph side is delta-net-base.cpp:502-521.
   - The negative src stride (`s_slot = K−t`) is why a single ggml view cannot do it.
   - −290…336 kernels → **−1.8…2.1 ms**. Plain decode gets −0.5 ms.
4. **A6. Remaining fusions.**
   - Fuse `quantize_q8_1` into rms_norm·w / swiglu / gate·mul producers. The output goes straight into the existing q8_1 cache slot (ggml-cuda.cu:4359, 4468, 4495). −256 kernels → **−1.0…1.2 ms**.
   - Attention-layer trimming → **−0.4…0.5 ms**:
     - an IMROPE path in `rms_norm_mul_rope` fusion (exists only for NORMAL/NEOX, ggml-cuda.cu:2780-2825; qwen35 uses `rope_multi`, qwen35.cpp:313-323);
     - rope+FWHT;
     - drop `ggml_cont_2d(gate)` at qwen35.cpp:307 and :592 (non-contiguous unary #29781 is already in tree).
5. **Then, optionally: `hipExtAnyOrderLaunch`** for provably independent neighbours.
   - API: `ggml_cuda_kernel_launch`, common.cuh:1724-1742; hip_ext.h:95-103. The barrier bit is cleared at rocvirtual.cpp:5125-5127.
   - 150–200 barriers remain after steps 1–4 → **−0.5 ms**.
   - Medium risk (races). First check that stream capture keeps the flag (`AMD_LOG_LEVEL=4` prints `barrier=` per packet).

- **Package total:**
  - 2188 → ~1050 kernels, **−6.5…7.5 ms/step** [INFERENCE].
  - Step 41.8 → ≈34.5 ms, i.e. **74.5 → ≈90 t/s mixed** (+19–22 %).
  - At 94k the same absolute saving applies: after A2, ~53 → ~46 ms, giving ≈71 t/s.
  - Plain decode gains ≈2–3 ms/token (GDN parts).
- **Checks:**
  - `test-backend-ops -o GATED_DELTA_NET|SSM_CONV|CONCAT|CPY|MUL_MAT|RMS_NORM|ROPE`;
  - greedy equality;
  - rocprofv3 kernel count and gap sum.

### A7. Zero-code A/Bs (one per `spec_sweep.sh` run)

| Knob | Why | Expected | Evidence |
|---|---|---|---|
| `-bs` (target backend sampling) | stepcost measured ~0.7–0.96 ms of CPU-sampling gap after catch-up plus a ~5 MB logits D2H per verify (5 × 248320 × 4 B ≈ 0.2 ms over PCIe 4.0 x16, link verified 16 GT/s x16). The earlier A/B was spoiled by CPU load (NOTES.md:185) | −0.7…1.4 ms/step → +2–3 % | All default chain samplers have `backend_apply`: penalties, top_k, top_p, min_p, temp, dist (llama-sampler.cpp:1519, 1719, 1882, 2104, 3203, 1399). It is disabled with grammar or `reasoning_control` (sampling.cpp:422-431); `--reasoning-effort` alone does not trigger that (it only sets the template). Lossless in distribution with sample-and-match verify [INFERENCE: penalty history across verify rows. Keep penalties neutral or check] |
| `-ctkd q4_0 -ctvd q4_0` | MTP KV f16 → q4_0 | −0.6 GB VRAM; −1…5 ms/step at ≥94k once A2 covers n=1 | common.h:350-351, arg.cpp:4109-4133. Only acceptance can move |
| `ROCBLAS_USE_HIPBLASLT=1` | Q6_K above 128 columns goes to dequant + hipBLAS on RDNA3 (mmq.cu:460-461) | prefill +0–2 % (UD), more on Q4_K_M (Q6_K is 17.5 % of its matmul FLOPs) | [PR #17576](https://github.com/ggml-org/llama.cpp/pull/17576) |
| `-ub 1024`, then `2048` (do after `-ctkd`, for VRAM) | amortizes Q6_K dequant (≤2.3 %), f16 KV conversion and launches per ubatch | prefill 0–3 % | MMQ is flat ub512→2048 on gfx1100 (#17576). Recurrent split is unaffected (llama-memory-hybrid.cpp:84-89) |
| `cpupower frequency-set -g performance` (governor is `schedutil` now) | serial host path: ~2 ms/step of inter-graph gaps + ~1.15 ms of uploads | 0–1.5 % [INFERENCE] | sysfs read 2026-10-12 |
| log `pp_dpm_fclk` during decode at 285 W | if FCLK drops below 2301 MHz under the cap, the IC/memory path slows | diagnostic | `rr-hip.md` §9 |

### A8. Upstream cherry-picks (merged after base, or open and small)
- **[#30103](https://github.com/ggml-org/llama.cpp/pull/30103):** FA MMA race fix (`fattn-mma-f16.cuh:1775`). It is used for prefill and any verify of ≥9 tokens on gfx1100. Correctness fix.
- **[#30329](https://github.com/ggml-org/llama.cpp/pull/30329):** graph-realloc counter. Diagnostic for the 2 ms of inter-graph host gaps. Pair it with #30223 (static backend-sampling graph across ubatches).
- **[#30139](https://github.com/ggml-org/llama.cpp/pull/30139):** in-place recurrent state read. −48 kernels and −6 MB traffic per GDN layer per step, ≈0.2–0.35 ms.
- **[#29768](https://github.com/ggml-org/llama.cpp/pull/29768):** no graph re-warm when n_kv crosses a 256 boundary, roughly every 85 steps (common.cuh:1458-1486; ggml-cuda.cu:4577-4596). 0.1–0.4 ms/step amortized, plus smoother latency.
- **#30141 / #30345 / #30311:** MTP hidden-state save/restore, masked-row selection, rollback guard. Prerequisites for the single-graph MTP chain (B3) and for n-gram drafts longer than n_rs_seq (A9).

### A9. n-gram + MTP hybrid for code editing and agent loops (`rr-engines-drafters.md` §3)
- **Mechanics:**
  - `--spec-type` is a priority list and the first non-empty draft wins (speculative.cpp:2716-2728, 2912-2967).
  - n-gram drafts are **not** capped by `--spec-draft-n-max` (server-context.cpp:517-535; speculative.cpp:2934-2944).
  - `n_rs_seq` follows the MTP n_max (common.h:403-409). Any longer draft triggers a ≈151 MB host recurrent checkpoint (server-context.cpp:3429-3447, 4433-4463).
- **Config now:**
  ```
  --spec-type ngram-mod,draft-mtp --spec-draft-n-max 4 \
  --spec-ngram-mod-n-match 16 --spec-ngram-mod-n-min 3 --spec-ngram-mod-n-max 4
  ```
  - n-match 16 comes from [rdna-boosts](https://github.com/stew675/llama-cpp-rdna-boosts/blob/main/benchmarks/2026-09-13-qwen38-unc-ngram-mod.md): the defaults never drafted.
- **Patch (~10–30 LOC):**
  - `n_rs_seq = max(MTP n_max, ngram cap ≤ 7)`, costing ≈+0.5 GB VRAM;
  - clamp non-model drafts at speculative.cpp:2934-2944;
  - optionally gate n-gram drafts on their recent acceptance.
- **Gain** (an n-gram step needs no MTP passes, so step ≈ 29.3 + 1.4·k ms [INFERENCE]):
  - Code rewrite with 80 % copied tokens: **85 → 121 t/s (cap 4) / 149 t/s (cap 7)**.
  - Agent decode: +5–20 %. Chat: ≈0, because the n-min gate keeps MTP in charge.
  - External checks:
    - KyaniteLabs MTP+ngram on Qwen3.8-27B UD-Q4_K_XL (Strix Halo): 164–168 t/s on verbatim replay vs 59–61 MTP-only, and +1.96 % on novel text (cited in `rr-engines-drafters.md` §2–3);
    - [ik_llama PR 1646](https://github.com/ikawrakow/ik_llama.cpp/pull/1646): ngram_mod +65 %.

### A10. Host-path fixes (HIP)
1. **Input uploads and split.**
   - Every `set_tensor` is an H2D blit plus a stream sync (ggml-cuda.cu:783-789): ≈1.15 ms per step across 10+ upload groups.
   - Every verify is also preceded by an 8-kernel prefix submission and a 120–155 µs gap. Diagnose with `GGML_SCHED_DEBUG=2` (ggml-backend.cpp:1950).
   - Fix: batch all inputs into one pinned async copy via `set_tensor_async` (ggml-cuda.cu:2534). **−0.5…0.9 ms/step**.
2. **KQ mask at long context.**
   - `set_input_kq_mask_impl` scans all n_kv cells on the CPU for the first row of each sequence (llama-kv-cache.cpp:1645-1715, verified).
   - That happens on about 6 evals per step (verify + catch-up + 4 drafts, each with a 94k-long KV), all on the serial path.
   - [INFERENCE] 1–3 ms/step at 94k. Measure with the timer at llama-kv-cache.cpp:1798 first.
   - Fix: cache the mask per context and rewrite only the tail, or build it on the GPU from `pos`.
3. **Per-request fixed cost** (TTFT for chat turns). A tiny prompt takes 150 ms without MTP and 230 ms with it (logs, `rr-prefill-kv.md` F3).
   - (a) The forced 4-token final split for the n−4 checkpoint (server-context.cpp:3986-4005) is a full ~40 ms forward. Take that state from the GDN rollback snapshots that already exist (gated_delta_net.cu:154-166): **−40 ms**, bit-identical.
   - (b) The MTP prompt hook (speculative.cpp:1557-1643) does a 20 KB/token h_nextn D2H plus a serialized ctx_dft decode of every prompt token: ≈+80 ms on tiny prompts. Also measure it at 30k/94k: rdna-boosts reports −23–28 % prefill with MTP on RDNA4; our pp4096 1044 vs server 924 hints 5–12 %.

### A11. Undervolt (OverDrive): longevity first, speed second
- **State:**
  - `ppfeaturemask` = 0xfff7bfff, so OverDrive is off. Enable it with `amdgpu.ppfeaturemask=0xfff7ffff` and a reboot (`rr-hip.md` §9).
  - SMU13 OD accepts `vo -N`, `s`, `m`, `f`, then `c` ([kernel doc](https://docs.kernel.org/gpu/amdgpu/thermal.html)).
  - The KFD already selects the COMPUTE power profile (amdgpu_amdkfd.c:751-769).
- **Why:**
  - Junction reached 106 °C at 281 W during a 196k prefill, with an edge-to-junction delta of ~40 °C (NOTES.md:134). Decode sits at the 285 W cap (NOTES.md:162).
  - `vo -50…-100 mV` lowers junction temperature at the same clocks, or raises sclk inside the same 285 W.
  - That helps compute-bound prefill (≈45 TFLOPS, power-capped) and the ~12 ms of sclk-sensitive small ops and gaps per verify [INFERENCE].
- **Expected:** prefill 0–5 %, decode 0–2 % [INFERENCE]. The main payoff is temperature.
- **Validate:** `greedy_check.sh` plus long prefill runs. Instability shows up as hangs or wrong tokens.
- The 40 °C edge-to-junction delta still suggests repaste/pads (hardware, outside software scope).

---

## B. Bigger bets (measure first, or multi-day)

| # | Item | Gain (arithmetic) | Effort | Risk |
|---|---|---|---|---|
| B1 | Verify width 9–16: measure ROCm step at 9/12/16 columns. If ≈ 29.3 + 1.4·k ms holds, extend multi-col MMVQ to 16 and add an adaptive draft ceiling (~12) for code/recall | rdna-boosts on RDNA4: code +28 %, recall +61 %, prose +13 % vs n3; at T=1 chat ≈0 (p≈0.64 caps it) | measure: 1 h; MMVQ to 16 cols: high | med (MMQ cliff today: n=8 p_min → 47 t/s, NOTES.md:159) |
| B2 | MTP head self-distillation (planned). New evidence: [KaedeTai/Qwen3.8-27B-MTP-zh](https://huggingface.co/KaedeTai/Qwen3.8-27B-MTP-zh) did hard self-distillation on a frozen 4-bit trunk (the same orca-family trunk): zh acceptance 56.8 → 62.6 %, EN/code flat | PL ≈ +6 pp acceptance → +0.23 tok/step on ≈2.8 → **+6–9 % PL** | high (1.5–2 days) | med |
| B3 | Single-graph MTP chain (planned). HIP 10 has **no conditional/while graph nodes** (hip_runtime_api.h:1859-1868), so it has to be an unrolled graph. Take #30141/#30345 first | 4 draft graphs at 1.17 ms wall / 0.88 ms busy plus catch-up gaps: ≈1.5–2.5 ms/step → +4–6 % | high | med |
| B4 | FA prefill at long context: a GQA-6 MMA tile (all 6 Q heads × 8–16 tokens) if a `--pmc` profile shows KV traffic as the limit | 94k prefill FA ≈37 s; 1.3–1.5× → −9…12 s (−6…8 %), 30k −3 % | med-high | med |
| B5 | Q6_K MMQ tuning for RDNA3 (mmq-config-rdna3.cuh:137-147), then flip mmq.cu:461 | prefill +3.5 % (Uncensored Q4_K_M, 17.5 % Q6_K), +1.8 % (UD) | high | low |
| B6 | MTP layer: sliding-window KV, or catch-up limited to the last W prompt tokens | prefill +2–5 % at ≥30k, decode +1–2 % at 94k [INFERENCE]; drafts only | med | acceptance on long-doc quotes |
| B7 | VRAM OC (`m 1 ~1350` MHz ≈ +8 % bandwidth, [7900 XTX OC write-up](https://medium.com/@opinali/overclocking-the-radeon-7900-xtx-4e963bd5cda1)) | matvec ~25 of 36.9 ms is bandwidth-bound → −1.5…2 ms → +3–5 % | root | GDDR6 instability (EDC retries, no ECC at rest), VRAM temperature; conflicts with the longevity goal, so do it after A11 |
| B8 | GDN prefill: software-pipeline per-token loads (gated_delta_net.cu:72) | +1–1.5 % prefill. A chunked (WY) kernel is capped at ≈2.7 %: GDN is 0.5–0.75 µs/token/layer, so the +7 % of #29353 on Strix Halo cannot happen here | low / high | chunked kernels from forks were non-deterministic (nasone32) |
| B9 | mmvq: `amdgpu_waves_per_eu` on multi-column instantiations; `slc` non-temporal weight loads (never `dlc`: 697 vs 1237 GB/s, [braidinfer](https://raw.githubusercontent.com/mcelrath/braidinfer/master/GFX1100_CACHE_HINTS.md)) | verify matvec runs at ~700 GB/s vs 81–88 % at n=1: 0–5 % of 25 ms → ≤1.2 ms | low each | low |
| B10 | DFlash2 probabilistic path (planned). New data: on Strix Halo the hipEngine survey found DFlash2 ≈ MTP on mixed prompts | lower the expectation to 0 … +10 % on EN chat | med | low |
| B11 | Snapshot-free rollback (replay from inputs, ReplaySSM / closed #29763) | ≤0.8 ms/verify of IC write-back | high | med |

---

## C. Avoid (with reason)

**Engines and big rewrites**
- **Switching engines.** The fork is already ahead of every measured alternative.
  - Only same-GPU, same-model comparison ([hipEngine artifact](https://github.com/shisa-ai/hipEngine/blob/main/benchmarks/results/2026-09-08-rx7900xtx-engine-comparison.json)): hipEngine 63.5 t/s greedy with MTP (and an MTP regression on 128-token outputs), nasone32 fork 58.6, strix fork 47.7. We are at 78.6 (T=0).
  - ik_llama.cpp: ROCm unsupported per its README, and it discourages `_XL` quants.
  - ExLlamaV3 ROCm: closed unmerged, ≈15 t/s ([#441](https://github.com/turboderp-org/exllamav3/pull/441)).
  - SGLang-radeon: no HIP graphs, TPOT 54 ms ([doc](https://github.com/AMD-AIM/sglang-radeon/blob/main/docs/qwen3.8-27b.md)).
  - vLLM ROCm: no batch-1 data, and 200k context does not fit in 24 GB.
  - Lemonade / Ollama / MLC / tinygrad: no delta, or no qwen35+MTP.
- **Megakernel / Mirage MPK / Hazy-style persistent decode.** Tooling is CUDA/Hopper-only. The only gfx1100 LLM megakernel ([braidinfer](https://github.com/mcelrath/braidinfer)) has a 2.79 µs persistent dispatch (not better than the 3.3 µs graph gap) and runs a 27B at 4.1 t/s. The ceiling is ~7 ms of gaps, which A3–A6 recover more cheaply.

**HIP and compiler knobs**
- **Wave64 rewrite:** HIP wave32 already wins on production-shaped dot kernels (ROCm #6409).
- **`dlc=1` loads:** about halves bandwidth on gfx1100.
- **HIP graph device launch / conditional nodes:** none in HIP 10, and they would not change the per-node CP cost.
- **`GGML_CUDA_GRAPH_OPT=1`, disabling graphs, CLR env knobs:** measured −1 % / −3 % / noise (NOTES.md:117-118).

**Lossy or wrong for qwen35**
- **`--cache-reuse N`:** not lossless for qwen35. The hybrid cache claims it can shift (llama-memory-hybrid.cpp:133-136), but the recurrent state keeps the removed span (llama-memory-recurrent.cpp:200-224).
- **`--cache-reuse-hybrid` (#29918):** lossy.
- **`--ctx-checkpoints 2`** (from another 7900 XTX recipe): only causes more full re-prefills in this tree.
- **BF16/F16 rollback snapshots:** change recurrent numerics.
- **Trunk requantization or INT4 WMMA activations:** change the model.

**Wrong build flags**
- **`GGML_CUDA_FORCE_MMQ`:** Q6_K becomes 25 % slower.
- **`GGML_CUDA_FORCE_CUBLAS`:** Q4_K/IQ4_XS become 6–17 % slower (#17576).
- **`GGML_HIP_ROCWMMA_FATTN`:** removed in #26046.
- **`MMQ_MFMA`:** CDNA only.

**KV cache options**
- **q8_0 KV:** 1.89× the bytes, so higher long-context floors.
- **f16 KV:** 13.4 GB, does not fit.
- **Lossy KV/context methods:** StreamingLLM, SnapKV, H2O, Quest, DMS, KV below 4 bit (KVarN-2/3, q3/q2).
- **BeeLlama precision tail:** it changes outputs, so it is a quality option only.

**Speculative-decoding variants**
- **Lookahead/Jacobi:** τ 1.69 vs 3.94 ([EAGLE-2](https://arxiv.org/abs/2406.16858)).
- **Tree drafts:** GDN rollback is chain-only.
- **Uncapped n-gram defaults (24/48/64):** they never draft, or they produce 49–65-token verifies plus host checkpoints.
- **`ngram-cache` with its fixed 8-token draft:** 9 columns.
- **New drafter repacks** (FrostDFlash, DFlash2-b32, NVFP4 heads, Qwen3.6 EAGLE-3): no gain or a target mismatch.
- **Polish 64k-vocab rebuild:** only 3.5 % of PL tokens are outside the list, so ≤1–2 %. Optional at most.

**System**
- **Lowering the power cap for speed, `pp_power_profile_mode`:** decode is at the cap, and KFD already sets COMPUTE.
- **NUMA/threads/hugepages:** single-socket CPU and fully offloaded model. `-t` and THP only affect load time or CPU ops, of which there are none [INFERENCE].
- **PCIe:** Gen4 x16 is verified, and only ~5 MB/step crosses it (removed by `-bs`).

---

## D. Projected outcome (if A lands; [INFERENCE], non-overlapping savings)

| Scenario | Today | After A2+A3–A6+A7(-bs)+A8 | Arithmetic |
|---|---|---|---|
| Short context, mixed T=1 | 74.5 t/s (41.8 ms) | **≈90–95 t/s** | −7 (fusion) −1 (`-bs`) −0.5 (picks) ≈ 33.3 ms → 3.11/33.3 |
| 29.5k decode (T=0) | 62.4 | ≈ 85–90 | 52.7 − 9.7 (A2) − 8.5 → ~34.5 ms → 3.29/0.0345 = 95 at 100 % FA efficiency; ~85 at 75 % |
| 94k decode (T=0) | 43.0 | ≈ 65–75 | 76.4 − 23…31 (A2) − 8.5 → 37–45 ms |
| 94k doc + 1000 tokens, first turn | 165 s | ≈ 150 s | prefill 142 s − (A7 ub/hipBLASLt 1–4 %) − (B4 later −9…12 s); decode 23 → ~14 s |
| Same doc, follow-up turn | 165 s | **≈ 15–25 s** | A1 restore ≈0.3 s + new-turn prefill + 14 s decode |
| Code rewrite (80 % copied) | ~85 t/s | 120–150 t/s | A9 |

## E. Measurement order for Main (cheap first; GPU runs belong to Main)
1. A1 flags; confirm the checkpoint restore lines and greedy equality on a 30k follow-up.
2. A7 A/Bs, one at a time: `-bs`, `-ctkd/-ctvd q4_0`, `ROCBLAS_USE_HIPBLASLT=1`, `-ub 1024/2048`, governor; plus FCLK logging.
3. Cherry-pick #30103 and #30329 and read `graph reallocs` during spec. Run `GGML_SCHED_DEBUG=2` once to find the verify prefix split.
4. ROCm step time at verify widths 6/8/9/12/16 (decides B1).
5. Server prefill at 30k/94k with and without `draft-mtp` (decides A10.3b and B6). Timer around `set_input_kq_mask` at 94k (A10.2).
6. Implement A3 → A4 → A5 → A6. After each: test-backend-ops, `greedy_check.sh`, rocprofv3 kernel count and gap sum.
