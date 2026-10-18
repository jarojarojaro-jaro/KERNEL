---
typ: lekcja
tags: [lekcje, rdna3, chlodzenie]
aktualizacja: 2026-10-18
zrodlo: ~/qwen-opt/tools/fan.sh:6-7,22-45; /proc/cmdline; komunikat Main do WikiIngest 2026-10-18
status: aktualne
---
# Wentylator RDNA3: PWM odrzucony, krzywa tylko przez overdrive

**Na 7900 XTX sterownik amdgpu (SMU13) odrzuca bezpośredni zapis `pwm1`; jedyna droga to krzywa `gpu_od/fan_ctrl/fan_curve`, dostępna dopiero po włączeniu overdrive parametrem jądra `amdgpu.ppfeaturemask=0xfff7ffff` i restarcie (2026-10-18). Fabryczna krzywa trzymała 44% przy junction 86–87 °C i pamięci 89–90 °C.**

- Krzywa ma 5 punktów (temperatura hotspot → %), zapis `c` zatwierdza, `r` przywraca; ustawienie znika po restarcie, więc `fan.sh max` (sudo) po każdym starcie.
- Zero-RPM: w spoczynku poniżej progu `fan1_input` pokazuje 0 RPM – to nie awaria.
- Restart czyści `/tmp` ([[lekcja-tmp-po-restarcie]]).

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[rx-7900-xtx]]
- [[lekcja-losowe-spowolnienia]]
- [[2026-10-09-limit-mocy-odlozony]]
