---
typ: llm
tags: [llm, uwaga, sparse-attention, dlugi-kontekst, kv, trening]
aktualizacja: 2026-11-26
zrodlo: https://aleph-alpha.com/en/blog/sparse-attention-in-kolibri-1-1/ (2026-11-25); X Aleph__Alpha 2125967904092938704 i alessio__serra 2125997732410065257 (panel JARO 2026-11-26); nasze liczby K-012 (~/qwen-opt/queue/logs/k012-*.log), lc.py 94k (~/qwen-opt/k183c/logs)
status: aktualne
---
# YASA (Kolibri 1.1): rzadka uwaga dorobiona do gotowego modelu i co by dała u nas

**YASA zamienia pełną uwagę na wybór ok. 2,2 tys. tokenów (indeks dwustopniowy liczony z istniejącej głowy KV) i daje 14× dekodu przy 1M względem Kolibri 1, ale kosztem dotrenowania (805 mld tokenów) i zmiany wyników; u nas pełna uwaga to tylko 16 z 64 warstw Qwena, więc taki zabieg dałby przy 94k najwyżej ok. 13%, przy 192k ok. 25% kroku dekodu.**

## Mechanizm (blog)
- **Indeks dwustopniowy:** bloki po 16 tokenów oceniane średnim kluczem → 1024 bloki (16 384 tokenów) → z nich top 2048 tokenów; uwaga liczy 2048 wybranych + 8 „sink” + 128 ostatnich = 2184 tokenów, niezależnie od długości kontekstu.
- **Indeks bez osobnej sieci:** wynik = średnia po 12 głowach Q z ReLU(q·k) jednej grupy KV; bez straty destylacyjnej KL.
- **Mało indeksów:** liczone tylko w warstwach 5, 15, 20, 30; sześć kolejnych warstw („reindexery”) bierze ich pulę i robi tylko krok drobny.
- **KV współdzielony między warstwami** (4 cache producentów, 6 konsumentów), zapisany w NVFP4; inicjalizacja przez obrót + SVD macierzy V zmniejsza skok straty bez treningu z 2,31 do 0,62 bita/bajt.
- **Prefill exit:** pełną sekwencję widzi tylko 30 pierwszych warstw.

## Liczby (blog, 4× B300, vLLM 0.33, maks. batch)
| kontekst | dekod vs Kolibri 1 | TTFT |
|---|---|---|
| 16k | 1,6× | 1,0× |
| 64k | 4,0× | 1,1× |
| 256k | 10,1× | 1,7× |
| 1M | 14,0× | 4,4× |
- Odczyt cache na krok przy 1M: 10,8 GB → 0,09 GB; KV na sekwencję 10,8 → 2,8 GB.
- Jakość bazowa −1,5 pkt (EN), RULER prawie bez zmian do 16k i przy 128k, trochę gorzej przy 32k, 64k i 256k–1M.
- Uwaga: baza porównania już miała okno przesuwne w 40/50 warstw, więc 14× nie jest względem pełnej uwagi.

## Co by dało u nas (nasze pomiary)
- Qwen3.8-27B: 16 warstw pełnej uwagi z 64 (reszta GDN ze stałym stanem).
- Kernel kvq przy weryfikacji 5 tokenów (K-012b, z poprawką par fal): 96k ok. 275 µs/warstwę, 192k ok. 521 µs → 16 warstw = ok. 4,4 ms i 8,3 ms.
- Krok dekodu przy 94k: 31,7 ms (lc.py, K-183c). Uwaga to więc ok. 14% kroku przy 94k i ok. 25% przy 192k; YASA zdjęłaby większość tego, reszta kroku (wagi) bez zmian.
- Wniosek: dla Qwena przy naszych długościach to rząd +15–30% przy 96–192k, nie 14×. Duże zyski są dla modeli z pełną uwagą w większości warstw i przy setkach tysięcy tokenów.

## Na później
- **Model z pełną uwagą w większości warstw przy długim kontekście** (np. klient Enigmy z dużym modelem dense na 256k+): YASA-podobny przepis to główna dźwignia, ale tylko z dotrenowaniem i zgodą na zmianę wyników (bramka jakości RULER + nasze zadania).
- **Własny trening (filar 2):** inicjalizacja KV-sharing przez SVD i indeks z istniejącej głowy to tani start bez osobnej sieci indeksującej; koszt ok. ¼ pretreningu.
- **Teraz u nas:** wersja bez treningu (wybór stron KV przy dekodzie) to K-188 w kolejce, bramka KLD + igły.
- **NVFP4 KV:** u nas wbrew zasadzie bezstratności; na Blackwellu u klientów jako opcja pamięci.

## Test u nas
- K-188: rzadka uwaga bez treningu w 16 warstwach pełnej uwagi Qwena, bramka KLD + igły; przygotowuje agent K188Sparse.

## Powiązane
- [[linki-2026-11-26-wieczor]]
- [[2026-11-26-wiedza-na-pozniej]]
