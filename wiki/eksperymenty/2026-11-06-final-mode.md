---
typ: eksperyment
tags: [eksperymenty, termika, kontekst, rx-7900-xtx, eco]
aktualizacja: 2026-11-06
zrodlo: ~/qwen-opt/thermal/final-unc.csv; ~/qwen-opt/thermal/quick-20261106.txt; ~/qwen-opt/queue/logs/ctx-262144.log; ~/qwen-opt/queue/logs/final-qwen-262144.log
status: aktualne
---
# Final mode: eco 2200 MHz + kontekst 262 144 (2026-11-06)

**Tryb docelowy czatu (Qwen3.8-27B-Uncensored): +28% kontekstu (262 144), −14% watów i −4 °C hotspot za −1,8% pisania; odpowiedzi greedy bitowo te same.**

Decyzja użytkownika 2026-11-06 ~18:00 UTC: eco jest trybem finalnym, rekordy liczymy w nim ([[REKORDY]]). Profil `qwen` (UD-Q4_K_XL, rekordy historyczne) pominięty na razie na prośbę użytkownika.

| Uncensored | stock, ctx 204 800 | final (eco 2200, ctx 262 144) | zmiana |
|---|---|---|---|
| ms/krok spec_sweep T=1 | 26,32 | 26,91 | +2,2% |
| mediana T=1 t/s | 120,2 | 118,3 | w szumie T=1 |
| greedy 256 tok. t/s | 108,4 | 106,4 | −1,8% |
| prefill 12k t/s | 1036,8 | 914,9 | −11,8% |
| waty (> 150 W) | 280 | 241 | −13,9% |
| hotspot / VRAM °C | 67,9 / 69,8 | 63,5 / 72,8 | −4,4 / +3,0 |
| md5 greedy | 0221afd9 | 0221afd9 | identyczne |

Przy 255k: prefill 465 t/s, decode 78,7 t/s ([[2026-11-06-ctx-262k-fit]]). UD-Q4_K_XL przy 262 144 mieści się, ale zapas tylko 336 MiB (szczyt 24 224 MiB), więc nie wdrożony. Stock: krótkie ramiona ([[2026-11-06-eco-szybki-bench]]); final: 84 s pomiaru.

## Powiązane
- [[eksperymenty/_hub|eksperymenty]]
- [[2026-11-06-profil-eco-2200]]
- [[2026-11-06-eco-sweep-sclk]]
- [[qwen3-8-27b]]
