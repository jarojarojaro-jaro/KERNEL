---
typ: lekcja
tags: [lekcje, isa, nvidia]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21l-reverse-engineering-gpu.md:12
status: aktualne
---
# radare2 „sass” ≠ nvdisasm

**Plugin `ptx`/„sass” radare2 6.2.4 (sm_50–sm_110) dekoduje ten sam kod sm_86 inaczej niż nvdisasm (`lopc/brev` zamiast `IMAD.MOV/S2R`), niezależnie od `asm.cpu` – wyniki bezużyteczne (raport 21l, 2026-10-19).**

Reguła: ISA NVIDIA tylko przez `cuobjdump`/`nvdisasm` (CUDA 13.1 z wheela `triton`), ISA AMD przez `llvm-objdump --mcpu=gfx1100` i RGA; ogólne narzędzia RE porównać z deasemblerem producenta, zanim się im zaufa.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[raport-21l-re-gpu]]
- [[sm-86-89-120]]
