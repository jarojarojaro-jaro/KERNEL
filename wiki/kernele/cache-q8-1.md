---
typ: kernel
tags: [kernele, q8-1, fuzje]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:82-85,229-231,346,364; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:78,90,124,131
status: aktualne
---
# Cache q8_1 aktywacji i „producenci” q8_1

**MMVQ potrzebuje wejścia skwantyzowanego do q8_1; zamiast osobnego kernela kwantyzacji przed każdym matvec, kwantyzujemy raz i najlepiej już w kernelu, który to wejście produkuje.**

| łatka | co | zysk | wyłącznik |
|---|---|---|---|
| 0003 | cache: kolejne MUL_MAT z tym samym src1 (Q/K/V, qkv/z/alpha/beta) kwantyzują wejście raz na ewaluację grafu; bufor 4 MB poza przechwytywaniem grafu | +2–4% e2e (commit 3a05006a0) | brak (build) |
| 0015 | rms_norm·mul, swiglu, unary·mul piszą q8_1 dla MMVQ (część A6) | 1308 → 1052 kerneli; 37.73 → 37.04 ms | brak (build) |
| 0049 | norma FFN pisze q8_1 dla gate/up ekspertów (LFM) | 720 → 682 kerneli/token, 5.067 → 4.979 ms | `GGML_HIP_Q8_IDS` |
| 0056 | gate+up(+GLU) pisze q8_1 dla down | 4.070 → 3.973 ms | `GGML_HIP_GATE_UP_Q8` |

Wszystkie bitowo identyczne (greedy z/bez cache równy). Kod wspólny CUDA/HIP: kompiluje się dla NVIDIA, ale nigdy tam nie był uruchomiony (manifest). Raport 07 rekomenduje 0003 i 0015 do upstreamu.

## Powiązane
- [[kernele/_hub|Kernele]]
- [[fuzje-weryfikacji]]
- [[fuzje-lfm-moe]]
- [[mmvq-multikolumnowe]]
- [[seria-amd-opt]]
