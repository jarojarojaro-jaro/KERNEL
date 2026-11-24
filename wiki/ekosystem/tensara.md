---
typ: ekosystem
tags: [ekosystem, ocena, telemetria]
aktualizacja: 2026-11-24
zrodlo: ~/KERNEL/qwen-opt/research/repos/18-tensara.md:1-22; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:28
status: aktualne
---
# tensara/tensara

**Platforma zawodów w pisaniu kerneli (commit `fae96618`, 2026-07-21) z silnikiem oceny na Modal; werdykt: niska.**

Pomiar parą zdarzeń CUDA wokół jednego wywołania, zimny L2 przez `fill_` 160 MB, adaptacyjne 5–20 iteracji do CV < 1%, kalibracja tolerancji, która musi odrzucać wynik FP16. Jedyne czego nie mamy: telemetria `gpu_metrics` co 5 ms (zegar, temperatura, throttling) przypięta do iteracji. Do tego wejścia grafu przez zero-copy.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)
- Tensara to harness oceny kerneli, więc porównujemy go z naszymi harnessami: kolejką `run-jobs.sh`, fabryką i benchmarkiem aplikacji `app/engine/src/server/bench.ts`.
- Lepsze od nas: telemetria co 5 ms (zegar, temperatura, P-state, bity throttlingu) przypięta do każdej iteracji (`engine/gpu_monitor.py:39-76`, raport `qwen-opt/research/repos/18-tensara.md:20,62`). U nas kolejka zapisuje tylko temperaturę złącza na końcu joba (`qwen-opt/queue/run-jobs.sh:83`), a `bench.ts` w aplikacji podaje mediany bez zegarów i throttlingu. Na laptopach i APU klientów throttling w trakcie benchmarku może wybrać zły przepis i nikt tego nie zobaczy.
- Kalibracja tolerancji z kontrolą negatywną (tolerancja musi odrzucić wynik FP16, `tolerance.py:72-76`) przeszła do nas jako [[bramka-kld-kanarki]].
- Gorsze od nas: jedno wywołanie w parze zdarzeń przy kernelach 10–50 µs, średnia i stop przy CV < 1%, `sleep(0.5)` po rozgrzewce, test atencji z prawie równomiernym softmaxem (`18-…md:98-110`). To lista błędów do unikania w każdym naszym benchmarku, także w aplikacji.
- Bierzemy: telemetrię GPU per powtórzenie w `bench.ts` (zegar, temperatura, throttling, zapis w wyniku) i alarm w kolejce; test FA z ostrym softmaxem (P4).

## Powiązane
- [[kernelbench]]
- [[pygpubench]]
- [[amd-smi]]
- [[repos-30-przeglad]]
