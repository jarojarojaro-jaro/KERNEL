---
typ: ekosystem
tags: [ekosystem, konkurencja, autotuning]
aktualizacja: 2026-11-25
zrodlo: ~/KERNEL/product/research/15c-nowe-silniki.md:17-22,52-66,108-164,229-254,380; ~/KERNEL/product/research/16d-magnitude-vs-nasz.md:22-28,37,119-129; ~/KERNEL/product/research/16i-magnitude-co-robia-dobrze.md:16-21,111-118,308-321; ~/KERNEL/product/research/16j-magnitude-vulkan-xtx.md:9,17-32; ~/KERNEL/product/research/16d-magnitude-vs-nasz.md:5-28,119-138; ~/KERNEL/product/research/16i-magnitude-co-robia-dobrze.md:11-40,308-321; ~/KERNEL/product/research/16j-magnitude-vulkan-xtx.md:10-13,85-91
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

## Ze scalonej notatki: Magnitude (magnitudedev): najbliższy konkurent

Zespół z własnym silnikiem w Ruście; wygrywa z nami tam, gdzie kopiuje (code-edit 1.35–1.56×) dzięki drafterowi DFlash2 i adaptacyjnej szerokości draftu, a przegrywa na polskim, bez draftera, w prefillu i na 16 GB (pomiary 2026-10-16).

Mocne strony: code-edit 156.1 vs 105.2 t/s (3090 27B), kod przy T=1 +21…+38%, kontroler szerokości bez strojenia przez użytkownika, sprzężone próbkowanie, Mac/Metal i Vulkan, desktop i integracje agentów.

Słabe: polski (9B sweep 68.2 vs 121.0 t/s; drafter trenowany bez PL), bez draftera na poziomie upstreamu (LFM 209.0 vs 291.6), prefill 64k 86.4 vs 72.4 s, brak IQ2_S/Q4_1 (żaden 27B na 16 GB), LFM 64k OOM na 16 GB, brak HIP (AMD tylko Vulkan), autotune w release 67/67 domyślnych.

Decyzja użytkownika: badać ich podejście i przejąć, co się da ([[2026-10-16-badamy-magnitude]]).

Na AMD (16j, 2026-10-18): przez Vulkan na 7900 XTX ~2× wolniejszy od nas (Qwen sweep 50.1 vs 100.0, code-edit 87.7 vs 170.0 t/s; LFM ×1.42–×2.24), bo każdy szerszy krok jest drogi (blok 8 = ×3.0 kroku 1-wierszowego). Konkurent w instalacji, nie w wydajności ([[2026-10-18-magnitude-vulkan-xtx]]).

## Zwiad 2026-11-24
**Aktualizacja 2026-11-24 (0.3.0-alpha.0..2, `155e1b67`):** główna nowość to strumień ekspertów MoE przez VRAM, RAM i SSD z dokładnym routingiem: brakujący ekspert jest doładowywany, nie podmieniany (`experts/watcher/mod.rs:1-60`). Bank ekspertów zmienia rozmiar w trakcie pracy według zmierzonych czasów, kosztem miejsca na KV i prefill. Rekomendacja modelu ocenia prędkość **przy 50 000 tokenów** kontekstu (`candidates.rs:5163-5174`), z celem 10 t/s (wcześniej 20) i kontekstem roboczym 64K. Enigma ocenia prędkość z tg128, więc dla agentów ją zawyża. Pamięć liczą z cgroup procesu: min(`memory.max`, `memory.high`) i rezerwa OOM `min(limit/12, 2–4 GiB)` (`limits.rs:176-260`). `/health` zwraca stałe „ok” (`lib.rs:648-660`), więc nie jest wzorem nadzoru. Błąd z wydania: podniesienie VERIFY_ROWS z 8 do 16 zostawiło w kernelach Vulkan MoE niezainicjowane wiersze 8–15 (`59060928`), co uczy, że szerszą weryfikację trzeba testować przy nowym maksimum.

## Delta 2026-11-25 (cli 0.3.0 → 0.3.3)
- 0.3.0: strumień ekspertów MoE przez VRAM, RAM i SSD wydany jako stabilny. Kolejność ekspertów według ponownego użycia, prefetch według nadchodzących tokenów, bezpośrednie odczyty NVMe z pominięciem page cache, a prefill czyta zimnego eksperta raz na warstwę. 0.3.1–0.3.3 to poprawki: zakleszczenia, CPU w spoczynku, **awarie kerneli Vulkan na AMD RDNA3** (Windows), pamięć na Windows i iGPU.
- Wartość z tweeta: Qwen3.8 Flash Next 180B w 2 bitach na M4 Max 64 GB, 56 t/s w OpenCode przy 64k kontekstu. To liczba z filmu autora tweeta, nie z repo. Na ich stronie benchmarków nie ma AMD.
- HIP/ROCm dalej nie istnieje; AMD tylko przez Vulkan. Test na XTX razem z RustingStrata (model większy niż VRAM): K-172.


## Powiązane
- [[tqllm]]
- [[turbollm]]
- [[raport-15c-nowe-silniki]]
- [[produkt-ryzyka]]
- [[lekcja-benchmark-kopia]]
