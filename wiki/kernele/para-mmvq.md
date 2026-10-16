---
typ: kernel
tags: [kernele, mmvq, fuzje]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:260,265-266; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:99,222; ~/KERNEL/product/research/patch-manifest.json (0024)
status: aktualne
---
# Para MMVQ jedną siatką (0024)

**Dwa MUL_MAT tego samego typu na tym samym wejściu (ffn up/gate, GDN qkv/z) liczone jednym uruchomieniem kernela zamiast dwóch.**

- Łatka 0024, runda K2 (gałąź `opt-k2`, 2026-10-13). W grafie qwen35 qkv i z rozwijają się obok siebie, więc para pasuje bez zmiany modelu.
- Zysk: razem z 0025–0026 kernele weryfikacji 972 → 911 (raport 07); całe K2: Qwen 33.17 → 32.14 ms/krok (97.8 t/s), Uncensored → 30.68 ms/krok (99.6 t/s).
- Poprawność: bitowo identyczne.
- Wyłącznik: `GGML_HIP_MMVQ_PAIR=0`. Ta łatka wprowadziła wspólny mechanizm przełączników `ggml_cuda_env_switch`.
- Kod wspólny CUDA/HIP; raport 07 ocenia szansę upstreamu jako dobrą.

## Powiązane
- [[kernele/_hub|Kernele]]
- [[mmvq-multikolumnowe]]
- [[gdn-fuzje-k2]]
- [[wylacznik-w-kazdej-latce]]
- [[wylaczniki-env]]
