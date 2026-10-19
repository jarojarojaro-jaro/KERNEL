---
typ: lekcja
tags: [lekcje, pm4, testy]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/17-gpu-page-fault.md:248,333-376,393-398
status: aktualne
---
# Soak nie testuje wywłaszczenia: wymuszać ewikcje deterministycznie

**Soak PM4 po 4 min na model przeszedł bez awarii (14.10), a resety przyszły dopiero w godzinnych seriach, gdy po zapełnieniu pamięci jądro migrowało strony i ewikowało kolejki (raport 17 §9, 2026-10-19).**

Reguła: odporność na wywłaszczenie testować wstrzykniętą ewikcją – `madvise(MADV_DONTNEED)` na zakresie z `hsa_amd_memory_lock` (prototyp `GGML_HIP_PM4_EVICT_TEST_MS=<n>`, `b7fb3fe85`) – z liczbą ewikcji „w trakcie taśmy” ≥ 1000 przed dopuszczeniem do produkcji.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-wlasny-pm4-musi-robic-to-co-firmware]]
- [[pm4-soak]]
- [[2026-10-19-pm4-priv-analiza]]
