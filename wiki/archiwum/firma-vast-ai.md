---
typ: archiwum
tags: [archiwum, chmura]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/05-chmura-gpu-do-testow.md:7,13-22
status: nieaktualne
wycofano: 2026-11-22
powod: ten sam dostawca dwa razy (firma i chmura)
zastapiona_przez: karty/vast-ai
---
# Vast.ai

**Rynek wynajmu GPU na godziny; nasze główne źródło NVIDIA do testów (kontenery do benchmarków, VM do profilowania).**

Mediany on-demand z feedu 2026-10-15 21:30 UTC: RTX 3060 0.08 $, 3090 0.23 $, 4090 0.51 $, 5060 Ti 0.16 $, 5070 0.29 $, 5090 0.73 $ (445 ofert). Zero ofert AMD (feed: 80 modeli, wszystkie NVIDIA). W kontenerach brak liczników profilera i blokady zegarów; VM ma „CUDA profiling with hardware counters”. Szczegóły operacyjne, CLI i lekcje w notatce chmury.

## Powiązane
- [[karty/runpod]]
- [[karty/salad]]
- [[vast-ai]]
- [[karty/vast-ai]]
