---
typ: repo
tags: [repo, moe]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/repos/05-pplx-kernels.md:1-22; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:15
status: aktualne
---
# perplexityai/pplx-kernels i pplx-garden/lily

**Kernele MoE all-to-all Perplexity (porzucone, HEAD `f70d1eb7`) i następca `lily` (MoE decode na jednym GPU); werdykt: niska.**

pplx-kernels: kooperacyjny launch z barierą gridu, flagi acquire/release z kodowaniem `count+1`, combine w stałej kolejności (deterministyczny). Liczby autorów: EP8 NVLink dispatch 41.6 µs i combine 41.7 µs przy 1 tokenie/GPU. `lily` (Rust+Metal, Qwen3.6-35B-A3B): 194.7 t/s przy kontekście 256 na M5 Max, 1.31x względem MLX. Dla nas tylko potwierdzenie ticketów/barier i pomysł rozgrzewania Infinity Cache między kernelami.

## Powiązane
- [[repo/_hub|repo]]
- [[deepgemm]]
- [[mkernel]]
- [[fuzje-lfm-moe]]
- [[repos-30-przeglad]]
