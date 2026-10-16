---
typ: repo
tags: [repo, kurs]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/repos/02-a-hamdi-gpu.md:1-22; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:12
status: aktualne
---
# a-hamdi/GPU (100 dni nauki)

**Dziennik nauki CUDA „100 days” (HEAD `a9b0a17c`, 2025-04-27) z błędnymi benchmarkami; werdykt: niska.**

Po jednym małym kernelu dziennie według PMPP, głównie CUDA na Colab T4 i kilka portów HIP na MI250. Liczby autora: CUDA Graph 220 ms bez grafu vs 89.9 ms z grafem (10 000 uruchomień), SGEMM HIP 18.6 TFLOPS vs rocBLAS 34.3. „Winograd 52.4 TFLOPS przy N=512” jest niewiarygodne. Jedyna wartość: odnośnik do artykułu seb-v o SGEMM FP32 na RX 7900 XTX (dual-issue, padding LDS).

## Powiązane
- [[repo/_hub|repo]]
- [[how-to-optimize-in-gpu]]
- [[gpu-kernel-engineer-from-scratch]]
- [[rdna3-gfx1100]]
- [[repos-30-przeglad]]
