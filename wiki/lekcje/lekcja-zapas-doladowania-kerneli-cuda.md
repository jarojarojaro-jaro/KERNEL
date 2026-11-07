---
typ: lekcja
tags: [lekcje, cuda, pamiec, planer, enigma]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/product/research/67-nvidia-vast-kampania.md:48-56; ~/KERNEL/app/engine/src/server/catalog/index.ts (CUDA_GAP_MIB, CUDA_KERNEL_MARGIN_MIB)
status: aktualne
---
# Załadowany model z 0,6 GiB wolnego i tak pada przy pierwszym długim prompcie (CUDA)

**Qwen3.8-27B ISTA IQ3_XXS-mtp z MTP ładował się na 16 GB (5060 Ti, 5080, 4060 Ti) przy 200–217k z 0,5–0,66 GiB wolnego według `nvidia-smi`, a potem wywalał się przy pierwszym prefillu 4 096 tokenów w `launch_mul_mat_q`, bo CUDA doładowuje kernele leniwie (2026-11-07).**

Dwa błędy na raz:
- `nvidia-smi` pokazuje więcej, niż CUDA może przydzielić: różnica 313–498 MiB zależnie od karty (3080 313, 4070 327, 3070 350, 3060 379, 4060 Ti 433, 2080 Ti 447, 3090 450, 5060 Ti 465, 5080 466, 4090 482, 5090 498);
- po załadowaniu potrzeba jeszcze ~0,3 GiB na kernele, które CUDA wczytuje przy pierwszym większym batchu.

Reguła: budżet planu = suma CUDA (tabela per karta), a nad nim zapas ≥0,7 GiB łącznie; walidacja konfiguracji = załadowanie **i** pełne wypełnienie kontekstu na tych samych flagach. Sam load nic nie dowodzi.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[jak-przyspieszylismy-nvidia]]
- [[2026-11-07-kampania-nvidia-vast]]
- [[lekcja-rezerwa-mtp-kopia-f16]]
