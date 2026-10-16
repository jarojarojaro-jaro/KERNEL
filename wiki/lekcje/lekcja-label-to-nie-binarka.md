---
typ: lekcja
tags: [lekcje, pomiar, proces]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15f-agentowa-nauka.md:178-182; ~/llama-master/tools/server/server-context.cpp:5171; ~/KERNEL/product/research/16h-fabryka-v1.md:46-47
status: aktualne
---
# Label w pomiarach nie jest tożsamością binarki

**Label „base” w `spec_sweep.jsonl` wskazywał na nadpisywany katalog `~/llama-opt`, więc ta sama nazwa dawała 29.77, 29.36, 29.12 i 29.16 ms/krok w różnych sesjach i nie da się oddzielić dryfu sprzętu od zmian kodu.**

Pary z tym samym labelem w jednej sesji różnią się o 0.09% (mediana), więc rozrzut 29.12–29.81 ms między sesjami to inne binarki albo inny stan karty, a nie szum.
Reguła: w każdym wierszu pomiaru zapisywać sha256 bibliotek `libggml-*.so` i `build_info` z `/props` (llama-server je zwraca), a baseline mierzyć w tej samej sesji, nie z historii.

Backtest R20 (2026-10-16): w `spec_sweep.jsonl` 7 labeli z rozrzutem ms/krok > 1%, np. `DRAFT_N=4 qwen mtp rocm` 28.94–41.74; w `fusion/spec_sweep.jsonl` `r1-base-qwen` 33.15–41.81 ([[2026-10-16-backtest-regul-fabryki]]).

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-dowod-poza-commitem]]
- [[lekcja-commity-bez-pomiaru]]
- [[spec-sweep]]
- [[raport-15f-agentowa-nauka]]
