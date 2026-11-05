---
typ: metoda
tags: [metody, cache, agent, serwer]
aktualizacja: 2026-11-05
zrodlo: ~/KERNEL/product/research/63b-colibri-maya-delta.md:33-39,200-208,260-270,299-320
status: aktualne
---
# Wspólny początek promptu i chude checkpointy (Maya #607, RTP-LLM #1574)

**Mały osobny wpis cache z samym system promptem i narzędziami (Maya #607: nowa rozmowa 19× szybciej) oraz stan liniowy trzymany tylko na granicach wiadomości i ogonie (RTP #1574) to dwie formy tej samej zasady: mały stan na granicach wiadomości zamiast kopii całej sesji.**

- Dziś nasz `CACHE_SHARE_MIN` kopiuje cały wpis długiej sesji: 2.3 GB przy 53k, do 9–14 GB przy 100k+; po jego wyrzuceniu nowa sesja czyta system prompt od zera (4.4k → 4.4 s w logu 2026-11-05).
- Port #607: przy `is_user_start` i pos ≥ 1024 zapisać KV 0..p + jeden stan GDN (~0.42 GB przy 14k) jako osobną pozycję LRU; oczekiwane −70…−95% startu sesji `[SZACUNEK]`.
- Chude checkpointy: 1. i 2 ostatnie wiadomości usera + n−4−ub i n−4; wpis 118k 14.2 → ~3–4 GB.
- Oba bezstratne (md5 bez zmian z konstrukcji). Benchmark: `tools/agent_bench.py` z Mai.

## Powiązane
- [[metody/_hub|metody]]
- [[project-maya]]
- [[lekcja-cache-ram-za-maly]]
- [[sglang-hicache]]
- [[cache-sesji-na-dysku]]
