---
typ: research
tags: [research, reverse-engineering, isa]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21l-reverse-engineering-gpu.md:1-93
status: aktualne
---
# Raport 21l: narzędzia reverse engineeringu dla GPU

**Lista awesome-reverse-engineering nie ma ani jednej pozycji GPU (Ghidra, Capstone, REA – brak AMDGPU/NVIDIA; radare2 „sass” dekoduje sm_86 błędnie); działa zestaw producentów i LLVM: `llvm-objdump`/`clang-offload-bundler`, RGA 2.15 (`--livereg`), umr offline (PM4), ATT, `cuobjdump`/`nvdisasm` (raport 21l, CPU, 2026-10-19).**

- Nasze 7832 kernele gfx1100: prawdziwe spille w 165 (81 `flash_attn_ext_f16`, 47 `mul_mat_q`, 25 `flash_attn_tile`…), 2376 to stuby `NO_DEVICE_CODE`; MMQ/MMVQ Q4_K/Q5_K/Q6_K 0 spilli; CUDA sm_120a 7109 funkcji, 0 spilli. Narzędzie: [[co-stats]].
- Najważniejsza dźwignia: [[mmvq-multikolumnowe]] – klif VGPR przy ncols 4 → 5 (akcja A1, kill: spill > 0 albo verify ≤ +2%).
- Audyt taśmy PM4 offline: [[umr-offline-pm4]] (deskryptor MMVQ PRIV=0 potwierdzony).
- Nie działa na gfx1100: rocprof-compute (Omniperf); NVBit tylko dla własnych binarek; CuAssembler/TuringAs odrzucone ([[lekcja-radare2-sass]]).
- Zasady prawne: [[re-vendorow-zasady]].

## Powiązane
- [[research/_hub|research]]
- [[raport-23a-rea]]
- [[hip-fatbin-extract]]
