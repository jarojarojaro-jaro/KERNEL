---
typ: model
tags: [modele, gemma, iswa]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/33-modele-na-karty.md:44-46,76
status: aktualne
model: gemma-4
rozmiar: 26B-A4B, 31B, 12B
kwant: Q4_K_XL
karty: rtx-3090
wynik: gemma-4 | rtx-3090 | 138.3 t/s | dekod mediana; 26B-A4B Q4_K_XL, LM | 2026-10-21
---
# Gemma 4 (26B-A4B, 31B, 12B)

**Gemma 4 ma iSWA (okno 1024: 25/30 warstw SWA w 26B, 50/60 w 31B, 40/48 w 12B), co fitcalc v2 uwzględnia; w raporcie 33 nie wygrała żadnej klasy kart.**

- LM: Gemma 4 26B-A4B Q4_K_XL na 3090 mediana 138.3 t/s (`33:76`).
- Globalne warstwy: brak `attn_v` oznacza V = K, ale V jest w cache.

<!-- TABELE:START -->
## Wyniki z notatek (2)

Najlepszy wynik na metrykę z pól `wynik` notatek testów (tools/tabele.py, 2026-11-27); pełna tabela: [[najlepsze-wyniki]].

| karta | metryka | najlepszy | warunki | data | źródło |
|---|---|---|---|---|---|
| NVIDIA RTX 3060 12 GB [[rtx-3060]] | dekod | **37,38 t/s** | 12B q8_0 ctx 262 144 | 2026-11-07 | [[rtx-3060]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod mediana | **138.3 t/s** | 26B-A4B Q4_K_XL, LM | 2026-10-21 | [[gemma-4]] |
<!-- TABELE:END -->

## Powiązane
- [[modele/_hub|modele]]
- [[raport-21o-gemma]]
- [[raport-33-modele-na-karty]]
- [[qwen3-6-35b-a3b]]
