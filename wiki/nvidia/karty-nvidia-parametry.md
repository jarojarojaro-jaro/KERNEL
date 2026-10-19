---
typ: nvidia
tags: [nvidia, karty, pasmo]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21b-gpu-perf-zasoby.md:72-84
status: aktualne
---
# Karty NVIDIA (i XTX): pasmo, L2, SM – liczby do rachunków

**Parametry do modeli kosztu: XTX 960 GB/s, 6 MB L2 + 96 MB MALL, 96 CU; 3090 936 GB/s, 6 MB, 82 SM; 4090 1008 GB/s, 72 MB, 128 SM; 5060 Ti 448 GB/s, 32 MB, 36 SM; 5090 1792 GB/s, 96 MB (persist ≤ 60 MB), 170 SM (raport 21b, 2026-10-19).**

| karta | PDL | TMA | klastry | FP8 / FP4 tensor |
|---|---|---|---|---|
| XTX (gfx1100) | brak | brak | brak | brak / brak |
| 3090 (sm_86) | brak | brak (cp.async) | brak | brak / brak |
| 4090 (sm_89) | brak (cc < 9.0) | brak | brak | tak / brak |
| 5060 Ti, 5090 (sm_120) | tak | tak | tak, bez multicast | tak / tak (`sm_120a`) |

Little's law (latencja DRAM ~600 ns `[ZAŁOŻENIE]`): każda karta potrzebuje ~5–8 KB w locie na SM/CU ([[lekcja-littles-law-gemv]]). Źródła: whitepaper Blackwell RTX tab. 1, Wikipedia RTX 50, fengwang (60 MB persist).

## Powiązane
- [[nvidia/_hub|NVIDIA]]
- [[sm-86-89-120]]
- [[inne-karty-nvidia]]
- [[projekcja-rtx-5090]]
