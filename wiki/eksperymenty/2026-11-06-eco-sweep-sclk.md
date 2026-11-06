---
typ: eksperyment
tags: [eksperymenty, termika, rx-7900-xtx, eco]
aktualizacja: 2026-11-06
zrodlo: ~/qwen-opt/thermal/run-20261106T1221/results.csv; ~/qwen-opt/thermal/bugcheck-20261106T1216/result.txt; ~/qwen-opt/thermal/sweep.sh
status: aktualne
---
# Sweep eco: limit taktowania rdzenia XTX (2026-11-06)

**Limit max sclk przy niezmienionym napięciu (offset 0 mV), pamięci i limicie mocy 285 W: 2000 MHz daje −4,1% pisania za −16% watów i −12 °C hotspot; md5 identyczne we wszystkich ramionach.**

Warunki: Qwen3.8-27B UD-Q4_K_XL, topka-q63, ctx 204800, spec_sweep T=1 seedy 1,2; prefill 11 962 tok.; 6 min soak na ramię; wentylator 100% (3480–3500 RPM); ABBA `stock 2400 2200 2000 1800 2000 2400 stock` 12:21–13:2x UTC. Bugcheck (błąd OD z [[lekcja-od-commit-gubi-krzywa]]) PASS 12:21.

| limit | MHz | pisanie t/s | prefill t/s | W pisanie | hotspot °C | VRAM °C | J/token |
|---|---|---|---|---|---|---|---|
| stock (śr. 2 ramion) | 2369 | 123,6 | 1030 | 280,5 | 68,9 | 74,7 | 2,27 |
| 2200 | 2210 | 121,3 (−1,9%) | 940 (−8,8%) | 251 (−10,5%) | 61,5 | 72,2 | 2,07 (−8,8%) |
| 2000 (śr. 2) | 1974 | 118,5 (−4,1%) | 869 (−15,7%) | 235 (−16,2%) | 56,7 | 71,8 | 1,98 (−12,8%) |
| 1800 | 1816 | 114,8 (−7,1%) | 791 (−23,3%) | 222 (−20,9%) | 54,6 | 70,3 | 1,93 (−15,0%) |

Powtórki 2000/2400/stock zgodne co do 0,1 t/s. 2400 = kontrola (≈ stock). Drugą serię z 1600 MHz przerwano na polecenie użytkownika (13:29, „200 W to już za mało”) – bez wyników.

Do decyzji: profil eco 2100–2200 MHz (cel użytkownika: −15% za −3%). Limit leży w `/run`, restart wraca do stock.

## Powiązane
- [[eksperymenty/_hub|eksperymenty]]
- [[2026-11-06-xtx-eco-instalacja]]
- [[raport-64-termika]]
- [[rx-7900-xtx]]
- [[amdgpu-moc-i-termika]]
