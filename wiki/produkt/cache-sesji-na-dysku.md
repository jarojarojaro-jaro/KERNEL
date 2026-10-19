---
typ: produkt
tags: [produkt, cache, serwer]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/product/research/16f-xtx-szybkie.md:16,192-215; ~/wt/quickwins/qw/e5.jsonl
status: aktualne
---
# Cache sesji na dysku (projekt z 16f E5)

**Istniejący mechanizm llama-server `--slot-save-path` + `/slots/0?action=save|restore` (z checkpointami) przywraca sesję 53k z SSD 23–24× szybciej niż prefill: Qwen MTP 2.28 GiB w 2.51 s zamiast ~61.5 s, LFM 553 MiB w 0.53 s zamiast ~12.2 s (2026-10-18).**

| model | sesja | plik | zapis | odczyt | potem nowa sesja |
|---|---|---|---|---|---|
| LFM | 53 030 tok. | 553 MiB | 0.37 s | 0.53 s | 502 tok., 836 ms |
| Qwen MTP | 53 258 tok. | 2.28 GiB | 1.99 s | 2.51 s | 63 tok., 2224 ms |

Warianty:
- **A, wrapper (~1 dzień):** proces obok serwera robi `save` przy zmianie modelu, zatrzymaniu i bezczynności; plik nazwany hashem (model, typy KV, draft MTP, szablon, pierwsze 4096 tokenów); `restore` przed żądaniem po najdłuższym prefiksie. Wady: jeden slot, restore blokuje serwer.
- **B, natywny (3–5 dni lub upstream #28092):** asynchroniczny zapis wpisów usuwanych z `--cache-ram`, indeks hashy bloków na dysku, budżet i TTL jak w Lucebox (128 GB, 72 h).

Zalecenie raportu: najpierw A (95% zysku przy przełączaniu Qwen ↔ LFM). Niezaimplementowane.

## Powiązane
- [[produkt/_hub|Produkt]]
- [[2026-10-18-cache-promptu-agenta]]
- [[raport-15d-prefill-dlugi-kontekst]]
- [[produkt-architektura]]
