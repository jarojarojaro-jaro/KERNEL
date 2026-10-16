---
typ: repo
tags: [repo, dsl]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/repos/10-tilelang.md:1-22; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:20
status: aktualne
---
# tile-ai/tilelang

**Python DSL do kafelkowych kerneli (HEAD `19da924`, 2026-10-14); na RDNA3 tylko f16 WMMA, bez iu8; werdykt: niska.**

Generuje CUDA, HIP, Metal i Ascend, ma autotuner. Na gfx11 `T.gemm` emituje `wmma_f32_16x16x16_f16`, int8 GEMM na RDNA jest pomijany, async copy bufor→LDS tylko na CDNA gfx94+, więc `T.Pipelined` na RDNA nie nakłada transferów. Nie generuje lepszych kerneli niż nasze; generowanie przez TileLang/cuTile/Triton odrzucone (brak iu8 WMMA i formatów GGUF).

## Powiązane
- [[repo/_hub|repo]]
- [[cutile-python]]
- [[tilegym]]
- [[wmma-small-n]]
- [[repos-30-przeglad]]
