---
typ: lekcja
tags: [lekcje, cache, agent, serwer]
aktualizacja: 2026-11-05
zrodlo: ~/KERNEL/product/research/63b-colibri-maya-delta.md:23-26,47-81,306-307; ~/KERNEL/qwen-opt/run-llm.sh:109
status: aktualne
---
# `--cache-ram 16384` za mały: 74% prefillu agenta to ponowne czytanie

**Analiza 704 żądań z `~/qwen-opt/logs/server-*.log` (2026-11-05): z 4753 s prefillu 3536 s (74%) to 38 tur, w których prompt ≥ 20k był czytany od zera lub od ≤ 8k; najgorsze tury trwały 150–200 s.**

- Przyczyna: wpis cache Qwena przy 75–120k waży 7–14 GB (zmierzone 14.2 GB przy 118k wobec ~5 GB z rachunku KV + checkpointów), a limit to 16 384 MiB. Mieści się jeden długi wątek; drugi (subagent, druga sesja omp) go wyrzuca („removing oldest entry (size = 9554 MiB)”, 22 z 38 przypadków).
- Lekcja: przy pracy agentowej czas czekania to nie decode ani kernele, tylko pojemność i kształt prompt cache. Mierzyliśmy „ile tokenów przeliczono”, nie „dlaczego”.
- Poprawka bezstratna: `--cache-ram 40960` (RAM 62 GB) + chude checkpointy ([[wspolny-poczatek-promptu]]); oczekiwane tury 85–200 s → ~4–8 s `[SZACUNEK]`. Wymaga zgody na restart serwera :8080.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[run-llm-sh]]
- [[2026-10-18-cache-promptu-agenta]]
- [[ksztalt-ruchu-agentowego]]
- [[colibri]]
