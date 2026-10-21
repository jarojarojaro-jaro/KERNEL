---
typ: research
tags: [research, xtx, re-kerneli]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/41-re-kerneli-xtx.md:1-19
status: aktualne
---
# Raport 41: RE kerneli XTX – GDN i małe opy vs hipfire

**MMVQ q8 n=5 spędza 70–82% w `wait vmcnt` (pamięć); `GGML_HIP_GDN_PREFETCH=1` bitowo zgodny, kernel −6%, ale E0 −0.13% → nie adoptowany.**

- Na wiersz GDN jesteśmy tańsi niż hipfire (278 vs 417 instr.).
- PREFETCH=2: +53% → odrzucone.

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-20-21]]
- [[hipfire]]
- [[pamiec-stanu-gdn]]
