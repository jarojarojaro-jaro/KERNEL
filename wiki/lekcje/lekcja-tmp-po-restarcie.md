---
typ: lekcja
tags: [lekcje, dane, proces]
aktualizacja: 2026-10-18
zrodlo: komunikat Main do WikiIngest 2026-10-18; komunikat Main do WikiIngest 2026-10-18 (drugi); ls ~/qwen-opt/tmp-archive-20261018 (2026-10-18); ~/.omp/agent/sessions/-tmp/2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8/LandingWow.jsonl:1224
status: aktualne
---
# `/tmp` znika przy restarcie: wyniki trzymać poza nim

**Restarty serwera 2026-10-18 czyszczą `/tmp`: `/tmp/bxv/summary.txt` i `/tmp/bxd/*` (walidacja bit-exact) zniknęły już przy wcześniejszym restarcie ~18:53 UTC, przed archiwizacją; przed restartem ~20:27 UTC (overdrive) resztę zarchiwizowano do `~/qwen-opt/tmp-archive-20261018/` (63 MB: coupled, lookup, pm4pdl, lfmmoe, qa).**

Skutek: surowe wyniki run 3 (np. bitexact MTP 107.0 vs prod 107.5 t/s, cytowane przez landing) są nie do sprawdzenia; kanonicznym źródłem jest raport 12 §13 run 4 (108.3 vs 107.7/107.6 t/s), na który landing przepina `BITEXACT_XTX` ([[2026-10-16-bit-exact]]).

Reguła: wyniki pomiarów od razu do `~/qwen-opt/...` albo `results/`, nigdy tylko do `/tmp`; przed planowanym restartem archiwizacja całego `/tmp` z listą katalogów sprawdzoną względem `zrodlo` notatek.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-unikalny-katalog-wynikow]]
- [[lekcja-uslugi-poza-omp]]
- [[lekcja-wentylator-rdna3]]
