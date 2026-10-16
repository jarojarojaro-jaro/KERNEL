---
typ: eksperyment
tags: [eksperymenty, konkurencja, spekulacja]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/16i-magnitude-co-robia-dobrze.md:124-196; ~/KERNEL/product/research/16i-magnitude/results.txt; ~/qwen-opt/cloud/results/magnitude-vs-3090-20261016/x/xbench.jsonl; ~/qwen-opt/cloud/results/magnitude-vs-5060ti-20261016/x/xbench.jsonl
status: aktualne
---
# 2026-10-16: rozkład wygranej Magnitude (tok/krok × ms/krok)

**We wszystkich czterech przypadkach całą przewagę Magnitude daje tok/krok (×1.45…×2.74), a ich czas kroku działa na ich niekorzyść (×0.57…×0.93); analiza CPU na danych z 16d, jedna runda na silnik.**

| GPU / workload | tok/krok Mag vs fork | ms/krok | t/s | czynnik tok/krok | czynnik krok |
|---|---|---|---|---|---|
| 3090 27B code-edit | 7.14 vs 4.91 | 50.3 vs 46.6 | 141.9 vs 105.3 | 1.45× | 0.93× |
| 3090 27B copy 64k | 7.31 vs 4.51 | 91.2 vs 64.7 | 80.2 vs 69.7 | 1.62× | 0.71× |
| 5060 Ti 9B code-edit | 13.17 vs 4.81 | 35.3 vs 20.1 | 372.9 vs 239.3 | 2.74× | 0.57× |
| 5060 Ti 9B copy 64k | 8.26 vs 4.53 | 47.2 vs 35.2 | 174.8 vs 128.6 | 1.82× | 0.75× |

(suma żądań; mediany rund w [[2026-10-16-magnitude-vs-fork]] różnią się o ≤ 1 t/s).

- pad.cu: 7.88 vs 4.92 tok/krok, 50.2 vs 46.5 ms, 157.0 vs 105.7 t/s; obie strony na suficie (Mag 894/897, my 816/828).
- lazy.py (prompt 3148 > okno DFlash2 2048): Mag 5.63 tok/krok, tylko 1.05× nad nami.
- Krok przy 64k: u nich +41 ms względem 2k, u nas +18 ms.
- Sweep 27B T=1: pl-kod 109.2 vs 79.3, en-code 86.5 vs 71.2, pl-proza 30.1 vs 44.9 t/s; propozycji/krok od 1.81 (pl-proza) do 6.75 (pl-kod), na 9B pl-proza 0.23.

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[lekcja-sufit-bloku]]
- [[kontroler-szerokosci-draftu]]
- [[raport-16i-magnitude]]
