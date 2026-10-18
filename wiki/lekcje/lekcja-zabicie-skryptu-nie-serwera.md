---
typ: lekcja
tags: [lekcje, proces, gpu]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/product/research/16e-kwanty-kld.md:306
status: aktualne
---
# Zabicie skryptu nie zabija serwera

**Po zabiciu skryptu zadań osierocony `llama-server` (Saluki, `-np 20`) trzymał 18 GB na A40, przez co dwa kolejne serwery zadań (U3, B0) dostały OOM (E1, 2026-10-16).**

Reguła: skrypt uruchamiający serwer ma `trap` zabijający serwer, a ręczne przerwanie kończy się `pkill -9 -f "llama-server.*<port>"` i sprawdzeniem VRAM przed następnym startem.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-zombie-serwery]]
- [[lekcja-pkill-wlasna-powloka]]
- [[serializacja-gpu]]
