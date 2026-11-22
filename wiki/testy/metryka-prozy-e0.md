---
typ: test
tags: [testy, proza, metryka]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/37-proza-100.md:9-38
status: aktualne
model: qwen3-8-27b
karta: rx-7900-xtx
wynik: qwen3-8-27b | rx-7900-xtx | 78.93 t/s | proza E0 T=1; produkcja, thinking off | 2026-10-20
---
# Metryka prozy E0 (XTX, Qwen3.8-27B)

**E0 = 8 promptów prozy (4 PL, 4 EN) × seedy 1–8, 400 tokenów, T=1, `enable_thinking: false`, świeży serwer na ramię; baza produkcyjna 78.93 t/s [75.69, 82.21], 2.158 tok/krok, 27.34 ms/krok (2026-10-20).**

- Liczenie `prose_sum.py`: suma tokenów / suma czasu, bootstrap po promptach, A/B sparowane.
- Starsze „pl-proza” 96–104 t/s liczyły tekst z myśleniem – nieporównywalne.

## Powiązane
- [[raport-37-proza-100]]
- [[lekcja-proza-e0-vs-myslenie]]
- [[pomiar-abba]]
