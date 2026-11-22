---
typ: archiwum
tags: [archiwum, ttft, topka]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/45-opoznienia.md:1-126
status: nieaktualne
wycofano: 2026-11-22
powod: opóźnienia topki dwa razy
zastapiona_przez: optymalizacje/opoznienia-ttft
---
# Raport 45: opóźnienia – cache MTP, rozgrzewka, natywny ChatML, budżet TTFT

**Cache konwersji MTP skraca start Qwen z 38.5 do 6.55 s (−83%), natywny ChatML parse 108.6 → 8.8 ms (476 KiB), TTFT tury agenta to ~440 z ~580 ms kopii checkpointów; rozgrzewka w serwerze bezstratna, ale opt-in.**

- Przełączenie LFM → Qwen 38.9 → 6.9 s.

## Powiązane
- [[raporty-2026-10-20-21]]
- [[opoznienia-ttft]]
- [[raport-38-ckpt-vram]]
