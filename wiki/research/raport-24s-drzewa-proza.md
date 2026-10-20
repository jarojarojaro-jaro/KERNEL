---
typ: research
tags: [research, spekulacja, drzewa, wynik-negatywny]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/24s-proza-drzewa.md:8-21,58-63,82-85,109
status: aktualne
---
# Raport 24s: drzewa draftu MTP i temperatura draftu na prozie – sufit offline

**Drzewo statyczne daje najwyżej +1.2% netto, dynamiczne +3.9% (5 wierszy) / +4.7% (6 wierszy) – poniżej progu +6%; próg wymaga kosztu wiersza ≤ 0.57 ms (dziś 0.85 ms); DT draftu zostaje 1.0 (2026-10-20, tylko CPU).**

- Lustro MTP na CPU, 17 692 starty prozy, T=1 (`24s:28-31`).
- W 44% pierwszych odrzuceń tokenu celu nie ma w top-6 MTP – proza jest płaska (`24s:98`).
- DT 0.7 / 1.3 / 1.6: +0.26% / −0.6% / −1.5% tok/krok (`24s:17-20`).
- Sprzężenie + drzewo statyczne: +0.3% (`24s:21`).
- Warunek powrotu: V8 − V5 ≤ 1.7 ms; wtedy dynamiczne drzewo o stałych 5 wierszach (`24s:109-110`). Metoda: [[koszt-szerokosci-weryfikacji]].

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[raport-24p-sprzezone-t1]]
- [[koszt-szerokosci-weryfikacji]]
- [[lekcja-wyrazna-wygrana-albo-nic]]
