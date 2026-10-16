---
typ: lekcja
tags: [lekcje, megakernel, szacunki]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15a-monokernel.md:12-18,171-183; ~/KERNEL/qwen-opt/NOTES.md:379; ~/KERNEL/qwen-opt/research/lfm-decode-round2.md:30-31; ~/KERNEL/qwen-opt/research/lfm-decode-round4.md:51
status: do-sprawdzenia
---
# Trwały kernel: zysk to prefetch, nie granica

**Szacunek „trwały kernel MoE po PM4 ≈ 1.4%” liczył tylko granice kerneli; megakernele wygrywają nakładaniem rampy wag i małych operacji, a zmierzona bariera trwałej siatki (0.48–0.77 µs) kosztuje tyle co granica PM4 (0.46–0.86 µs).**

- Trwały kernel z barierami między fazami na XTX nie pobije PM4 – wniosek rundy 4 dla tej klasy projektów był słuszny.
- Pobić PM4 może tylko kernel *dataflow*: (a) wagi następnej operacji ładowane przed czekaniem, (b) małe operacje na wolnych CTA, (c) redundantne liczenie zamiast hand-offów. Szacunek `[SZACUNEK]` +12…+28% LFM.
- Nieusuwalne dla LFM: wagi ekspertów zależą od top-k (38 × ~5–6.5 µs ≈ 0.2–0.25 ms/token).
Reguła: przy szacowaniu fuzji i trwałych kerneli liczyć całą pulę „DRAM bezczynny” (rampa, pierwszy bajt, małe kernele), nie tylko koszt granicy. Status do sprawdzenia, dopóki mikrobench X1/X2 nie potwierdzi.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-mikrobench-klamie]]
- [[lekcja-bledny-roofline]]
- [[raport-15a-monokernel]]
- [[pm4-replay]]
