---
typ: decyzja
tags: [decyzje, rx-7900-xtx, chlodzenie]
aktualizacja: 2026-10-19
zrodlo: komunikat Main do WikiIngest 2026-10-19 (decyzja użytkownika 00:00 UTC); ~/qwen-opt/tools/fan.sh:5-6,16; /sys/class/drm/card0/device/gpu_od/fan_ctrl/fan_curve (odczyt 2026-10-19)
status: aktualne
---
# 2026-10-19: wentylator XTX 100%, gdy GPU pracuje

**Użytkownik zdecydował (2026-10-19, 00:00 UTC): gdy GPU pracuje, wentylator RX 7900 XTX chodzi na 100% (`FAN=100` w `fan.sh`, wcześniej 90%).**

Weryfikacja: krzywa 100% we wszystkich 5 punktach, busy 95% → 3426 RPM (Main); odczyt WikiIngest przy busy 99%: 3432 RPM. Bezczynność bez zmian: 40% poniżej 50 °C, 100% od 50 °C.

Omówione wady: tylko hałas, nieco szybsze zużycie łożyska wentylatora i kilka W mocy; brak ryzyka dla GPU.

## Powiązane
- [[decyzje/_hub|Decyzje]]
- [[rx-7900-xtx]]
- [[lekcja-wentylator-rdna3]]
- [[2026-10-09-limit-mocy-odlozony]]
