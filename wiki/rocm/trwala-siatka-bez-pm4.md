---
typ: rocm
tags: [rocm, pm4, megakernel, lfm]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21b-gpu-perf-zasoby.md:215-228,297-303; ~/KERNEL/qwen-opt/research/lfm-decode-round4.md:30-50
status: do-sprawdzenia
---
# XTX bez PM4: trwała siatka wraca do gry (warunkowo)

**Bez PM4 granica między kernelami kosztuje 2.75 µs w HIP graph, a podłoga pakietu AQL to 2.08 µs nawet bez fence'ów, podczas gdy bariera trwałej siatki to 0.48–0.77 µs; jeśli PM4 nie da się zabezpieczyć, trwały blok MoE na warstwę LFM jest jedyną bezstratną drogą do odzyskania części −12% (szacunek +8–10% względem PM4-off) (raport 21b, 2026-10-19).**

LFM: 305 granic × (2.75 − ~0.6) µs ≈ 0.66 ms górnej granicy; zmierzona strata po wyłączeniu PM4 3.40 → 3.86 ms (293.7 → 259.3 t/s). Trwały blok (norm+router+top-k → gate+up → down) usuwa ~170 granic → ~0.3–0.36 ms. Ryzyko: co-residency z wyświetlaczem i zawieszenia – potrzebne bounded spin + słowo błędu i dynamiczny indeks zadań; fault w zwykłej kolejce AQL zabija tylko proces ([[lekcja-pm4-zamienia-fault-w-reset]]). Decyzja zależy od Pm4Fix: przy 0 faultów z guardem pozycja spada na koniec listy.

## Powiązane
- [[rocm/_hub|ROCm]]
- [[pm4-replay]]
- [[hip-graph-narzut]]
- [[raport-15a-monokernel]]
