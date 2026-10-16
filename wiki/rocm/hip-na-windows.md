---
typ: rocm
tags: [rocm, windows, pal]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/08-analiza-platformy-latek.md:14-21,41-68; ~/KERNEL/product/PLAN.md:257; ~/KERNEL/reports/Optymalizacja kerneli na AMD.md:31
status: aktualne
---
# HIP na Windows: PAL zamiast ROCr

**Na natywnym Windows HIP używa runtime PAL, a nie ROCr; dlatego łatki zależne od ROCr (PM4 replay 0060/0061) i profiler rocprofv3 tam nie działają.**

Dowody (raport 08 §2):
- dokumentacja AMD: rocclr współpracuje z „ROCr on Linux or PAL on Microsoft Windows”;
- kod CLR `device.cpp`: na Windows domyślnie `GPU_ENABLE_PAL = 1` („keep PAL path for now”);
- TheRock: ROCR-Runtime na Windows „Unsupported”; próba przełączenia (rocm-systems#8900) zamknięta bez merge 2026-10-04, TheRock#6713 nadal draft.

Skutki dla naszych łatek:
- kod GPU z intrynsykami gfx11 (WMMA, DPP, buffer resource) nie zależy od runtime, więc skompiluje się i wykona pod PAL; inny kompilator (HIP SDK 7.2 vs ROCm 10.0 clang) wymaga sprawdzenia bitowości;
- koszt granicy kernela pod PAL jest nieznany, a od niego zależy wartość fuzji;
- 0060 dodaje bezwarunkowe `find_package(hsa-runtime64 REQUIRED)`, co [SZACUNEK raportu] łamie build HIP na Windows; trzeba to owinąć w `if (NOT WIN32)`;
- testy z `__builtin_popcountll` (0019, 0057) nie skompilują się pod MSVC [SZACUNEK].

Wersjonowanie: w ROCm 10.0 AMD zastąpiło HIP SDK for Windows przez ROCm Core SDK (raport AMD).

## Powiązane
- [[rocm/_hub|ROCm]]
- [[rocr]]
- [[analiza-platformy]]
- [[wsl2-rocm]]
- raport-08-platforma
