---
typ: eksperyment
tags: [eksperymenty, lfm, atencja]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:362-370; ~/KERNEL/qwen-opt/research/lfm-decode-round3.md
status: aktualne
---
# 2026-10-14: LFM runda 3 (0055–0059)

**Kernel `kvq` dla KV q8_0 (jedyna zmiana numeryki, przyjęta po bramce KLD) plus trzy fuzje bitowe i zbiorczy upload: LFM przy 98k 152.4 → 191.4 t/s (+25.6%), przy 0 241.1 → 262.1.**

| łatka | zmiana | ms/token |
|---|---|---|
| 0055 `GGML_HIP_KVQ_Q8` | `kvq` czyta KV q8_0 (head dim 64/128) | 0: 4.121 → 4.099; 32k: 4.875 → 4.526; 98k: 6.561 → 5.462 |
| 0056 `GGML_HIP_GATE_UP_Q8` | gate+up pisze q8_1 dla down | 4.070 → 3.973 |
| 0057 `GGML_HIP_ATTN_PREP` | wejście atencji jednym kernelem zamiast pięciu | 4.043 → 3.907 |
| 0058 `GGML_HIP_KVQ_FWHT` | FWHT wyjścia + q8_1 w combine | 3.928 → 3.879 |
| 0059 `GGML_HIP_INPUT_BATCH` | 12 uploadów wejść → 1 H2D + kernel rozrzucający | 3.840 → 3.806 |

KLD 0055 vs f16 KV (wikitext-2, 3 × 16k, ub 1): stary kernel q8_0 0.044171 (same top 92.25%), nowy 0.044196 (92.35%) — przyjęty; q4_0 dla porównania 0.128 (85.2%).

Wynik (KV q8_0, przeplatane z 5909da1f1): llama-bench 0: 241.1 → 262.1, 32k: 205.4 → 231.0, 98k: 152.4 → 191.4 t/s; serwer 237–243 → 251–252 t/s; 416 → 305 kerneli/token; Qwen bez zmian. Greedy LFM z nowym kernelem atencji 894e56e4 (oczekiwana zmiana).

Nie wyszło: norma następnej warstwy jako ogon kernela MoE down (13 → 56 µs), ładowania nontemporal gate+up (12.9 → 14.4 µs). Referencja f16 do KLD (6.3 GB): `~/wt/lfm3-prof`.

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[fattn-kvq]]
- [[attn-prep-fwht]]
- [[lfm-runda-4-pm4]]
- [[bramka-kld-kanarki]]
