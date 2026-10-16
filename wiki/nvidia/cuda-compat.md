---
typ: nvidia
tags: [nvidia, cuda-compat, poprawki]
aktualizacja: 2026-10-16
zrodlo: ~/qwen-opt/cloud/CUDA-AUDIT.md:5-18,52-97,174-196; ~/qwen-opt/cloud/patches-cuda-compat/ (4 pliki); git -C ~/llama.cpp log cuda-compat
status: aktualne
---
# Gałąź cuda-compat: poprawki forka dla NVIDIA

**`amd-opt` nie kompilował się dla CUDA; gałąź `cuda-compat` @ `7b2680760` dodaje 4 commity (2 kompilacyjne, 2 semantyczne), a kod GPU dla gfx1100 zostaje bit w bit ten sam.**

| # | commit | łatka | problem na CUDA |
|---|---|---|---|
| 1 | `57e0bdfe4` | 0070 | `ggml_cuda_mmq_epi_pin` (asm `"+v"`, `ext_vector_type`) bez guarda psuł każdą TU z `mmq.cuh` → teraz pod `GGML_USE_HIP` |
| 2 | `780365407` | 0057 | range-for po braced list: clang przyjmuje, nvcc (EDG) nie → jawny `std::initializer_list` |
| 3 | `14506801c` | 0053, 0057 | brak `ggml_cuda_pdl_sync`: na sm_120 (PDL) kernel mógł czytać dane poprzednika przed jego końcem |
| 4 | `7b2680760` | 0056 | brak bariery warpu (`__syncwarp`) przy tickecie q8_1 (model pamięci Volta+) |

Bez poprawek build `amd-opt` padał w 25 TU (`ggml-cuda.cu`, `mmq.cu`, `mmvq.cu`, `quantize.cu`, 21 instancji MMQ). Po: 579/579 kroków, rc=0, 835 s.

Dowód niezmienności HIP (`hip-proof.py`): dla 6 dotkniętych TU wszystkie sekcje code objectu gfx1100 identyczne (sha256), host `.text` różni się tylko argumentami `__LINE__`.

Te same 4 commity siedzą na gałęziach opartych o v0.7.0 (`cuda-v070`: `b479c67dd`…`7a538d96f`). Gałęzie z kampanii: `cuda-3090-opt` i `cuda-v070-5060ti` dokładają wyłączniki do bisekcji md5 (`GGML_HIP_GDN_L2`, `GGML_HIP_GDN_AB`, `GGML_HIP_Q8_PRODUCER`) i `GGML_CUDA_MMVQ_N1_ROWS=2|4` (domyślnie wyłączone, w pomiarach).

## Powiązane
- [[nvidia/_hub|NVIDIA]]
- [[latki-na-nvidia]]
- [[cuda-stos]]
- cuda-v070
- [[lekcja-pdl-sm120]]
