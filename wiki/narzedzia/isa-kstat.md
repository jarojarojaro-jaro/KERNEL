---
typ: narzedzie
tags: [narzedzia, isa, vgpr]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/tools/re/isa_kstat.py:1-20; ~/KERNEL/product/research/23f-podrecznik-optymalizacji-gpu.md:111-136,190
status: aktualne
---
# `tools/re/isa_kstat.py`: zasoby i miks instrukcji z `.s` AMDGPU

**`isa_kstat.py FILE.s [REGEX] [--max N]` czyta asembler AMDGPU (`clang -S --offload-device-only`) i podaje per kernel VGPR, SGPR, statyczny LDS, scratch, fale wave32 z reguły gfx1100 (granulat 24) oraz statyczne liczby instrukcji: ładowania wg szerokości (b32/b64/b96/b128, sub), LDS, `s_waitcnt`, DPP, VOPD, WMMA, dot, bariery, atomiki (2026-10-19).**

Liczby statyczne (bez krotności pętli), do tabel dowodowych z naszych buildów (nie z binarek vendorów, [[re-vendorow-zasady]]). Uzupełnia [[co-stats]] (ten czyta gotowe `.so`/`.co`); diff per łatka jako bramka przeciw spillom ([[lekcja-vgpr-limit-hak-spill]]).

## Powiązane
- [[narzedzia/_hub|Narzędzia]]
- [[co-stats]]
- [[podrecznik-gpu]]
