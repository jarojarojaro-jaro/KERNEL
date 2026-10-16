---
typ: lekcja
tags: [lekcje, cuda, build]
aktualizacja: 2026-10-16
zrodlo: ~/qwen-opt/cloud/CUDA-AUDIT.md:5-18
status: aktualne
---
# Fork amd-opt nie budował się dla CUDA (0057, 0070)

**`amd-opt` nie kompilował się dla CUDA: dwa błędy z łatek 0070 i 0057 psuły 25 jednostek kompilacji; naprawa w `cuda-compat` (4 commity), build 579/579 kroków w 835 s.**

- 0070: helper epilogu MMQ `ggml_cuda_mmq_epi_pin` (asm `"+v"`, `ext_vector_type`) bez guarda → teraz pod `GGML_USE_HIP`.
- 0057: range-for po braced list – clang przyjmuje, nvcc nie → jawny `std::initializer_list`.
Przy okazji wyszły dwa błędy semantyczne: brak `ggml_cuda_pdl_sync` w 0053/0057 na sm_120 i brak bariery warpu przy tickecie 0056. Lekcja: kod „GEN-CUDA/HIP” (12 łatek) nigdy nie był uruchomiony na NVIDIA, więc każdy commit HIP trzeba choćby kompilować dla CUDA w CI.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-pdl-sm120]]
- [[lekcja-mtp-embd-state]]
- [[cuda-compat]]
- [[cuda-compat-galaz]]
