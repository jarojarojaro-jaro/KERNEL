---
typ: lekcja
tags: [lekcje, statystyka, pomiar]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21j-flameox.md:171-187; ~/qwen-opt/research-src/flameox-demo/fx_cov.py; ~/qwen-opt/research-src/flameox-demo/exp.json
status: aktualne
---
# Percentile bootstrap przy małym n kłamie

**Symulacja przy prawdziwej H0 (1500 prób na n, N(0,1)): 95% CI z percentile bootstrap wyklucza 0 przy n = 5 w 17.8% przypadków dla średniej i 7.4% dla mediany, a Student t w 5.5%; przy n = 4 bootstrap średniej 19.7%, dopiero od n ≈ 12 zbliża się do 5% (raport 21j, 2026-10-19).**

| n | bootstrap mediana | bootstrap średnia | Student t |
|---|---|---|---|
| 4 | 12.3% | 19.7% | 5.1% |
| 5 | 7.4% | 17.8% | 5.5% |
| 8 | 7.9% | 11.6% | 4.8% |
| 12 | 5.7% | 7.7% | 4.3% |

Reguła: przy n < 12 par (typowe 2–4 rundy ABBA) liczyć CI Studentem t; fabryka domyślnie używa `t` (`fk/stats.py`), więc strażnik P1 ma chronić przed regresją, nie naprawiać błędu. Przykład z życia: A/A flameoxa z CI [0.58, 29.80] ms dla identycznych programów.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[pomiar-abba]]
- [[lekcja-szum-t-s-przy-t1]]
- [[fabryka-cli]]
