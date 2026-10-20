---
typ: metoda
tags: [metody, proces, negatywne]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:98-105,351,369; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:234; ~/KERNEL/product/research/16a-pm4-pdl.md:7-19; ~/KERNEL/product/research/26-kolejka-gpu-wieczor.md:10-12; ~/KERNEL/product/research/24n-mmvq-n5.md:7-12; ~/KERNEL/product/research/24r-mmvq-pasmo.md:10-13; ~/KERNEL/product/research/24w-pair2.md:5,21-34
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

2026-10-19/20: bariera LDS (szum), MMVQ n=1 wide (−1.0%), ogon OOV klastrowy (−1.5%), obłożenie MMVQ n=5 (−0.5% / −6.4%), RPB=1 (−3.0%), `-np 2` (wall +11%), router DFlash2 (sufit +1.1%), entropia wag (≤ 0.9%), FA bez spilli (+0.4–0.8%, za mało) – przegląd w [[raporty-2026-10-19-20]].
PAIR2 (24w, 2026-10-20 rano): para MMVQ dla mieszanych typów, md5 OK, czat +0.4% (115.1 → 115.6 t/s) – odrzucone ([[raport-24w-pair2]]).

## Powiązane
- [[metody/_hub|Metody]]
- [[playbook-optymalizacji]]
- [[pomiar-abba]]
- [[eksperymenty/_hub|Eksperymenty]]
- [[gdn-fast]]
