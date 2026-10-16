# 08 — Analiza platformy 70 łatek `amd-opt` (PLAN §4.5, Faza 0 / E3)

Data: 2026-10-15. Analiza wyłącznie „na papierze”: diffy 70 łatek z `~/KERNEL/qwen-opt/patches/llama.cpp-amd-opt/`, drzewo `~/llama-master` @ `amd-opt` (`f61994f58`, baza upstream `e60eff95f`), raport 07, `NOTES.md`, `tools/loo/loo-plan.json` oraz źródła AMD/Microsoft/NVIDIA z sieci (lista w §10). GPU nie było używane, nic nie było budowane.

Wynik maszynowy: `~/KERNEL/product/research/patch-manifest.json` (klucz = numer łatki `0001`…`0070`, plus `_meta` z legendą, kolumnami i źródłami). Każdy wpis ma pola `file`, `title`, `backends`, `effective_backend`, `guard`, `os`, `runtime`, `arch`, `model_family`, `env_switch`, `correctness`, `gain_xtx`, `gain_ms`, `portability` (19 kolumn platforma × rodzina GPU), `evidence`, `notes`.

Konwencje:
- `[SZACUNEK]` oznacza wniosek bez pomiaru albo bez przeczytania źródła zewnętrznego.
- Odwołania `patches/<plik>:<n>` wskazują linię w pliku łatki.
- Odwołania `amd-opt:<ścieżka>:<n>` wskazują linię w drzewie `amd-opt`.

## 1. TL;DR

- **HIP na Windows działa na PAL, nie na ROCr.** To potwierdzają:
  - dokumentacja AMD: „rocclr … ROCr on Linux or PAL on Microsoft Windows”;
  - kod CLR: `device.cpp:856-860` „On Windows by default keep PAL path for now, until we completely switch to ROCr backend”;
  - TheRock: ROCR-Runtime na Windows ma status „Unsupported”.

  Próba przełączenia Windows na ROCr (rocm-systems#8900) została zamknięta bez merge 2026-10-04. W efekcie **0060 (PM4 replay) i 0061 nie działają na Windows**.

  Co gorsza, 0060 dodaje do `ggml-hip/CMakeLists.txt` bezwarunkowe `find_package(hsa-runtime64 REQUIRED)` (`patches/0060…:776`). `[SZACUNEK]` To prawdopodobnie **łamie build całego backendu HIP na Windows**, bo HIP SDK nie ma ROCr. Przed buildem Windows w CI (E3) trzeba to owinąć w `if (NOT WIN32)` / opcję `GGML_HIP_PM4`.

- **Korekty względem raportu 07** (szczegóły w §5):
  - **Kod ogólny jest aktywny także na NVIDIA i innych RDNA.** Wielokolumnowy `vec_dot_q_multi` z 0001/0002, nowe loadery z 0021 oraz kernele 0025 (rms_norm) i 0026 (argmax) nie mają strażnika arch, więc działają też na NVIDIA i innych RDNA. Raport 07 zaliczył je do „AMD-RDNA3”, a NOTES pisze „tylko HIP/RDNA3”.
  - **0054 działa na każdym RDNA.** Bramka to `GGML_CUDA_CC_IS_RDNA`.
  - **0042 działa też na RDNA4.** Siedzi w tabeli `get_config_rdna` dla `AMD_WMMA_AVAILABLE`.
  - **0022, 0040, 0060 i 0070 obejmują też RDNA3.5 (gfx115x).** Bramka `RDNA3` / `GGML_CUDA_CC_IS_RDNA3` zawiera gfx115x.

- **Ile zysku XTX da się przenieść** (suma per-łatkowych Δ: Qwen 14.14 ms/krok, LFM 1.736 ms/token; §7):

  | platforma | Qwen pewne (G) | Qwen do testu (?) | LFM G | LFM ? |
  |---|---|---|---|---|
  | Linux RDNA3 (XTX) | 100% | 0% | 100% | 0% |
  | Linux RDNA2/RDNA4 | 73% `[SZACUNEK]` | +12% | 53% `[SZACUNEK]` | +8% |
  | Windows AMD HIP | 25% (host) | +66% | 0% | +73% |
  | NVIDIA (Linux i Windows) | 25% (host) | +59%, realnie ok. +14% po skalowaniu kosztu granicy kernela `[SZACUNEK]` | 0% | +53%, realnie ok. +16% |
  | macOS / Vulkan | 7% (host) | +21% (graf MTP) | 0% | 0% |

  Na każdą platformę bez zmian przenosi się warstwa samplera i UI: 0048 i 0065–0069 dają +6–8% (Qwen MTP) i +13–15% (LFM) w ścieżkach UI/narzędzi.

- **Rzeczy, które ograniczą Windows niezależnie od runtime:**
  - **Testy z popcount nie kompilują się pod MSVC.** `test-backend-ops` używa `__builtin_popcountll` (0019, 0057), czego MSVC nie ma `[SZACUNEK]`.
  - **Ścieżka SSE2 samplera wypada pod MSVC.** MSVC nie definiuje `__SSE2__`, więc ta ścieżka w 0031 jest wycinana i zostaje skalarny fallback (ten sam wynik).
  - **Brak profilera ROCm.** rocprofv3 nie istnieje na Windows (TheRock: rocprofiler-sdk „Unsupported”), więc nasz playbook profilowania nie działa tam bez zmian.
- **Przełączniki `GGML_HIP_*` sterują też buildem CUDA.** `ggml_cuda_env_switch` (`patches/0024…:35`) czyta je w każdym buildzie `ggml-cuda` i domyślnie są włączone. Na NVIDIA „GGML_HIP_MOE_DOWN_REDUCE” itd. są więc aktywne. Manifest i daemon muszą to wiedzieć. Rekomendacja: zmienić nazwy na `GGML_CUDA_*` albo dodać do bramki `GGML_USE_HIP`.

## 2. Kluczowe pytanie: jaki runtime ma HIP na Windows

| fakt | źródło |
|---|---|
| „rocclr is a virtual device interface that enables the HIP runtime to interact with different backends, such as ROCr on Linux or PAL on Microsoft Windows.” | AMD HIP docs, *Using HIP runtime API* [S1] |
| HIP SDK for Windows 7.2.0, tabela komponentów: Runtime = „HIP (closed source)” na Windows vs „HIP (open sourced)” na Linux; Profiler: Radeon GPU Profiler zamiast ROCProfiler; System Management: hipInfo zamiast rocminfo | AMD, *ROCm components supported in HIP SDK* [S2] |
| `Device::init()`: `if (IS_WINDOWS && flagIsDefault(GPU_ENABLE_PAL)) { // On Windows by default keep PAL path for now, until we completely switch to ROCr backend … GPU_ENABLE_PAL = 1; }`; ROCr (`roc::Device::init`) tylko gdy `GPU_ENABLE_PAL` = 0/2 | `rocm-systems@6e6db17 projects/clr/rocclr/device/device.cpp:843-907` [S3] |
| `option(ROCCLR_ENABLE_HSA … ON)`, `option(ROCCLR_ENABLE_PAL … OFF)`: PAL to osobny backend włączany w buildzie (Windows) | `ROCclr.cmake:7-8` [S4] |
| TheRock *Windows Support*: ROCR-Runtime „❌ Unsupported”; clr „🟡 Needs a folder with prebuilt static libraries” (interop PAL); rocprofiler-sdk, rocminfo, amdsmi „Unsupported” | `TheRock@4d992b3 docs/development/windows_support.md` [S5] |
| Próba „Use rocr backend for HIP/OCL by default” (także Windows): draft, auto-zamknięty 2026-10-04 bez merge; równoległy TheRock#6713 nadal draft | [S6], [S7] |

**Wniosek:** na Windows HIP SDK (stan 2026-10) kolejka, sygnały i loader to PAL. Nie ma tam `hsa_queue_create`, `hsa_ven_amd_loader_*`, vendor AQL packetu `AMD_AQL_FORMAT_PM4_IB` ani `/dev/kfd`.

- **Wykluczone są łatki zależne od ROCr:**
  - 0060: `hsa_init`, `hsa_system_get_major_extension_table(HSA_EXTENSION_AMD_LOADER)`, `hsa_queue_create`, `hsa_amd_memory_pool_allocate`, vendor packet, `patches/0060…:112,368,411,723`;
  - 0061: dodatkowo `abi::__cxa_demangle`, `patches/0061…:97`.
- **Kod GPU z intrynsykami gfx11 nie zależy od runtime.** Dotyczy to `__builtin_amdgcn_*`: WMMA, DPP, `permlanex16`, buffer resource, bity cpol GLC/DLC. To sprawa kompilatora i ISA, więc taki kod skompiluje się clangiem z HIP SDK i wykona pod PAL.
- **Zastrzeżenia do kodu GPU na Windows:**
  - **inny kompilator:** HIP SDK 7.2 vs ROCm 10.0 clang na Linux (`patches/0070…`: „ROCm 10.0 clang”), więc inny ISA i bitowa zgodność do sprawdzenia;
  - **inny koszt granicy kernela w PAL**, którego nie znamy. A od niego zależy wartość większości naszych fuzji.

Długoterminowo, jeśli AMD przełączy Windows na ROCr, PM4 może wrócić jako opcja. Na dziś: `os: [linux]`, `runtime: rocr`.

## 3. Metoda i legenda

1. Dla każdej łatki skrypt wyciągnął dodane linie z dyrektywami preprocesora, intrynsykami (`__builtin_amdgcn_*`, `hsa_*`, `__shfl*`), bramkami runtime (`GGML_CUDA_CC_IS_*`, `table_id`, `warp_size == 32`, `getenv`/`ggml_cuda_env_switch`) i przeniesione pliki. Bramki ścieżek sprawdziłem potem w drzewie `amd-opt`:
   - `mmvq.cu:124-146`, `mmvq.cu:879-895`, `mmvq.cu:1494`;
   - `common.cuh:86-93`, `common.cuh:278-280`;
   - predykaty `*_supported` w `ggml-cuda.cu`, `mmvq.cu`, `norm.cu`, `rope.cu`, `topk-moe.cu`, `fattn.cu`;
   - `ggml-hip/CMakeLists.txt:49,145`;
   - Metal i Vulkan `is_host` / `set_tensor_async` / `event_new`.
2. Zakres (`scope` w manifeście):
   - `host`, `llama`: kod CPU lub grafu, wszystkie backendy;
   - `cuda`: wspólny `ggml-cuda` bez strażnika arch, czyli CUDA + każdy HIP;
   - `cuda+llama`: nowy op z fallbackiem przez `supports_op`;
   - `hip_rdna`: RDNA1–4;
   - `hip_rdna3`: gfx110x i gfx115x;
   - `hip_rdna3_0`: tylko gfx110x;
   - `hip_wmma`: RDNA3, RDNA3.5, RDNA4;
   - `rocr`: Linux ROCr + RDNA3;
   - `vulkan`;
   - `tests`.
3. Werdykty:

   | symbol | werdykt | znaczenie |
   |---|---|---|
   | G | `works+gain` | działa, oczekiwany zysk; poza Linux RDNA3 to `[SZACUNEK]` z mechanizmu łatki |
   | N | `works-neutral` | działa lub kompiluje się, bez zysku: fix, tooling, opt-in wyłączony, fallback |
   | X | `excluded` | wycięte w kompilacji, wyłączone bramką runtime, inny backend albo brak runtime |
   | ? | `unknown-needs-test` | kod jest **aktywny**, ale nie był tam nigdy uruchomiony |

   Reguły przypisywania:
   - Wspólne fuzje CUDA/HIP na **innym RDNA pod Linux** (ten sam kompilator, ten sam ROCr) dostają G, jeśli są bitowe z konstrukcji i nie mają strojenia gfx1100. Kernele strojone albo nowe dostają „?”.
   - Na **NVIDIA** i **Windows HIP** każda aktywna łatka kernelowa to „?”: inny kompilator lub ISA, kontrakcja FMA, inny koszt granicy kernela.
4. Model: kolumna `model_family`. Werdykt platformowy zakłada, że model ma dany wzorzec (np. GDN dla 0013).

## 4. Macierz zbiorcza

Skróty kolumn:
- L / W: Linux / Windows;
- R3 / R3.5 / R2 / R4: RDNA3 (gfx110x) / RDNA3.5 (gfx115x) / RDNA2 / RDNA4;
- VK: Vulkan;
- NV: CUDA. sm_86, sm_89 i sm_120 mają identyczne werdykty, bo żadna łatka nie ma kodu specyficznego dla arch NVIDIA. Pełne 19 kolumn jest w manifeście.

| # | łatka (skrót) | zakres | L R3 | L R3.5 | L R2 | L R4 | W HIP R3/R3.5/R2/R4 | VK AMD L-R3/L-R2,4/W-R3/W-R2,4 | NV L (sm86/89/120) | NV W | macOS |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0001 | HIP mmvq: multi-column (2-8) vec_dot for RDNA3 with wide contiguous lo… | cuda | G | ? | ? | ? | ?/?/?/? | X/X/X/X | ? | ? | X |
| 0002 | HIP mmvq multi-column: i-quants, Q2_K, per-type rows per block on RDNA3 | cuda | G | ? | ? | ? | ?/?/?/? | X/X/X/X | ? | ? | X |
| 0003 | CUDA/HIP mmvq: reuse q8_1 activations across consecutive MUL_MATs with… | cuda | G | G | G | G | ?/?/?/? | X/X/X/X | ? | ? | X |
| 0004 | MTP: optional reduced-vocabulary draft LM head (--spec-draft-vocab) | llama | G | G | G | G | G/G/G/G | ?/?/?/? | G | G | ? |
| 0005 | mmvq: drop local tuning include | cuda | N | N | N | N | N/N/N/N | X/X/X/X | N | N | X |
| 0006 | vulkan: AMD RDNA small-M matvec uses float path with 256-thread workgr… | vulkan | X | X | X | X | X/X/X/X | G/?/?/? | X | X | X |
| 0007 | vulkan: MMVQ fast path for Q4_K/Q5_K/Q6_K/IQ4_XS with hoisted per-thre… | vulkan | X | X | X | X | X/X/X/X | G/?/?/? | X | X | X |
| 0008 | vulkan: AMD RDNA uses the integer-dot MMVQ path for Q6_K from four col… | vulkan | X | X | X | X | X/X/X/X | G/?/?/? | X | X | X |
| 0009 | vulkan: AMD RDNA uses the float matvec path for m < 4096 above four co… | vulkan | X | X | X | X | X/X/X/X | G/?/?/? | X | X | X |
| 0010 | vulkan: RDNA3/4 MMVQ uses 2 rows per workgroup at eight columns | vulkan | X | X | X | X | X/X/X/X | G/?/?/? | X | X | X |
| 0011 | HIP FA: RDNA3 kernel reading the q4_0 KV cache directly for small batc… | hip_rdna3_0 | G | X | X | X | ?/X/X/X | X/X/X/X | X | X | X |
| 0012 | CUDA/HIP: bias/residual ADD epilogue for multi-column MMVQ | cuda | G | G | G | G | ?/?/?/? | X/X/X/X | ? | ? | X |
| 0013 | CUDA/HIP: fuse the GATED_DELTA_NET prologue (alpha/beta projections, q… | cuda | G | G | G | G | ?/?/?/? | X/X/X/X | ? | ? | X |
| 0014 | CUDA/HIP: fold the conv-state concat, snapshot copies and gather into … | cuda | G | G | G | G | ?/?/?/? | X/X/X/X | ? | ? | X |
| 0015 | CUDA/HIP: write the q8_1 MMVQ activations from the producing norm/GLU/… | cuda | G | G | G | G | ?/?/?/? | X/X/X/X | ? | ? | X |
| 0016 | CUDA/HIP: GDN alpha/beta MMVQ templated on the token count | cuda | G | G | G | G | ?/?/?/? | X/X/X/X | ? | ? | X |
| 0017 | CUDA/HIP + qwen35: fuse IMROPE/MROPE into RMS_NORM+MUL+ROPE, drop the … | cuda | G | G | G | G | ?/?/?/? | ?/?/?/? | ? | ? | ? |
| 0018 | CUDA/HIP: fix race in flash_attn_ext_f16_process_tile when nbatch_comb… | cuda | N | N | N | N | N/N/N/N | X/X/X/X | N | N | X |
| 0019 | CUDA/HIP: fold the q/k Hadamard rotation of a rotated KV cache into RM… | cuda | G | G | G | G | ?/?/?/? | X/X/X/X | ? | ? | X |
| 0020 | speculative + qwen35: greedy MTP drafts as one unrolled draft-chain gr… | llama | G | G | G | G | G/G/G/G | ?/?/?/? | G | G | ? |
| 0021 | HIP/RDNA3 multi-column MMVQ: buffer-resource loads, per-type occupancy… | cuda | G | ? | ? | ? | ?/?/?/? | X/X/X/X | ? | ? | X |
| 0022 | HIP/RDNA3 multi-column MMVQ: stream weight loads past the per-CU cache… | hip_rdna3 | G | ? | X | X | ?/?/X/X | X/X/X/X | X | X | X |
| 0023 | CUDA/HIP: clamp the fp16 (d, sum) of every q8_1 block written to +-655… | cuda | N | N | N | N | N/N/N/N | X/X/X/X | N | N | X |
| 0024 | CUDA/HIP: MMVQ pair launch for two products of the same src1 | cuda | G | G | G | G | ?/?/?/? | N/N/N/N | ? | ? | N |
| 0025 | CUDA/HIP: unrolled rms_norm*mul(+q8_1) for 2048..8192-column rows, DPP… | cuda | G | G | G | G | ?/?/?/? | X/X/X/X | ? | ? | X |
| 0026 | CUDA/HIP: argmax with 16 loads in flight and DPP exchanges | cuda | G | G | G | G | ?/?/?/? | X/X/X/X | ? | ? | X |
| 0027 | CUDA/HIP: GDN gated output norm silu(z) * (rms_norm(x) * w) + q8_1 in … | cuda | G | G | G | G | ?/?/?/? | X/X/X/X | ? | ? | X |
| 0028 | CUDA/HIP: GDN fused SSM_CONV and alpha/beta projections in one grid | cuda | G | G | G | G | ?/?/?/? | X/X/X/X | ? | ? | X |
| 0029 | ggml-backend/llama: asynchronous graph input uploads | host | G | G | G | G | G/G/G/G | ?/?/?/? | G | G | ? |
| 0030 | llama: MTP draft chain on its own scheduler | llama | G | G | G | G | G/G/G/G | ?/?/?/? | G | G | ? |
| 0031 | common/server: top-k candidates without the full candidate array, no s… | host | G | G | G | G | G/G/G/G | G/G/G/G | G | G | G |
| 0032 | llama/common: re-quantize the MTP draft head and MTP block at load tim… | llama | G | G | G | G | G/G/G/G | ?/?/?/? | G | G | ? |
| 0033 | ggml/llama: delta-net speculative rollback by replay of a lagged state… | cuda+llama | G | G | G | G | ?/?/?/? | N/N/N/N | ? | ? | N |
| 0034 | llama/ggml: GATED_DELTA_NET_LAG lag info as [n_seqs, 4], its first row… | cuda+llama | G | G | G | G | ?/?/?/? | N/N/N/N | ? | ? | N |
| 0035 | CUDA/HIP: GATED_DELTA_NET_LAG issues the loads of the next pending row… | cuda | G | G | G | G | ?/?/?/? | X/X/X/X | ? | ? | X |
| 0036 | llama: the lagged delta-net state is read from its cache row (single c… | cuda+llama | G | G | G | G | ?/?/?/? | N/N/N/N | ? | ? | N |
| 0037 | CUDA/HIP: RDNA3 verify batches of 9-16 columns: WMMA small-N MUL_MAT k… | hip_rdna3_0 | G | X | X | X | ?/X/X/X | X/X/X/X | X | X | X |
| 0038 | llama/CUDA: lagged conv history for the delta-net rollback by replay, … | cuda+llama | G | G | G | G | ?/?/?/? | N/N/N/N | ? | ? | N |
| 0039 | common/llama: cost-priced adaptive MTP draft depth (--spec-draft-adapt… | llama | N | N | N | N | N/N/N/N | N/N/N/N | N | N | N |
| 0040 | CUDA/HIP: RDNA3 MMQ picks a narrower tile when the widest one leaves C… | hip_rdna3 | G | ? | X | X | ?/?/X/X | X/X/X/X | X | X | X |
| 0041 | llama: the qwen35 MTP layer computes only K/V for rows without output … | llama | G | G | G | G | G/G/G/G | ?/?/?/? | G | G | ? |
| 0042 | CUDA/HIP: RDNA FA MMA D=256 prompt tile keeps Q in SRAM (Q in register… | hip_wmma | G | ? | X | ? | ?/?/X/? | X/X/X/X | X | X | X |
| 0043 | CUDA/HIP: FA MMA walks the K chunks in order unless K is the V view (M… | cuda | N | N | N | N | N/N/N/N | X/X/X/X | ? | ? | X |
| 0044 | tests: perf cases for the Qwen3.5/3.8 27B prompt matmul shapes (FFN, G… | tests | N | N | N | N | N/N/N/N | N/N/N/N | N | N | N |
| 0045 | CUDA/HIP: prompt batches of the fused-l2 GDN normalize q/k once per (h… | cuda | G | G | G | G | ?/?/?/? | X/X/X/X | ? | ? | X |
| 0046 | MTP: attention window of the MTP layer (--spec-mtp-window, WIP) | llama | N | N | N | N | N/N/N/N | N/N/N/N | N | N | N |
| 0047 | llama/server: per-step host costs of the spec loop off the critical pa… | host | G | G | G | G | G/G/G/G | G/G/G/G | G | G | G |
| 0048 | common: fast top-k candidates also behind a penalties sampler that onl… | host | G | G | G | G | G/G/G/G | G/G/G/G | G | G | G |
| 0049 | CUDA/HIP: the FFN norm writes the q8_1 activations of the single-token… | cuda | G | G | G | G | ?/?/?/? | X/X/X/X | ? | ? | X |
| 0050 | CUDA/HIP: LFM2 shortconv: b*x and c*conv folded into the fused SSM_CON… | cuda | G | G | G | G | ?/?/?/? | X/X/X/X | ? | ? | X |
| 0051 | CUDA/HIP: single-token MoE tail (down MUL_MAT_ID, expert weighting, re… | cuda | G | G | G | G | ?/?/?/? | X/X/X/X | ? | ? | X |
| 0052 | HIP/RDNA3 one-column MMVQ: 2 rows per block for the K-quants | hip_rdna3_0 | G | X | X | X | ?/X/X/X | X/X/X/X | X | X | X |
| 0053 | CUDA/HIP: single-token MoE routing (FFN norm, F32 router, topk_moe) in… | cuda | G | G | G | G | ?/?/?/? | X/X/X/X | ? | ? | X |
| 0054 | CUDA/HIP: LFM2 shortconv in_proj MMVQ with the fused conv as per-group… | hip_rdna | G | ? | ? | ? | ?/?/?/? | X/X/X/X | X | X | X |
| 0055 | HIP/RDNA3 FA: the kvq decode kernel also reads a q8_0 KV cache | hip_rdna3_0 | G | X | X | X | ?/X/X/X | X/X/X/X | X | X | X |
| 0056 | CUDA/HIP: single-token gate/up(+GLU) MMVQ writes the q8_1 input of the… | cuda | G | G | G | G | ?/?/?/? | X/X/X/X | ? | ? | X |
| 0057 | CUDA/HIP: single-token attention input (q/k norm+rope+FWHT, v FWHT, q8… | cuda | G | G | G | G | ?/?/?/? | X/X/X/X | ? | ? | X |
| 0058 | CUDA/HIP: kvq attention applies the output FWHT (+ q8_1 for the o proj… | hip_rdna3_0 | G | X | X | X | ?/X/X/X | X/X/X/X | X | X | X |
| 0059 | CUDA/HIP: batch the small async input uploads of a graph into one H2D … | cuda | G | G | G | G | ?/?/?/? | X/X/X/X | ? | ? | X |
| 0060 | HIP/RDNA3: replay a captured decode graph as one PM4 indirect buffer o… | rocr | G | ? | X | X | X/X/X/X | X/X/X/X | X | X | X |
| 0061 | HIP PM4 replay: GGML_HIP_PM4_DEBUG=2 per-launch timing (GPU timestamps… | rocr | N | N | X | X | X/X/X/X | X/X/X/X | X | X | X |
| 0062 | CUDA/HIP RDNA3: the shortconv in_proj MMVQ runs 4 rows per block | hip_rdna3_0 | G | X | X | X | ?/X/X/X | X/X/X/X | X | X | X |
| 0063 | CUDA/HIP: GGML_HIP_PM4 and GGML_HIP_CONV_ROWS4 read through ggml_cuda_… | cuda | N | N | N | N | N/N/N/N | X/X/X/X | N | N | X |
| 0064 | HIP/RDNA3 one-column MMVQ: Q8_0 joins the 2-row path (and the 4-row co… | hip_rdna3_0 | G | X | X | X | ?/X/X/X | X/X/X/X | X | X | X |
| 0065 | server: LLAMA_SERVER_REASONING_CONTROL=0 ignores the client reasoning_… | host | G | G | G | G | G/G/G/G | G/G/G/G | G | G | G |
| 0066 | common: fast top-k candidates also with a reasoning-budget sampler | host | G | G | G | G | G/G/G/G | G/G/G/G | G | G | G |
| 0067 | common: fast top-k candidates also with n_probs > 0 | host | G | G | G | G | G/G/G/G | G/G/G/G | G | G | G |
| 0068 | common: fast top-k candidates also behind a logit-bias sampler | host | G | G | G | G | G/G/G/G | G/G/G/G | G | G | G |
| 0069 | common: fast top-k candidates also with a grammar, unless grammar_first | host | G | G | G | G | G/G/G/G | G/G/G/G | G | G | G |
| 0070 | HIP/RDNA3 MMQ: Q4_K/Q5_K scale epilogue in VOPD-pairable f32 ops, bitw… | hip_rdna3 | G | ? | X | X | ?/?/X/X | X/X/X/X | X | X | X |

Zliczenia i udział zysku XTX per kolumna. „G” i „?” to sumy `gain_ms` łatek z danym werdyktem; Qwen = 14.14 ms/krok, LFM = 1.736 ms/token.

| kolumna manifestu | G | N | X | ? | Qwen ms/krok: G | Qwen: ? | LFM ms/tok: G | LFM: ? |
|---|---|---|---|---|---|---|---|---|
| `linux-amd-hip-rdna3` | 56 | 9 | 5 | 0 | 14.14 (100%) | 0.00 (0%) | 1.736 (100%) | 0.000 (0%) |
| `linux-amd-hip-rdna3.5` | 40 | 9 | 12 | 9 | 10.28 (73%) | 3.86 (27%) | 0.914 (53%) | 0.594 (34%) |
| `linux-amd-hip-rdna2` | 40 | 8 | 18 | 4 | 10.28 (73%) | 1.63 (12%) | 0.914 (53%) | 0.131 (8%) |
| `linux-amd-hip-rdna4` | 40 | 8 | 17 | 5 | 10.28 (73%) | 1.63 (12%) | 0.914 (53%) | 0.131 (8%) |
| `windows-amd-hip-rdna3` | 14 | 8 | 7 | 41 | 3.51 (25%) | 9.27 (66%) | 0.000 (0%) | 1.273 (73%) |
| `windows-amd-hip-rdna3.5` | 14 | 8 | 14 | 34 | 3.51 (25%) | 9.27 (66%) | 0.000 (0%) | 1.045 (60%) |
| `windows-amd-hip-rdna2` | 14 | 8 | 18 | 30 | 3.51 (25%) | 8.40 (59%) | 0.000 (0%) | 1.045 (60%) |
| `windows-amd-hip-rdna4` | 14 | 8 | 17 | 31 | 3.51 (25%) | 8.40 (59%) | 0.000 (0%) | 1.045 (60%) |
| `linux-amd-vulkan-rdna3` | 13 | 8 | 42 | 7 | 0.94 (7%) | 2.93 (21%) | 0.000 (0%) | 0.000 (0%) |
| `linux-amd-vulkan-rdna2_4` | 8 | 8 | 42 | 12 | 0.94 (7%) | 2.93 (21%) | 0.000 (0%) | 0.000 (0%) |
| `windows-amd-vulkan-rdna3` | 8 | 8 | 42 | 12 | 0.94 (7%) | 2.93 (21%) | 0.000 (0%) | 0.000 (0%) |
| `windows-amd-vulkan-rdna2_4` | 8 | 8 | 42 | 12 | 0.94 (7%) | 2.93 (21%) | 0.000 (0%) | 0.000 (0%) |
| `linux-nvidia-cuda-sm86` | 14 | 7 | 19 | 30 | 3.51 (25%) | 8.40 (59%) | 0.000 (0%) | 0.914 (53%) |
| `linux-nvidia-cuda-sm89` | 14 | 7 | 19 | 30 | 3.51 (25%) | 8.40 (59%) | 0.000 (0%) | 0.914 (53%) |
| `linux-nvidia-cuda-sm120` | 14 | 7 | 19 | 30 | 3.51 (25%) | 8.40 (59%) | 0.000 (0%) | 0.914 (53%) |
| `windows-nvidia-cuda-sm86` | 14 | 7 | 19 | 30 | 3.51 (25%) | 8.40 (59%) | 0.000 (0%) | 0.914 (53%) |
| `windows-nvidia-cuda-sm89` | 14 | 7 | 19 | 30 | 3.51 (25%) | 8.40 (59%) | 0.000 (0%) | 0.914 (53%) |
| `windows-nvidia-cuda-sm120` | 14 | 7 | 19 | 30 | 3.51 (25%) | 8.40 (59%) | 0.000 (0%) | 0.914 (53%) |
| `macos-metal-apple` | 8 | 8 | 47 | 7 | 0.94 (7%) | 2.93 (21%) | 0.000 (0%) | 0.000 (0%) |

Uwagi do tabeli:
- **Kolumny Vulkan i macOS:** Δ Qwen pochodzą z pomiarów ROCm. W Vulkan i Metal są tylko orientacyjne, bo inny backend daje inny koszt kroku. Zysk samych łatek Vulkan (0006–0010) mierzono osobno, na RADV: −5.2% ms/krok + ~0.5 ms.
- **Wyłączenie 0006–0010:** łatki Vulkan są w kolumnach HIP oznaczone X, bo to inny backend. Dlatego w kolumnie Linux R3 jest 5×X.

## 5. Ustalenia, które zmieniają klasyfikację z raportu 07

| # | ustalenie | dowód | konsekwencja |
|---|---|---|---|
| 1 | `use_multi = mmvq_has_multi(type) && ncols_dst >= MMVQ_MULTI_MIN_NCOLS`, bez strażnika arch. `mmvq_has_multi` zależy tylko od typu. Na NVIDIA, RDNA2, RDNA3.5 i RDNA4 weryfikacja spekulacji (2–8 kolumn) idzie przez `vec_dot_q_multi` z innym `vdr` | `patches/0001…:345,363`; `amd-opt:ggml/src/ggml-cuda/mmvq.cu:124-146,1494` | 0001/0002 to w praktyce GEN-CUDA/HIP (zmieniona numeryka i wydajność na NVIDIA, nigdy nie testowane). Strojenie wiersze/blok/waves jest tylko w tabeli `MMVQ_PARAMETERS_RDNA3_0` (`patches/0001…:334`) |
| 2 | 0021: buffer resource tylko `GGML_USE_HIP && RDNA3`. Nowe loadery bajtowe z fallbackiem `__builtin_memcpy(__builtin_assume_aligned(...))` działają w ścieżce multi na każdej arch. DPP butterfly działa na każdym RDNA | `patches/0021…:36,78,377` | Na NVIDIA i innych RDNA: „?” |
| 3 | 0025 i 0026 mają ścieżkę non-DPP (`__shfl_xor_sync`). Przełącznik domyślnie włączony, brak bramki arch | `patches/0025…:33`, `patches/0026…:93,138` | Aktywne na NVIDIA. „bitowo z jawnym łańcuchem fmaf” sprawdzono tylko na hipcc |
| 4 | `GGML_CUDA_DPP_REDUCE` = `GGML_USE_HIP && RDNA` (RDNA1–4). `permlanex16` i DPP `row_xmask` istnieją od gfx10 | `patches/0025…:32-45` | DPP kompiluje się i działa na RDNA2 i RDNA4 |
| 5 | 0054: `GGML_CUDA_CC_IS_RDNA(cc) && table != GB10 && warp 32` | `patches/0054…:329` | Aktywne na RDNA2/3.5/4. Wiersze/blok tylko na RDNA3_0 |
| 6 | 0042 zmienia `get_config_rdna`, używane przy `AMD_WMMA_AVAILABLE` = RDNA3 lub RDNA4 | `amd-opt:fattn-mma-f16.cuh:130,262`; `common.cuh:278-280` | Zmiana kafla FA prefill na RDNA4 bez testu (VGPR, spill, bity) |
| 7 | `GGML_CUDA_CC_IS_RDNA3` i `#if defined(RDNA3)` obejmują RDNA3.5 (`common.cuh:90-92`, `vendors/hip.h:223-232`) | 0022, 0040, 0060 (`patches/0060…:354`), 0070 (`patches/0070…:97,298`) | PM4, GLC/DLC, MMQ-epilog i wybór kafla MMQ są aktywne na gfx1151 (Strix Halo) bez testu |
| 8 | `ggml_cuda_env_switch` zwraca `true`, gdy zmiennej brak. Nie zależy od `GGML_USE_HIP` | `amd-opt:common.cuh:1760-1763` | Wszystkie „GGML_HIP_*” są domyślnie włączone także w buildzie CUDA |
| 9 | 0029: async inputs działa dla każdego backendu z `set_tensor_async` i `event_new`. Metal: `is_host=false` dla buforów shared/private, więc ścieżka jest aktywna. Vulkan: oba ifejsy są | `patches/0029…:86,316`; `amd-opt:ggml-metal.cpp:285-287,593,788`; `ggml-vulkan.cpp:15171,16149` | 0029 na Vulkan i Metal: „?” |
| 10 | 0033: rs_lag wymaga `ggml_backend_dev_supports_op(GATED_DELTA_NET_LAG)` | `patches/0033…:949` | Vulkan/Metal: automatyczny fallback na snapshoty, czyli N, nie błąd |
| 11 | 0060: `find_package(hsa-runtime64 REQUIRED)` i link `hsa-runtime64::hsa-runtime64` bezwarunkowo | `patches/0060…:776`; `amd-opt:ggml/src/ggml-hip/CMakeLists.txt:49,145` | `[SZACUNEK]` Build HIP na Windows padnie przy konfiguracji CMake. Wymagany strażnik |
| 12 | `__builtin_popcountll` w `tests/test-backend-ops.cpp` | `patches/0019…:477`, `patches/0057…:613` | `[SZACUNEK]` MSVC (Windows CUDA) nie skompiluje testów. Zamienić na `std::popcount` (C++20) albo pętlę |
| 13 | 0031: SSE2 pod `#if defined(__SSE2__)`, ze skalarnym fallbackiem | `patches/0031…:34`; `amd-opt:common/sampling.cpp:52-72` | MSVC i ARM64 (Apple) używają fallbacku: poprawne, nieco wolniejsze |
| 14 | Tickety „ostatni blok” (0053, 0054, 0056) mają `__threadfence()` przed `atomicAdd` | `amd-opt:mmvq.cu:1863-1873,3477-3480`; `topk-moe.cu:431-434` | Model pamięci NVIDIA prawdopodobnie OK `[SZACUNEK]`. Do potwierdzenia testem |

## 6. Listy łatek per platforma

Zakładam, że model ma dany wzorzec. Pełne uzasadnienie per łatka jest w `manifest[*].notes` i `arch`.

### 6.1 Linux AMD

**RDNA3 gfx1100 (nasz XTX; punkt odniesienia):**
  - **works+gain**: 0001, 0002, 0003, 0004, 0011, 0012, 0013, 0014, 0015, 0016, 0017, 0019, 0020, 0021, 0022, 0024, 0025, 0026, 0027, 0028, 0029, 0030, 0031, 0032, 0033, 0034, 0035, 0036, 0037, 0038, 0040, 0041, 0042, 0045, 0047, 0048, 0049, 0050, 0051, 0052, 0053, 0054, 0055, 0056, 0057, 0058, 0059, 0060, 0062, 0064, 0065, 0066, 0067, 0068, 0069, 0070
  - **unknown-needs-test**: —
  - **works-neutral**: 0005, 0018, 0023, 0039, 0043, 0044, 0046, 0061, 0063
  - **excluded**: 0006, 0007, 0008, 0009, 0010

Inne RDNA3_0 (7900 XT/GRE, 7800 XT, 7700 XT: gfx1100–1102) kompilują ten sam kod. Strojenie jest pod 96 CU:
- 0052/0064: wiersze na blok;
- 0062: siatka 3072 = pojemność fal 96 CU.

Na 60/54 CU efekt może być inny `[SZACUNEK]`. 0040 i kvq (`nsplit`) liczą się z `nsm` urządzenia, więc adaptują się same.

**RDNA3.5 (gfx115x, np. Strix Halo):**
  - **works+gain**: 0003, 0004, 0012, 0013, 0014, 0015, 0016, 0017, 0019, 0020, 0024, 0025, 0026, 0027, 0028, 0029, 0030, 0031, 0032, 0033, 0034, 0035, 0036, 0038, 0041, 0045, 0047, 0048, 0049, 0050, 0051, 0053, 0056, 0057, 0059, 0065, 0066, 0067, 0068, 0069
  - **unknown-needs-test**: 0001, 0002, 0021, 0022, 0040, 0042, 0054, 0060, 0070
  - **works-neutral**: 0005, 0018, 0023, 0039, 0043, 0044, 0046, 0061, 0063
  - **excluded**: 0006, 0007, 0008, 0009, 0010, 0011, 0037, 0052, 0055, 0058, 0062, 0064

**RDNA2 (gfx1030):**
  - **works+gain**: 0003, 0004, 0012, 0013, 0014, 0015, 0016, 0017, 0019, 0020, 0024, 0025, 0026, 0027, 0028, 0029, 0030, 0031, 0032, 0033, 0034, 0035, 0036, 0038, 0041, 0045, 0047, 0048, 0049, 0050, 0051, 0053, 0056, 0057, 0059, 0065, 0066, 0067, 0068, 0069
  - **unknown-needs-test**: 0001, 0002, 0021, 0054
  - **works-neutral**: 0005, 0018, 0023, 0039, 0043, 0044, 0046, 0063
  - **excluded**: 0006, 0007, 0008, 0009, 0010, 0011, 0022, 0037, 0040, 0042, 0052, 0055, 0058, 0060, 0061, 0062, 0064, 0070

**RDNA4 (gfx1200/1201):**
  - **works+gain**: 0003, 0004, 0012, 0013, 0014, 0015, 0016, 0017, 0019, 0020, 0024, 0025, 0026, 0027, 0028, 0029, 0030, 0031, 0032, 0033, 0034, 0035, 0036, 0038, 0041, 0045, 0047, 0048, 0049, 0050, 0051, 0053, 0056, 0057, 0059, 0065, 0066, 0067, 0068, 0069
  - **unknown-needs-test**: 0001, 0002, 0021, 0042, 0054
  - **works-neutral**: 0005, 0018, 0023, 0039, 0043, 0044, 0046, 0063
  - **excluded**: 0006, 0007, 0008, 0009, 0010, 0011, 0022, 0037, 0040, 0052, 0055, 0058, 0060, 0061, 0062, 0064, 0070

**Vulkan RDNA3 (RADV, zmierzone 0006–0010):**
  - **works+gain**: 0006, 0007, 0008, 0009, 0010, 0031, 0047, 0048, 0065, 0066, 0067, 0068, 0069
  - **unknown-needs-test**: 0004, 0017, 0020, 0029, 0030, 0032, 0041
  - **works-neutral**: 0024, 0033, 0034, 0036, 0038, 0039, 0044, 0046
  - **excluded**: 0001, 0002, 0003, 0005, 0011, 0012, 0013, 0014, 0015, 0016, 0018, 0019, 0021, 0022, 0023, 0025, 0026, 0027, 0028, 0035, 0037, 0040, 0042, 0043, 0045, 0049, 0050, 0051, 0052, 0053, 0054, 0055, 0056, 0057, 0058, 0059, 0060, 0061, 0062, 0063, 0064, 0070

Vulkan RDNA2/RDNA4: jak wyżej, ale 0006–0010 to „?”. 0010 i 2-wierszowe IQ4_XS z 0007 są tylko dla RDNA3/4. Shader z 0007 jest bitowy dla każdego vendora.

### 6.2 Windows AMD

HIP SDK, runtime PAL.

**RDNA3:**
  - **works+gain**: 0004, 0020, 0029, 0030, 0031, 0032, 0041, 0047, 0048, 0065, 0066, 0067, 0068, 0069
  - **unknown-needs-test**: 0001, 0002, 0003, 0011, 0012, 0013, 0014, 0015, 0016, 0017, 0019, 0021, 0022, 0024, 0025, 0026, 0027, 0028, 0033, 0034, 0035, 0036, 0037, 0038, 0040, 0042, 0045, 0049, 0050, 0051, 0052, 0053, 0054, 0055, 0056, 0057, 0058, 0059, 0062, 0064, 0070
  - **works-neutral**: 0005, 0018, 0023, 0039, 0043, 0044, 0046, 0063
  - **excluded**: 0006, 0007, 0008, 0009, 0010, 0060, 0061

RDNA3.5, RDNA2 i RDNA4 na Windows: przecięcie powyższej listy z wykluczeniami arch z §6.1 (manifest, kolumny `windows-amd-hip-*`).

**Vulkan na Windows** (sterownik AMD, nie RADV):
  - **works+gain**: 0031, 0047, 0048, 0065, 0066, 0067, 0068, 0069
  - **unknown-needs-test**: 0004, 0006, 0007, 0008, 0009, 0010, 0017, 0020, 0029, 0030, 0032, 0041
  - **works-neutral**: 0024, 0033, 0034, 0036, 0038, 0039, 0044, 0046
  - **excluded**: 0001, 0002, 0003, 0005, 0011, 0012, 0013, 0014, 0015, 0016, 0018, 0019, 0021, 0022, 0023, 0025, 0026, 0027, 0028, 0035, 0037, 0040, 0042, 0043, 0045, 0049, 0050, 0051, 0052, 0053, 0054, 0055, 0056, 0057, 0058, 0059, 0060, 0061, 0062, 0063, 0064, 0070

Uwagi:
- **Build:** do builda HIP potrzebny jest strażnik CMake z 0060 (§5 #11).
- **TDR (2 s):** dotyczy też AMD, ale żaden nasz kernel dekodowania nie trwa dłużej niż milisekundy. Prefill FA przy 32k to ~3.4 s łącznie na wiele kerneli, więc pojedynczy kernel jest ≪ 2 s `[SZACUNEK]`.
- **Profilowanie:** rocprofv3 nie istnieje na Windows, więc A/B na Windows to tylko pomiar e2e (`spec_sweep`, `llama-bench`).

### 6.3 Linux NVIDIA (sm_86 / sm_89 / sm_120)

  - **works+gain**: 0004, 0020, 0029, 0030, 0031, 0032, 0041, 0047, 0048, 0065, 0066, 0067, 0068, 0069
  - **unknown-needs-test**: 0001, 0002, 0003, 0012, 0013, 0014, 0015, 0016, 0017, 0019, 0021, 0024, 0025, 0026, 0027, 0028, 0033, 0034, 0035, 0036, 0038, 0043, 0045, 0049, 0050, 0051, 0053, 0056, 0057, 0059
  - **works-neutral**: 0005, 0018, 0023, 0039, 0044, 0046, 0063
  - **excluded**: 0006, 0007, 0008, 0009, 0010, 0011, 0022, 0037, 0040, 0042, 0052, 0054, 0055, 0058, 0060, 0061, 0062, 0064, 0070

Uwagi:
- **Wspólny kod, nigdy nie uruchomiony.** 30 łatek z „?” to wspólny kod `ggml-cuda`, aktywny domyślnie i nigdy nie uruchomiony na NVIDIA.
- **Mniejszy zysk z fuzji `[SZACUNEK]`.** Ich zysk na AMD pochodzi głównie z usuwania granic kernela: 2.53–2.75 µs w grafie HIP vs ~0.8 µs/węzeł w grafie CUDA (raport 07 §2.2.1, F7).
- **0043 zmienia kolejność akumulacji.** Dotyczy FA MMA, gdy `nbatch_K2 < DKQ/2`, więc bity są inne niż upstream (jakość neutralna).

### 6.4 Windows NVIDIA (WDDM)

Werdykty są identyczne jak w §6.3 (manifest `windows-nvidia-cuda-*`), z dodatkami specyficznymi dla Windows:
- **Build:**
  - testy z `__builtin_popcountll` (0019, 0057) pod MSVC, `[SZACUNEK]`, że się nie skompilują;
  - nvcc z hostem MSVC dla `__builtin_memcpy` / `__builtin_assume_aligned` w kodzie urządzenia (`amd-opt:mmvq.cu:228,397,449`) do sprawdzenia w CI.
- **Sysmem Fallback:**
  - 0020 dodaje +180 MiB VRAM (kopia wierszy `token_embd`);
  - 0059 dodaje 2×2 MiB pinned + 4 MiB device;
  - 0029 dodaje pinned staging.

  Na kartach 12–16 GB przy pełnym `--fit` może to przelać alokacje do RAM bez błędu [S9]. Budżet VRAM w daemonie musi to uwzględnić. 0033 działa odwrotnie: zmniejsza VRAM stanów GDN z 748 do 195 MiB.
- **TDR 2 s [S8]:** jak w §6.2. Najdłuższe kernele to prefill (MMQ/FA), ms na kernel.
- **WDDM:** batching launchy i wyższy koszt submit. Fuzje mogą dać tu relatywnie więcej niż na Linux `[SZACUNEK]`. Do zmierzenia.

### 6.5 macOS (Metal)

  - **works+gain**: 0031, 0047, 0048, 0065, 0066, 0067, 0068, 0069
  - **unknown-needs-test**: 0004, 0017, 0020, 0029, 0030, 0032, 0041
  - **works-neutral**: 0024, 0033, 0034, 0036, 0038, 0039, 0044, 0046
  - **excluded**: 0001, 0002, 0003, 0005, 0006, 0007, 0008, 0009, 0010, 0011, 0012, 0013, 0014, 0015, 0016, 0018, 0019, 0021, 0022, 0023, 0025, 0026, 0027, 0028, 0035, 0037, 0040, 0042, 0043, 0045, 0049, 0050, 0051, 0052, 0053, 0054, 0055, 0056, 0057, 0058, 0059, 0060, 0061, 0062, 0063, 0064, 0070

Na Metal przenosi się warstwa hosta/samplera:
- 0031 i 0047–0048: ARM64 bez SSE2, skalarny fallback;
- 0065–0069.

Pozostałe:
- **Zmiany grafu MTP** (0004, 0020, 0030, 0032, 0041) są niezależne od backendu, ale nie były uruchomione na Metal.
- **0029 aktywne na Metal**, bo bufory Metal mają `is_host=false`.
- **0033–0038:** nowy op nie jest wspierany na Metal, więc działa automatyczny fallback (N).
- **Brak kodu GPU.** Żaden nasz kernel nie przenosi się na Metal; to nowa kampania (raport 07 §2.3.2).

## 7. Ile zysku z XTX jest osiągalne na każdej platformie

Podstawa:
- **Qwen3.8-27B:** spec_sweep, MTP n=4, T=1, 41.7 → 27.74 ms/krok (Σ per-łatkowych Δ = 14.14 ms; raport 07 §2.1, NOTES:221-239). Podział A3–A5 (4.0 ms) na 0012/0013/0014 jest proporcjonalny do liczby usuniętych kerneli: 128/384/336 z 848, `[SZACUNEK]`. Podział K2 i K3 jest przeskalowany do sumy etapu `[SZACUNEK]`.
- **LFM2.5:** tg128 5.07 → 3.40 ms/token (Σ 1.736). Wcześniejsze +17% LFM z łatek Qwena (169.3 → 198.3 t/s) nie jest przypisane do łatek, więc nie wchodzi do sumy.

| platforma | Qwen: G | Qwen: ? | realistycznie `[SZACUNEK]` | LFM: G | LFM: ? | realistycznie `[SZACUNEK]` |
|---|---|---|---|---|---|---|
| Linux RDNA3 (XTX) | 14.14 ms (100%) | 0 | 100% (zmierzone) | 1.736 (100%) | 0 | 100% |
| Linux RDNA3 inne SKU | jak XTX | — | 85–100% (strojenie 96 CU w 0052/0062/0064) | jak XTX | — | 80–100% |
| Linux RDNA3.5 (gfx1151) | 10.28 (73%) | 3.86 (27%: 0021, 0022, PM4) | 75–95% | 0.914 (53%) | 0.594 (34%: 0054, PM4) | 55–85% |
| Linux RDNA4 | 10.28 (73%) | 1.63 (12%: 0021) | 70–80%; brak PM4 (−10%) i kvq (długi ctx) | 0.914 (53%) | 0.131 (8%) | ~55%; brak PM4 (−27%), kvq, n1-rows |
| Linux RDNA2 | 10.28 (73%) | 1.63 (12%) | 65–75% | 0.914 (53%) | 0.131 (8%) | ~50% |
| Windows AMD HIP RDNA3 | 3.51 (25%, host/llama) | 9.27 (66%) | 25–90%; górna granica, jeśli PAL ma podobny koszt granicy co ROCr; bez PM4 max 90% | 0 | 1.273 (73%) | 0–73% |
| Linux/Windows NVIDIA | 3.51 (25%) | 8.40 (59%) | ~39% = G + 0.3 × (? bez 0021) | 0 | 0.914 (53%) | ~16% |
| Vulkan AMD (L/W) | 0.94 (7%) | 2.93 (21%) | ~15–25% + własne 0006–0010 (−5.2% ms/krok) | 0 | 0 | sampler |
| macOS Metal | 0.94 (7%) | 2.93 (21%) | ~15–25% | 0 | 0 | sampler |

Poza tabelą (inne scenariusze):
- **Pre-baseline (0001–0004).** Zysk liczony przed punktem 41.7 ms:
  - 0001/0002 MMVQ multi: +20% t/s. Na innych arch „?”, ścieżka aktywna;
  - 0003 cache q8_1: +2–4%. Na RDNA G, na NVIDIA i Windows HIP „?”;
  - 0004 słownik draftu: +7.5%. Przenosi się wszędzie z MTP; na Metal i Vulkan „?”.
- **Długi kontekst.**
  - Kvq FA (0011: 94k +65%; 0055: 98k LFM +20%) to **tylko RDNA3_0**. Na RDNA3.5, RDNA4, RDNA2, NVIDIA, Metal i Vulkan tego zysku nie będzie bez portu WMMA gfx12 lub mma.
  - Na Windows RDNA3 jest „?”: kompiluje się, ale inny clang.
- **Prefill:**
  - 0040, 0045, 0070: +2% każda;
  - 0042+0043: FA prefill 40 → 49 TFLOPS.

  Na RDNA3 (Linux) G. 0045 jest ogólna (G na RDNA, „?” na NVIDIA). 0042/0070 na RDNA3.5 i RDNA4 „?”.
- **Sampler i UI (0048, 0065–0069):** jedyna warstwa z G na **każdej** platformie: Qwen MTP UI 99 → 107–113 t/s, LFM UI 255 → 291–294 t/s, LFM z `repeat_penalty` +13%. To jest główny ogólny zysk dla NVIDIA i macOS, zgodnie z raportem 07 §2.3.4 („+13–15% w ścieżkach samplera”).

Interpretacja:
- **Zysk XTX w 75% to kod GPU.** Na NVIDIA i Windows AMD „pewne” jest tylko 25% zysku Qwena (host + graf MTP).
- **Fuzje decydują o reszcie.** Pozostałe ~60–66% to fuzje, które na tych platformach są aktywne, ale niesprawdzone. Pierwszy test na RTX 5060 Ti / 3060 (E4) rozstrzygnie, czy na NVIDIA zostawić je włączone, czy wyłączyć przełącznikiem.
- **PM4 wyłącznie na Linux RDNA3.** PM4 (10% Qwen, 27% LFM) to największa pojedyncza strata poza tą platformą.

## 8. Testy potrzebne do rozstrzygnięcia „?”

Kolejność według kosztu. Narzędzia już istnieją (`tools/fusion/greedy.sh`, `test-backend-ops`, `tools/kld_canary.sh` / `kld_gate.py`, `tools/loo.py`, `samp_ab.py`, `spec_sweep.py`, `pm4_soak.py`).

| ID | test | platforma / sprzęt | rozstrzyga łatki | kryterium |
|---|---|---|---|---|
| T0 | **Build matrix bez GPU (CI):**<br>• Linux CUDA `-DCMAKE_CUDA_ARCHITECTURES=86;89;120`<br>• Linux HIP `gfx1030;gfx1151;gfx1201`<br>• Windows HIP SDK 7.2 (najpierw bez, potem ze strażnikiem `hsa-runtime64`)<br>• Windows CUDA + MSVC z `LLAMA_BUILD_TESTS=ON`<br>• macOS Metal | CI, darmowe | wszystkie (kompilacja); §5 #11, #12; build-breaker 0060; `__builtin_popcountll` | build zielony; dla gfx1201/gfx1151 dump ISA i VGPR/spill kerneli 0021, 0042, 0054, 0070 (`--save-temps`, `isadiff.py`) |
| T1 | **NVIDIA op-level:** `test-backend-ops -b CUDA0` dla:<br>• MUL_MAT n=1–16 (wszystkie typy multi), MUL_MAT_PAIR, MUL_MAT_ADD, MUL_MAT_ID<br>• RMS_NORM*, RMS_NORM_GATE, SSM_CONV(_LAG_CACHE_FUSION), GATED_DELTA_NET(_LAG)<br>• MOE_DOWN_REDUCE, NORM_ROUTER_TOPK, TOPK_MOE, FFN_GATE_UP_DOWN, ATTN_PREP, SHORTCONV<br>• FLASH_ATTN_EXT, GET_ROWS, ARGMAX | RTX 3060 (sm_86), 5060 Ti (sm_120); 4090 (sm_89, Vast) | 0001–0003, 0012–0017, 0019, 0021, 0024–0028, 0033–0036, 0038, 0043, 0045, 0049–0051, 0053, 0056, 0057, 0059 | 100% PASS vs CPU |
| T2 | **NVIDIA bitowość w obrębie jednej binarki:** `greedy.sh` (Qwen plain, Qwen MTP, LFM) i hash logitów 64 kroków dla wszystkich `GGML_HIP_*=0` vs domyślnie. Łatki bez przełącznika (0001–0003, 0012–0017, 0019, 0021, 0034–0036, 0045) porównujemy przez build upstream v0.7.0 (po rebase E6) + `kld_canary.sh` | j.w. | j.w. | env-off == env-on (md5); KLD fork vs upstream ≤ 2σ szumu |
| T3 | **NVIDIA wydajność:**<br>• `loo.py` (ABBA, sparowane CI) per przełącznik na `spec_sweep` (Qwen MTP n=4) i `llama-bench tg128` (LFM)<br>• osobno `test-backend-ops perf` MUL_MAT n=2..8 fork vs upstream (0001/0002/0021) | j.w. | zysk/strata każdej fuzji; decyzja o domyślnym `=0` na NVIDIA | zysk ≥ 3% albo „brak istotnej zmiany”; regresja → predykat `arch != nvidia` |
| T4 | **Inne RDNA (Linux):** T1 + T2 + T3 na RX 9070 XT (RDNA4), RDNA3.5 (gfx1151, np. Strix Halo) i RDNA2 (6700 XT). Na gfx1151 dodatkowo:<br>• `pm4_soak.py` + `GGML_HIP_PM4_DEBUG=1` (0060)<br>• A/B `MMVQ_R3_X_CPOL` (0022)<br>• `GGML_HIP_MMQ_EPI=0/1` (0070)<br>Na RDNA4: FA prefill D=256 perf + KLD (0042) | 9070 XT (zakup), Hostkey R9700, gfx1151 (do wypożyczenia), 6700 XT (beta) | 0001, 0002, 0021, 0022, 0040, 0042, 0054, 0060, 0070 (+ potwierdzenie G z §6.1) | md5 = env-off; zysk w ABBA |
| T5 | **Windows AMD HIP** (dual boot tej samej karty): po T0 uruchomić T1 + T2, z md5 porównanym z Linuxem na tej samej karcie (różne clangi mogą dać różne bity; wtedy KLD). Do tego mikrobench granicy kernela w grafie HIP pod PAL (jak raport 07 §2.2.1 pkt 4) | 7900 XTX + Windows (PLAN §5.1: później) | wszystkie „?” w `windows-amd-hip-*` (41 łatek) | md5/KLD; koszt granicy decyduje, czy fuzje się opłacają |
| T6 | **Vulkan:** 0006–0010 na RDNA2/RDNA4 i na Windows AMD Vulkan: `test-backend-ops -b Vulkan0` MUL_MAT + KLD dla 0006/0008/0009 + `llama-bench` ABBA. 0029 na Vulkan: md5 i ms/krok przy `LLAMA_ASYNC_INPUTS=0/1`. Graf MTP (0004, 0020, 0030, 0032, 0041) na Vulkan: drafty identyczne, md5 MTP | 9070 XT, 6700 XT, XTX pod Windows | 0004, 0006–0010, 0017, 0020, 0029, 0030, 0032, 0041 | PASS, KLD ≤ 2σ, zysk w ABBA |
| T7 | **macOS Metal** (Mac mini M4, Scaleway): md5 Qwen MTP i LFM z `LLAMA_ASYNC_INPUTS=0/1`, `LLAMA_MTP_CHAIN_SCHED=0/1`, `--spec-draft-vocab` on/off; `samp_ab.py` dla samplera (sprawdza też ścieżkę bez SSE2) | Mac mini M4 (€0.22/h, min. 24 h) | 0004, 0017, 0020, 0029, 0030, 0032, 0041; potwierdzenie G dla 0031, 0047, 0048, 0065–0069 | md5 równe, zysk w ABBA |
| T8 | **Windows NVIDIA specyficznie:** pełna karta przy `--fit` z 0020 (+180 MiB) i bez, z monitorowaniem „Shared GPU memory” w Menedżerze zadań lub `nvidia-smi`; sprawdzenie, że nie ma resetu TDR na najdłuższym prefillu (`-ub 512`, 32k) | 5060 Ti 16 GB / 3060 12 GB | 0020, 0029, 0059 (VRAM/pinned); wszystkie (TDR) | brak spadku t/s × 5–30, brak TDR |
| T9 | **Luka z raportu 07:** KLD Qwena dla 0011 (kvq q4_0), tylko RDNA3 | XTX | 0011 | KLD ≤ 2σ vs f16-KV |

Szacunek GPU-h `[SZACUNEK]`:
- T1–T3: ~6–8 h na kartę NVIDIA;
- T4: ~6 h na kartę AMD;
- T6: ~3 h;
- T7: ~4 h, przy czym Scaleway liczy minimum 24 h wynajmu;
- T0: tylko CI.

Wynajem dotyczy tylko 4090 (T1–T3) i Mac mini (T7); koszt do zatwierdzenia na liście kosztów rodzica. Niczego nie wynajmowałem.

## 9. Rekomendacje dla manifestu i daemona

1. **Predykaty z manifestu** (`portability`, `scope`, `guard`) jako `applies_if`:
   - 0060/0061: `os: linux, runtime: rocr, arch: gfx110x` (gfx115x dopiero po T4);
   - 0011/0037/0052/0055/0058/0062/0064: `backend: hip, arch: gfx110x`;
   - 0022/0040/0070: `arch: gfx110x` do czasu T4 (dziś kod bierze też gfx115x);
   - wszystkie łatki ze `scope: cuda` na NVIDIA: domyślnie **wyłączone przełącznikiem** do czasu T1–T3. Obecny stan to „włączone bez testu”.
2. **Poprawki kodu, które powinny wejść przed E3/E4** (do decyzji rodzica, ja nic nie zmieniałem):
   - strażnik CMake dla `hsa-runtime64` (0060): `if (GGML_HIP_PM4 AND NOT WIN32)` + `#ifdef` w `hip-pm4.cu`;
   - zamiana `__builtin_popcountll` w testach;
   - przemianowanie przełączników `GGML_HIP_*` czytanych w kodzie wspólnym na `GGML_CUDA_*` (lub alias);
   - zawężenie `GGML_CUDA_CC_IS_RDNA3` → `_RDNA3_0` w 0060/0070/0040 do czasu testu na gfx1151.
3. **Poprawić raport 07 i NOTES:** klasa 0001/0002/0021/0025/0026 to „GEN-CUDA/HIP (strojenie RDNA3)”, a nie „AMD-RDNA3 / tylko HIP”.
4. **W PLAN §4.5 wiersz „Windows: HIP SDK na innym runtime niż ROCr `[SZACUNEK]`”** można zamienić na fakt z cytatami [S1–S5]. Dopisać, że na Windows nie ma rocprofv3, więc fabryka nie może profilować per kernel na Windows (RGP to inne narzędzie).

## 10. Źródła

- [S1] AMD, *Using HIP runtime API* (HIP docs, latest): https://rocm.docs.amd.com/projects/HIP/en/latest/how-to/hip_runtime_api.html
- [S2] AMD, *ROCm components supported in HIP SDK* (HIP SDK for Windows 7.2.0, 2026-08-20): https://rocm.docs.amd.com/projects/install-on-windows/en/latest/conceptual/component-support.html
- [S3] ROCm/rocm-systems `projects/clr/rocclr/device/device.cpp:843-907` @ `6e6db17`: https://github.com/ROCm/rocm-systems/blob/6e6db1702450885dfa8d1234b1e8e1e5ebab626f/projects/clr/rocclr/device/device.cpp#L843-L907
- [S4] ROCm/rocm-systems `projects/clr/rocclr/cmake/ROCclr.cmake:7-8` @ `6e6db17`: https://github.com/ROCm/rocm-systems/blob/6e6db1702450885dfa8d1234b1e8e1e5ebab626f/projects/clr/rocclr/cmake/ROCclr.cmake#L7-L8
- [S5] ROCm/TheRock `docs/development/windows_support.md` @ `4d992b3`: https://github.com/ROCm/TheRock/blob/4d992b34d67c91397ecaf4483d73d01c0b5c3fa3/docs/development/windows_support.md
- [S6] ROCm/rocm-systems PR #8900 „Use rocr backend for HIP/OCL by default” (draft, zamknięty 2026-10-04): https://github.com/ROCm/rocm-systems/pull/8900
- [S7] ROCm/TheRock PR #6713 „Change HIP to use default GPU_ENABLE_PAL=0” (draft): https://github.com/ROCm/TheRock/pull/6713
- [S8] Microsoft, *TDR registry keys* (TdrDelay, domyślnie 2 s): https://learn.microsoft.com/en-us/windows-hardware/drivers/display/tdr-registry-keys
- [S9] NVIDIA, *System Memory Fallback* (sterownik 536.40+): https://nvidia.custhelp.com/app/answers/detail/a_id/5490
- Lokalne:
  - `~/KERNEL/product/research/07-nasze-metody-uogolnienie.md` (§2.1, §2.3);
  - `~/KERNEL/qwen-opt/NOTES.md:40-66,182-239`;
  - `~/qwen-opt/tools/loo/loo-plan.json` (head `c36fd2c87`, 65 łatek; 0066–0070 dopisane z diffów);
  - drzewo `~/llama-master` @ `amd-opt` `f61994f58` (odczyt `git show`, bez checkoutu).
