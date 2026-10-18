---
typ: metoda
tags: [metody, proces, negatywne]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:98-105,351,369; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:234; ~/KERNEL/product/research/16a-pm4-pdl.md:7-19
status: aktualne
---
# Wyniki negatywne zapisujemy z liczbami

**Każda próba, która nie dała zysku, trafia do NOTES z liczbami i powodem, żeby nikt nie wracał do niej bez nowego pomysłu.**

Przykłady z `qwen-opt/NOTES.md` (sekcja „Wyniki negatywne (nie wracać bez nowego pomysłu)” i wpisy rund):
- fuzja gate+up (+SwiGLU) w MMVQ dla 2–8 kolumn: DFlash 111 → 96, MTP 82 → 76 t/s (podwójne rejestry = niższe obłożenie);
- zmienne środowiskowe HIP (graph batch/segment, classic path, kernarg…): szum; `GGML_CUDA_GRAPH_OPT=1`: −1%;
- LFM runda 1: Hadamard + quantize wyjścia atencji 4.474 → 4.490 ms, `--backend-sampling` (szybki, ale nie bitowo);
- LFM runda 3: ładowania nontemporal wag gate+up 12.9 → 14.4 µs (wolniej);
- raport „1075 GB/s, 112% peaku” był błędny: przy MTP jeden przebieg daje ~2.7 tokenu, więc odczyt wag to ~400 GB/s.

Zasada scalania: tylko realny zysk w przeplatanym A/B. Bitowy, ale w szumie (GDN fast +0.15%) = nie scalamy, gałąź zostaje.

2026-10-18: PM4-PDL i prefetch MALL na XTX ([[raport-16a-pm4-pdl]], [[lekcja-prefetch-mall-xtx]]); MoE matvec LFM ([[2026-10-18-lfm-moe-negatywne]]).

## Powiązane
- [[metody/_hub|Metody]]
- [[playbook-optymalizacji]]
- [[pomiar-abba]]
- [[eksperymenty/_hub|Eksperymenty]]
- [[gdn-fast]]
