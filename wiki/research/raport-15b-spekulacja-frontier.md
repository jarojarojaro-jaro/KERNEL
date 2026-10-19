---
typ: research
tags: [research, spekulacja, lookup, mtp]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/15b-spekulacja-frontier.md:1-31; ~/KERNEL/product/research/15b-sim/results.txt:3-5; ~/KERNEL/product/research/16b-lookup-tail.md:152-161
status: aktualne
---
# Raport 15b: frontier spekulacji (lookup, szeroki blok, DFlash2, bit-exact)

**Lookup z kontekstu i szeroki blok weryfikacji (HyperQwen) dają nam mało, bo nasza głowica MTP już kopiuje (P(MTP d1 | lookup d1) = 0.968 vs 0.765 bazowo); sens ma tylko doklejanie ogona („EXT”) na edycjach agenta.**

Raport 2026-10-16, symulacja CPU na naszych danych, bez GPU.
- HyperQwen: 381 t/s to kopiowanie dokumentu słowo w słowo (14.97 tok/krok, 39.3 ms/krok); na czacie pozycje 7–14 bloku dają 0.65% przyjętych tokenów, 133 vs 131 t/s w szumie.
- Kopiowalność: czat/proza/kod – lookup trafia 1–17% pozycji, zysk ≈ 0%; wyjścia agenta omp (7.2 M tokenów): edycje hashline 58% / 26% (d1 / ≥ 8), `str_replace` 60% / 38%, bash 51% / 20%.
- Najlepsza polityka EXT (MTP zostaje głową, lookup dokleja ogon): krótki kontekst hashline +8%, `str_replace` +23%, mieszanka agenta +2.9%, czat 0%; przy ~32k mieszanka +0.2% (W=8) albo −3.8% (W=16). Nadpisywanie głowy lookupem (HYB) jest ujemne.
- Koszt szerokości na XTX: V(8) = V(5) + 2.48 ms, V(16) = V(5) + 7.09 ms; kvq czyta KV raz na kafel 16 wierszy (`ceil(6·W/16)`).
- DFlash2 n=15: akceptacja na kodzie rośnie (pl-kod 4.21 → 5.67), ale krok 32.9 → 39.1 ms; średnio 97.9 vs MTP 108.8 t/s.
- tqLLM „identyczne wyjście”: greedy, 1 slot, naprawione 2026-10-13; metodyka testu end-to-end z przemiataniem `ubatch` do przejęcia.
Ranking: shadow-log lookupu (0.5 osobodnia) → EXT-W8 + łańcuchy (2) → EXT-W16 po pomiarze V(W) przy 32k; nie robić HYB, DFlash2+lookup, bloków 32/64.

E1–E4 zrealizowane w [[raport-16b-lookup-tail]]: E2 V16 − V5 @32k 9.50 ms, E3 copy +41%, E4 W16 +51% nad W8; E1 (ruch użytkownika) otwarte.

## Powiązane
- [[research/_hub|research]]
- [[hyperqwen]]
- [[tqllm]]
- [[2026-10-16-lookup-kopiowalnosc]]
- [[lekcja-mtp-juz-kopiuje]]
- [[glowica-mtp]]
