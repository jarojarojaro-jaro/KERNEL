---
typ: lekcja
tags: [lekcje, rdna3, chlodzenie]
aktualizacja: 2026-10-19
zrodlo: ~/qwen-opt/tools/fan.sh:6-7,22-45; /proc/cmdline; komunikat Main do WikiIngest 2026-10-18; ~/qwen-opt/tools/fan.sh:1-40,66-90; /etc/systemd/system/xtx-fan.timer; komunikat Main do WikiIngest 2026-10-18 (wentylator, Chrome); komunikat Main do WikiIngest 2026-10-19 (decyzja użytkownika 00:00 UTC); ~/KERNEL/product/research/17-gpu-page-fault.md:55-56
status: aktualne
---
# Wentylator RDNA3: PWM odrzucony, krzywa tylko przez overdrive

**Na 7900 XTX sterownik amdgpu (SMU13) odrzuca bezpośredni zapis `pwm1`; jedyna droga to krzywa `gpu_od/fan_ctrl/fan_curve`, dostępna dopiero po włączeniu overdrive parametrem jądra `amdgpu.ppfeaturemask=0xfff7ffff` i restarcie (2026-10-18). Fabryczna krzywa trzymała 44% przy junction 86–87 °C i pamięci 89–90 °C.**

- Krzywa ma 5 punktów (temperatura hotspot → %), zapis `c` zatwierdza, `r` przywraca; ustawienie znika po restarcie i po resecie GPU – dlatego timer systemd zamiast ręcznego `fan.sh max`.
- Zero-RPM: w spoczynku poniżej progu `fan1_input` pokazuje 0 RPM – to nie awaria.
- Restart czyści `/tmp` ([[lekcja-tmp-po-restarcie]]).

**Przyczyny awarii 2026-10-18:** o 23:25 mode1 reset GPU (awaria taśmy PM4, nie kolizja blokad – raport 17, [[2026-10-19-page-faulty-gpu-analiza]]) wyzerował krzywą overdrive; potem zapis `acoustic_target` po krzywej przełączył SMU13 w tryb akustyczny (tryby krzywa / akustyczny / temperatura docelowa wykluczają się, wygrywa ostatni commit) – wentylator stał na ~1800 RPM przy pamięci 88–90 °C. Naprawa: `fan.sh` pisze tylko krzywą, timer `xtx-fan.timer` (root) co 30 s śledzi `gpu_busy_percent` i wykrywa wyzerowaną krzywą. Weryfikacja: busy 99% → 3320–3500 RPM w 12 s, hotspot 73 °C, pamięć 74 °C.

Od 2026-10-19 przy pracy GPU krzywa 100% (`FAN=100`, decyzja użytkownika: [[2026-10-19-wentylator-100-przy-pracy]]).

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[rx-7900-xtx]]
- [[lekcja-losowe-spowolnienia]]
- [[2026-10-09-limit-mocy-odlozony]]
