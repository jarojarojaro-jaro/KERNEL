---
typ: narzedzie
tags: [narzedzia, rocm, isa]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/23a-rea.md:3,61-66,100-107; ~/KERNEL/tools/re/hip_fatbin_extract.py:1-12
status: aktualne
---
# `tools/re/hip_fatbin_extract.py`: code objects z `.hip_fatbin`

**Skrypt w czystym Pythonie (CPU) wyciąga z sekcji `.hip_fatbin` biblioteki HIP nieskompresowane bundle `__CLANG_OFFLOAD_BUNDLE__` (jeden na jednostkę kompilacji) i zapisuje każdy wpis `hipv4-amdgcn-*` jako `<outdir>/<idx>.<target>.co`; `--filter SUBSTR` zostawia tylko obiekty zawierające nazwę kernela (raport 23a, 2026-10-19).**

Użycie: `python3 ~/KERNEL/tools/re/hip_fatbin_extract.py <lib.so> <outdir> [--filter mul_mat_vec_q]`, potem `/opt/rocm/core-10.0/llvm/bin/llvm-objdump -d <outdir>/<n>.gfx1100.co`. Bundle skompresowane (CCOB) tylko zgłasza – do nich `clang-offload-bundler`.

Nasza `libggml-hip.so.0.26.0` (81 851 752 B): `.hip_fatbin` 63.9 MB, 140 nieskompresowanych bundli, tylko gfx1100; TU mmvq = 8 307 640 B code object, pełny dump 99 MB tekstu, 862 symbole, 798 instancji `mul_mat_vec_q*`. Zasoby per kernel (VGPR, SGPR, spille, LDS, fale/SIMD) dla wszystkich 7832 kerneli: `product/research/21l-skrypty/ours-llama-opt-gfx1100.csv`.

## Powiązane
- [[narzedzia/_hub|Narzędzia]]
- [[gdnemu-isadiff]]
- [[raport-23a-rea]]
- [[lekcja-vgpr-limit-hak-spill]]
