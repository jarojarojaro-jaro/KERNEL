---
typ: eksperyment
tags: [eksperymenty, lfm, pm4]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:372-379; ~/KERNEL/qwen-opt/research/lfm-decode-round4.md:6-14,101-127
status: aktualne
---
# 2026-10-14: runda 4 — replay PM4 (0060–0064)

**Odtwarzanie grafu dekodowania jako bufora PM4 skróciło granicę kernela z ~2.75 do ~0.5–0.9 µs: LFM 259.3 → 293.6 t/s, Qwen MTP 103.7 → 108.8 t/s, bitowo identycznie.**

Wynik (gałąź `opt-lfm4` e41c2330e vs `~/llama-opt` 9d493cf6e, przeplatane). Uwaga: NOTES podaje dla Qwena 103.7 → 108.8 t/s (29.16 → 27.80 ms/krok, 2 rundy), raport rundy 4 — 1 rundę 101.72 → 108.82 (tabela niżej):

| pomiar | przed | po |
|---|---|---|
| llama-bench tg128, KV q8_0, głębokość 0 | 258.48 t/s | 294.84 t/s |
| to samo, głębokość 98304 | 193.40 t/s | 212.95 t/s |
| spec_sweep `lfm none` 6×3, T=1 | 259.31 / 259.13 t/s | 293.75 / 293.43 t/s |
| spec_sweep `qwen mtp` 6×3, T=1 | 101.72 t/s, 29.218 ms/krok | 108.82 t/s, 27.812 ms/krok |
| LFM Uncensored tg128 (0064) | 3.933 ms/token | 3.706 ms/token |

Łatki: 0060 `GGML_HIP_PM4` (3.887 → 3.424 ms/token), 0061 `GGML_HIP_PM4_DEBUG`, 0062 `GGML_HIP_CONV_ROWS4` (3.458 → 3.402 ms, znika rozrzut per proces), 0063 przełączniki przez `ggml_cuda_env_switch`, 0064 `GGML_HIP_MMVQ_N1_Q8_0`.

Bezpieczeństwo: 20 przebiegów testu, soak `pm4_soak.py` (~4 min na model) bez zawieszeń; greedy md5 i hashe logitów bez zmian.

Odkrycia przy okazji: determinizm w obrębie serwera nie istnieje (2. wywołanie rozjeżdża się po ~270 znakach, upstream też); spowolnienie per proces wywołują siatki dokładnie 3072 bloków (pełna pojemność fal).

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[pm4-replay]]
- [[mikrobench-granicy-kernela]]
- [[2026-10-15-sampler]]
- [[determinizm-fma]]
