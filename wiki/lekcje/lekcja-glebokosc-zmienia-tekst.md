---
typ: lekcja
tags: [lekcje, spekulacja, determinizm, md5]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/24q-adaptacyjna-spekulacja.md:16-21,100
status: aktualne
---
# Zmienna głębokość draftu = inny tekst greedy, dopóki weryfikacja zależy od szerokości

**Adaptacyjna głębokość MTP (24q) nie jest md5-identyczna: zmienia szerokość weryfikacji (3…7 wierszy), a numeryka weryfikacji zależy od szerokości – greedy dał `d217c1a0`/`888170e6` zamiast `6f14e814`, rozjazd na znaku 130 (2026-10-20).**

- Rozkład wyjścia się nie zmienia, ale wymóg „md5 identyczne z topką” nie jest spełniony – bramka nie przechodzi.
- To ta sama przyczyna co plain ≠ MTP n=4 ([[lekcja-spekulacja-zmienia-numeryke]]).
- Dotyczy każdej polityki zmieniającej szerokość weryfikacji per krok (głębokość, bramka ogona, stała głębokość 6).
- Bezstratność w sensie md5 dałaby tylko weryfikacja niezależna od szerokości (`batch-invariant`, `LLAMA_SPEC_BITEXACT`, raport 12), która kosztuje −2.8…−9% – więcej niż zysk kontrolera (+2.6…3.1% czat).

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-spekulacja-zmienia-numeryke]]
- [[raport-24q-adaptacyjna-spekulacja]]
- [[raport-12-bit-exact]]
- [[kontroler-szerokosci-draftu]]
