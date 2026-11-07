---
typ: karta
tags: [karty, nvidia, lab]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/product/research/05-chmura-gpu-do-testow.md:15-19,100-108,234-236,305-321; ~/KERNEL/product/PLAN.md:282,290,296; ~/qwen-opt/cloud/PLAN-TESTOW.md:102,138; ~/KERNEL/qwen-opt/research/tensorfold/issues.md:34; ~/KERNEL/qwen-opt/research/tensorfold/spec-host.md:156; ~/qwen-opt/cloud/results/nv67c-summary.txt
status: aktualne
---
# Pozostałe karty NVIDIA (2080 Ti, 3070, 3080, 4060 Ti, 4070, 5080, 4090, 5070, 5090, A40, L40S)

**Karty bez osobnej strony: dane rynkowe z raportu 05 (2026-10) i zmierzone picki Enigmy z kampanii 67c (2026-11-07).**

| karta | arch | VRAM | Steam 09/2026 | Vast mediana $/h | uwagi |
|---|---|---|---|---|---|
| RTX 4060 Ti 16 GB | sm_89 | 16 | 2.85% | 0.153 (feed: wariant 8 GB) | opcjonalna 4. karta w PLAN-TESTOW |
| RTX 4070 | sm_89 | 12 | 2.11% | 0.176 | MVP |
| RTX 4090 | sm_89 | 24 | — | 0.507 | używana €2,185; RunPod $0.89/h |
| RTX 5070 | sm_120 | 12 | 6.15% (#1) | 0.294 | pozycja 4 na liście zakupów |
| RTX 5090 | sm_120 | 32 | 0.40% | 0.734 (445 ofert) | nowa ~$7,444; RunPod $1.19/h |

Decyzja z 2026-10-15 (PLAN §5.2): popularne karty kupujemy, rzadkie i drogie (3090, 4090, 5090) wynajmujemy na Vast.

Karty spotkane tylko w cudzych pomiarach: **A40** (TensorFold #358: 27B za Xeonem 2.1 GHz, CUDA graphs 57–76 → 65–86 t/s na jednym GPU) i **L40S** (TensorFold #296: 27B — TensorFold 152, vLLM 96, llama.cpp 71 t/s). Nie planujemy ich.

## Kampania 67c (2026-11-07, Vast, seed 1 T=1, fill PASS jeśli nie napisano inaczej)

| karta (limit mocy) | pick Enigmy | t/s, peak MiB | z silnikiem Enigmy |
|---|---|---|---|
| 5090 (575 W) | Qwen3.8-27B UD-Q6_K 262 144 MTP n3, pin | 62,49 → **102,19**, 28 592 | fork+kvq+lean ub 512 **148,57** (+47,4%), 28 232; pin vs b12110 ABBA 99,8 vs 91,7 |
| 4090 (250/450 W) | UD-Q4_K_XL 262 144 MTP n3 ub 256 | 46,94 → **76,44**, 24 028 | fork+kvq+lean **101,27**, 23 852 |
| 5080 (250/360 W) | ISTA IQ3_XXS-mtp 208 896 plain | 58,81, 14 562 | lean MTP n2 217 088 **81,62**, 15 632 |
| 4070 (200 W) | Saluki IQ2-mix 151 552 plain | 44,35, 11 201 | prism Bonsai PTQ1_0 MTP n2 208 896 **94,73**, 11 163; LFM UD-IQ3_XXS w VRAM 179,32 |
| 3080 (260/320 W) | Qwen3.5-9B Q6_K 192 512 | **85,20**, 9 345 | LFM Q4_K_M ncm 20: 40,83 |
| 3070 (220 W) | Qwen3.5-9B Q4_K_M 151 552 | 66,90, 7 251 | LFM Q4_K_M ncm 26: 8,92 |
| 2080 Ti (250 W, czysty host) | Bonsai 2 Q2_0 131 072 (upstream) | 39,57, 10 243 | prism PTQ1_0-mtp-lean MTP n2 155 648 ub 512 **77,96**, 10 151 (n1 max 196 608 PASS) |

Przepisy na stronę: [[final-recipes-nvidia]]; kampania: [[2026-11-07-kampania-nvidia-vast]].

## Powiązane
- [[karty/_hub|Karty]]
- [[rtx-3090]]
- [[rtx-5060-ti]]
- [[vast-ai]]
- raport-05-chmura
