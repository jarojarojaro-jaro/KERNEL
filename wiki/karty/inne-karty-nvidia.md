---
typ: karta
tags: [karty, nvidia, lab]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/05-chmura-gpu-do-testow.md:15-19,100-108,234-236,305-321; ~/KERNEL/product/PLAN.md:282,290,296; ~/qwen-opt/cloud/PLAN-TESTOW.md:102,138; ~/KERNEL/qwen-opt/research/tensorfold/issues.md:34; ~/KERNEL/qwen-opt/research/tensorfold/spec-host.md:156
status: aktualne
---
# Pozostałe karty NVIDIA w planie (4060 Ti, 4070, 4090, 5070, 5090, A40, L40S)

**Karty z listy MVP produktu, których jeszcze nie testowaliśmy; dane rynkowe z raportu 05 (2026-10).**

| karta | arch | VRAM | Steam 09/2026 | Vast mediana $/h | uwagi |
|---|---|---|---|---|---|
| RTX 4060 Ti 16 GB | sm_89 | 16 | 2.85% | 0.153 (feed: wariant 8 GB) | opcjonalna 4. karta w PLAN-TESTOW |
| RTX 4070 | sm_89 | 12 | 2.11% | 0.176 | MVP |
| RTX 4090 | sm_89 | 24 | — | 0.507 | używana €2,185; RunPod $0.89/h |
| RTX 5070 | sm_120 | 12 | 6.15% (#1) | 0.294 | pozycja 4 na liście zakupów |
| RTX 5090 | sm_120 | 32 | 0.40% | 0.734 (445 ofert) | nowa ~$7,444; RunPod $1.19/h |

Decyzja z 2026-10-15 (PLAN §5.2): popularne karty kupujemy, rzadkie i drogie (3090, 4090, 5090) wynajmujemy na Vast.

Karty spotkane tylko w cudzych pomiarach: **A40** (TensorFold #358: 27B za Xeonem 2.1 GHz, CUDA graphs 57–76 → 65–86 t/s na jednym GPU) i **L40S** (TensorFold #296: 27B — TensorFold 152, vLLM 96, llama.cpp 71 t/s). Nie planujemy ich.

## Powiązane
- [[karty/_hub|Karty]]
- [[rtx-3090]]
- [[rtx-5060-ti]]
- [[vast-ai]]
- raport-05-chmura
