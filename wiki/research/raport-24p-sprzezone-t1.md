---
typ: research
tags: [research, spekulacja, sampler, topka]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/24p-sprzezone-t1.md:8-12,29-41,63
status: aktualne
---
# Raport 24p: sprzężone próbkowanie draftu (`LLAMA_SPEC_COUPLED`) na topce przy T=1

**Sprzężony Gumbel daje +3.5% t/s przy T=1 (CI95 +1.8…+5.3%): 107.6 → 111.4 t/s, 3.037 → 3.111 tok/krok, bezstratnie rozkładowo i zgodnie z GPU verify; T=0 md5 bez zmian (2026-10-20).**

- Czysty efekt draftu (tryb 1 vs kontrola 2): tok/krok +3.7% [+2.1, +5.3], op Gumbel +0.66% ms/krok (`24p:9`).
- Metoda: ABBA z nowymi seedami w drugim przejściu, 96 żądań/tryb, bootstrap po (prompt, seed) (`24p:27-41`); zob. [[lekcja-ustalony-seed-to-nie-powtorzenie]].
- Zalecenie: `LLAMA_SPEC_COUPLED=1` w topce tylko dla qwen/uncensored (`24p:63`). DT zostaje 1.0 ([[raport-24s-drzewa-proza]]).
- Metoda: [[sprzezone-probkowanie-draftu]]; poprzednik [[raport-16k-sprzezone-probkowanie]].

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[sprzezone-probkowanie-draftu]]
- [[raport-16k-sprzezone-probkowanie]]
- [[lekcja-ustalony-seed-to-nie-powtorzenie]]
- [[raport-24s-drzewa-proza]]
