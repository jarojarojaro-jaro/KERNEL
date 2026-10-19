---
typ: lekcja
tags: [lekcje, pomiar, spekulacja]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/product/research/16f-xtx-szybkie.md:96-115; ~/wt/quickwins/qw/spec_sweep.jsonl (e2s5-*)
status: aktualne
---
# spec_sweep z 2 seedami potrafi odwrócić znak efektu

**Typ bloku MTP Q6_K „wygrywał” z IQ4_XS przy 2 seedach (108.7 vs 106.5 t/s, bo pl-kod 3.67 vs 3.25 tok/krok), a przy 5 seedach przegrał (109.4 vs 113.2 t/s, 3.012 vs 3.063 tok/krok) (E2 z 16f, 2026-10-18).**

Przy T=1 rozrzut per prompt przy 2 seedach jest większy niż efekt ±3%. Reguła: decyzje o typach kwantów i drobnych zmianach spekulacji – co najmniej 5 seedów, ABBA, porównanie tok/krok i ms/krok osobno.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-szum-t-s-przy-t1]]
- [[lekcja-jeden-prompt]]
- [[latki-spekulacji]]
