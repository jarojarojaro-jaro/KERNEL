---
typ: metoda
tags: [metody, benchmarki, fabryka]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21i-rsi-inference-bench.md:276-350
status: do-sprawdzenia
---
# `aob-v1` (AMD-Opt Bench): benchmark regresji RSI-F z naszej historii (projekt)

**Własny benchmark w formacie Harbor-lite (`task.toml`, `instruction.md`, `environment/`, ukryte `tests/`, `solution/oracle.patch` + `null.patch`) z fabryką jako weryfikatorem i podziałem dev (łatki 0001–0047) / test (0048–0070 + negatywy); przy naszym budżecie GPU to test regresji i postępu RSI-F, nie leaderboard – przy 10 zadaniach SE ≈ 0.15 (raport 21i, 2026-10-19).**

Ocena: CPU tier zawsze (build HIP i CUDA, reguły statyczne, testy hosta, ISA offline), GPU tier tylko po CPU (`factory verify` z kartą generowaną przez `tests/`); `opt`/`port`: `reward = max(0, r − 1)` przy `CONFIRMED` i `recovery = (r−1)/(oracle−1)` (> 2 → `NEEDS-HUMAN`); `fix`: binarna + f2p; `neg`: trafność go/kill + jakość oszacowania.

| zadanie | rodzaj | wyrocznia | GPU |
|---|---|---|---|
| T1 `opt_mmq_epilogue` | opt, test | 0070: pp4096 1099.5 → 1123.2 t/s (+2.2%) | ~15 min |
| T2 `fix_q8_1_overflow` | fix, dev | 0023 clamp q8_1 | ~10 min |
| T3 `opt_sampler_slow_path` | opt (host), test | 0065–0069: LFM przez omp 254.2 → 294.3 t/s | ~20 min |
| T4 `neg_pm4_pdl_ceiling` | neg, tylko CPU | 16a: kill (X1 −0.11 µs, X2 realnie ~+3%) | 0 |
| T5 `fix_mtp_embd_state_rebase` | fix, test | crash `embd_state` po rebase v0.7.0 | ~45 min |

Pełny przebieg ~90 min GPU na agenta i próbę + sonda `null.patch` ~15 min `[SZACUNEK]`. Pierwszy krok tylko CPU: T4 i części CPU T2/T3 z Implementerem RSI-F z `skills/` i bez. Zastrzeżenia: kontaminacja (łatki w `qwen-opt/patches`, 0018 jest w upstreamie) – potrzebne A9/A10; żadne zadanie nie włącza PM4.

## Powiązane
- [[metody/_hub|Metody]]
- [[zmiany-fabryki-z-21i]]
- [[seria-amd-opt]]
- [[2026-10-19-plan-retro-rsr-0070]]
