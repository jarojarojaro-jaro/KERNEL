---
typ: lekcja
tags: [lekcje, agenci, weryfikacja]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21i-rsi-inference-bench.md:20-25,182-230
status: aktualne
---
# Reguła zapisana tylko w prompcie nie istnieje

**W RSI-Inference Bench wszystkie 20 instrukcji optymalizacji obiecują „ukryte workloady” i zero punktów za same zmiany flag, a w 20/20 zadań `environment/public/workloads.json` jest bajt w bajt równe `tests/workloads.json` i `NARROW_REJECTED_KINDS = set()`; serwerowy web search API omijał też `network_mode: none` (raport 21i, 2026-10-19).**

Reguła: każde „nie wolno X” w prompcie agenta ma odpowiadającą regułę w kodzie weryfikatora (z fixture'em z prawdziwego incydentu) albo znika z promptu; izolacja (sieć, historia gita, dostęp do danych testowych) wymuszana systemem, nie instrukcją.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-verified-to-nie-poprawny]]
- [[lekcja-agent-zmienia-protokol]]
- [[zmiany-fabryki-z-21i]]
