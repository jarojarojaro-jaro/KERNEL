---
typ: eksperyment
tags: [eksperymenty, termika, rx-7900-xtx, eco]
aktualizacja: 2026-11-06
zrodlo: ~/qwen-opt/thermal/quick-20261106.txt; ~/qwen-opt/thermal/quick-20261106.csv
status: aktualne
---
# Szybki bench produkcji: eco 2200 vs stock (2026-11-06)

**Na serwerze czatu użytkownika (Qwen3.8-27B-Uncensored Q4_K_M, topka-q63, ctx 204800, cache-ram 40 GB) eco 2200 MHz kosztuje ok. 2% pisania i 10–12% prefillu za −35 W i −6 °C hotspot; greedy md5 identyczne.**

ABA (eco → stock → eco), 224 s, bez rozgrzewki 6 min (krótkie ramiona):

| metryka | stock | eco 2200 (A / B) | zmiana |
|---|---|---|---|
| spec_sweep T=1 ms/krok | 26,32 | 26,86 / 26,83 | +2,0% (wolniej) |
| spec_sweep T=1 mediana t/s | 120,2 | 120,1 / 117,9 | szum próbkowania T=1 |
| greedy 256 tok. t/s | 108,4 | 106,2 / 106,4 | −2,0% |
| prefill 11 962 tok. t/s | 1036,8 | 916,0 / 932,0 | −11,0% |
| waty (wiersze > 150 W) | 280 | 245 | −12,5% |
| hotspot °C | 67,9 | 61,8 | −6,1 |
| VRAM °C | 69,8 | 70,2 | 0 |
| greedy md5 | 0221afd9 | 0221afd9 | identyczne |

Mediana t/s przy T=1 skacze z akceptacją draftu (tok/krok 3,11–3,48), więc porównanie opiera się na ms/krok i greedy t/s. Zgodne z [[2026-11-06-eco-sweep-sclk]].

## Powiązane
- [[eksperymenty/_hub|eksperymenty]]
- [[2026-11-06-profil-eco-2200]]
- [[2026-11-06-eco-sweep-sclk]]
- [[rx-7900-xtx]]
