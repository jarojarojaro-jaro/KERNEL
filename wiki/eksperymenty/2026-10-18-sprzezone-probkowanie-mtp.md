---
typ: eksperyment
tags: [eksperymenty, spekulacja, sampler, mtp]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/16k-sprzezone-probkowanie.md:6-24,76-170; ~/qwen-opt/coupled/logs/, ~/qwen-opt/coupled/logs5/, ~/qwen-opt/coupled/test-coupled-sampling-200k.txt
status: do-sprawdzenia
---
# 2026-10-18: E-X4 – sprzężone próbkowanie draftu MTP na XTX (nierozstrzygnięte)

**Mechanizm Magnitude przeniesiony do forka (`LLAMA_SPEC_COUPLED`, gałąź `opt-coupled`, `760ee6990` + `3f25fc204`) jest bezstratny i poprawny, ale zysk na Qwen MTP przy T=1 to szacunkowo +0…+3.6% t/s – próg kill +2% nierozstrzygnięty, bo A/B przerwały resety GPU; decyzja: nie włączać domyślnie.**

Poprawność: CPU 200k losowań (chi² p > 1e-4), spekulacja == plain 0/20 000 różnic; `test-backend-ops GUMBEL_MAX` 152/152; greedy md5 `c4708318` / `6f14e814` bez zmian (przy T=0 sprzężenie się nie włącza).

Run 3 (12 bloków ABBA, seedy 1–3, tryb 0 off / 1 sprzężony / 2 kontrola = sprzężony cel + draft greedy):

| T | tryb | t/s | tok/krok | ms/krok |
|---|---|---|---|---|
| 1.0 | 0 / 1 / 2 | 107.7 / 114.2 / 116.1 | 3.00 / 3.16 / 3.11 | 28.12 / 28.57 / 28.16 |
| 0.7 | 0 / 1 / 2 | 112.7 / 118.3 / 117.8 | 3.11 / 3.19 / 3.11 | 28.18 / 28.61 / 28.15 |

Czysty efekt (1 vs 2): tok/krok +1.6% (T=1) / +2.6% (T=0.7), koszt +1.5% ms/krok → netto +0.2%. Kontrola sama dała +7.8% t/s względem off – to szum innego strumienia RNG ([[lekcja-ustalony-seed-to-nie-powtorzenie]]). Test identyczności (160 tekstów): akceptacja 0.377 → 0.404, tok/krok +4.0%. Run 5 (20 seedów, szybszy kernel `3f25fc204`): tryb 1 vs 0 +4.4% t/s, +3.8% tok/krok, +0.4% ms/krok – jeden blok, bez kontroli.

Przerwane: 7 bloków skończyło się page faultem SQC @0 i resetem GPU, także w trybie 0 ([[pm4-replay]]); build wstrzymany na GPU ([[2026-10-19-bezpieczenstwo-sprzetu]]). Dokończenie: 20–40 seedów, tryby 0/1/2, `LLAMA_SPEC_COUPLED_DT` 1.3.

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[sprzezone-probkowanie-draftu]]
- [[gumbel-max]]
- [[raport-16k-sprzezone-probkowanie]]
- [[2026-10-15-sampler]]
