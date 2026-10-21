---
typ: model
tags: [modele, gemma, iswa]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/33-modele-na-karty.md:44-46,76
status: aktualne
---
# Gemma 4 (26B-A4B, 31B, 12B)

**Gemma 4 ma iSWA (okno 1024: 25/30 warstw SWA w 26B, 50/60 w 31B, 40/48 w 12B), co fitcalc v2 uwzględnia; w raporcie 33 nie wygrała żadnej klasy kart.**

- LM: Gemma 4 26B-A4B Q4_K_XL na 3090 mediana 138.3 t/s (`33:76`).
- Globalne warstwy: brak `attn_v` oznacza V = K, ale V jest w cache.

## Powiązane
- [[modele/_hub|modele]]
- [[raport-21o-gemma]]
- [[raport-33-modele-na-karty]]
- [[qwen3-6-35b-a3b]]
