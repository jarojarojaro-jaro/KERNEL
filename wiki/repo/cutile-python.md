---
typ: repo
tags: [repo, dsl, pdl]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/repos/13-cutile-python.md:1-21; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:23
status: aktualne
---
# NVIDIA/cutile-python (cuTile)

**Kafelkowy DSL NVIDIA kompilowany do Tile IR (commit `d9d8520`, 2026-10-13); bierzemy odpowiednik PDL na AMD; werdykt: niska–średnia.**

PDL jako operacja języka, dzielenie pętli K/V wg maski (do +32% FA prefill, pomiar NVIDIA), FMHA decode sm100a bez osobnego kernela combine, model checker harmonogramów bez GPU. Dla nas: wcześniejszy start następnego kernela przez `hipExtAnyOrderLaunch` + flagę (L5, szacunek −0.2…−0.45 ms/token).

## Powiązane
- [[repo/_hub|repo]]
- [[tilelang]]
- [[tilegym]]
- [[lekcja-pdl-sm120]]
- [[repos-30-przeglad]]
