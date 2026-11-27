---
typ: lekcja
tags: [lekcje, kontekst, maya, inkling, produkcja]
aktualizacja: 2026-11-27
zrodlo: panel JARO 2026-11-27 21:40; ~/k134/maya-atomic.json (`--max-context 16384`); obliczenie K-202 (agent X202)
status: aktualne
---
# Lekcja: Maya stała w produkcji i testach na 16k kontekstu, choć mieści ok. 488k

**Od wdrożenia Mai (21.11) `maya-atomic.json` miał `--max-context 16384` i nikt tego nie sprawdził: wszystkie wall Inklinga, K-158/K-185/K-200 i czat JARO szły z 16k, a silnik z drafterem mieści ok. 488k (KV q4 9 KB/token + uwaga draftera 4,9 KB/token), bez draftera ok. 848k.**

- Przyczyna: konfigurację przejąłem z przykładu Mai i patrzyłem tylko na prędkość; przy Qwenie pełny kontekst (262k) był sprawdzony, przy nowym silniku tego kroku nie było na liście.
- Reguła: [[2026-11-27-zawsze-pelny-kontekst]] — każda topka dostaje pomiar maksimum przed wdrożeniem, a `stos/topki` podaje kontekst każdego modelu.
- Wpływ na wyniki: prędkość dekodu przy krótkich promptach od wielkości bufora praktycznie nie zależy (uwaga liczy tylko zajęte pozycje), ale wszystkie testy długiego kontekstu Mai (K-189/K-194/K-196/K-200) ustawiały kontekst ręcznie, więc są ważne; czat JARO po prostu obcinał rozmowy powyżej 16k.

## Powiązane
- [[topki]]
