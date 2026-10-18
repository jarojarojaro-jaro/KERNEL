---
typ: lekcja
tags: [lekcje, dane, proces]
aktualizacja: 2026-10-18
zrodlo: komunikat Main do WikiIngest 2026-10-18; ls ~/qwen-opt/tmp-archive-20261018 (2026-10-18); ~/.omp/agent/sessions/-tmp/2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8/LandingWow.jsonl:1224
status: aktualne
---
# `/tmp` znika przy restarcie: wyniki trzymać poza nim

**Restart serwera 2026-10-18 (~20:27 UTC, włączenie overdrive) wyczyścił `/tmp`; część wyników zarchiwizowano wcześniej do `~/qwen-opt/tmp-archive-20261018/` (63 MB: skrypty i logi coupled, lookup, pm4pdl, lfmmoe, qa), ale `/tmp/bxv/summary.txt` i `/tmp/bxd/*` (walidacja bit-exact) w archiwum nie ma.**

Skutek: liczby z `summary.txt` (np. bitexact MTP 107.0 vs prod 107.5 t/s, cytowane przez landing) przetrwały tylko w wiki ([[2026-10-16-bit-exact]], przepisane 2026-10-16) i w raporcie 12; surowego pliku nie da się już sprawdzić.

Reguła: wyniki pomiarów od razu do `~/qwen-opt/...` albo `results/`, nigdy tylko do `/tmp`; przed planowanym restartem archiwizacja całego `/tmp` z listą katalogów sprawdzoną względem `zrodlo` notatek.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-unikalny-katalog-wynikow]]
- [[lekcja-uslugi-poza-omp]]
- [[lekcja-wentylator-rdna3]]
