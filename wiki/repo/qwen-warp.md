---
typ: repo
tags: [repo, dlugi-kontekst, rtx-3090, kv]
aktualizacja: 2026-11-05
zrodlo: ~/KERNEL/product/research/63a-silniki-lokalne.md:24-26,389-407,471-487; https://github.com/tuan3w/qwen-warp (`146a654`, 2026-11-05)
status: aktualne
---
# qwen-warp (tuan3w): 262k na jednej RTX 3090

**Graf CUDA z fuzjami W4A16 (Swift-1.5 INT4), MTP k ≤ 3 + ogon prompt-lookup; decode 124 / 115 / 102 / 94 t/s przy 32k / 100k / 190k / 262k (2026-11-05).**

- Po przeskalowaniu pasma (×1.026) ~105 / 96 t/s wobec naszych 74.5 przy 199k: najmocniejszy dowód zapasu przy ≥ 100k.
- Lekcja z ich portu: atencja w weryfikacji była 15–20% wolniejsza przy 190k, bo dekwantyzowała ten sam kafel KV raz na kafel zapytań; naprawa = raz na grupę. To nasz otwarty punkt w [[fattn-kvq]] (dwa przejścia po KV przy 30 kolumnach).
- KV 4-bit z rotacją WHT i dokładnym pierścieniem fp16 (4 sinki + 256 ostatnich): tool-call 46 → 92–96%. Zmienia numerykę KV, więc u nas odrzucone ([[2026-11-05-tylko-bezstratne]]).
- Akcja bezstratna: jedno przejście KV na weryfikację, oczekiwane +5…15% przy 94–199k `[SZACUNEK]`.

## Powiązane
- [[repo/_hub|repo]]
- [[fattn-kvq]]
- [[qwen-qsa-llama-cpp]]
- [[raport-63-synteza]]
