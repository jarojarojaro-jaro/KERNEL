---
typ: lekcja
tags: [lekcje, pomiary, jaroserverai, cpu, smt]
aktualizacja: 2026-11-26
zrodlo: agent K036Impl 2026-11-26 (ślady ~/qwen-opt/k036/logs-prod vs raport 37, ~/qwen-opt/queue/logs/k036m-trace.log)
status: aktualne
---
# Lekcja: build na `taskset -c 6-15` dzieli fizyczne rdzenie z serwerem testowym na 2–5

**Co się stało:** ślad przerw hosta K-036 (2026-11-26 11:32) pokazał 2,9–5,8% bezczynności GPU na krok i werdykt „opłaca się”. Równolegle szedł build k183e na `taskset -c 6-15`. Na jaroserverai (8 rdzeni / 16 wątków) CPU 10–13 to drugie wątki SMT rdzeni 2–5, na których stał serwer testowy, więc praca hosta szła 2–3× wolniej (sprawdzenie strażnika taśmy 4,96 → 10,9 µs, `inputs → gc.in` 26,6 → 57,7 µs). Do tego parser brał średnią za medianę. Powtórka z trzymaną blokadą `/tmp/kbuild.lock` i medianą: 1,82–1,85%, żaden kawałek ≥ 0,5 ms, K-036 zamknięty.

**Reguła:** pomiary zależne od hosta (ślady przerw, ms/krok, wall z krótkimi krokami) trzymają `/tmp/kbuild.lock` na czas pomiaru albo sprawdzają, że nie działa żaden kompilator; raport podaje medianę, nie średnią. Wyniki wall z dnia, gdy równolegle szły buildy, mają szum hosta (rzędu 1–3% przy krótkich krokach); bramki ABBA go częściowo znoszą, ale progi ±2% wymagają cichego CPU.

## Powiązane
- [[szybsze-testowanie-2026-11-26]]
