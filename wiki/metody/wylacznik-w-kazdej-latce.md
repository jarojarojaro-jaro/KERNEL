---
typ: metoda
tags: [metody, wylaczniki, ab]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:222; ~/KERNEL/product/research/08-analiza-platformy-latek.md:45; ~/KERNEL/qwen-opt/patches/llama.cpp-amd-opt/0024-*.patch, 0063-*.patch; ~/KERNEL/qwen-opt/NOTES.md:374,383
status: aktualne
---
# Wyłącznik w każdej łatce

**Każda łatka z prędkością ma przełącznik `GGML_HIP_*=0` / `LLAMA_*=0`, który przywraca starą ścieżkę w tej samej binarce, więc A/B nie miesza zmiennej „inny build”.**

- Wspólny mechanizm `ggml_cuda_env_switch` wszedł z łatką 0024 (para MMVQ); 0063 przeniosło na niego `GGML_HIP_PM4` i `GGML_HIP_CONV_ROWS4`.
- Przykłady: `GGML_HIP_PM4=0` (replay PM4), `LLAMA_GDN_REPLAY=0` (lag/replay GDN), `LLAMA_SAMPLER_FAST_GRAMMAR=0` (każdy `=0` przywraca pełną ścieżkę 128k/248k kandydatów).
- Dzięki wyłącznikom działa [[loo]] (27 wyłączników env + 2 CLI) i diagnoza regresji u użytkownika.
- Pułapka (raport 08): przełączniki `GGML_HIP_*` czyta także build CUDA i domyślnie są włączone; raport rekomenduje nazwy `GGML_CUDA_*` albo bramkę `GGML_USE_HIP`.

Pełna tabela przełączników: [[wylaczniki-env]].

## Powiązane
- [[metody/_hub|Metody]]
- [[playbook-optymalizacji]]
- [[pomiar-abba]]
- [[wylaczniki-env]]
- [[cuda-compat]]
