---
typ: produkt
tags: [produkt, uncensored, cache]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21e-kv-miedzy-modelami.md:120-136,188-207,238-242; ~/llama.cpp/src/llama-context.cpp:3204; src/llama-kv-cache.cpp:2528-2640
status: do-sprawdzenia
---
# Przełączanie Main ↔ Uncensored (i „Uncensored jako tryb”)

**Dziś przełączenie Main ↔ Uncensored to przeładowanie modelu i pełny prefill (~61.5 s przy 53k dla Qwena); llama.cpp przyjmuje jednak plik slotu z drugiego modelu o tych samych kształtach (sprawdza tylko magic, wersję i rozmiary), więc restore trwa 2.51 s – a tryb Uncensored w locie (`h ← h − r(r·h)`) zniósłby przełączenie i osobne pliki całkiem (raport 21e, 2026-10-19).**

- **Wariant A (identity przez plik slotu):** ~59 s oszczędności na przełączenie; nie bit-exact; wymaga szablonu Maina w obu serwerach i obcięcia KV do początku tury asystenta (wyciek odmowy); blokada hashem modelu z jawną allowlistą par.
- **Wariant B (tryb w locie):** Qwen s = 1 – rzut strumienia po embeddingu i każdym dodaniu (`qwen35.cpp:180,195`, MTP `:603,618`); LFM s = 1.75 – korekta na wyjściu writera przed dodaniem (26 warstw × 2). `--control-vector` jest tylko addytywny, potrzebny nowy „projection vector”, najlepiej w istniejących fuzjach add + rms_norm. Zysk: 0 s przełączenia, −15.66 GiB (Qwen) i −16.10 GiB (LFM) plików, Uncensored na lepszym kwancie Maina; prędkość Qwen-Unc 115.5 → ~109 t/s (kwant Maina), LFM-Unc 267.3 → ~293 t/s (~+10%); narzut ~2% bez fuzji `[INFERENCE]`.
- **Otwarte (decyzja użytkownika):** źródło wektorów – dystrybuować kierunki wyciągnięte z cudzych GGUF (Qwen/Orca Apache 2.0; LFM licencja `lfm1.0`, własny proces AtomicChat) czy liczyć własne (metoda Arditi: prompty harmful/harmless + jeden przebieg modelu) ([[otwarte-decyzje-techniczne]]).
- Czeka na E2 (KLD ≤ 0.01, refusal ±5 pp) i E3.

## Powiązane
- [[produkt/_hub|produkt]]
- [[uncensored-ablacja-kierunku]]
- [[cache-sesji-na-dysku]]
- [[lekcja-restore-stanu-exactness]]
