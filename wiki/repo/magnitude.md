---
typ: repo
tags: [repo, konkurencja, autotuning]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15c-nowe-silniki.md:17-22,52-66,108-164,229-254,380
status: do-sprawdzenia
---
# Magnitude (silnik Seismic z autotunem 60 s)

**Własny silnik w Ruście z językiem kerneli „Seismic” (Metal, CUDA, Vulkan, CPU; bez HIP/ROCm), który stroi kernele 60 s przy pierwszym załadowaniu z bramką błędu α = 8 (nie bitową); najbliższy bezpośredni konkurent, ale bez AMD natywnie, bez bitowej bramki i bez MoE offload.**

Repo `magnitudedev/magnitude` @ `1f54d5b7` (2026-10-15), Apache-2.0, 6,944★ (2026-10-16), YC, ~2 osoby `[NIEZWERYFIKOWANE]`. Silnik produkcyjny od PR #130 (2026-09-27), wcześniej fork llama.cpp.
- **Autotune:** budżet `STANDARD_TUNING_BUDGET = 60 s` (`tuning/mod.rs:331`), dyskretne parametry (KSPLIT, LANES, ROWS, ROTATE, WEIGHTS_AHEAD, INT8), cel to ważony czas prefill i decode przy 4k i 64k z launchami draftera i verify.
- **Bramka:** `sqrt(Σ(c−d)²/Σ(w²/12)) ≤ α`, `STANDARD_ALPHA = 8.0` (`precision.rs:22`) – hasło „nie zmienia wyjścia” jest fałszywe w sensie bitowym; KV domyślnie K8V4 (`options.rs:121`); jakości w benchmarkach nie mierzą.
- **Benchmarki:** 2.19× / 2.17× decode vs domyślna Ollama v0.35.1 na zadaniu „powtórz fragment Moby-Dick” przy 64k (Mac M4 Pro / DGX Spark); wycofane porównanie z llama.cpp bez spekulacji: +19% decode na CUDA (Spark, Qwen3.6-35B-A3B, commit `658cb1ec`). Roofline: Qwen3.8-27B 66.7 t/s na Sparku wymaga ≥ 4.8 tok/rundę – możliwe tylko przy kopiowaniu.
- **AMD:** tylko Vulkan, niekwalifikowany, błędy iGPU/Strix Halo (#151, #154, #157). Brak offloadu MoE do RAM (#194).
- Wyprzedzają nas: integracje agentów jednym kliknięciem, desktop Mac/Win/Linux.

## Powiązane
- [[repo/_hub|repo]]
- [[tqllm]]
- [[turbollm]]
- [[raport-15c-nowe-silniki]]
- [[produkt-ryzyka]]
- [[lekcja-benchmark-kopia]]
