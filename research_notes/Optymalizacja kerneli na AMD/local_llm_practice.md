# Running and optimizing local LLMs on AMD Radeon consumer hardware (RDNA3 / RDNA4 / Strix Halo), as of October 2026

Research date: 2026-10-06. Every number below is tagged with the date and software version the source gave. Where the source gave no version, the entry says so. Several sources are 2026 community blogs (runaihome.com, seehiong, zolotukhin.ai) or AI-generated summaries (deepwiki). Treat those as medium-confidence, and prefer the llama.cpp GitHub discussions and issues, which are the primary sources.

Memory-bandwidth arithmetic used in this file: tg tokens/s × model bytes read per token ÷ peak bandwidth. Llama 2 7B Q4_0 = 3.56 GiB ≈ 3.83 GB. Peak bandwidth figures used: RX 7900 XTX 960 GB/s, RX 9070 XT / R9700 ~640 GB/s, Strix Halo 256 GB/s theoretical (212 GB/s measured), RTX 3090 936, RTX 4090 1008, RTX 5090 1792 GB/s. These spec values are background knowledge, not fetched in this session, except Strix Halo, R9700 and 640 GB/s, which appear in the sources cited below.

---

## 1. Engines and backends: which is best for which case

### Takeaway
llama.cpp is the default engine on Radeon, used directly or wrapped by Ollama, LM Studio, Lemonade or KoboldCpp. In 2026 its **Vulkan (RADV)** backend is usually the fastest or most stable choice for token generation on RDNA3, RDNA4 and Strix Halo. **ROCm/HIP** can match or beat Vulkan on prompt processing, and on some dense, long-context or quantized-KV workloads. vLLM on RDNA4 works but is still patch-heavy. ik_llama.cpp and upstream ExLlamaV3 are effectively NVIDIA-first. Lemonade with FastFlowLM is the only practical route to the NPU.

### Cited Findings

**llama.cpp HIP vs Vulkan**
- On RDNA4, Vulkan beats ROCm 7.2 on decode by a wide margin (Llama 2 7B Q4_0, July 2026). RX 9070 XT: tg128 137.1 (Vulkan) vs 101.3 (ROCm). R9700: 138.8 vs 98.0, both with FA. Prefill is roughly a tie on the 9070 XT (5,036 vs 5,055 pp512). On the R9700, Vulkan leads prefill 5,620 vs 4,773 (FA). — [runaihome, RDNA4 Vulkan vs ROCm 7.2 (2026)](https://runaihome.com/blog/rdna4-vulkan-vs-rocm-local-llm-benchmark-2026/)
- The same source puts lower-tier RDNA4 the same way (July 2026, Llama 2 7B Q4_0). RX 9070: Vulkan 119.7 tg / 3,164 pp vs ROCm 114.5 / 2,382. RX 9060 XT: Vulkan 70.5 / 2,142 vs ROCm 67.6 / 1,480. — [runaihome](https://runaihome.com/blog/rdna4-vulkan-vs-rocm-local-llm-benchmark-2026/)
- It also has a counterexample for dense models (July 2026). On the R9700, Qwen3.6-27B (Q8-class, quantized KV) ran 42.8 tok/s decode / 960 pp on ROCm 7.2 vs 29.1 on Vulkan, so ROCm was "47% faster" there. The article's recommendation: "Vulkan first" for the 9070 XT on 7B–14B models and MoE; keep both builds on the R9700 if you run dense 27B+ models. — [runaihome](https://runaihome.com/blog/rdna4-vulkan-vs-rocm-local-llm-benchmark-2026/)
- On the RX 7900 XTX (gfx1100), ROCm token generation is 15–25% below Vulkan (llama.cpp issue #20934, March 2026, ROCm 6.4.4 / 7.1.1 / 7.2 / 7.9 vs RADV, Ubuntu 24.04). Llama 7B Q4_0: Vulkan ~167–177 tg128 vs ROCm ~129–144 tg128 (ROCm pp ~4,000–4,400). The reporter saw "bursty GPU utilization" on ROCm. No root cause was identified and the issue is still bug-unconfirmed. — [llama.cpp #20934](https://github.com/ggml-org/llama.cpp/issues/20934)
- A 2026 article reports that on the 7900 XTX with Qwen3.6-27B, ROCm was better at prompt processing but Vulkan was ~30% faster at generation. — [XDA via search snippet](https://www.xda-developers.com/replaced-chatgpt-local-model-beating-cloud-didnt-expect/) (snippet only; not fetched)
- Strix Halo (gfx1151) toolbox benchmarks: Vulkan RADV 881 pp512 / 52.8 tg128 vs HIP + hipBLASLt 765 / 45.0. Across the model set, Vulkan AMDVLK and ROCm 6.4.4 + hipBLASLt each took 6 first places in pp, and RADV took 10 first places in tg. — [deepwiki summary of kyuz0 toolboxes benchmarks](https://deepwiki.com/kyuz0/amd-strix-halo-toolboxes/4.1-benchmark-results) (AI-generated summary of [kyuz0/amd-strix-halo-toolboxes](https://github.com/kyuz0/amd-strix-halo-toolboxes))
- The kyuz0 README calls `vulkan-radv` "most stable and compatible. Recommended for most users and all models." It also ships `rocm-10.0` (described as the latest stable ROCm Core SDK for gfx1151), `therock-nightly`, and several experimental images. — [kyuz0/amd-strix-halo-toolboxes](https://github.com/kyuz0/amd-strix-halo-toolboxes)

**Ollama / LM Studio / Lemonade / KoboldCpp**
- Lemonade orchestrates llama.cpp (GGUF via Vulkan/ROCm), FastFlowLM (NPU-native, XDNA2), OnnxRuntime GenAI (ONNX, hybrid NPU+iGPU), whisper.cpp, stable-diffusion.cpp and Kokoro TTS. Version timeline: v10.7 (June 2026) added CUDA, v11.0 (15 July 2026) added a Metal backend, v11.7 (19 August 2026). — [runaihome Lemonade guide 2026](https://runaihome.com/blog/amd-lemonade-local-llm-server-npu-gpu-guide-2026/)
- The same guide recommends Lemonade for Ryzen AI 300+ owners who want fast time-to-first-token, and calls Ollama "safer" on discrete Radeon because of its broader model library. — [runaihome Lemonade guide](https://runaihome.com/blog/amd-lemonade-local-llm-server-npu-gpu-guide-2026/)
- Lemonade's documentation has a dedicated llama.cpp backend-options page (Vulkan/ROCm selection). — [Lemonade docs](https://lemonade-server.ai/docs/guide/configuration/llamacpp/) (found in search; not fetched)
- In an October 2025 Strix Halo test, Lemonade's ONNX path was limited to ONNX models, ~2,000–3,000 token context and models up to ~8B. That limitation is dated, and FastFlowLM has since improved context (see section 5). — [hardware-corner, 17 Oct 2025](https://www.hardware-corner.net/strix-halo-llm-optimization/)

**vLLM on Radeon (RDNA3/RDNA4)**
- vLLM PR #56005 adds FlyDSL FP8 block-scaled GEMM kernels for RDNA4 (gfx1200/gfx1201). On the R9700 they passed all 18 shapes against Triton and were faster in every case, at a 1.786× geometric mean. — [vllm PR #56005](https://github.com/vllm-project/vllm/pull/56005)
- vLLM PR #58238 adds a W8A8 FP8 HIP kernel for gfx1201 (fast prefill and decode) to replace the default Triton path. — [vllm PR #58238](https://github.com/vllm-project/vllm/pull/58238)
- Issue #28649 asked for a gfx1201 FP8 patch to be upstreamed. The FP8 path had worked "since November", but only behind an out-of-tree patch. — [vllm #28649](https://github.com/vllm-project/vllm/issues/28649)
- Issue #40081: vLLM fails to start on RDNA4 inside containers (amdsmi, circular import and `torch.cuda.device_count()` all broken). — [vllm #40081](https://github.com/vllm-project/vllm/issues/40081)
- Head-to-head on the RX 9070 XT with Qwen3.5-9B (July 2026): llama.cpp Vulkan with Q6_K GGUF gave 62 tok/s, vLLM with FP8 gave 48 tok/s. vLLM was reported to "silently dequantize to FP32" (refers to vllm#28649). — [runaihome](https://runaihome.com/blog/rdna4-vulkan-vs-rocm-local-llm-benchmark-2026/); [ivangotoy/llama-server-rdna4-vulkan](https://github.com/ivangotoy/llama-server-rdna4-vulkan)
- A community Nix build of vLLM for gfx1201/R9700 adds native W4A16/W8A16 weight-only kernels plus FP8, MXFP4 and ParoQuant. — [ewtodd/vllm-radiance-nix](https://github.com/ewtodd/vllm-radiance-nix)
- Strix Halo: the PyTorch + flash-attention + vLLM effort is ongoing (Framework community thread). gfx1151 PyTorch flash attention was an open TheRock issue. — [Framework community](https://community.frame.work/t/pytorch-w-flash-attention-vllm-for-strix-halo/74736); [TheRock #1364](https://github.com/ROCm/TheRock/issues/1364)

**ExLlamaV3 / ik_llama.cpp**
- Upstream exllamav3 is CUDA-only: its EXL3 kernels use mma.sync, ldmatrix, cp.async and cooperative launches, and TabbyAPI refuses AMD GPUs. Community ports (wtogami/bsvinay/rti `exllamav3-rocm`) add RDNA3-specific EXL3 matmul and decode-attention kernels. They support DFlash2/MTP speculative decoding, vision, and 8-bit KV at 192K–256K context on a 24 GB 7900 XTX. — [wtogami/exllamav3-rocm](https://github.com/wtogami/exllamav3-rocm)
- ik_llama.cpp: ROCm and Vulkan "are not the focus", and users hit ROCm build errors (June 2025 discussion). — [ik_llama.cpp discussion #562](https://github.com/ikawrakow/ik_llama.cpp/discussions/562)

### Inferences
- Practical decision tree as of October 2026:
  - Single Radeon, GGUF models, max decode speed → llama.cpp Vulkan (RADV, recent Mesa).
  - Dense 27B+ with long context or quantized KV on RDNA4/RDNA3 → also benchmark a ROCm 7.2+ build, because the results conflict.
  - Strix Halo → kyuz0 `vulkan-radv` toolbox as the baseline, plus a ROCm toolbox for long-context prefill.
  - NPU → Lemonade + FastFlowLM.
  - Batched serving or FP8 safetensors → vLLM only on RDNA4, with patches.
  - EXL3 on a 7900 XTX → community port only.
- Ollama and LM Studio inherit llama.cpp performance, but they lag upstream builds and expose fewer knobs (e.g., rocWMMA build flags, -ub). A hand-built llama.cpp is the ceiling.

### Gaps
- No fetched 2026 data for SGLang on Radeon, MLC-LLM (Vulkan/ROCm), or KoboldCpp-ROCm. Their RDNA4 status was not verified.
- No first-party AMD statement on official vLLM support for RDNA3 vs RDNA4 was fetched.
- No direct benchmarks of Ollama or LM Studio vs upstream llama.cpp on the same Radeon were found.

---

## 2. Quantization formats and kernels on AMD

### Takeaway
On Radeon, GGUF Q4_0, Q4_K and Q8_0 are the safest fast formats. Mixed "UD" quants and odd KV types underperform. RDNA4 has native FP8 and INT4/INT8 WMMA but **no native FP4**, so MXFP4 (gpt-oss) saves bandwidth but gets no compute speedup over FP16. Flash attention is generally on. The rocWMMA FA path helps RDNA3 but **regresses on gfx1151** in 2026 builds.

### Cited Findings
- RDNA4 (gfx1201, R9700) native WMMA throughput: FP16/BF16 191 TFLOPS, FP8 (E4M3, E5M2) 383 TFLOPS, INT8 383 TOPS, INT4 766 TOPS. There is "no native WMMA instruction" for FP4. MXFP4 is dequantized to FP16 in a fused prelude and then run on `v_wmma_f32_16x16x16_f16`, so it is capped at the FP16 ceiling. — [zolotukhin.ai, 9 May 2026](https://zolotukhin.ai/blog/2026-05-09-the-fp4-wave-breaks-at-rdna4-and-fp8-wmma-already-does-what-local-qwen3-needs/)
- Triton on gfx1201 automatically emits `v_wmma_f32_16x16x16_fp8_fp8` for FP8 ops. RDNA4 uses the same E4M3FN format as MI350X, so datacenter FP8 kernel work is reusable. — [vLLM forum, native FP8 WMMA on RDNA4](https://discuss.vllm.ai/t/native-fp8-wmma-support-for-amd-rdna4-rx-9070-xt-r9700-in-vllm/1900/2); [vllm #28649](https://github.com/vllm-project/vllm/issues/28649)
- Community FP8 results on gfx1201 with the patch (date and versions not given): Qwen3-0.6B 160–200 tok/s decode, Qwen3-30B-2507 52–85 tok/s decode, and prefill "nearly doubled" up to 10k-token prompts. — [zolotukhin.ai](https://zolotukhin.ai/blog/2026-05-09-the-fp4-wave-breaks-at-rdna4-and-fp8-wmma-already-does-what-local-qwen3-needs/)
- R9700 tuning thread (llama.cpp discussion #21043, March–September 2026):
  - Recommended model formats: Q8_0 or Q4_K.
  - KV cache: q4_0 is "vastly superior to q4_1, q5_x, iq4_nl".
  - "Mixed-precision UD-Q4_K_XL underperforms on ROCm".
  - At 65,536 context you need q4_0 KV; at 40,000 context q8_0 KV fits (32 GB card).
  - [llama.cpp discussion #21043](https://github.com/ggml-org/llama.cpp/discussions/21043)
- The same thread gives kernel-level reasons why Vulkan Q4_K decode does not reach peak bandwidth: the ACO compiler emits 31 redundant `s_wait_kmcnt` per Q4_K shader, and a 144 B Q4_K block in 192 B lines gives 75% cache-line utilization. — [llama.cpp discussion #21043](https://github.com/ggml-org/llama.cpp/discussions/21043)
- Vulkan env var `GGML_VK_DISABLE_MMVQ=1` (disables the quantized mat-vec path, i.e. dequant + float mat-vec) gave +0.5–0.8% decode on the R9700. `GGML_VK_DISABLE_COOPMAT=1` gave +17% on AMDVLK dense prefill, as a workaround for AMDVLK's 4× slower dense prefill (207 vs 823 tok/s on 27B). — [llama.cpp discussion #21043](https://github.com/ggml-org/llama.cpp/discussions/21043)
- A one-line change, `rm_kq=1` (Vulkan FA shader parameter), cuts VGPR pressure on RDNA4 wave32: +13% dense decode on AMDVLK, +1.1% on RADV MoE. — [llama.cpp discussion #21043](https://github.com/ggml-org/llama.cpp/discussions/21043)
- Flash attention, discrete cards (Llama 2 7B Q4_0):
  - Vulkan scoreboard: FA raised 7900 XTX tg from 182.6 to 190.9 and pp from 3,727 to 3,890. FA slightly lowered 7900 XT and 9070 XT tg (123.2→120.6 and 137.1→131.5). FA raised R9700 pp/tg from 5,610/145.7 to 5,908/152.7.
  - ROCm scoreboard: 7900 XTX pp 3,552→3,874 and tg 167.1→170.1 with FA.
  - [Vulkan scoreboard #10879](https://github.com/ggml-org/llama.cpp/discussions/10879); [ROCm scoreboard #15021](https://github.com/ggml-org/llama.cpp/discussions/15021)
- `-DGGML_HIP_ROCWMMA_FATTN=ON` "significantly improves flash attention performance on RDNA3+ and CDNA". — [ROCm scoreboard #15021](https://github.com/ggml-org/llama.cpp/discussions/15021); runaihome also recommends it for ROCm 7.2 on RDNA3+ ([link](https://runaihome.com/blog/rdna4-vulkan-vs-rocm-local-llm-benchmark-2026/))
- **gfx1151 exception**: llama.cpp issue #24437 reports that `GGML_HIP_ROCWMMA_FATTN=ON` causes a severe prefill regression with FA on Strix Halo. Against non-FA: rocWMMA ON gave −19% at pp512, −22% at pp2048 and −41% at pp8192; rocWMMA OFF gave −10%, −0.4% and −2.4%. The rocWMMA path was ~2.4× slower on prefill at 8k for dense Qwen3.5-27B and MoE Qwen3.6-A3B. Advice: on gfx1151, do not enable it. — [llama.cpp #24437](https://github.com/ggml-org/llama.cpp/issues/24437)
- That conflicts with earlier (2025) lhl / llm-tracker results on gfx1151. There, rocWMMA kept pp8192 at 368.8 t/s vs 245.6 without it, and lhl's rocWMMA FATTN tuning improved decode at depth by 33–104%. That patch no longer applies cleanly to master. — [llm-tracker Strix Halo](https://llm-tracker.info/_TOORG/Strix-Halo); [#24437 / search summary](https://github.com/ggml-org/llama.cpp/issues/24437)
- hipBLASLt on Strix Halo is crucial for HIP prompt processing (Llama 2 7B Q4_0, 2025, ROCm 6.4/6.5 nightly):

  | HIP configuration | pp512 | tg128 |
  |---|---|---|
  | HIP + FA | 332 | 45.8 |
  | HIP + rocWMMA + FA | 344 | 50.9 |
  | HIP + rocWMMA + FA + hipBLASLt (`ROCBLAS_USE_HIPBLASLT=1`) | 986 | 50.6 |
  | Vulkan + FA | 884 | 52.7 |

  gfx1151 rocBLAS kernels were 2.5–6× slower than gfx1100 equivalents. — [llm-tracker Strix Halo (lhl)](https://llm-tracker.info/_TOORG/Strix-Halo)
- GEMM efficiency on gfx1151: the baseline reached 5.1 TFLOPS of 57–59 theoretical FP16 (8.9%). Optimized Docker builds reached 36.9 TFLOPS (64.4%). — [llm-tracker Strix Halo](https://llm-tracker.info/_TOORG/Strix-Halo)
- gpt-oss MXFP4 on Strix Halo (October 2025): GPT-OSS-20B MXFP4 pp512 was 1,533.7 on ROCm 6.4.4 vs 1,914.7 on Vulkan AMDVLK. — [hardware-corner](https://www.hardware-corner.net/strix-halo-llm-optimization/)
- A Blackwell-only native-MXFP4 path exists in llama.cpp (NVIDIA forum on the experimental PR). AMD consumer GPUs dequantize instead. — [NVIDIA forum](https://forums.developer.nvidia.com/t/llama-cpp-experimental-native-mxfp4-support-for-blackwell-pr/355639) (search result only); RDNA4 behaviour per [zolotukhin.ai](https://zolotukhin.ai/blog/2026-05-09-the-fp4-wave-breaks-at-rdna4-and-fp8-wmma-already-does-what-local-qwen3-needs/)

### Inferences
- Decode is memory-bound, so quant choice mostly matters through bytes per weight and kernel efficiency. Q4_0 and Q4_K have the most-tuned MMVQ/MMQ shaders on both backends. IQ quants decode via lookup tables and are, by community experience, usually somewhat slower per byte on AMD. This is not directly benchmarked in fetched sources (see Gaps).
- On RDNA4, FP8 (W8A8) is the only low-precision format with a real compute uplift (2× FP16) for prefill and batched serving. INT4 WMMA (766 TOPS) exists but no mainstream engine was shown using it for W4A4.
- On gfx1151, build two binaries (rocWMMA ON and OFF) and benchmark at your actual context depth, because the 2025 and 2026 findings disagree.

### Gaps
- No fetched head-to-head of GGUF IQ2/IQ3/IQ4_XS vs Q4_K_M kernel speed on AMD in 2026.
- No data on AWQ/GPTQ kernel speed on ROCm consumer cards, apart from the vllm-radiance W4A16 mention.
- I found no source quantifying MMQ vs the dequant + hipBLAS(Lt) path crossover batch size on RDNA3/RDNA4. Only the Strix Halo hipBLASLt pp effect above is sourced.

---

## 3. Benchmark numbers (pp512 / tg128) and % of memory bandwidth

### Takeaway
On Llama 2 7B Q4_0, Radeon decode on Vulkan is roughly equal to RTX 3090/4090: 7900 XTX ~191 tg vs 4090 ~190. Prefill is far behind Ada and Blackwell: ~3.9k (7900 XTX) and ~5.9k (R9700) vs ~10.8k (4090). Strix Halo gets ~50 tg on 7B and ~49 tg on gpt-oss-120b. Best-case AMD decode reaches roughly 75–90% of peak DRAM bandwidth on dense models and ~56–61% on MoE.

### Cited Findings

**Llama 2 7B Q4_0, llama.cpp Vulkan scoreboard** (builds as listed; the scoreboard does not give dates in this summary) — [discussion #10879](https://github.com/ggml-org/llama.cpp/discussions/10879)

| GPU | FA | pp512 | tg128 | build | approx. % of peak BW in tg (my calc) |
|---|---|---|---|---|---|
| RX 7900 XTX | 0 / 1 | 3,727 / 3,890 | 182.6 / 190.9 | 304665f | ~73% / ~76% of 960 GB/s |
| RX 7900 XT | 0 / 1 | 2,942 / 2,701 | 123.2 / 120.6 | 71e74a3 | ~59% of 800 GB/s (spec assumed) |
| RX 9070 XT | 0 / 1 | 5,036 / 5,048 | 137.1 / 131.5 | e9fd8dc | ~82% of 640 GB/s |
| Radeon AI PRO R9700 | 0 / 1 | 5,610 / 5,908 | 145.7 / 152.7 | dd1ea52 | ~87% / ~91% of 640 GB/s (suspiciously high; maybe higher memory clock or GiB vs GB in the size) |
| RTX 3090 (coopmat2) | 0 / 1 | 4,666 / 5,201 | 164.1 / 171.6 | d05fe1d | ~70% of 936 GB/s |
| RTX 4090 (coopmat2) | 0 / 1 | 9,452 / 10,830 | 188.0 / 190.1 | 4ae88d0 | ~72% of 1008 GB/s |
| RTX 5090 (coopmat2) | 0 / 1 | 10,382 / 11,796 | 263.6 / 273.7 | ca71fb9 | ~58% of 1792 GB/s |

**Llama 2 7B Q4_0, llama.cpp ROCm/HIP scoreboard** (ROCm 6.4 to 7.0 preview) — [discussion #15021](https://github.com/ggml-org/llama.cpp/discussions/15021)

| GPU | FA | pp512 | tg128 |
|---|---|---|---|
| RX 7900 XTX | 0 / 1 | 3,552 / 3,874 | 167.1 / 170.1 (~68% BW) |
| Pro W7900 | 0 / 1 | 3,213 / 3,472 | 121.2 / 127.4 |
| RX 7900 XT | 0 / 1 | 3,098 / 3,261 | 116.2 / 112.3 |
| MI300X (reference) | 0 / 1 | 11,476 / 11,945 | 232.9 / 218.5 |

**RDNA4, July 2026 (ROCm 7.2 vs Vulkan)**
- See section 1 for the 9070 XT, R9700, 9070 and 9060 XT figures. — [runaihome](https://runaihome.com/blog/rdna4-vulkan-vs-rocm-local-llm-benchmark-2026/)
- An older RX 9070 XT result on RADV 26.2.2 gave pp512 2,845 / 3,228 and tg128 71.1 / 74.0 (FA off / on). The model was not identified in the snippet and is likely larger than 7B. — [openbenchmarking via search snippet](https://openbenchmarking.org/result/2509078-NE-ROCMVSVUL92)

**R9700 (32 GB), llama.cpp Vulkan, 2026** — [discussion #21043](https://github.com/ggml-org/llama.cpp/discussions/21043)

| Model | Configuration | Prefill | Decode (tg128) |
|---|---|---|---|
| Qwen3.5-35B-A3B (MoE) | stock → tuned | pp2048 2,381 → 3,075 | 147 → 163.7; 127 stock → 156 with `-ub 2048 -b 16384` per [runaihome](https://runaihome.com/blog/rdna4-vulkan-vs-rocm-local-llm-benchmark-2026/) |
| Qwen3.5-27B (dense) | — | pp2048 799–993 | 29–33.2 |
| Qwen3.6-27B, dual R9700 | — | pp512 812–820 | 33–36 |
| Qwen3.8-27B Q8_0, single R9700 | baseline → MTP (spec-draft-n-max=7) | — | 59.2 → 64.95 (+9.7%), acceptance 77–95% |

- Bandwidth efficiency on the R9700: dense models reach 79–83% of the 640 GB/s peak, MoE only 56–61% (expert-routing dispatch overhead). — [discussion #21043](https://github.com/ggml-org/llama.cpp/discussions/21043)

**Strix Halo (Ryzen AI Max+ 395, Radeon 8060S, 40 CU, 128 GB LPDDR5X-8000)**

| Model | Backend / version | pp512 | tg128 | Source |
|---|---|---|---|---|
| Llama 2 7B Q4_0 | Vulkan + FA | 884 | 52.7 | [llm-tracker / lhl](https://llm-tracker.info/_TOORG/Strix-Halo) |
| Llama 2 7B Q4_0 | HIP + rocWMMA + FA + hipBLASLt | 986 | 50.6 | [llm-tracker / lhl](https://llm-tracker.info/_TOORG/Strix-Halo) |
| Llama 2 7B Q4_0 | CPU | 295 | 28.9 | [llm-tracker / lhl](https://llm-tracker.info/_TOORG/Strix-Halo) |
| Qwen3 30B (MoE A3B) | HIP + rocWMMA + FA + hipBLASLt | 547.8 | 60.3 | [llm-tracker / lhl](https://llm-tracker.info/_TOORG/Strix-Halo) |
| Llama 2 7B Q4_0 | Vulkan RADV / HIP + hipBLASLt | 881 / 765 | 52.8 / 45.0 | [kyuz0 via deepwiki](https://deepwiki.com/kyuz0/amd-strix-halo-toolboxes/4.1-benchmark-results) |
| Gemma-3-4B Q3_K_S | ROCm 6.4.4 / AMDVLK | 2,262 / 1,150 | — | [hardware-corner, Oct 2025](https://www.hardware-corner.net/strix-halo-llm-optimization/) |
| Llama-2-7B Q4_0 | ROCm 6.4.4 / AMDVLK | 1,117 / 1,380 | — | [hardware-corner](https://www.hardware-corner.net/strix-halo-llm-optimization/) |
| Gemma-3-12B Q8_K_XL | ROCm 6.4.4 / AMDVLK | 814 / 660 | — | [hardware-corner](https://www.hardware-corner.net/strix-halo-llm-optimization/) |
| GPT-OSS-20B MXFP4 | ROCm 6.4.4 / AMDVLK | 1,534 / 1,915 | — | [hardware-corner](https://www.hardware-corner.net/strix-halo-llm-optimization/) |
| Llama-3.3-70B Q8_K_XL | ROCm 6.4.4 / AMDVLK | 105 / 99 | ~5 | [hardware-corner](https://www.hardware-corner.net/strix-halo-llm-optimization/) |

- August 2026 Strix Halo results (llama.cpp b10440 / 6b4344ecc, HIP 7.1.52801, kernel 7.0, Ubuntu 26.04, `-fa on -ngl 99`). Note these "prompt" numbers are at the listed context, not pp512. — [seehiong, Aug 2026](https://seehiong.github.io/posts/2026/08/running-llama.cpp-on-amd-strix-halo/)

  | Model | Prompt t/s | Generation t/s |
  |---|---|---|
  | Llama 2 7B Q4_K_M | 581.5 | 43.6 |
  | Qwen 3.8 27B Q4_K_XL @ 8k | 177.3 | 11.3 |
  | Qwen 2.5 72B Q5_K_M | 102.0 | 4.1 |
  | Qwen 2.5 72B Q6_K | 73.4 | 3.7 |
  | **GPT-OSS-120B MXFP4 @ 8k** | **165.9** | **49.0** |

- Other gpt-oss-120b figures on Strix Halo: ~48 tok/s with a stable 128K context (96 GB box, llama.cpp Vulkan, Ubuntu 26.04) — [agledger](https://agledger.ai/blog/local-llm-strix-halo-ubuntu-26-04/). 31.41 tok/s in another configuration (conflicting; settings unknown) — [datahardware.ai](https://datahardware.ai/blog/strix-halo-tokens-per-second-2026). ~50 t/s via Lemonade — [runaihome Lemonade](https://runaihome.com/blog/amd-lemonade-local-llm-server-npu-gpu-guide-2026/).
- Strix Halo, kyuz0 `rocm-10.0-strix-llama` image: Qwen3.8-Flash-Next Q4_K_XL ran pp2048 1,207 t/s at depth 0, 1,055 t/s at depth 32k, and 43.9 t/s decode. — [kyuz0 README](https://github.com/kyuz0/amd-strix-halo-toolboxes)
- Strix Halo bandwidth: rocm_bandwidth_test measured 212 GB/s GPU-internal and 84 GB/s CPU↔GPU. At ~50 tok/s on the 3.56 GB 7B quant, llama.cpp achieves "about 180 GB/s" (~85% of 212 measured; ~70–79% of 256 theoretical, my calc). — [llm-tracker](https://llm-tracker.info/_TOORG/Strix-Halo); hardware-corner quotes ~215 GB/s ([link](https://www.hardware-corner.net/strix-halo-llm-optimization/))

**Multi-GPU**
- Dual R9700 (llama.cpp Vulkan, 2026): decode drops ~26% vs a single card on a model that fits on one. Prefill scales better (+34–50% at large context). MTP acceptance degrades on a second concurrent thread. — [discussion #21043](https://github.com/ggml-org/llama.cpp/discussions/21043)

### Inferences
- gpt-oss-120b on Strix Halo at ~49 t/s implies roughly 2.5–3 GB of weights read per token (5.1B active, MXFP4 plus higher-precision attention). That works out to roughly 125–150 GB/s, about 50–60% of 256 GB/s, consistent with the 56–61% MoE efficiency measured on the R9700.
- For 7B-class decode, the 9070 XT / R9700 on Vulkan (~137–153 tg) roughly equals a 3090 (~172) per dollar or watt, but trails the 7900 XTX (~191) because of lower bandwidth (640 vs 960 GB/s). The R9700's selling point is 32 GB, which fits 27–32B Q8 or 30B-A3B with long context.
- Prefill is where AMD consumer parts lose most to NVIDIA: the 4090 is ~2–2.8× the 7900 XTX and ~1.8× the R9700 at pp512.

### Gaps
- No fetched 2026 numbers for Llama 3.x 8B specifically, Qwen3-Next-80B-A3B, or GLM-4.5-Air on Radeon or Strix Halo.
- No fetched multi-GPU tensor-parallel numbers (vLLM TP=2 on 2×R9700 or 2×7900 XTX). Only llama.cpp layer split, from #21043.
- No fetched 7900 XTX Qwen3-30B-A3B number. A modelfit.io page claims "~72 tok/s top pick" for a 32B on the 7900 XTX, but it is an estimator site and not used.
- The R9700 Vulkan tg (152.7) implying ~91% of 640 GB/s is suspicious and could not be verified.

---

## 4. Performance tips: build flags, env vars, kernel parameters, runtime flags

### Takeaway
The high-value knobs:
- **`-fa 1`, `--no-mmap` and `-ngl 999`**, especially on Strix Halo.
- **`-ub 2048 -b 16384`** for MoE prefill.
- **hipBLASLt** (`ROCBLAS_USE_HIPBLASLT=1`) on ROCm, and rocWMMA FA on RDNA3, but not on gfx1151.
- PCIe ASPM performance mode for discrete RDNA4.
- On Strix Halo: `amd_iommu=off` plus a large `ttm.pages_limit` / `amdgpu.gttsize` so the GPU can use ~115–124 GB.

### Cited Findings

**Build**
- ROCm build: `-DGGML_HIP=ON -DAMDGPU_TARGETS="gfx1151"` (or gfx1100/gfx1201). — [seehiong](https://seehiong.github.io/posts/2026/08/running-llama.cpp-on-amd-strix-halo/)
- Add `-DGGML_HIP_ROCWMMA_FATTN=ON` for RDNA3+ and CDNA. — [#15021](https://github.com/ggml-org/llama.cpp/discussions/15021) — but avoid it on gfx1151 (see section 2): [#24437](https://github.com/ggml-org/llama.cpp/issues/24437)
- Vulkan build: `-DGGML_VULKAN=ON -DGGML_NATIVE=ON -DCMAKE_BUILD_TYPE=Release`. Use a recent glslc (Vulkan SDK 1.4.341.1+ or 1.4.357.1+); an old glslc (2023.8) causes "severe regressions". Source builds are recommended over prebuilt binaries. — [#21043](https://github.com/ggml-org/llama.cpp/discussions/21043)

**Env vars**
- `ROCBLAS_USE_HIPBLASLT=1`: large pp gains on Strix Halo (986 vs ~344 pp512). — [llm-tracker](https://llm-tracker.info/_TOORG/Strix-Halo); [hardware-corner](https://www.hardware-corner.net/strix-halo-llm-optimization/)
- `VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.json` forces RADV. `GGML_VK_VISIBLE_DEVICES=0` isolates one GPU. — [#21043](https://github.com/ggml-org/llama.cpp/discussions/21043)
- `GGML_VK_ALLOW_GRAPHICS_QUEUE=1`: +4.7% MoE decode on AMDVLK, −8% on dense, no effect on RADV. — [#21043](https://github.com/ggml-org/llama.cpp/discussions/21043)
- `GGML_VK_DISABLE_MMVQ=1` (+0.5–0.8% decode) and `GGML_VK_DISABLE_COOPMAT=1` (AMDVLK dense prefill workaround). — [#21043](https://github.com/ggml-org/llama.cpp/discussions/21043)
- For multi-GPU ROCm benchmarking, isolate one GPU with `-sm none -mg N`. — [#15021](https://github.com/ggml-org/llama.cpp/discussions/15021)

**Runtime flags**
- Strix Halo: "Always use flash attention (`-fa 1`) and no-mmap (`--no-mmap`) … to avoid crashes/slowdowns". Also use `-ngl 999`. — [kyuz0](https://github.com/kyuz0/amd-strix-halo-toolboxes)
- `-ub 2048 -b 16384` gave +29% MoE prefill on the R9700; "the most impactful single change". Avoid `-ub 65–256` on Qwen3.5/3.6 hybrid architectures (a 40× throughput collapse). — [#21043](https://github.com/ggml-org/llama.cpp/discussions/21043)
- Strix Halo: monitor for GPU hangs with batch sizes above 256 (2025 note). — [llm-tracker](https://llm-tracker.info/_TOORG/Strix-Halo)
- MoE expert offload: `--n-cpu-moe N` keeps N MoE layers' experts on the CPU. Reference point: ~30 t/s on gpt-oss-120b at zero context on an RTX 5090 with `--n-cpu-moe 21`. — [llama.cpp gpt-oss guide #15396](https://github.com/ggml-org/llama.cpp/discussions/15396)
- Speculative decoding: MTP on Qwen3.8-27B on the R9700 gave +9.7%. — [#21043](https://github.com/ggml-org/llama.cpp/discussions/21043). EXL3 ROCm port supports DFlash2/MTP. — [exllamav3-rocm](https://github.com/wtogami/exllamav3-rocm)

**System and kernel (discrete RDNA4)**
- `pcie_aspm.policy=performance` (or `echo performance > /sys/module/pcie_aspm/parameters/policy`) gave +10.8% dense decode on RADV. `amdgpu.ras_enable=0` had minimal impact. — [#21043](https://github.com/ggml-org/llama.cpp/discussions/21043)
- Leave DPM on auto. `rocm-smi --setperflevel auto` beats `high` for prefill: `high` pins 2,350 MHz, while auto boosts to 3,348 MHz, and `high` costs 8–9% prefill. — [#21043](https://github.com/ggml-org/llama.cpp/discussions/21043)
- Resizable BAR is essential. A USB4 eGPU with a 256 MB BAR gave a 39× slowdown at `-ub 256`. — [#21043](https://github.com/ggml-org/llama.cpp/discussions/21043)
- Kernel regression: Linux 6.19 RADV was ~10% slower than 6.17. MCLK boost fails on 6.17 and works on 6.19.8+. — [#21043](https://github.com/ggml-org/llama.cpp/discussions/21043)
- Mesa 25.3+ reportedly brought "double-digit MoE gains". — [runaihome](https://runaihome.com/blog/rdna4-vulkan-vs-rocm-local-llm-benchmark-2026/)

**Strix Halo kernel parameters**
- 128 GB system: `amd_iommu=off amdgpu.gttsize=126976 ttm.pages_limit=32505856 ttm.page_pool_size=32505856` (~124 GB GPU-addressable). `amd_iommu=off` is reportedly 5–12% faster than `amd_iommu=pt`. — [search summary of Framework/kryoz/Lychee guides](https://community.frame.work/t/amd-strix-halo-llama-cpp-installation-guide-for-fedora-42/75856); [kryoz/llama-strix-halo](https://github.com/kryoz/llama-strix-halo)
- An alternative setting, `amd_iommu=off ttm.pages_limit=30146560` (~115 GiB GTT), was used for the August 2026 benchmarks above. — [seehiong](https://seehiong.github.io/posts/2026/08/running-llama.cpp-on-amd-strix-halo/)
- A Level1Techs thread reports "ROCm can only use half of the unified memory" without these settings. — [Level1Techs](https://forum.level1techs.com/t/rocm-can-only-use-half-of-the-unified-memory-on-my-strix-halo/253152)
- Use a recent kernel: lhl notes 6.15+ gave ~15% improvement. — [llm-tracker](https://llm-tracker.info/_TOORG/Strix-Halo)
- kyuz0 builds include a workaround for llama.cpp issue #25992 (ROCm host-buffer selection on iGPUs). The repo also ships `gguf-vram-estimator.py`. — [kyuz0](https://github.com/kyuz0/amd-strix-halo-toolboxes)

### Inferences
- `HSA_OVERRIDE_GFX_VERSION` (e.g. 11.0.0 to run gfx1100 kernels on unsupported RDNA3 or 3.5 parts) and `GGML_HIP_UMA` (older build flag for hipMallocManaged on APUs) are long-standing community knobs. With native gfx1151/gfx1201 targets in ROCm 6.4+/7.x they should be unnecessary on these parts, and the GTT approach supersedes UMA on Strix Halo. This was not re-verified in 2026 sources.

### Gaps
- No 2026 source fetched on `HSA_OVERRIDE_GFX_VERSION` or `GGML_HIP_UMA` behaviour with ROCm 7.x.
- No numbers for `-ot` tensor-override strategies on Radeon specifically.
- No tensor-parallel (vLLM/SGLang TP) data over multiple Radeons.

---

## 5. The NPU angle (XDNA / XDNA2)

### Takeaway
The XDNA2 NPU (50 TOPS, 32 AIE tiles) is now usable for LLMs on Linux through Lemonade + FastFlowLM, which uses closed-source kernels. It is useful mainly for low-power, small and medium models and for prefill (time-to-first-token) offload. On Strix Halo the iGPU is still the main engine. Custom kernels via IRON/MLIR-AIE reach ~38 TOPS int8 GEMM, which suits research more than hobbyist speedups.

### Cited Findings
- XDNA2: 4×8 array of 32 AIE compute cores, 8 memory tiles and 8 shim tiles, up to 50 TOPS. Optimized GEMM via MLIR-AIE/IRON reached 38.05 TOPS int8 and 14.71 TOPS bf16 (arXiv 2512.13282). Separate experiments report 56 TOPS INT8 peak with custom kernels. — [arXiv 2512.13282](https://arxiv.org/pdf/2512.13282); [emergentmind summary](https://www.emergentmind.com/topics/amd-xdna-2-npu)
- IRON exposes compute, memory and shim tiles, ObjectFifos and DMA tasks from Python, with core code in C++ via the AIE API. A fused LLaMA 2 MHA prototype in ~150 lines of MLIR cut latency from 834 μs to 373 μs (2.24×). — [emergentmind / search summary](https://www.emergentmind.com/topics/ryzen-ai-xdna-npus)
- TileFuse (arXiv 2606.11357) is a fused mixed-precision kernel library for quantized LLM inference on AMD NPUs. — [arXiv 2606.11357](https://arxiv.org/pdf/2606.11357) (not fetched)
- Lemonade 10.0 + FastFlowLM made Ryzen AI NPUs useful on Linux for LLMs (March 2026). — [agent-wars](https://agent-wars.com/news/2026-03-14-amd-ryzen-ai-npu-linux-lemonade-10-fastflowlm)
- FastFlowLM 0.9.35 supports contexts up to 256k on current NPUs. It reaches ~52 tok/s at 16K context on Strix Halo; the model is unspecified in the snippet. — [search summary of Lemonade/FLM sources](https://ai.miraheze.org/wiki/Lemonade_(AI_server)) (low confidence). One Lemonade issue reports FLM auto-context falling back to 4,096 on an HX 470 with 64 GB. — [lemonade #3748](https://github.com/lemonade-sdk/lemonade/issues/3748)
- NPU support is limited to XDNA2 (Ryzen AI 300/400, Strix Halo). XDNA1 (7000/8000/200 series) gets no NPU benefit. FastFlowLM holds an exclusive NPU lock (one model at a time) and its kernels are closed-source. Example: Llama 3.2-3B on the Strix Point NPU at 28 t/s. Hybrid NPU prefill is claimed to give "2.3× faster time-to-first-token" vs GPU-only. — [runaihome Lemonade guide](https://runaihome.com/blog/amd-lemonade-local-llm-server-npu-gpu-guide-2026/)
- FastFlowLM is now under the ROCm GitHub organization, with an XDNA2 performance-observations and validation-roadmap issue. — [ROCm/FastFlowLM #636](https://github.com/ROCm/FastFlowLM/issues/636)
- A containerized Lemonade + FastFlowLM install for the Strix Halo NPU exists. — [oresk/lemonade-npu-toolbox](https://github.com/oresk/lemonade-npu-toolbox)

### Inferences
- With NPU bf16 GEMM at ~15 TOPS vs the Strix Halo iGPU at ~59 TFLOPS FP16 theoretical, the NPU cannot beat the iGPU on prefill throughput. Its value is power efficiency and offloading work while the GPU does something else. NPU decode is still bandwidth-bound on the same LPDDR5X.

### Gaps
- No fetched head-to-head of NPU-only vs iGPU-only decode on the same model on Strix Halo.
- Riallto (the educational XDNA1 framework) status in 2026 was not verified.

---

## 6. Community resources

### Takeaway
The main living references:
- **llama.cpp discussions #10879 (Vulkan), #15021 (ROCm) and #21043 (RDNA4 tuning)**.
- **kyuz0/amd-strix-halo-toolboxes**, plus its benchmark viewer and strix-halo-toolboxes.com.
- **lhl's llm-tracker.info Strix Halo pages**.
- Framework and Level1Techs forums.

### Cited Findings
- [kyuz0/amd-strix-halo-toolboxes](https://github.com/kyuz0/amd-strix-halo-toolboxes) and [strix-halo-toolboxes.com](https://strix-halo-toolboxes.com/)
- [llm-tracker.info Strix Halo (lhl)](https://llm-tracker.info/_TOORG/Strix-Halo), [llm-tracker AMD GPUs how-to](https://llm-tracker.info/howto/AMD-GPUs), and [AMD Strix Halo GPU Performance](https://llm-tracker.info/AMD-Strix-Halo-(Ryzen-AI-Max+-395)-GPU-Performance)
- llama.cpp scoreboards: [Vulkan #10879](https://github.com/ggml-org/llama.cpp/discussions/10879), [ROCm #15021](https://github.com/ggml-org/llama.cpp/discussions/15021), [RDNA4 R9700 experiments #21043](https://github.com/ggml-org/llama.cpp/discussions/21043), [gpt-oss guide #15396](https://github.com/ggml-org/llama.cpp/discussions/15396)
- [Level1Techs Strix Halo unified-memory thread](https://forum.level1techs.com/t/rocm-can-only-use-half-of-the-unified-memory-on-my-strix-halo/253152) and the [Framework community Fedora 42 llama.cpp guide](https://community.frame.work/t/amd-strix-halo-llama-cpp-installation-guide-for-fedora-42/75856)
- Strix benchmark aggregators: [slb350 strix-benchmarks](https://slb350.github.io/strix-benchmarks/) and [strix-benchmarks.vercel.app](https://strix-benchmarks.vercel.app/)
- [ROCm 7 toolbox benchmarking blog](https://sleepingrobots.com/dreams/rocm7-toolbox-upgrade-strix-halo/)
- AMD's official gpt-oss on Ryzen AI / Radeon blog (2025). — [AMD blog](https://www.amd.com/en/blogs/2025/how-to-run-openai-gpt-oss-20b-120b-models-on-amd-ryzen-ai-radeon.html)

### Inferences
- The strixhalo.wiki and GPU MODE Discord AMD channel were named in the brief. They were not reachable or fetched here, so their content is not represented.

### Gaps
- Not fetched: strixhalo.wiki, r/LocalLLaMA threads (Reddit not fetched), Phoronix and chipsandcheese 2026 Radeon LLM articles, the GPU MODE Discord.
