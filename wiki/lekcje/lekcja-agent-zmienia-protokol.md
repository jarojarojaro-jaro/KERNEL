---
typ: lekcja
tags: [lekcje, agenci, bramki]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15f-agentowa-nauka.md:25-27,74,313-321
status: aktualne
---
# Agent potrafi „poprawić” wynik zmianą protokołu ewaluacji

**W papierze Sakana (arXiv 2610.18933 §6.3) w 2 z 3 przebiegów agent zmienił protokół ewaluacji (majority vote zamiast pass@1), a ani ewaluator, ani rubryki tego nie złapały – wykrył to dopiero ręczny audyt.**

Odpowiednik u nas: agent „przyspiesza” zmianą `max_tokens`, `cache_prompt`, flag serwera, promptów albo `-ub`/`-c` w `spec_sweep`.
Obrona strukturalna, nie rubryka: harness poza zasięgiem Implementera (zmiana tylko osobnym commitem z akceptacją), denylist ścieżek pomiaru w diffie (`spec_sweep*`, `factory/`, `tools/`, `cloud/bench.sh`), flagi serwera z pliku profilu, stała liczba tokenów w każdym wierszu, md5 liczone z tych samych przebiegów co czas.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-dowod-poza-commitem]]
- [[lekcja-mikrobench-klamie]]
- [[sakana-agentic-scientist]]
- [[fabryka-v1]]
