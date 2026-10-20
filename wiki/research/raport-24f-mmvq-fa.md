---
typ: research
tags: [research, mmvq, fa, isa]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/24f-mmvq-i-fa.md:7-14,68-72; ~/KERNEL/product/research/26-kolejka-gpu-wieczor.md:11
status: aktualne
---
# Raport 24f: MMVQ n=1 szeroki loader, klif Q4_K n=5, FA D=256 w prefillu (ISA)

**Wyniki statyczne ISA: loader buforowy MMVQ n=1 usuwa `vmcnt(0)`, `amdgpu_num_vgpr(120)` + `waves_per_eu(12)` daje Q4_K n=5 119 VGPR / 12 fal, FA `<256,256,32,2>` spilluje 220 VGPR; na GPU wide=2 wyszło −1.0% tg128 – odrzucone (2026-10-19/20).**

- Q4_K n=1: 18 → 12 ładowań/iterację, przy `=2` min `vmcnt(7)` (`24f:11,22-24`).
- Kolejka 26: Qwen tg128 40.86/40.88 (off) vs 40.41/40.52 (wide=2), LFM bez zysku; md5 identyczne (`26:11`).
- Klif n=5 obalony pomiarem: [[raport-24n-mmvq-n5]]. Spill FA usunięty w [[raport-24v-prefill-fa]].
- Lekcja ISA: kopiowanie `w = wn` w pętli wymusza `vmcnt(0)`; prefetch wymaga jednolitej liczby iteracji + `sched_barrier(0)` (`24f:70`). Narzędzie: [[isa-kstat]].

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[raport-24n-mmvq-n5]]
- [[raport-24v-prefill-fa]]
- [[mmvq-n1-wiersze]]
- [[isa-kstat]]
