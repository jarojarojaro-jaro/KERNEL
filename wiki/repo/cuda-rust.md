---
typ: repo
tags: [repo, rust]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/repos/29-cuda-rust.md:1-9; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:39
status: aktualne
---
# NVIDIA/cuda-rust

**Oficjalna platforma NVIDIA „CUDA dla Rusta” (HEAD `bc46b1f`, 2026-10-12); daje tylko liczbę odniesienia; werdykt: brak.**

cuda-oxide (Rust → PTX), cutile-rs (Rust → Tile IR) i wspólny runtime hosta. Autorzy: bezpieczne indeksy w persistent GEMM B200 „within 0.3%” surowych wskaźników, 2068.88 TFLOP/s = 96.35% cuBLAS. Dla nas tylko odniesienie: granica kernela w grafie CUDA ~0.81 µs (RTX 5090) vs nasze ~2.5 µs w grafie HIP.

## Powiązane
- [[repo/_hub|repo]]
- [[cutile-python]]
- [[hipfire]]
- [[hip-graph-narzut]]
- [[repos-30-przeglad]]
