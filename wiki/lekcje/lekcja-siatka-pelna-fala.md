---
typ: lekcja
tags: [lekcje, rdna3, kernel]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:272; ~/KERNEL/qwen-opt/NOTES.md:378
status: aktualne
---
# Siatka równa pojemności fali daje bimodalne czasy

**Siatka dokładnie 3072 bloków na 96 CU (pełna pojemność jednej fali) dawała per proces 13.6 albo 14.6 µs; 2560 bloków zawsze 12.2 µs.**

Tryb awarii #11 (runda 4 LFM, 2026-10-14). Konwolucję naprawiła łatka 0062 (`GGML_HIP_CONV_ROWS4`, 4 wiersze/blok: 3.458 → 3.402 ms, znika rozrzut per proces). Gate+up nadal 25.5 vs 26.2 µs. Audyt „siatka w pełnych falach” polecał też TileGym.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-losowe-spowolnienia]]
- [[lekcja-bledny-roofline]]
- [[lfm-shortconv]]
- [[rdna3-gfx1100]]
