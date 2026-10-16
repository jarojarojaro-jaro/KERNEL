---
typ: repo
tags: [repo, ocena, telemetria]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/repos/18-tensara.md:1-22; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:28
status: aktualne
---
# tensara/tensara

**Platforma zawodów w pisaniu kerneli (commit `fae96618`, 2026-07-21) z silnikiem oceny na Modal; werdykt: niska.**

Pomiar parą zdarzeń CUDA wokół jednego wywołania, zimny L2 przez `fill_` 160 MB, adaptacyjne 5–20 iteracji do CV < 1%, kalibracja tolerancji, która musi odrzucać wynik FP16. Jedyne czego nie mamy: telemetria `gpu_metrics` co 5 ms (zegar, temperatura, throttling) przypięta do iteracji. Do tego wejścia grafu przez zero-copy.

## Powiązane
- [[repo/_hub|repo]]
- [[kernelbench]]
- [[pygpubench]]
- [[amd-smi]]
- [[repos-30-przeglad]]
