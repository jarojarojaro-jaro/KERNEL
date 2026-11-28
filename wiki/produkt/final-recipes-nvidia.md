---
typ: produkt
tags: [produkt, nvidia, przepisy, enigma, vram]
aktualizacja: 2026-11-28
zrodlo: ~/qwen-opt/cloud/results/nv67c-summary.txt; product/research/67-nvidia-vast-kampania.md §1, §7; wiki/testy/2026-11-27-k204-enigma-16gb-inkling.md (16 GB 5060 Ti / 4060 Ti, decyzja JARO 2026-11-28); app/engine/data/catalog.json; app/engine/data/engines.json; app/engine/CONTRACT.md:174-194
status: aktualne
---
# Finalne przepisy NVIDIA per klasa VRAM (na stronę)

**Zmierzone przepisy Enigmy z kampanii 67c (2026-11-07): dziś na silniku upstream (pin b11856) 24–32 GB daje 61–102 t/s przy 245–262k, a z silnikami Enigmy (lean / prism / fork, po publikacji archiwów) 5090 148,6, 4090 101,3, 3090 80,0 t/s przy 262 144, 12 GB Bonsai 58–95 t/s. 16 GB od 2026-11-28 (K-204, decyzja JARO): 5060 Ti i 4060 Ti na Inklingu 2 Mini bez cenzury z DSpark, 66,5 / 48,6 t/s przy 262 144 / 283 648; 5080 bez zmian (Qwen3.8-27B GSQ, lean MTP 81,6 t/s przy 217 088).**

Wspólne flagi: `llama-server -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c <ctx> -ub <ub> --jinja`. MTP upstream: `--spec-type draft-mtp --spec-draft-n-max 3 --spec-draft-n-ubatch 64`. Lean: to samo z `--spec-draft-n-max 2 -ctkd q4_0 -ctvd q4_0`. Fork: `--spec-draft-n-max 4 -ctkd q4_0 -ctvd q4_0 --spec-draft-vocab <draft_vocab_qwen38.txt> --spec-draft-vocab-n 65536 --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs` + env `GGML_CUDA_KVQ=1 LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_GPU_VERIFY=1 LLAMA_SERVER_CACHE_SHARE_MIN=1024`. t/s = mediana `spec_sweep` T=1 (6 promptów, seed 1), na nazwanej karcie i jej limicie mocy; peak = szczyt VRAM po pełnym wypełnieniu kontekstu (fill PASS, jeśli nie napisano inaczej). Wiersze „po publikacji” działają u użytkownika dopiero po uploadzie archiwów (`app/engine/CONTRACT.md`, „brakujący krok”).

Inkling na 16 GB (K-204): `llama-server -m Inkling-2-Mini-GSQ-RCO-IQ3_S.gguf --lora Inkling-2-Mini-Uncensored-LoRA.gguf -md dspark-Inkling-2-Mini-Q8_0.gguf -ngl 99 -ngld 99 -fit off -fa on -ctk q4_0 -ctv q4_0 -c <ctx> -ub 128 -b 128 -np 1 --jinja --spec-type draft-dspark --spec-draft-n-max 2 --spec-draft-p-min 0`, oficjalny llama.cpp b12811. Bez `-ctkd/-ctvd` (KV draftera q4 zajmuje więcej i pada przy 270k). Te wiersze mierzą inaczej niż reszta tabeli: t/s = mediana 4 promptów (kod, tech, pl, json) × 300 tok., T=0 / T=0,7, a peak = szczyt VRAM przy 95% głębokości + 700 tok. odpowiedzi.

Licencje: Qwen3.8-27B, Qwen3.5-9B, ISTA GSQ (Qwen i Inkling), Bonsai, Inkling 2 Mini (Thinking Machines), LoRA bez cenzury Inklinga ([AtomicChat](https://huggingface.co/AtomicChat/Inkling-2-Mini-Uncensored-GGUF)), drafter DSpark – Apache-2.0; LFM2.5 – LFM Open 1.0 (firmy < $10M przychodu).

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

## 16 GB (RTX 5080 przy 250 W, 5060 Ti przy 160 W (K-204: 180 W), 4060 Ti (K-204: 150 W))

| wariant | model, kwant | ctx | silnik, flagi | t/s | peak MiB | licencja |
|---|---|---|---|---|---|---|
| Enigma dziś: 5060 Ti, 4060 Ti (silnik upstream, K-204) | [Inkling 2 Mini GSQ-RCO](https://huggingface.co/ISTA-DASLab/Inkling-2-Mini-GSQ-RCO-GGUF) IQ3_S + [LoRA bez cenzury](https://huggingface.co/AtomicChat/Inkling-2-Mini-Uncensored-GGUF) + DSpark Q8_0 n2 | 5060 Ti 262 144, 4060 Ti 283 648 (igły 5/5 przy 95%) | b12811, ub/b 128, KV q4_0, p_min 0 | 5060 Ti **66,45 / 61,97**, 4060 Ti **48,58 / 48,99** (T=0 / 0,7) | 15 698 / 15 955 | Apache-2.0 |
| Enigma dziś: 5080 (silnik upstream); Inkling na 5080 niezmierzony | [Qwen3.8-27B ISTA GSQ](https://huggingface.co/ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF) IQ3_XXS-mtp | 208 896 | pin b11856, bez MTP, ub 256 | **58,81** | 14 562 | Apache-2.0 |
| poprzednio Enigma dziś: 5060 Ti, 4060 Ti (do 2026-11-28) | j.w. (Qwen3.8-27B ISTA GSQ IQ3_XXS-mtp) | 5060 Ti 200 704, 4060 Ti 217 088 | pin b11856, bez MTP, ub 256 | 5060 Ti **31,42**, 4060 Ti **24,02** (K-204 na tym samym hoście i tym samym skrypcie: 32,50 / 23,94 przy T=0) | 14 230 / 14 566 | Apache-2.0 |
| z silnikiem Enigmy (lean) – Qwen3.8-27B GSQ; dla 5060 Ti i 4060 Ti już tylko alternatywa | j.w. (Qwen3.8-27B ISTA GSQ IQ3_XXS-mtp) | 5080 217 088, 5060 Ti i 4060 Ti 229 376 | b12110lean, MTP n2, ub 256 | 5080 **81,62**, 5060 Ti **43,40**, 4060 Ti **36,30** | 15 632 / 15 762 / 15 736 | Apache-2.0 |
| z silnikiem Enigmy (fork+kvq+lean) – wariant krótszego ctx | j.w. (Qwen3.8-27B ISTA GSQ IQ3_XXS-mtp) | 196 608 | fork kvqlean, ub 256 | 5060 Ti **49,44** | 15 416 | Apache-2.0 |
| alternatywa MoE (upstream) | [LFM2.5-24B-A2B](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B-GGUF) Q4_K_M | 131 072 | b12110, KV q8_0, ub 512, w całości w VRAM | 5060 Ti **139,48** | 15 820 | LFM Open 1.0 (< $10M) |

W aplikacji Enigma (Linux): 5060 Ti i 4060 Ti dostają Inklinga z silnikiem `enigma-cuda-inkling` (oficjalny b12811, LoRA i DSpark pobierane z HF razem z silnikiem); Windows i 5080 zostają przy Qwen3.8-27B GSQ. LoRA kosztuje 17–33% dekodu (bez niej 79,6 / 72,2 t/s); tańsza droga to K-207.

## 12 GB (RTX 4070, RTX 3060 przy 140 W)

| wariant | model, kwant | ctx | silnik, flagi | t/s | peak MiB | licencja |
|---|---|---|---|---|---|---|
| Enigma dziś (silnik upstream) | [Bonsai 2 27B](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) Q2_0 | 4070 196 608, 3060 196 608 (pełne wypełnienie PASS) | upstream, bez MTP, ub 256 | 4070 **49,43**, 3060 **32,23** (przy 65 536) | – | Apache-2.0 |
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
- [[KOLEJKA-TESTOW]]
- [[rtx-3090]]
- [[inne-karty-nvidia]]
- [[2026-11-27-k204-enigma-16gb-inkling]]
- [[inkling-2-mini]]
