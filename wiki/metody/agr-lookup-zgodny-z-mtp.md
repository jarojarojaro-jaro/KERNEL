---
typ: metoda
tags: [metody, spekulacja, lookup]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21c-copy-paste-lm.md:12,126-133,185-195
status: aktualne
---
# AGR: wybór kandydata lookupu zgodnego z draftami MTP

**Reguła bez treningu i bezstratna: spośród kandydatów lookupu (sufiks ≥ 2 albo ≥ 4 tokenów) zostawić tych, których pierwsze 4 tokeny kontynuacji równają się 4 draftom MTP, potem najdłuższy sufiks, potem najnowszy; w symulacji AGR2 daje +3.7% t/s na agencie (2/3 sufitu idealnego pointera) i +0.6% na czacie (raport 21c, 2026-10-19).**

Wdrożenie (proponowane, ~0.5 dnia kodu + ~0.5 dnia A/B): w `common_spec_lookup` (`common/speculative.cpp`) indeks 2-gramów obok 4-gramów, przegląd ≤ 64 najnowszych kandydatów po wyliczeniu draftów MTP, ogon do W16, przełącznik `LLAMA_SPEC_LOOKUP_AGREE=1`. Weryfikacja bez zmian, więc tekst T=0 identyczny (z zastrzeżeniem W16 poza `LLAMA_SPEC_BITEXACT`). Ryzyko: fałszywe ogony, każdy +6.4 ms.

Eksperyment: ABBA w jednej binarce na `mvs`, `copy` (hashline-pl, `str_replace`) i `spec_sweep`, T=0 i T=1 × 3 seedy; metryki ms/krok, tok/krok, liczba i akceptacja ogonów. Kill: < +2% t/s na hashline + `str_replace`, albo > +0.5% ms/krok na `spec_sweep`, albo akceptacja ogonów AGR < 80% na czacie, albo zmiana md5 przy T=0 na W8 z `BITEXACT`.

## Powiązane
- [[metody/_hub|Metody]]
- [[2026-10-19-sufit-pointera-lookup]]
- [[2026-10-18-lookup-ogon]]
- [[zestaw-copy-mvs]]
