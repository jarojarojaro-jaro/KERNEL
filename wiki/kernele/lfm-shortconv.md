---
typ: kernel
tags: [kernele, lfm, conv]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:337,347,356,374,378; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:125,129,137,182,272; ~/KERNEL/product/research/08-analiza-platformy-latek.md:25
status: aktualne
---
# Fuzje shortconv LFM2 (0050, 0054, 0062)

**LFM2.5 ma 30 warstw krótkiej konwolucji (shortconv); trzy łatki wciągają mnożenia i samą konwolucję do sąsiednich kerneli: łącznie −0.366 ms/token (~22% zysku LFM).**

| łatka | co | ms/token | wyłącznik |
|---|---|---|---|
| 0050 | b·x i c·conv w kernelu SSM_CONV, który pisze q8_1 dla out_proj | 4.979 → 4.800 (→ 595 kerneli) | `GGML_HIP_CONV_MUL` |
| 0054 | shortconv w kernelu in_proj: blok kończący grupę 32 kanałów liczy jej konwolucję (drugi slot cache q8_1) | 4.231 → 4.100 (445 → 416 kerneli) | `GGML_HIP_INPROJ_CONV` |
| 0062 | in_proj+conv: 4 wiersze/blok | 3.458 → 3.402, znika rozrzut per proces | `GGML_HIP_CONV_ROWS4` |

Skąd 0062: siatka dokładnie 3072 bloków (96 CU × 32 fale = pełna pojemność GPU) dawała bimodalne 13.6 lub 14.6 µs per proces; 2560 bloków zawsze 12.2 µs.

Bitowo identyczne. Platformy: 0050 to kod wspólny CUDA/HIP; 0054 działa na każdym RDNA (bramka `GGML_CUDA_CC_IS_RDNA`, korekta raportu 08); 0062 tylko gfx110x i zależy od liczby CU.

## Powiązane
- [[kernele/_hub|Kernele]]
- [[fuzje-lfm-moe]]
- [[mmvq-n1-wiersze]]
- [[lfm2-5-24b-a2b]]
- [[lfm-runda-4-pm4]]
