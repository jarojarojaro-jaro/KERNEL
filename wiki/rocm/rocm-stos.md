---
typ: rocm
tags: [rocm, wersje, instalacja]
aktualizacja: 2026-10-16
zrodlo: dpkg -l / amd-smi version / rocminfo na serwerze (odczyt 2026-10-16); ~/KERNEL/reports/Optymalizacja kerneli na AMD.md:29-31; ~/KERNEL/research_notes/Optymalizacja kerneli na AMD/rocm_stack.md:8-17; ~/KERNEL/product/research/13-rocm-10.1.md:3-6,28; ~/KERNEL/qwen-opt/README.md:31-45
status: aktualne
---
# Stos ROCm na naszym serwerze

**Pracujemy na ROCm 10.0 (`/opt/rocm/core-10.0`, wersja kandydująca 10.0.0~pre4) z RX 7900 XTX (gfx1100); ROCm 10.1 leży obok w katalogu użytkownika do testów.**

Stan zainstalowany (odczyt 2026-10-16):
- pakiety `amdrocm*` 10.0.0~pre4-32424980240, `amdgpu-install` 31.50; jądro 6.8.0-138-generic;
- `amd-smi version`: AMDSMI 27.0.0, ROCm 10.0.0; `rocminfo`: Runtime Version 1.21, GPU `gfx1100`;
- kompilator AMD clang 23.0.0git (raport 13);
- build llama.cpp: `-DGGML_HIP=ON -DGPU_TARGETS=gfx1100 -DGGML_HIP_GRAPHS=ON -DGGML_HIP_NO_VMM=ON`, kompilator `/opt/rocm/core-10.0/lib/llvm/bin/clang++`, biblioteki przez `LD_LIBRARY_PATH` (nie ma ich w ld.so.conf); bez sudo.

Historia wersji (raport AMD, research notes): 7.14.0 (2026-07-15) → 10.0.0 (2026-08-26) → 10.1.0 (2026-10-05). Wersji 8 i 9 nie było; wydania co 6 tygodni, budowane przez TheRock. W 10.0 AMD zastąpiło HIP SDK for Windows przez ROCm Core SDK.

Rekomendacja raportu 13 (2026-10-16): zostać na 10.0, 10.1 trzymać obok (`~/opt/rocm-10.1`), upgrade systemu dopiero po teście md5/hash logitów.

## Powiązane
- [[rocm/_hub|ROCm]]
- [[rocm-10-1]]
- [[therock]]
- [[hip]]
- [[rx-7900-xtx]]
