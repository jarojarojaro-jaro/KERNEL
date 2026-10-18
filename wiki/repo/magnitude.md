---
typ: repo
tags: [repo, konkurencja, autotuning]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/product/research/15c-nowe-silniki.md:17-22,52-66,108-164,229-254,380; ~/KERNEL/product/research/16d-magnitude-vs-nasz.md:22-28,37,119-129; ~/KERNEL/product/research/16i-magnitude-co-robia-dobrze.md:16-21,111-118,308-321; ~/KERNEL/product/research/16j-magnitude-vulkan-xtx.md:9,17-32
status: aktualne
---
# Magnitude (silnik Seismic z autotunem 60 s)

**Własny silnik w Ruście z językiem kerneli „Seismic” (Metal, CUDA, Vulkan, CPU; bez HIP/ROCm), który stroi kernele 60 s przy pierwszym załadowaniu z bramką błędu α = 8 (nie bitową); najbliższy bezpośredni konkurent, ale bez AMD natywnie, bez bitowej bramki i bez MoE offload.**

Repo `magnitudedev/magnitude` @ `1f54d5b7` (2026-10-15), Apache-2.0, 6,944★ (2026-10-16), YC, ~2 osoby `[NIEZWERYFIKOWANE]`. Silnik produkcyjny od PR #130 (2026-09-27), wcześniej fork llama.cpp.
- **Autotune:** budżet `STANDARD_TUNING_BUDGET = 60 s` (`tuning/mod.rs:331`), dyskretne parametry (KSPLIT, LANES, ROWS, ROTATE, WEIGHTS_AHEAD, INT8), cel to ważony czas prefill i decode przy 4k i 64k z launchami draftera i verify.
- **Bramka:** `sqrt(Σ(c−d)²/Σ(w²/12)) ≤ α`, `STANDARD_ALPHA = 8.0` (`precision.rs:22`) – hasło „nie zmienia wyjścia” jest fałszywe w sensie bitowym; KV domyślnie K8V4 (`options.rs:121`); jakości w benchmarkach nie mierzą.
- **Benchmarki:** 2.19× / 2.17× decode vs domyślna Ollama v0.35.1 na zadaniu „powtórz fragment Moby-Dick” przy 64k (Mac M4 Pro / DGX Spark); wycofane porównanie z llama.cpp bez spekulacji: +19% decode na CUDA (Spark, Qwen3.6-35B-A3B, commit `658cb1ec`). Roofline: Qwen3.8-27B 66.7 t/s na Sparku wymaga ≥ 4.8 tok/rundę – możliwe tylko przy kopiowaniu.
- **AMD:** tylko Vulkan, niekwalifikowany, błędy iGPU/Strix Halo (#151, #154, #157). Brak offloadu MoE do RAM (#194).
- Wyprzedzają nas: integracje agentów jednym kliknięciem, desktop Mac/Win/Linux.

**Aktualizacja 2026-10-16 (16d, 16i; release 0.2.9 `954d677d`):**
- Kontroler szerokości draftu domyślnie (`options.rs:280-290`, [[kontroler-szerokosci-draftu]]) i sprzężone próbkowanie (`generation/src/lib.rs:745-779`).
- Autotune w release: 67/67 domyślnych konfiguracji; gotowość 51.5 s (Qwen) / 62.5 s (LFM), z cache 5–10 s.
- Kwanty: brak IQ2_S/IQ2_XXS/Q4_1/Q2_K (`weights.rs:2085`) → żaden 27B ≤ 16 GB; Q3_K/IQ3_S → q6k. LFM 64k OOM na 16 GB; „MemoryPressure HostRam” przy 31 GB RAM.
- AMD tylko przez Vulkan (`docs/compatibility.md:150`). Pomiary: [[2026-10-16-magnitude-vs-fork]].

Vulkan na gfx1100 (16j, 2026-10-18): działa (RADV 25.2.8, user-local ICD); pierwszy start 95.6 s (przygotowanie kerneli 70.7 s), z cache 23–26 s; autotune 67/67 i 21/21 kanoniczne defaulty, 0 pomiarów; na XTX ~2× wolniejszy od nas ([[2026-10-18-magnitude-vulkan-xtx]]).

## Powiązane
- [[repo/_hub|repo]]
- [[tqllm]]
- [[turbollm]]
- [[raport-15c-nowe-silniki]]
- [[produkt-ryzyka]]
- [[lekcja-benchmark-kopia]]
