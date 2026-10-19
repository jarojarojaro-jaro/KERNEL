---
typ: metoda
tags: [metody, pomiar, fabryka]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21b-gpu-perf-zasoby.md:230-249; ~/KERNEL/wiki/metody/wyniki-negatywne.md:17
status: aktualne
---
# Physics-floor check: czas kernela ≥ bajty / pasmo

**Każdy zmierzony czas kernela porównać z fizyczną podłogą (bajty do przeczytania / szczytowe pasmo); wynik szybszy niż podłoga to błąd pomiaru, nie rekord – u nas tak wyszedł raport „1075 GB/s, 112% peaku”, który przy MTP był ~400 GB/s (propozycja raportu 21b #8, wzorem KernelGuard i SOL-ExecBench, 2026-10-19).**

Wdrożenie: reguła w weryfikatorze fabryki (obok R12 roofline na tekście, [[2026-10-16-backtest-regul-fabryki]]) – twierdzenie z metryką czasu kernela musi podać bajty, a G5 odrzuca czasy poniżej bajty/pasmo; ~0.5 dnia.

## Powiązane
- [[metody/_hub|Metody]]
- [[lekcja-bledny-roofline]]
- [[fabryka-cli]]
- [[sufit-pasma-i-mapa-czasu]]
