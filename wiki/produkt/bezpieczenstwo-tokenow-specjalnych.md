---
typ: produkt
tags: [produkt, bezpieczenstwo, safe-special, safe-tools]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/32e-safe-special-tokens.md:7-20; ~/KERNEL/product/research/42-safe-io.md:1-10; ~/KERNEL/product/research/43-integracja-2026-10-20.md:10,34
status: aktualne
---
# Bezpieczeństwo: SAFE_SPECIAL (wejście) i SAFE_TOOLS (wyjście)

**Dwie dziury lustrzane: tekst z żądania stawał się tokenami sterującymi (32e), a tekst modelu udający marker otwierał prawdziwy tool call (39c); obie zamknięte i domyślnie włączone w `run-topka.sh` od 2026-10-21.**

- `LLAMA_SERVER_SAFE_SPECIAL=1`: zakresy bajtów treści z renderu jinja, `llama_tokenize_plain_ranges` nie uznaje tokenów specjalnych w tych zakresach.
- `LLAMA_SERVER_SAFE_TOOLS=1`: parser PEG dopasowuje markery tylko jako tokeny specjalne.
- Bramka: md5 on == off (c4708318/6f14e814/894e56e4), raport 43.

## Powiązane
- [[produkt/_hub|produkt]]
- [[raport-32e-safe-special]]
- [[raport-42-safe-io]]
- [[raport-39c-deepseek-deploy]]
- [[wylaczniki-env]]
