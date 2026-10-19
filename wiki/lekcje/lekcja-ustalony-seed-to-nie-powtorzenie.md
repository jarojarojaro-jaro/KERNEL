---
typ: lekcja
tags: [lekcje, pomiar, spekulacja]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/16k-sprzezone-probkowanie.md:112-115
status: aktualne
---
# Ustalony seed to nie powtórzenie: ABBA nie redukuje szumu tekstu

**Przy ustalonym seedzie każde powtórzenie bloku generuje ten sam tekst (rozrzut bloków ±0.1–0.5 t/s), więc ABBA nie zmniejsza szumu tekstu; sama zmiana strumienia RNG (tryb kontrolny 2 vs 0, ten sam drafter) dała +7.8% t/s i +3.6% tok/krok na 18 tekstach (E-X4, run 3, 2026-10-18).**

Reguła: efekt rzędu 2% przy T>0 wymaga ≥ 20 seedów (różnych tekstów), a nie powtórzeń bloku, oraz ramienia kontrolnego o tym samym rozkładzie tekstów; porównanie off vs on miesza zmianę RNG ze zmianą mechanizmu.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-5-seedow]]
- [[lekcja-szum-t-s-przy-t1]]
- [[2026-10-18-sprzezone-probkowanie-mtp]]
