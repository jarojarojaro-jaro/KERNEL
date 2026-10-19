---
typ: metoda
tags: [metody, fabryka, bramki]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21i-rsi-inference-bench.md:231-274
status: do-sprawdzenia
---
# Zmiany fabryki v1 i RSI-F z RSI-Inference Bench (propozycja)

**Dwanaście mechanizmów z benchmarku Apple przełożonych na karty i bramki naszej fabryki; najwyżej w priorytecie: werdykt `VOID` oddzielony od `INVALID`, audyt promptów Implementera (każde „nie wolno X” ma regułę z fixture'em albo znika) i worktree bez historii przed P2 (raport 21i, 2026-10-19).**

| # | zmiana | priorytet |
|---|---|---|
| A1 | R37 `acceptance-floor`: przy profilu spekulacji `CONFIRMED` wymaga, by CI `tok_step` nie leżał w całości poniżej −max(MDE, 1%) – zepsuty drafter potrafi podnieść t/s | wysoki |
| A2 | G2c generation judge: serwer bazy bez spekulacji teacher-forcuje emisję kandydata (J1: ε = 0.5 nata) | średni |
| A3 | werdykt `VOID` (preflight, crash ramienia A, A/A ponad próg) ≠ `INVALID` (wina kandydata); page fault/reset nigdy VOID – kwarantanna | wysoki |
| A4 | karta `null-rebuild` raz na cykl (neutralna łatka przez pełny rebuild, oczekiwany `NULL`) | średni |
| A5 | pole `reward` = efekt − 1 przy `CONFIRMED`, ramiona RSI-F porównywane geomeanem | średni |
| A6 | pole karty `guards` (np. `qwen-plain`, pp4096, `lfm`): żaden strażnik z całym CI < −MDE | średni |
| A8 | audyt promptów Implementera | wysoki |
| A9 | worktree Implementera bez historii i bez dostępu do łatek/wiki/research | wysoki przed P2 |
| A10 | sieć odcięta (`bwrap --unshare-net`), wyłączone serwerowe narzędzia API | średni |
| A11 | plik z pozostałym czasem, „land early” | niski |
| A12 | pula sealed 40 promptów, 10 losowanych per `verify` z seedem w ledgerze | niski |

Schemat karty: `guards`, `spec.acceptance_floor_pct`, `task_ref` (bench, task, `oracle_effect_pct`), `seed` (wpisywany przez weryfikator); wiersz `verdict` dostaje `reward`, `recovery`, `void_reason`.

## Powiązane
- [[metody/_hub|Metody]]
- [[fabryka-v1]]
- [[petla-rsi-f]]
- [[raport-21i-rsi-inference-bench]]
