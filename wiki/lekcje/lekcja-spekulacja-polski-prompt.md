---
typ: lekcja
tags: [lekcje, spekulacja, pomiar, inkling]
aktualizacja: 2026-11-25
zrodlo: ~/qwen-opt/queue/logs/k158w-fpol2.log (jaroserverai)
status: aktualne
---
# Spekulację sprawdzamy na polskim prompcie, zanim wejdzie do produkcji

**Maya K-158c (DSpark przy T=0, okno wg pewności) dała w rep2 +47% (Q1 191,1 vs 129,9 t/s), a w wall.py na polskim prompcie −39% (68,8 vs 113,5 t/s); rep2 nie ma polskiego promptu, więc tego nie widział (2026-11-25).**

- Mechanizm: drafter (DSpark, trenowany głównie na angielskim i kodzie) na polskim tekście trafia rzadko, a tryb okna wg pewności nie wraca do zwykłego dekodu, więc każda runda kosztuje propose + weryfikacja (ok. 3,6 + 13,5 ms) za ok. 1 token.
- Średnia z promptów kodu i JSON (+44…65%) przykryłaby stratę na języku, którym mówią nasi użytkownicy.

Reguła: zmiana spekulacji (drafter, szerokość okna, polityka) przed wdrożeniem przechodzi wall.py z promptem `pl` (`qwen-opt/nib/wall.py`) i wynik każdej kategorii osobno; strata na `pl` powyżej 2% blokuje wdrożenie, nawet gdy mediana rośnie. Tryb spekulacji bez bramki adaptacyjnej (powrót do zwykłego dekodu przy niskiej akceptacji) nie wchodzi do produkcji.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[nib-chromadera]]
- [[lekcja-final-speed-to-najszybszy-znany]]
