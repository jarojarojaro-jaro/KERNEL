---
typ: narzedzie
tags: [narzedzia, determinizm, debug]
aktualizacja: 2026-10-16
zrodlo: ~/wt/batchinv/examples/bx-diff/bx-diff.cpp:1-11; git -C ~/llama-master log -1 204f108de
status: aktualne
---
# llama-bx-diff (pierwszy rozjeżdżający się węzeł)

**Program z gałęzi `batch-invariant`: znajduje pierwszy węzeł grafu, którego wynik dla tokenu różni się między zwykłym dekodem (token po tokenie) a weryfikacją N tokenów w jednym batchu.**

Kontekst A (plain): prompt (ostatnie 4 tokeny osobno, jak llama-server), potem N tokenów greedy po jednym. Kontekst B (jak MTP): `n_rs_seq` N−1 (GATED_DELTA_NET_LAG), te same N tokenów jednym batchem. Każdy węzeł pasujący do regexu (domyślnie `l_out`) jest kopiowany na hosta i porównywany bit w bit. Uwaga z kodu: callback dzieli graf na każdym dopasowanym węźle, więc fuzje przez ten węzeł są wyłączone w obu przebiegach. Commit `6e261fdb4` dodał porównanie węzłów f16 i wierszy KV cache. Użycie: `llama-bx-diff -m MODEL [-n N] [-f REGEX]`.

## Powiązane
- [[narzedzia/_hub|narzedzia]]
- [[gdnemu-isadiff]]
- [[det-probe]]
- [[batch-invariant]]
- [[lekcja-bit-exact-attention]]
