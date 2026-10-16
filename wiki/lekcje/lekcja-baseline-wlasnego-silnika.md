---
typ: lekcja
tags: [lekcje, pomiar, konkurencja]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15d-prefill-dlugi-kontekst.md:13,54-56
status: aktualne
---
# „Nx szybciej” bywa liczone względem własnego albo zimnego silnika

**Posty Lucebox podają przyspieszenia względem własnego silnika albo zimnego llama.cpp: KVFlash ma pełny prefill 32K 47.2 s (694 t/s) wobec 1168 t/s llama.cpp na tej samej 3090, a PFlash v1 porównywał się do „~257 s” na zimno zamiast 169.3 s na ciepło.**

- PFlash v1: „24.8 s vs ~257 s llama.cpp = ~10.4× at 128K” – względem ciepłego baseline'u to ×6.8.
- KVFlash: „prefill 2.8× at 256K (355 vs 999 s)” względem ich silnika, wolniejszego od llama.cpp.
Reguła: przy każdym cudzym „Nx” sprawdzić, czym jest baseline (który silnik, zimny czy ciepły, jakie flagi) i porównywać z dobrze ustawionym upstreamem na tej samej karcie (`optimizations/kvflash/RESULTS.md`, blog PFlash v1).

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-jeden-prompt]]
- [[lekcja-benchmark-kopia]]
- [[lucebox]]
- [[raport-15d-prefill-dlugi-kontekst]]
