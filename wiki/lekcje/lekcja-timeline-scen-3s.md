---
typ: lekcja
tags: [lekcje, landing, animacja]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/app/design/REDESIGN.md:165,167-168; komunikat Main do WikiIngest 2026-10-18 (LandingWow „Do bazy wiedzy”, rundy 9–12)
status: aktualne
---
# Timeline sceny ≤ 3 s, inaczej widać liczby w trakcie przewijania

**Na landingu scena „boost” wciąż przewijała licznik 3.3 s po wejściu w widok (timeline 5 s), a juror rundy 9 złapał licznik w połowie animacji; po skróceniu scan/boost do 2.6/2.8 s i dosuwaniu do wartości końcowej problem zniknął (rundy 9–12, 2026-10-18).**

Reguła: animacje liczników i scen ≤ 3 s; wartość końcowa w HTML z SSR i natychmiastowy „snap” przy wyjściu z widoku, ukrytej karcie i bfcache – użytkownik i zrzut ekranu nigdy nie mogą zobaczyć liczby pośredniej jako wyniku.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[app-landing]]
- [[lekcja-hydration-blok-w-p]]
- [[landing-qa]]
