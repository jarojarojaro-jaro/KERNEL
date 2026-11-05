---
typ: decyzja
tags: [decyzje, jakosc, bezstratne, metodologia]
aktualizacja: 2026-11-05
zrodlo: polecenie użytkownika 2026-11-05 (przekazane przez agenta głównego); ~/KERNEL/product/research/63-SYNTEZA.md:5,109-126
status: aktualne
---
# 2026-11-05: tylko optymalizacje bezstratne

**Decyzja użytkownika (2026-11-05): „nie chcę zmieniać jakości – mieliśmy tylko optymalizować”; przyspieszenia wyłącznie bez zmiany wyjścia modelu.**

- Dozwolone: zmiany bitowo identyczne albo różniące się tylko kolejnością działań na floatach, sprawdzane bramką greedy md5 i KLD jak dotąd ([[zgodnosc-bitowa-md5]]). Przykłady: jedno przejście KV w [[fattn-kvq]], cap LDS, MTP lean reserve, `--cache-ram`, chude checkpointy, wpis „wspólny początek”, n MTP per karta (draft nie zmienia wyjścia), asynchroniczny następny krok, przeszukiwanie flag, przycięcie nadmiaru KV 10.7 KiB/token.
- Odrzucone bez rankingu: rzadka atencja ([[qwen-qsa-llama-cpp]], [[latent-sparse-attention]]), [[strata-kva]], [[fly-stratna-weryfikacja]], KV 3-bit ([[vllm-rocm-octave]]), REAP, zmiany kwantów wag i KV (też pierścień f16 w KV).
- Port QSA zaparkowany; jego liczby pochodzą z RTX 4090, nie z XTX.
- Zmiany treści promptu (odsyłanie `reasoning_content`, kolejność narzędzi) tylko za osobną zgodą.
- Pełna lista: [synteza 63](../../product/research/63-SYNTEZA.md), sekcja 4.

## Powiązane
- [[decyzje/_hub|decyzje]]
- [[2026-10-20-karta-fabrycznie]]
- [[2026-11-05-termika-eco-test]]
- [[raport-63-synteza]]
- [[tryb-stratny-pflash]]
