---
typ: produkt
tags: [produkt, nvidia, przepisy, enigma, vram]
aktualizacja: 2026-11-07
zrodlo: ~/qwen-opt/cloud/results/nv67c-summary.txt; product/research/67-nvidia-vast-kampania.md §1, §7; app/engine/data/catalog.json; app/engine/data/engines.json; app/engine/CONTRACT.md:174-194
status: aktualne
---
# Finalne przepisy NVIDIA per klasa VRAM (na stronę)

**Zmierzone przepisy Enigmy z kampanii 67c (2026-11-07): dziś na silniku upstream (pin b11856) 24–32 GB daje 61–102 t/s przy 245–262k, a z silnikami Enigmy (lean / prism / fork, po publikacji archiwów) 5090 148,6, 4090 101,3, 3090 80,0 t/s przy 262 144, 16 GB MTP przy 217–229k (+57–84%), 12 GB Bonsai 58–95 t/s.**

Wspólne flagi: `llama-server -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c <ctx> -ub <ub> --jinja`. MTP upstream: `--spec-type draft-mtp --spec-draft-n-max 3 --spec-draft-n-ubatch 64`. Lean: to samo z `--spec-draft-n-max 2 -ctkd q4_0 -ctvd q4_0`. Fork: `--spec-draft-n-max 4 -ctkd q4_0 -ctvd q4_0 --spec-draft-vocab <draft_vocab_qwen38.txt> --spec-draft-vocab-n 65536 --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs` + env `GGML_CUDA_KVQ=1 LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_GPU_VERIFY=1 LLAMA_SERVER_CACHE_SHARE_MIN=1024`. t/s = mediana `spec_sweep` T=1 (6 promptów, seed 1), na nazwanej karcie i jej limicie mocy; peak = szczyt VRAM po pełnym wypełnieniu kontekstu (fill PASS, jeśli nie napisano inaczej). Wiersze „po publikacji” działają u użytkownika dopiero po uploadzie archiwów (`app/engine/CONTRACT.md`, „brakujący krok”).

Licencje: Qwen3.8-27B, Qwen3.5-9B, ISTA GSQ, Bonsai – Apache-2.0; Saluki – CC BY-NC 4.0 (**tylko niekomercyjnie**); LFM2.5 – LFM Open 1.0 (firmy < $10M przychodu).

## 32 GB (RTX 5090, 575 W)

| wariant | model, kwant | ctx | silnik, flagi | t/s | peak MiB | licencja |
|---|---|---|---|---|---|---|
| Enigma dziś (silnik upstream) | [Qwen3.8-27B](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF) UD-Q6_K | 262 144 | pin b11856, MTP n3, ub 1024 | **102,19** (bez MTP 62,49) | 28 592 | Apache-2.0 |
| z silnikiem Enigmy (fork+kvq+lean) – po publikacji archiwów | j.w. | 262 144 | fork kvqlean, ub 512 | **148,57** (pick na tym samym hoście 100,90) | 28 232 | Apache-2.0 |

## 24 GB (RTX 4090 przy 250 W, RTX 3090 przy 340 W)

| wariant | model, kwant | ctx | silnik, flagi | t/s | peak MiB | licencja |
|---|---|---|---|---|---|---|
| Enigma dziś (silnik upstream) | [Qwen3.8-27B](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF) UD-Q4_K_XL | 262 144 (3090: 245 760) | pin b11856, MTP n3, ub 256 | 4090 **76,44**, 3090 **61,49** | 24 028 / 23 448 | Apache-2.0 |
| z silnikiem Enigmy (fork+kvq+lean) – po publikacji archiwów | j.w. (UD-Q4_K_XL) | 262 144 | fork kvqlean (3090: `kvqleana`, CPU bez AVX2), ub 256 | 4090 **101,27**, 3090 **79,97** | 23 852 / 23 706 | Apache-2.0 |

## 16 GB (RTX 5080 przy 250 W, 5060 Ti przy 160 W, 4060 Ti)

| wariant | model, kwant | ctx | silnik, flagi | t/s | peak MiB | licencja |
|---|---|---|---|---|---|---|
| Enigma dziś (silnik upstream) | [Qwen3.8-27B ISTA GSQ](https://huggingface.co/ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF) IQ3_XXS-mtp | 5080 208 896, 5060 Ti 200 704, 4060 Ti 217 088 | pin b11856, bez MTP, ub 256 | 5080 **58,81**, 5060 Ti **31,42**, 4060 Ti **24,02** | 14 562 / 14 230 / 14 566 | Apache-2.0 |
| z silnikiem Enigmy (lean) – po publikacji archiwów | j.w. | 5080 217 088, 5060 Ti i 4060 Ti 229 376 | b12110lean, MTP n2, ub 256 | 5080 **81,62**, 5060 Ti **43,40**, 4060 Ti **36,30** | 15 632 / 15 762 / 15 736 | Apache-2.0 |
| z silnikiem Enigmy (fork+kvq+lean) – wariant krótszego ctx | j.w. | 196 608 | fork kvqlean, ub 256 | 5060 Ti **49,44** | 15 416 | Apache-2.0 |
| alternatywa MoE (upstream) | [LFM2.5-24B-A2B](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B-GGUF) Q4_K_M | 131 072 | b12110, KV q8_0, ub 512, w całości w VRAM | 5060 Ti **139,48** | 15 820 | LFM Open 1.0 (< $10M) |

## 12 GB (RTX 4070, RTX 3060 przy 140 W)

| wariant | model, kwant | ctx | silnik, flagi | t/s | peak MiB | licencja |
|---|---|---|---|---|---|---|
| Enigma dziś (silnik upstream) | [Underdog Saluki 27B](https://huggingface.co/Kujira/Underdog-Saluki-27B-1.0-MTP-GGUF) IQ2-mix | 4070 151 552, 3060 135 168 | pin b11856, bez MTP, ub 256 | 4070 **44,35**, 3060 **22,23** | 11 201 / 10 781 | CC BY-NC 4.0 – tylko niekomercyjnie |
| z silnikiem Enigmy (prism) – po publikacji archiwów | [Bonsai 2 27B PTQ1_0-mtp-lean](https://huggingface.co/sudoingx/Ternary-Bonsai-2-27B-PTQ1_0-MTP-GGUF) | 4070 208 896, 3060 204 800 | prism-b12128, MTP n2, ub 256 | 4070 **94,73**, 3060 **58,31** | 11 163 / 11 015 | Apache-2.0 |
| alternatywa MoE (upstream) | [LFM2.5-24B-A2B](https://huggingface.co/unsloth/LFM2.5-24B-A2B-GGUF) UD-IQ3_XXS | 131 072 | b12110, KV q8_0, ub 512, w całości w VRAM | 4070 **179,32**, 3060 **102,47** | 10 525 / 10 463 | LFM Open 1.0 (< $10M) |

## 11 GB (RTX 2080 Ti)

| wariant | model, kwant | ctx | silnik, flagi | t/s | peak MiB | licencja |
|---|---|---|---|---|---|---|
| Enigma dziś (silnik upstream) | [Bonsai 2 27B](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) Q2_0 | 131 072 | pin b11856 (min. b11555), bez MTP, ub 256 | **39,57** | 10 243 | Apache-2.0 |
| z silnikiem Enigmy (prism) – po publikacji archiwów | [Bonsai 2 27B PTQ1_0-mtp-lean](https://huggingface.co/sudoingx/Ternary-Bonsai-2-27B-PTQ1_0-MTP-GGUF) | 155 648 | prism-b12128, MTP n2, ub 512 | **77,96** | 10 151 | Apache-2.0 |

## 10 GB (RTX 3080 przy 260 W)

| wariant | model, kwant | ctx | silnik, flagi | t/s | peak MiB | licencja |
|---|---|---|---|---|---|---|
| Enigma dziś (silnik upstream) | [Qwen3.5-9B](https://huggingface.co/unsloth/Qwen3.5-9B-GGUF) Q6_K | 192 512 | pin b11856, ub 512 | **85,20** | 9 345 | Apache-2.0 |
| alternatywa MoE (upstream) | [LFM2.5-24B-A2B](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B-GGUF) Q4_K_M | 131 072 | b12110, KV q8_0, ub 512, `--n-cpu-moe 20` | 40,83 (tylko prędkość) | 9 685 (load) | LFM Open 1.0 (< $10M) |

## 8 GB (RTX 3070)

| wariant | model, kwant | ctx | silnik, flagi | t/s | peak MiB | licencja |
|---|---|---|---|---|---|---|
| Enigma dziś (silnik upstream) | [Qwen3.5-9B](https://huggingface.co/unsloth/Qwen3.5-9B-GGUF) Q4_K_M | 151 552 | pin b11856, ub 512 | **66,90** | 7 251 | Apache-2.0 |
| alternatywa MoE (upstream) | [LFM2.5-24B-A2B](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B-GGUF) Q4_K_M | 131 072 | b12110, KV q8_0, ub 512, `--n-cpu-moe 26` | 8,92 (tylko prędkość) | 7 555 (load) | LFM Open 1.0 (< $10M) |

Tekst na stronę (nagłówek, tabela, „jak to osiągnęliśmy”, zastrzeżenia): `product/SITE-NVIDIA.md`. Silniki Enigmy opublikowane 2026-11-07 (wydanie GitHub `enigma-engines-cuda-2026-11-07`, tylko Linux x64): wiersze „po publikacji archiwów” działają u użytkowników Linuksa.

## Powiązane
- [[jak-przyspieszylismy-nvidia]]
- [[produkt/_hub|Produkt]]
- [[final-modele-per-vram]]
- [[2026-11-07-kampania-nvidia-vast]]
- [[backlog-testow-nvidia]]
- [[rtx-3090]]
- [[inne-karty-nvidia]]
