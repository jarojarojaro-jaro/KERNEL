---
typ: kernel
tags: [kernele, vulkan, mmvq]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:162-168,190-191; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:81-85
status: nieaktualne
---
# Vulkan RDNA: matvec i MMVQ (0006–0010)

**Pięć łatek backendu Vulkan (RADV) z 2026-10-12, zanim ROCm został stałym backendem; dziś poza domyślną ścieżką.**

| łatka | co | zysk | poprawność |
|---|---|---|---|
| 0006 | small-M matvec (ssm_alpha/beta q8_0 m=48) ścieżką float, WG 256 | 13.6 → 8.6 µs/wywołanie (~0.5 ms/krok) | numeryka, bez osobnej bramki |
| 0007 | MMVQ fast path K-quantów/IQ4_XS | q4_K 6 kol. 614 → 690 GB/s | bitowa |
| 0008 | Q6_K przez integer-dot MMVQ od 4 kolumn | lm_head n=6 1.9 → 1.3 ms | KLD 0.0042 (szum batch 6 vs 512: 0.0036) |
| 0009 | float matvec dla m<4096 przy >4 kolumnach | q6_K m=1024 18.1 → 9.7 µs | numeryka, bez osobnej bramki |
| 0010 | 2 wiersze/WG przy 8 kolumnach | mieszane | bitowa |

Łącznie 0007–0010: ms/krok Qwen UD 43.73 → 41.46 (−5.2%), Uncensored 41.93 → 39.92 (−4.8%), powtarzalne co do 0.3 ms.

Status `nieaktualne`: od decyzji z 2026-10-12 optymalizujemy pod ROCm, a Vulkan zostaje opcją (`run-llm.sh … vulkan`). Wyłączniki: brak (build); w LOO liczone jako „nie-szybkościowe”.

## Powiązane
- [[kernele/_hub|Kernele]]
- [[mmvq-multikolumnowe]]
- [[rocm-vs-vulkan]]
- [[2026-10-12-rocm-domyslny]]
- [[seria-amd-opt]]
