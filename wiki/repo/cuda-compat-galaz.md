---
typ: repo
tags: [repo, llama-cpp, galezie, cuda]
aktualizacja: 2026-10-16
zrodlo: git -C ~/llama-master log --oneline e60eff95f..cuda-compat (74); ~/KERNEL/wiki/nvidia/cuda-compat.md:10-25
status: aktualne
---
# Gałąź cuda-compat

**`cuda-compat` @ `7b2680760` to `amd-opt` + 4 commity, które pozwalają zbudować fork dla CUDA bez zmiany kodu gfx1100 (74 commity nad `e60eff95f`).**

Dwa commity kompilacyjne (łatki 0070 i 0057) i dwa semantyczne (PDL w 0053/0057, `__syncwarp` przy tickecie 0056). Bez nich build padał w 25 TU; po nich 579/579 kroków. Niezmienność HIP sprawdzona porównaniem sha256 sekcji code objectu gfx1100 dla 6 dotkniętych TU. Szczegóły w notatce NVIDIA; te same zmiany na v0.7.0 niesie `cuda-v070`.

## Powiązane
- [[repo/_hub|repo]]
- [[cuda-v070]]
- [[amd-opt]]
- [[cuda-compat]]
- [[lekcja-build-cuda-0057-0070]]
