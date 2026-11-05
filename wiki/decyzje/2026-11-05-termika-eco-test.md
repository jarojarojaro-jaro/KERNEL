---
typ: decyzja
tags: [decyzje, sprzet, termika, rx-7900-xtx]
aktualizacja: 2026-11-05
zrodlo: polecenie użytkownika 2026-11-05 (przekazane przez agenta głównego); ~/KERNEL/product/research/63-WATKI.md:50; ~/KERNEL/product/research/63-SYNTEZA.md:72,105
status: aktualne
---
# 2026-11-05: test termiczny „eco” z capem taktowania rdzenia

**Użytkownik zatwierdził (2026-11-05) testy z ograniczonym taktowaniem rdzenia GPU: pamięć bez zmian, bez undervoltu; wyniki opisane jako „eco”, osobno od rekordów stock. Zmienia to [[2026-10-20-karta-fabrycznie]] tylko w tym zakresie.**

- Zakres: cap zegara rdzenia (zapis wymaga roota); taktowanie pamięci, napięcia i reszta ustawień fabrycznych bez zmian.
- Wyniki: t/s, moc i temperatury w osobnej kolumnie „eco”; [[REKORDY]] dalej tylko na ustawieniach fabrycznych.
- Bramka H7 fabryki (hash OD_SCLK i reszty) musi rozróżniać przebiegi eco od stock, inaczej odmówi pomiaru `[INFERENCE]`.
- Wątek #44 rejestru 63 (0xwhitemage, NullBurn, Blackfold); same źródła nie były badane w 63. Plan: pozycja #26 w [synteza 63](../../product/research/63-SYNTEZA.md).

## Powiązane
- [[decyzje/_hub|decyzje]]
- [[2026-10-20-karta-fabrycznie]]
- [[2026-10-09-limit-mocy-odlozony]]
- [[amdgpu-moc-i-termika]]
- [[rx-7900-xtx]]
