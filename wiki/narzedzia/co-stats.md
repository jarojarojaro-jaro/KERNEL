---
typ: narzedzie
tags: [narzedzia, isa, vgpr]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21l-reverse-engineering-gpu.md:33-47,76-78; ~/KERNEL/product/research/21l-skrypty/co_stats.py; ~/KERNEL/product/research/21l-skrypty/ours-llama-opt-gfx1100.csv
status: aktualne
---
# `co_stats.py`: statyczny audyt kerneli (VGPR, spille, fale)

**`21l-skrypty/co_stats.py OUT.csv <lib.so|*.co|*.hsaco>` czyta wszystkie kernele z bundli HIP (także skompresowanych CCOB) i zapisuje per kernel VGPR, SGPR, spille, LDS i fale/SIMD; reguła fal gfx1100 = min(16, ⌊1536 / ⌈VGPR⌉₂₄⌋), zgodna z kompilatorem i RGA (raport 21l, 2026-10-19).**

Stan `~/llama-opt` (2026-10-19): 7832 kernele, 165 ze spillami, 2376 stubów; CSV `ours-llama-opt-gfx1100.csv`, producent `vendor-rocm-gfx1100.csv` (hipBLASLt 690 kerneli 0 spilli, rocBLAS 644 / 21). Plan: diff CSV przed/po łatce jako bramka builda ([[lekcja-vgpr-limit-hak-spill]]); CUDA odpowiednik `cuobjdump -res-usage`. Ciężkie przebiegi pod `cpuheavy.lock` ([[2026-10-19-szanujemy-sprzet-serwera]]).

## Powiązane
- [[narzedzia/_hub|Narzędzia]]
- [[hip-fatbin-extract]]
- [[raport-21l-re-gpu]]
