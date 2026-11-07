---
typ: kernel
tags: [kernele, flash-attention, kv, weryfikacja]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/product/research/66b-1cat-tokenspeed.md:99-129,216-217; ~/KERNEL/product/research/66d-saber-engine-rdna.md:63-78,157; ~/KERNEL/product/research/66e-anatomia-serwowania-tqllm.md:132-136,192; ~/KERNEL/product/research/24h-kv-jeden-przebieg.md:9-14
status: do-sprawdzenia
---
# KV czytane raz na weryfikację (plan #8): trzy wzorce

**Weryfikacja MTP-4 to 5 tokenów × 6 głów = 30 kolumn, a `kvq` ma kafel 16 kolumn, więc dziś czyta i dekwantuje KV q4_0 dwa razy na krok; 1Cat, Saber i tqLLM pokazują trzy sposoby na jeden odczyt, szacunek 199k 74.5 → 77–83 t/s (2026-11-07, `[SZACUNEK]`).**

| Wzorzec | Jak | Ich wynik | Bitowość u nas |
|---|---|---|---|
| 1Cat Pack-GQA48 (V100) | 8 tokenów × 6 głów w jednym kaflu 48 wierszy; 80 podziałów = liczba SM, ≥ 64 tokeny na podział | operator −20…21%, runda −8.6% przy 128K | kolejność sum → KLD |
| Saber `sattn_decode` (R9700) | do 4 fal × 16 wierszy Q, fale dzielą kafel KV | w produkcji | **wariant „2 grupy wierszy, podział jak dziś” bitowy z konstrukcji `[INFERENCE]`** |
| tqLLM T(x) (Metal) | klucze poniżej T(x) w kaflach 64 wspólnych dla wierszy, ogon 16–79 kluczy w kolejności AR | bit w bit z plain | zachowuje `LLAMA_SPEC_BITEXACT` |

- Górna granica z naszego 24h: +3.0…6.6% e2e przy 94k, ≤ 2.3% przy 32k (kafel ~130 µs przy d98304).
- Kolejność: profil kroku przy 199k (plan #3) → przegląd `blocks_per_sm` (1Cat: 1 → 2 CTA/SM = −21% operatora) → wariant Sabera. Kill: FA < −10% w rocprofv3.
- Ryzyko: podwójny LDS kontra cap 64 KB (occupancy).

## Powiązane
- [[kernele/_hub|kernele]]
- [[fattn-kvq]]
- [[raport-24h-kv-jeden-przebieg]]
- [[koszt-szerokosci-weryfikacji]]
- [[1cat-vllm]]
- [[saber-engine]]
- [[tqllm]]
- [[raport-66-synteza]]
