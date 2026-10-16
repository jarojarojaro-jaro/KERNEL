---
typ: kernel
tags: [kernele, moe, lfm]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:340-341,346,348,355,364; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:124,126,128,131,178-180; ~/KERNEL/product/research/09-chmura-3090.md:91-104,115; ~/KERNEL/product/research/09-chmura-5060ti.md:95-119; ~/KERNEL/product/research/09-chmura-3060.md:136,145-147
status: aktualne
---
# Fuzje MoE dla LFM2.5 (0049, 0051, 0053, 0056)

**Cztery fuzje dekodowania pojedynczego tokenu w warstwach MoE (64 ekspertów, 4 aktywne): łącznie −0.565 ms/token, ok. 34% zysku kampanii LFM.**

Profil przed (2026-10-14): mul_mat_vec_q 71%, topk_moe 3.5 µs × 38, router F32 2.5%, quantize_q8_1 3.7%; ~721 kerneli/token.

| łatka | co | ms/token (llama-bench) | wyłącznik |
|---|---|---|---|
| 0049 | norma FFN pisze q8_1 dla gate/up ekspertów | 5.067 → 4.979 (720 → 682 kerneli) | `GGML_HIP_Q8_IDS` |
| 0051 | down ekspertów + ważenie + residual jednym MMVQ; nowy test MOE_DOWN_REDUCE | 4.817 → 4.642 (→ 521 kerneli) | `GGML_HIP_MOE_DOWN_REDUCE` |
| 0053 | norma FFN + router F32 + top-k w jednym kernelu (top-k liczy ostatni blok z licznikiem atomowym) | 4.451 → 4.246 (521 → 445 kerneli) | `GGML_HIP_NORM_ROUTER` |
| 0056 | gate+up(+GLU) pisze q8_1 dla down | 4.070 → 3.973 | `GGML_HIP_GATE_UP_Q8` |

Wszystkie bitowo identyczne. Kod wspólny CUDA/HIP (kompiluje się dla NVIDIA, nieuruchomiony). Raport 07: działa dla MoE z dopasowanym wzorcem `topk_moe` (testowane 64/4); fuzje z ticketami atomowymi (0053) to obszar ryzyka cichych błędów na NVIDIA.

Na NVIDIA (kampania 2026-10-16) dwie z nich szkodzą, bo atomowy ticket i bariera warpu kosztują więcej niż tani osobny `quantize_q8_1` przy grafach CUDA i PDL:
- `GGML_HIP_GATE_UP_Q8` (0056): wyłączenie przyspiesza tg128 o +6.5% LFM / +2.2% Qwen (3090), +5.34% / +2.38% (5060 Ti), +2.39% Saluki (3060) → domyślnie off na NVIDIA od `3da7a02ec`;
- `GGML_HIP_Q8_IDS` (0049): +4.99% LFM po wyłączeniu na 5060 Ti → off w profilu Blackwell; na 3090 +4.6% sam, ale z `MMVQ_N1_ROWS=2` −1.6%, więc w profilu Ampere zostaje włączony.
`MOE_DOWN_REDUCE` i `NORM_ROUTER` pomagają też na NVIDIA (3090: −1.2% i −2.1% po wyłączeniu). Profile są bitowo równe forkowi.

Nie wyszło: norma następnej warstwy jako ogon kernela MoE down (13 → 56 µs/wywołanie).

## Powiązane
- [[kernele/_hub|Kernele]]
- [[lfm-shortconv]]
- [[cache-q8-1]]
- [[lfm2-5-24b-a2b]]
- [[lfm-runda-2]]
- [[latki-na-nvidia]]
