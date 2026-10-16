---
typ: nvidia
tags: [nvidia, cuda, toolkit]
aktualizacja: 2026-10-16
zrodlo: ~/qwen-opt/cloud/CUDA-AUDIT.md:20-50; ~/qwen-opt/cloud/results/{3090,5060ti,3060}-20261016/build/times.jsonl:1-3; ~/qwen-opt/cloud/results/*/hw/hw.json (odczyt 2026-10-16); ~/KERNEL/hardware/rx-7900-xtx.md:36-44
status: aktualne
---
# Stos CUDA: jak budujemy fork dla NVIDIA

**Fork budujemy dla NVIDIA nvcc 12.8 z conda-forge (bez sudo, bez sterownika na serwerze), dla architektur sm_86, sm_89 i sm_120; testy na GPU robimy w chmurze.**

Lokalny toolkit (CUDA-AUDIT, 2026-10-16):
- micromamba + conda-forge do `~/opt/cuda-12.8` (2.3 GB zamiast 5.4 GB runfile): `nvcc release 12.8, V12.8.93`, cuBLAS 12.8.5.5, host compiler systemowy g++ 13.3;
- serwer nie ma sterownika NVIDIA, więc linker dostaje stub `libcuda.so.1` przez `-rpath-link`;
- flagi: `-DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES="86;89;120"` (CMake zamienia 120 na `120a`), Ninja, Release; skrypt `~/qwen-opt/cloud/cuda-audit-build.sh`.

Czasy buildów lokalnie (86;89;120): upstream 799 s, `cuda-compat` 835 s (+4.5%), `amd-opt` tylko CPU 155 s. Na instancjach Vast (jedna architektura): 3090 sm_86 base 860 s / fork 787 s (7 wątków), 5060 Ti sm_120 base 501 s / fork 503 s (8 wątków), 3060 ~1140–1160 s (80 wątków).

Sterowniki na wynajętych kartach (hw.json): RTX 3090 615.71.09, RTX 5060 Ti 580.173.02; obraz `nvidia/cuda:12.8.1-devel-ubuntu24.04`.

Lokalnie w maszynie jest też RTX 5060 Ti (sm_120, 16 GB), na razie bez sterownika NVIDIA w systemie.

## Powiązane
- [[nvidia/_hub|NVIDIA]]
- [[cuda-compat]]
- [[sm-86-89-120]]
- [[harness-chmurowy]]
- [[rtx-5060-ti]]
