---
typ: karta
tags: [karty, amd, apu]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/reports/Optymalizacja kerneli na AMD.md:7,15,17,84,88,104,115; ~/KERNEL/product/research/05-chmura-gpu-do-testow.md:25,138,292; ~/KERNEL/product/PLAN.md:277
status: aktualne
---
# AMD Strix Halo (Ryzen AI Max, gfx1151)

**APU RDNA3.5 z pamięcią zunifikowaną do 128 GB; cel na fazę 3 produktu, dziś tylko w danych z raportów.**

- Arch: RDNA3.5 gfx1151 (Radeon 8060S); pamięć UMA mapowana przez GPUVM, 256 GB/s teoretycznie, ok. 212 GB/s zmierzone (llm-tracker).
- Konfiguracja wg AMD: minimalne VRAM w BIOS i alokacje z GTT, limit przez `ttm.pages_limit` / `amd-ttm`; bez tego ROCm widzi tylko połowę pamięci.
- llama.cpp (raport AMD): ROCm o 20.56% szybszy w pp i o 24.64% wolniejszy w tg niż Vulkan (Qwen3-Coder-30B-A3B, 08/2026); `GGML_HIP_ROCWMMA_FATTN=ON` szkodzi (−41% przy pp8192 w issue #24437); `ROCBLAS_USE_HIPBLASLT=1` daje ~3× pp.
- Strata na Strix Halo: 125B UD-IQ4_XS przy 8K ok. 1293 t/s promptu i 53.8 t/s wyjścia.
- Nasze łatki: część bramek RDNA3 obejmuje też gfx115x (0022, 0040, 0060, 0070 — korekta raportu 08), ale nic nie było mierzone.
- Dostęp: GigaGPU Ryzen AI Max+ 395 £299/mies.; PLAN: faza 3 (razem z macOS i Intel Arc).

## Powiązane
- [[karty/_hub|Karty]]
- [[rdna3-gfx1100]]
- raport-amd-kernele
- strata
- [[rx-7900-xtx]]
