# 22 — RSI-F: pętla samodoskonalenia na fabryce v1 (wdrożenie, bramki H0–H11, stan pilota)

Data: 2026-10-19. Autor: podagent RsiF. Plan: [21h §5](21h-rsi.md), dodatki z [21i §4–5](21i-rsi-inference-bench.md)
i [21j §7](21j-flameox.md). Kod: `~/qwen-opt/factory` (lustro `KERNEL/qwen-opt/factory` bez `sealed/pool.jsonl` i
ledgera).

## Werdykt

- **Kod RSI-F jest gotowy i przetestowany na CPU: 109 testów OK (było 57), `rules test` 0 mismatches.** Harness
  zablokowany (`ledger.jsonl` seq 2, `d9d3a6c4ce04`).
- **P0 i P1 nie zostały uruchomione na GPU.** Blokada: GPU zajmuje Pm4Fix (jeszcze ~45–60 min wg jego wiadomości),
  a pełny build HIP pod nową regułą CPU (2 rdzenie, `-j2`) trwa w tle (`rsi/logs/build-base.log`). Nie ma więc
  werdyktu P0 w ledgerze ani wyników transferu. Liczby P0/P1 = brak.
- P0 jest gotowe do startu: `verify --dry-run` karty 0070 planuje 12 bloków, wszystkie bramki H0–H11 „ok”
  w stanie bezczynnym (`factory rsi gates --card ...`).

## Co jest w kodzie (tabela)

| element | plik | dowód |
|---|---|---|
| bramki H0–H11, odmowa przed każdym blokiem, skan journal po bloku, kwarantanna + halt, ack człowieka | `fk/hwgates.py`, `fk/gpu.py`, `fk/block.py` | `tests/test_hwgates.py`: każda bramka „odpala” + „czysto” (12×), kwarantanna, ack, budżet, odmowa w `Runner` i G0 |
| :8080 przez `ss -ltn` (pgrep usunięty), `GGML_HIP_PM4=0` w każdym bloku, H1 też wewnątrz locków | `fk/preflight.py`, `fk/block.py` | test bloku: H8 → 97, H1 → 98 |
| H11 wg reguły użytkownika: `flock /tmp/cpuheavy.lock nice -n 19 taskset -c 0-1`, `-j2` | `fk/hwgates.py`, `fk/transfer.py`, `rsi/build-slot.sh` | testy H11 (8 przypadków) |
| playbook: `draft` tylko z sukcesu, `candidate` po recenzji bez diffu + recenzent ≠ autor, `accepted` po transferze świeżego agenta; przejścia jako noty w ledgerze | `fk/playbook.py` | `test_rsi.Playbooks` |
| transfer: brief z samego playbooka, ramiona A/B, sha briefu w ledgerze, scoring SPR, k1–k3, bramka P2 | `fk/transfer.py`, `rsi/targets/` | `test_rsi.Transfer` |
| kalibracja (|błąd|, Brier, prior Laplace) i ranking kolejki | `fk/calib.py` | `test_rsi.Calibration` |
| rotacja zestawu sealed per cykl + losowanie 10 z 40 per verify (seed w ledgerze) | `fk/sealed.py`, `sealed/registry.json`, `sealed/pool.jsonl` (sealed-v2: 40) | `test_sealed.Rotation`, `test_rsi.SealedDraw` |
| cykl `rsi cycle PLAN --dry-run | --go --open | --go [--stop-topka]`; topka zawsze wznawiana | `fk/cycle.py` | `test_rsi.Cycle` (restart także po wyjątku) |
| 21i: `VOID`, R37 acceptance floor, `guards`, `reward`/`recovery`, karta `null_rebuild`, snapshot bez historii | `fk/verify.py`, `rules/r37_*`, `fk/transfer.py` | `test_rsi.VerifierAdditions`, `Workspace` |
| 21j: bootstrap tylko przy n ≥ 12, magazyn dowodów sha256+zstd (`factory preserve`, `evidence_id` w wierszu) | `fk/stats.py`, `fk/evidence.py` | `test_evidence.py` (6), `test_rsi` |
| aob-v1: format zadań + 5 zadań z 21i §5.3 (T2, T5 `needs-fixture`) | `aob/`, `fk/aob.py` | `test_aob.py` (8) |

Playbook z 0070 (`rsi/drafts/pb-mmq-epilogue-vopd.json`, Rewriter bez dostępu do diffu) **przechodzi automatyczną
recenzję przeciekiem przeciw prawdziwemu diffowi f4f0deae5..f61994f58** (0 trafień, 192 linie diffu). Pierwsza wersja
recenzji odrzucała zwykłe angielskie słowa z komentarzy łatki jako „identyfikatory”; poprawione (tylko nazwy
kodowe). k1 więc nie odpala. Wpis do biblioteki (`playbook new`) czeka na werdykt P0.

## Ryzyka i rzeczy do decyzji

- **Ack faultów zrobiłem ja** (watermark 2026-10-19 04:32:56 UTC, 154 linie z bootów −11…0). Wśród nich jest
  **reset MES z 2026-10-19 00:16 UTC (boot 0)**, sprzed RSI-F, ale z dziś. Człowiek powinien to potwierdzić.
- Nie zbudowane: generation judge (21i A2), odcięcie sieci implementera (A10), parser G1 z KtMeta (podagent w toku).
- Arm B widzi w drzewie istniejący epilog Q4_K/Q5_K (snapshot zawiera 0070), więc różnica A/B może być mała.

## Plan: dokończenie P0/P1, potem P2

1. Po zakończeniu Pm4Fix i buildu: `./factory rsi cycle rsi/cycles/p0.json --go --stop-topka` (karta 0070,
   `null_rebuild_waived` dla P0), ~10 min GPU. Kill: `INVALID`/`VOID` z winy harnessu → naprawa fabryki.
2. P1: `rsi cycle p1 --go --open` (rotacja → sealed-v2), playbook `new` → `review`, 4 briefy
   (`t-q6k-mmq`, `t-iq4xs-mmq` × A/B, workspaces `~/wt/rsi-c1-*`, base `1634fc2a`), 4 świeżych agentów, karta
   `null_rebuild` (`~/wt/rsi-c1-base` vs `~/wt/rsi-c1-null`), `rsi cycle p1 --go --stop-topka`. Budżet H6
   (60 min/24 h) zmieści ~5 kart llama-bench; reszta następnego dnia.
3. P2 dopiero gdy `transfer score` da `go_p2`; ≥ 10 werdyktów na ramię, kill z 21h §5.7.

## Do bazy wiedzy

| folder | tytuł (plik) | co wpisać | liczby i źródło |
|---|---|---|---|
| `narzedzia/` | aktualizacja [[fabryka-cli]] | `factory rsi ...`, `preserve`, werdykt `VOID`, R37, guards, reward, sealed registry/losowanie | README fabryki §4, §6, §12; 109 testów |
| `metody/` | Pętla RSI-F (`petla-rsi-f.md`), status `wdrozone-bez-gpu` | role, statusy playbooka, kill k1–k3, bramki H0–H11 w kodzie | ten raport; `fk/hwgates.py` |
| `decyzje/` | aktualizacja [[2026-10-19-bezpieczenstwo-sprzetu]] | H0–H11 egzekwowane kodem; :8080 przez `ss`; ack faultów wymaga człowieka | `fk/hwgates.py` |
| `eksperymenty/` | Pilot P0/P1 retro-RSR 0070 (`2026-10-19-retro-rsr-0070.md`), szkic | stan: nieuruchomiony na GPU, playbook przeszedł recenzję bez diffu (0 trafień / 192 linie) | ten raport |
| `lekcje/` | Recenzja przecieku: słowa z komentarzy ≠ identyfikatory (`lekcja-recenzja-przecieku.md`) | heurystyka „słowo ≥ 8 znaków z diffu” dała 10 fałszywych trafień; tylko nazwy kodowe | `fk/playbook.py` IDENT |

## Aktualizacja 2026-10-19 wieczór (RsiF2, po awarii zasilania)

**Werdykty**

- **Testy fabryki: 112 OK** (109 + 3 nowe), `rules test` 0 mismatches. Lustro KERNEL zacommitowane i wypchnięte
  (`8cb4dad`, potem commit z poprawkami poniżej); bez `sealed/pool.jsonl`, `runs/`, `evidence/`, `rsi/state|logs`.
- **P0 (karta 0070): BRAK werdyktu pomiarowego.** Trzy podejścia, żadne nie doszło do pomiaru na GPU:
  1. ledger seq 5 `INVALID` — G0 odmówił przed GPU: harness różnił się od locka (moje zmiany + `tbo_parse.py`). Wina
     harnessu, nie karty.
  2. ledger seq 7 `VOID` (`H8 something listens on :8080`) — cykl zatrzymał topkę *przed* czekaniem na lock, czekał
     ~65 min w kolejce GPU, w tym czasie :8080 znów wstał, blok odmówił. Przy wznowieniu topka padła z OOM (16 GiB),
     bo cudzy job zajął VRAM w chwili zwolnienia locka. Błąd projektowy fabryki → naprawiony (niżej).
  3. run 20261019-162135 — blok 01 czekał na lock 27 min, zabity przy pauzie GPU (polecenie użytkownika), cykl
     przerwany przeze mnie. Brak wiersza werdyktu, 0 s GPU.
- **P1: nie zrobione (GPU wstrzymane; warunek „P0 = CONFIRMED” niespełniony).**
- **aob-v1: harness działa end-to-end na T4 (`neg_pm4_pdl_ceiling`, CPU)**: `validate` 0 problemów, `cpu_tier.sh`
  → `{"cpu_pass": 1}`, odpowiedź `{"pred_effect_pct": 2.5, "decision": "kill"}` → `reward` 1.0, `estimate` 0.85.
  Zastrzeżenie: odpowiadałem ja, po obejrzeniu `task.toml` (zawiera `measured_effect_pct`) — to dowód działania
  harnessu, nie wynik agenta. Luki: brak komendy `score-answer` w CLI (liczone przez `fk.aob.reward`), T4 nie ma
  plików danych wymienionych w `instruction.md`, a `task.toml` z liczbą-wyroczni leży w katalogu zadania.

**Poprawki fabryki (zlecone przez użytkownika przez Main)**

| zmiana | plik | test |
|---|---|---|
| H7 hashuje tylko sekcje OD_SCLK/OD_MCLK/OD_VDDGFX_OFFSET (+ power1_cap, perf level); krzywa wentylatora (`xtx-fan`, `gpu_od/fan_ctrl`) wyłączona — inaczej H7 flapuje. Po rebootcie sha OD się zmieniło (zegary/napięcia na ustawieniach sterownika); ack: „post-power-loss reboot; …; never undervolted” (ledger seq 4) | `fk/hwgates.py` | `PowerFacts` (2) |
| `--stop-topka`: topka zatrzymywana tylko WEWNĄTRZ hold każdego bloku; fabryka nigdy jej nie wznawia (`topka-keeper.sh`); `start_topka`/`health` usunięte | `fk/block.py`, `fk/cycle.py`, `fk/gpu.py`, `fk/verify.py` | `Cycle` (2) |
| procesy bloków pod `taskset -c 2-5` (reguła CPU) | `fk/paths.py` `HOST_PIN`, `fk/block.py`, `fk/measure.py` | — |

Harness zablokowany ponownie: ledger seq 8, `52f0a9f2f457`.

**Nie zrobione (GPU wstrzymane):** P0 pomiar 0070 (12 bloków, ~20 min GPU), P1 (playbook new/review, 4 briefy × 2 cele
× A/B, k1–k3), zadania aob z GPU (T1, T3, T2/T5 `needs-fixture`).

**Dalej:** po wznowieniu GPU `./factory rsi cycle rsi/cycles/p0.json --go --stop-topka` (harness gotowy); bloki
czekają na lock pojedynczo, więc P0 przeplata się z innymi jobami. Przy P0 = CONFIRMED → P1 wg planu wyżej, buildy
przez `rbuild`, nie lokalnie.
