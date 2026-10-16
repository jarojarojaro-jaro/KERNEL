---
typ: lekcja
tags: [lekcje, rebase, mtp]
aktualizacja: 2026-10-16
zrodlo: ~/wt/rebase070/REBASE.md:143-150
status: aktualne
---
# Crash MTP po rebase: embd_state

**Po rebase na v0.7.0 Qwen MTP ze słownikiem draftu przerywał serwer przy pierwszym żądaniu, bo upstream przeniósł stan ukryty MTP do `embd_state`, a dwa nasze wywołania git zmergował bez konfliktu na starym `set_embd`.**

Objaw: `GGML_ASSERT(ubatch->embd_state …)` w `llm_graph_input_embd_h::set_input`. Przyczyna: upstream `781dbc5ac` (#30257). Nasze miejsca: `draft_greedy_chain` (#20 `c90db29c6`) i `draft_chain_segment` (#39 `7e9c73d8b`). Bez słownika draftu łańcuch się nie włącza, więc MTP bez vocab działał. Naprawa `8c942e5a9`. Lekcja: brak konfliktu przy rebase nie znaczy, że semantyka się zgadza – po każdym rebase test GPU w trybie produkcyjnym.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-build-cuda-0057-0070]]
- [[lekcja-ten-sam-serwer-pending-h]]
- [[amd-opt-v070]]
- [[2026-10-16-rebase-v070]]
