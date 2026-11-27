---
typ: model
tags: [modele, qwen, maly-model]
aktualizacja: 2026-11-22
zrodlo: wiki/REKORDY.md:93,202,204; product/research/16d-magnitude-vs-nasz.md:110-114
status: aktualne
model: qwen3-5-9b
rozmiar: 9B
kwant: Q4_K_M, Q6_K
karty: rtx-5060-ti
wyniki:
  - qwen3-5-9b | rtx-5060-ti | 239.0 t/s | code-edit; fork CUDA gałąź cuda-v070-5060ti, 1 runda | 2026-10-16
  - qwen3-5-9b | rtx-5060-ti | 121.0 t/s | sweep; fork CUDA, 1 runda | 2026-10-16
  - qwen3-5-9b | rtx-5060-ti | 2343 t/s | prefill 64k; fork CUDA | 2026-10-16
---
# Qwen3.5-9B (mały Qwen do kart 8–12 GB)

**Mały model Qwena, który mierzymy jako model dla kart z 8–12 GB VRAM: na 5060 Ti nasz fork CUDA daje 239,0 t/s przy edycji kodu i 121,0 t/s w sweepie (1 runda, 2026-10-16).**

- 5060 Ti (fork `cuda-v070-5060ti`, 2026-10-16): sweep / code-edit / copy 64k 121,0 / 239,0 / 128,1 t/s, prefill 64k 2343 t/s (REKORDY:93).
- Kampania 67c (2026-11-07, Vast): RTX 3080 260 W Q6_K, ctx 192 512: 85,20 t/s; RTX 3070 Q4_K_M, ctx 151 552: 66,90 t/s (REKORDY:202, 204). Te karty nie mają własnych notatek.

<!-- TABELE:START -->
## Wyniki z notatek (3)

Najlepszy wynik na metrykę z pól `wynik` notatek testów (tools/tabele.py, 2026-11-28); pełna tabela: [[najlepsze-wyniki]].

| karta | metryka | najlepszy | warunki | data | źródło |
|---|---|---|---|---|---|
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | code-edit | **239.0 t/s** | fork CUDA gałąź cuda-v070-5060ti, 1 runda | 2026-10-16 | [[qwen3-5-9b]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | prefill 64k | **2343 t/s** | fork CUDA | 2026-10-16 | [[qwen3-5-9b]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | sweep | **121.0 t/s** | fork CUDA, 1 runda | 2026-10-16 | [[qwen3-5-9b]] |
<!-- TABELE:END -->

## Powiązane
- [[qwen3-8-27b]]
- [[rtx-5060-ti]]
- [[2026-10-16-magnitude-vs-fork]]
- [[REKORDY]]
