---
typ: lekcja
tags: [lekcje, hip, rdna3, maya, dokladnosc, k206]
aktualizacja: 2026-11-28
zrodlo: ~/k134/k203/test.log (K-206, 2026-11-27); Maya wt-k203 e03e1d4a
status: aktualne
---
# Lekcja: bitowa zgodność kerneli wymaga wyłączenia kontrakcji FMA

**Ten sam helper inline sumował o kilka ulp inaczej w trzech kernelach (bloki, planar T=1, planar T=4), bo clang na gfx1100 różnie łączy `a*b + c` w FMA zależnie od otoczenia; pomogło `#pragma clang fp contract(off)` w wspólnych helperach i jawne `fmaf`.**

- Co: K-206 przepakował macierze Mai do układu planarnego; test „planar = bloki bitowo” padł w wierszach Q8_0 (−894,280396 vs −894,280518), a planar T=1 i T=3 różniły się też między sobą.
- Dlaczego: kontrakcja FMA jest decyzją kompilatora per miejsce wstawienia; ta sama kolejność źródłowa nie gwarantuje tych samych bitów. Podobnie wcześniej: `f2h(a*b)` zamieniało −0 na +0 (Q2_0, K-203).
- Reguła: każda ścieżka, która ma się zgadzać bitowo z inną (okno weryfikacji vs dekod, nowy kernel vs stary), dostaje wspólne helpery z `contract(off)` i jawnymi `fmaf`; test bitowy porównuje też instancje między sobą (T=1 vs T>1).

## Na później
- Ten sam wzorzec dla kerneli AD (Q4_K/Q5_0) przy następnej przebudowie.

## Test u nas
K-206 (zrobione: test bitowy przechodzi, wall 1M +54%).
