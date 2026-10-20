---
typ: decyzja
tags: [decyzje, proces, produkcja]
aktualizacja: 2026-10-20
zrodlo: polecenie użytkownika 2026-10-20 23:3x (czat z Main)
status: aktualne
---
# 2026-10-20: co jest lepsze, wdrażamy bez pytania; agenci mają być wydajni

**Użytkownik (2026-10-20): „jak coś ma być lepiej, to dajemy, jak nie to nie — proste; działaj; subagenci mają być efficient”. Rozszerza [[2026-10-19-najlepiej-bez-pytania]] także na domyślne ustawienia topki (produkcji): poprawka, która przeszła bramki (md5/KLD, brak regresji, bezpieczeństwo sprzętu), trafia od razu do `run-topka.sh` i `~/llama-topka` (z kopią zapasową), bez pytania. Dotyczy też poprawek bezpieczeństwa (SAFE_SPECIAL, SAFE_TOOLS) i bitowo zgodnej tokenizacji równoległej.**

Wydajność agentów:
- jedno zadanie = jeden cel, limit czasu w briefie (zwykle ≤ 60–90 min), raport krótki;
- najpierw najtańszy test rozstrzygający; bez długich przebiegów „na zapas”;
- GPU tylko przez kolejkę, jedna sprawa naraz, ≤ 10 min na pomysł.

Nadal pytamy tylko o: celowe testy z ryzykiem resetu GPU, wydatki ponad budżet, usuwanie danych użytkownika.

## Powiązane
- [[decyzje/_hub|Decyzje]]
- [[2026-10-19-najlepiej-bez-pytania]]
- [[2026-10-20-szybkie-iteracje]]
