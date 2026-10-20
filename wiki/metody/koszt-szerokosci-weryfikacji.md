---
typ: metoda
tags: [metody, spekulacja, weryfikacja, kvq]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/16b-lookup-tail.md:55-70; ~/qwen-opt/lookup/e2/e2_table.txt:2-5; ~/qwen-opt/lookup/e2_bench.sh; ~/KERNEL/product/research/24k-koszt-weryfikacji.md:3-9; ~/KERNEL/product/research/24s-proza-drzewa.md:16,109
status: aktualne
---
# Krzywa kosztu szerokości weryfikacji V(w, kontekst) na XTX

**Pomiar E2 z 16b (`llama-bench -fa 1 -ctk q4_0 -ctv q4_0 -p 1,5,8,9,16 -n 0 -d …`, mediana powtórzeń 3–5, Qwen3.8-27B): V16 − V5 = 6.40 / 7.13 / 9.50 / 12.45 ms przy 2k / 8k / 32k / 64k – hipoteza 15b „≤ 12 ms przy 32k” potwierdzona (2026-10-18).**

| kontekst | V1 | V5 | V8 | V9 | V16 | V8 − V5 | V16 − V5 |
|---|---|---|---|---|---|---|---|
| 2k | 22.83 | 24.14 | 26.60 | 27.97 | 30.53 | 2.46 | 6.40 |
| 8k | 23.02 | 24.47 | 27.06 | 28.46 | 31.60 | 2.59 | 7.13 |
| 32k | 23.62 | 25.65 | 28.94 | 30.93 | 35.15 | 3.29 | 9.50 |
| 64k | 24.60 | 27.21 | 31.00 | 34.03 | 39.66 | 3.79 | 12.45 |

- Skok 8 → 9 kolumn (próg K4 WMMA) 1.4–3.0 ms, kolejne kolumny 9 → 16 ~0.37–0.8 ms/kol.
- Przyrost z kontekstem pochodzi z kafli kvq ([[fattn-kvq]]); 16i zakładało przy 64k +18 ms, pomiar daje +12.45.
- Pierwsze dwa powtórzenia to rozgrzewka grafu (+5…+40 ms) – odrzucać.
- Porównanie: Magnitude na Vulkanie blok 8 = ×3.0 kroku 1-wierszowego ([[lekcja-koszt-szerokosci-backendu]]). CUDA (>8 kolumn przez MMQ) do zmierzenia (16i E-C1).

W serwerze (24k, 2026-10-19): krok W16 na `mvs` 35.61 vs MTP4 29.62 ms; 5 → 16 wierszy ≈ 9.4 ms (llama-bench 6.4 ms nie liczy głowy LM, replay GDN ani kopii logitów 0.045 ms/wiersz) ([[raport-24k-koszt-weryfikacji]]). Drzewa MTP opłacą się (≥ +6% proza) dopiero przy ≤ 0.57 ms na wiersz 5 → 8 (dziś 0.85) ([[raport-24s-drzewa-proza]]).

## Powiązane
- [[metody/_hub|Metody]]
- [[kontroler-szerokosci-draftu]]
- [[2026-10-18-lookup-ogon]]
- [[mmvq-multikolumnowe]]
