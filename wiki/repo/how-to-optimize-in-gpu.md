---
typ: repo
tags: [repo, kurs, gemm]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/repos/08-how-to-optimize-in-gpu.md:1-9; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:18
status: aktualne
---
# Liu-xiandong/How_to_optimize_in_GPU

**Dydaktyczne „drabiny optymalizacji” CUDA dla V100 (HEAD `5d2def3e`, 2023-07-29); werdykt: niska.**

Elementwise, reduce v0–v7, sgemv, sgemm FP32, SpMV/SpMM; wszystkie liczby to pomiary autora na V100 (900 GB/s), np. sgemv 10.3 µs vs cuBLAS 8.4 µs (M=16384). Brak kwantyzacji, tensor cores i AMD. Jedyny wkład: wzór podwójnego bufora LDS dla MMQ (to samo co DeepGEMM i blocksparse).

## Powiązane
- [[repo/_hub|repo]]
- [[blocksparse]]
- [[a-hamdi-gpu]]
- [[prefill-mmq-fa]]
- [[repos-30-przeglad]]
