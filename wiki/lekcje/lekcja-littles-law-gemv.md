---
typ: lekcja
tags: [lekcje, pasmo, kernele]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21b-gpu-perf-zasoby.md:82-84; ~/KERNEL/product/research/16g-lfm-moe-pasmo.md:35-41
status: aktualne
---
# Little's law dla GEMV: liczy się liczba ładowań w locie

**Bajty w locie = pasmo × latencja: przy ~600 ns latencji DRAM `[ZAŁOŻENIE]` XTX potrzebuje ~6.0 KB w locie na CU, 3090 6.8 KB/SM, 4090 4.7, 5060 Ti 7.5, 5090 6.3 – czyli ~10–16 ładowań 16 B na falę/warp; to samo pokazał ATT na XTX (gate+up LFM 85% czasu w `s_waitcnt vmcnt`) (raport 21b, 2026-10-19).**

Reguła: w kernelu pasmowym przy batch 1 zwiększać liczbę niezależnych ładowań w locie (prefetch do rejestrów, więcej wierszy na falę przy kontroli VGPR), a nie zamieniać instrukcji ładowania (TMA niepotrzebne – cp.async już ~92% pasma na 5060 Ti).

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-sufit-wzorca]]
- [[att-gfx1100]]
- [[karty-nvidia-parametry]]
