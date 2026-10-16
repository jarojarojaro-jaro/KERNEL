---
typ: narzedzie
tags: [narzedzia, fabryka, pomiar, bramki]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/16h-fabryka-v1.md:1-60,61-80,176-205,253-262; `~/qwen-opt/factory/README.md`
status: aktualne
---
# Fabryka v1: CLI `factory`

**`~/qwen-opt/factory/` (Python stdlib, 2394 linie `fk/` + CLI, 36 reguł w 1141 liniach, 57 testów OK w 29.5 s na CPU) zamraża kartę twierdzenia przed pomiarem, mierzy kaskadą G0–G5 i zapisuje werdykt do `ledger.jsonl` z łańcuchem sha256; zbudowane 2026-10-16 bez GPU.**

Komendy: `card new/fill/check`, `register`, `verify [--dry-run|--fake]`, `ledger verify/show`, `report [--drafts]`, `rules list/test/backtest/text`, `sealed check/summary`, `harness status/lock`, `merge-check`.

Zasady dla agentów:
- **Implementer:** łatka za przełącznikiem → `card new` → `card fill` → `card check` → `register`; wolno `verify --dry-run`; nie wolno `verify` rzeczywistego, czytać `sealed/prompts.jsonl` ani edytować `factory/`, `greedy.sh`, `spec_sweep*`, `tools/`. Raportuje ścieżkę i sha256 karty, nie własne liczby.
- **Planista (Main):** `./factory verify <karta>` w oknie GPU (sam bierze locki, pauzy 45 s, bloki ≤ 290 s), do commita `ledger:<seq>/<sha8>`, przed scaleniem `merge-check`, do wiki `report --drafts`.
- **Zmiana harnessu:** osobny commit + `harness lock --reason`. Nowy incydent: fixture → reguła `rNN_*.py` → `rules test` → `harness lock`.

Stan: harness `4163856fa42e` (ledger seq 0), zestaw `sealed-v1` sha256 `1e6c3a4b…`; pierwsza karta `2026-10-17-mmq-epi-0070` (seq 1), `verify --dry-run` = 12 bloków, ok. 20 min GPU `[SZACUNEK]`. Nie walidowane na GPU.

## Powiązane
- [[narzedzia/_hub|Narzędzia]]
- [[fabryka-v1]]
- [[spec-sweep]]
- [[greedy-check]]
- [[2026-10-16-backtest-regul-fabryki]]
- [[raport-16h-fabryka-v1]]
