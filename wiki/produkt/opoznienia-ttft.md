---
typ: produkt
tags: [produkt, ttft, latencja]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/45-opoznienia.md:84-122; ~/KERNEL/product/research/38-checkpointy-vram.md:12-19
status: aktualne
---
# Opóźnienia: TTFT, start i przełączanie modeli (topka)

**Stan po f9b84bcfa: start Qwen 38.5 → 6.55 s (cache MTP), tura agenta S2-turn2 687/579 → 197 ms (CKPT_VRAM=2), świeży 2k −22% (2026-10-21).**

- Budżet tury przed zmianą: 3 × utworzenie checkpointu 144–150 ms = ~440 z ~580 ms (`45:90`).
- Szablon jinja 9–11 ms → ~1 ms natywnie; tokenizacja 7.3k 15 → ~3 ms (PAR=8).
- Prefill świeżego promptu: 2k 2.21 s, 8k 8.0 s, 32k 34.1 s (`45:98`).
- Rozgrzewka przed READY: bezstratna, ale ready +2.35 s → opt-in.

## Powiązane
- [[produkt/_hub|produkt]]
- [[raport-45-opoznienia]]
- [[raport-38-ckpt-vram]]
- [[cache-sesji-na-dysku]]
