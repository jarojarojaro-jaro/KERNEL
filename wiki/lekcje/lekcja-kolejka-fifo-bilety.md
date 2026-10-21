---
typ: lekcja
tags: [lekcje, kolejka, gpu]
aktualizacja: 2026-10-21
zrodlo: git 5570c04; git 23df077
status: aktualne
---
# Kolejka GPU: niesprawiedliwy flock głodził runner → bilety FIFO

**`flock` nie jest sprawiedliwy: krótkie zadania `cpuheavy --quiet` ciągle przechwytywały quiet.lock i runner kolejki GPU czekał; od 2026-10-21 bilety FIFO + `/tmp/gpu-wanted`.**

- 5570c04: kolejka FIFO po biletach + `cancel.sh`.
- 23df077: runner na czele kolejki ustawia `/tmp/gpu-wanted`, `cpuheavy --quiet` czeka, aż runner weźmie quiet.lock.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-nie-odtwarzac-lockow]]
- [[serializacja-gpu]]
