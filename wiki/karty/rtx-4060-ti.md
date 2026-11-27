---
typ: karta
tags: [karty, nvidia, sm-89]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/product/research/29-4060ti.md:3-5,9-21,25-28,56-71,77-82; ~/qwen-opt/cloud/results/nv67c-summary.txt
status: aktualne
karta: rtx-4060-ti
vram: 16 GB
pasmo: 288 GB/s
gdzie: Vast
stan: zmierzona (29, 67c)
wyniki:
  - qwen3-8-27b | rtx-4060-ti | 36,30 t/s | dekod MTP n2; ISTA IQ3_XXS-mtp lean, ctx 229 376 | 2026-11-07
  - qwen3-8-27b | rtx-4060-ti | 35.4 t/s | dekod czat T=1; UD-Q3_K_XL | 2026-10-20
  - qwen3-8-27b | rtx-4060-ti | 24,02 t/s | dekod plain; ISTA ctx 217 088 | 2026-11-07
  - lfm2-5-24b-a2b | rtx-4060-ti | 149.4 t/s | dekod; QAD-Q4_0 | 2026-10-20
---
# NVIDIA RTX 4060 Ti 16 GB (Vast, serwer buildów)

**Ada sm_89, 16 GB GDDR6 288 GB/s; zmierzona 2026-10-20 na hoście Vast z limitem mocy 100 W i PCIe gen3 x8: nasz silnik daje Qwen3.8-27B UD-Q3_K_XL czat 18.6 → 35.4 t/s (×1.90) i LFM2.5 QAD-Q4_0 114.4 → 149.4 t/s (×1.31).**

- Sprzęt: 16380 MiB, domyślny limit 165 W (host ustawił 100 W, nie do zmiany w kontenerze), sterownik 595.84 (CUDA 13.2 uruchamia buildy CUDA 12.8); host Ryzen 9 3950X, 31 GB RAM (`29:25-28`).
- Qwen Q3_K_XL (MTP w pliku): czat T=1 U0 18.6 / U1 30.6 / T 35.4 t/s, krok 81.56 vs 97.74 ms; mvs 170.9 t/s (×3.42 vs U1); decode po 16k T=0 40.1 t/s (`29:56-62`).
- Mieści kontekst 32k: VRAM T 14848 MiB po załadowaniu (`29:70`).
- Prefill T w `llama-bench` −3.5…−3.9% (sm_89) – do zbadania (`29:66-67`).
- Raport: [[raport-29-4060ti]]. Bliźniak 16 GB: [[rtx-5060-ti]] (T 50.8 t/s przy 448 GB/s).

Kampania 67c (2026-11-07, 165 W): stary pick UD-Q3_K_XL 143 360 plain PASS 19,78 t/s (b12110 19,80). Lean b12110 ISTA IQ3_XXS-mtp MTP n2 **229 376 PASS 36,30 t/s** (15 736 MiB; 245 760 crash, 262 144 OOM); n1 @200 704 34,29. Pick ISTA 217 088 plain PASS **24,02** (14 566 MiB; MTP n3 przy nim OOM). Przepisy: [[final-recipes-nvidia]].

<!-- TABELE:START -->
## Wyniki z notatek (10)

Najlepszy wynik na metrykę z pól `wynik` notatek testów (tools/tabele.py, 2026-11-28); pełna tabela: [[najlepsze-wyniki]].

| model | metryka | najlepszy | warunki | data | źródło |
|---|---|---|---|---|---|
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | dekod | **149.4 t/s** | QAD-Q4_0 | 2026-10-20 | [[rtx-4060-ti]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | serwer | **149.4 t/s** | QAD-Q4_0 | 2026-10-20 | [[raport-29-4060ti]] |
| Qwen3.8-27B [[qwen3-8-27b]] | code-edit | **170.9 t/s** | cuda-topka2 | 2026-10-20 | [[raport-29-4060ti]] |
| Qwen3.8-27B [[qwen3-8-27b]] | czat T=1 | **35.4 t/s** | Q3_K_XL, cuda-topka2, 100 W | 2026-10-20 | [[raport-29-4060ti]] |
| Qwen3.8-27B [[qwen3-8-27b]] | czat T=1 T' | **50.8 t/s** | UD-IQ4_XS, KV q4_0, 32k | 2026-10-20 | [[raport-31-4060ti]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod czat T=1 | **35.4 t/s** | UD-Q3_K_XL | 2026-10-20 | [[rtx-4060-ti]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod MTP n2 | **36,30 t/s** | ISTA IQ3_XXS-mtp lean, ctx 229 376 | 2026-11-07 | [[rtx-4060-ti]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod MTP n2 ctx 229 376 | **36,30 t/s** | ISTA IQ3_XXS-mtp, b12110lean, fill PASS | 2026-11-07 | [[2026-11-07-kampania-nvidia-vast]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod plain | **24,02 t/s** | ISTA ctx 217 088 | 2026-11-07 | [[rtx-4060-ti]] |
| Qwen3.8-27B [[qwen3-8-27b]] | mvs T' | **188.6 t/s** | UD-IQ4_XS | 2026-10-20 | [[raport-31-4060ti]] |
<!-- TABELE:END -->

## Powiązane
- [[karty/_hub|karty]]
- [[raport-29-4060ti]]
- [[rtx-5060-ti]]
- [[rtx-3090]]
- [[REKORDY]]
