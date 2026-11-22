---
typ: optymalizacja
tags: [optymalizacje, mmvq, xtx]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/49-mmvq-ogon-1024.md:1-77
status: do-sprawdzenia
technika: MMVQ n=5 ogon k/v 1024 wierszy
werdykt: w-toku
zysk: szac. −0,03 ms/krok, bez bramki
dowod: raport-49-mmvq-ogon-1024
model: qwen3-8-27b
karta: rx-7900-xtx
---
# Raport 49: MMVQ n=5 – ogon 1024-wierszowych k/v

**Wszystkie 1024-wierszowe macierze to `attn_k`/`attn_v` 17 warstw uwagi; kandydat `52784c744` szacuje −0.03 ms/krok, bramka md5 i ABBA nieuruchomione (GPU stop 21.10 ~03:30).**



## Powiązane
- [[raporty-2026-10-20-21]]
- [[mmvq-multikolumnowe]]
- [[raport-47-kernel-lab]]
