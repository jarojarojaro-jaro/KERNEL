---
typ: lekcja
tags: [lekcje, landing, build, sciezki, enigma]
aktualizacja: 2026-11-08
zrodlo: app/landing/scripts/cards.ts:20-35; app/landing/scripts/sync-results.ts:16-25,56; git nvidia-2026-11
status: aktualne
---
# Build landingu czytał dane ze `$HOME`, więc klon repo się nie budował

**`app/landing` brał arkusz benchmarków i scorecardy z `~/KERNEL/...` i `~/qwen-opt/cloud/results`, więc `bun run build` w świeżym klonie (albo w CI) padał na `must('rtx-3090 nemotron')` — dane liczb są w repo, tylko skrypty ich tam nie szukały (2026-11-08).**

Poprawka: `dataFile()` w `scripts/cards.ts` liczy ścieżkę od roota repo (`REPO_ROOT` = trzy poziomy nad `app/landing`), a `homedir()` zostaje wyłącznie jako fallback dla serwera GPU, gdzie tych plików nie ma w klonie. Katalog `qwen-opt/cloud/results` istnieje w repo, ale bez scorecardów, więc o użyciu repo kopii decyduje predykat `hasScorecard` (co najmniej jeden `<karta>/scorecard.json`), nie samo `existsSync`. Etykiety `source`/`file:` w JSON-ach zostały bez zmian (`KERNEL/product/...`), więc metodologia na stronie się nie zmieniła. Kontrola: build w klonie z pustym `HOME` kończy się kodem 0, `cards.json` i `cloud-results.json` mają te same sha256 co przed zmianą (4321b3d6…, 004266ad…).

Reguła: skrypt builda strony nie może domyślnie czytać niczego spoza repo — dane, które są w gicie, mają być brane z gita, a `$HOME` tylko jako świadomy fallback z komentarzem.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[app-landing]]
- [[jak-przyspieszylismy-nvidia]]
- [[landing-qa]]
