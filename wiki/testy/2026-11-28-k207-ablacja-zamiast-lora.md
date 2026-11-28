---
typ: test
tags: [testy, nvidia, vast, 5060ti, inkling, enigma, k207, ablacja, lora]
aktualizacja: 2026-11-28
zrodlo: ~/dev/KERNEL/qwen-opt/cloud/nvq3/results/qwenbench-nvq3-5060tia-11280352/; patch jaroserverai ~/wt/k207 (k207-ablate f7040f25e), kopia nvq3/k207/0001-ablate-lora.patch
status: aktualne
---
# 2026-11-28 K-207: ablacja kierunku zamiast LoRA w llama.cpp (Inkling 2 Mini, 5060 Ti)

**`--ablate-lora` (nasz patch na b12811) daje to samo odcenzurowanie co `--lora`, ale szybciej: wall 29,2 / 28,6 → 41,2 / 41,1 t/s (+41% / +44%), odmowy 0/5, KL vs LoRA 0,0087 przy podłodze szumu 0,0086. Koszt 0,045 $.**

Warunki: RTX 5060 Ti na hoście EPYC 7402 (moc 160/180 W, pamięć 14 001 MHz, 42 °C; bramka llama-bench 99% GPU), ten sam plik binarny w trzech ramionach, przepis K-204 (IQ3_S + DSpark n2, ub 128, `-c 262144`), wall = mediana 4 promptów × 300 tok. Host ogranicza procesor (LoRA 29 t/s wobec 66 w K-204 na Ryzenie), więc liczby tylko jako stosunek.

| ramię | wall T=0 / T=0,7 | odmowy | VRAM ładowanie / szczyt (MiB) |
|---|---|---|---|
| LoRA (baza) | 29,17 / 28,64 | 0/5 | 15 587 / 15 633 |
| **ablacja** | **41,17 / 41,11 (+41% / +44%)** | **0/5** | 15 587 / 15 657 |
| bez adaptera | 35,67 / 40,08 | – | 15 545 / 15 609 |

KL (wiki 16 × 255 tok., baza LoRA): ablacja 0,00865 (top1 95,8%), podłoga LoRA × 1,00001 0,00859 (96,1%), bez adaptera 0,0136. Przy sile LoRA × 8: ablacja 0,0176, bez adaptera 0,266.

## Pomiar bezwzględny na Ryzenie (2026-11-28 17:05, 0,054 $)
RTX 5060 Ti, host Ryzen 7 9700X (180/180 W, pamięć 14 001 MHz), ten sam przepis i plik binarny: **ablacja 88,45 / 90,78 t/s**, LoRA 76,58 / 71,22, bez adaptera 85,83 / 89,53; ablacja vs LoRA +15,5% / +27,5%, odmowy 0/5, 262 144 startuje we wszystkich ramionach (15,6 / 16 GB). Ten sam host vs EPYC 7402: 2,1–2,6× szybciej, choć llama-bench tg256 prawie równy (78,0 vs 74,9) — bramka llama-bench nie wykrywa wolnego procesora hosta.

## Mechanizm
- `--ablate-lora PLIK` czyta ten sam plik LoRA rzędu 1 i zamiast mnożenia przez macierze robi `y -= s·r(r·y)` po wyjściu uwagi, po sumie ekspertów MoE i na wierszach embeddingu, w każdym przejściu pętli (to samo co `IK2_ABLATE` w Mai); trzy operacje ggml na miejsce.
- LoRA jest wolna na MoE, bo jej ścieżka F32 przez wagi ekspertów (`mul_mat_id`) wymusza synchronizację strumienia i wyłącza grafy CUDA.
- Inkling IQ3_S reaguje na każde zaburzenie 1e-5 KL 0,002–0,009, więc porównania KL zawsze z ramieniem podłogi.
- Bramka tg256 nie łapie hostów wolnych na ścieżce serwera (EPYC 7402: 99% GPU w llama-bench, a dekod serwera z DSpark 2× wolniejszy niż na Ryzenie).

## Na później
- Przepis Enigmy 16 GB z `--ablate-lora` zamiast `--lora` wymaga naszego builda (nie upstream) — decyzja JARO (88,45 vs 66,45 t/s w K-204 na Ryzenie 7600, inny host).
- RTX 5080: pierwszy pomiar Inklinga czeka na budżet ok. 0,15 $ (hosty 0,32–0,37 $/h).
- Patch do upstream (ogólny, nie tylko Inkling).

## Test u nas
Zrobione (K-207). Pomiar bezwzględny na Ryzenie: przy następnej rundzie Vast.
