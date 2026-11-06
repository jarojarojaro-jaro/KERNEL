---
typ: lekcja
tags: [lekcje, termika, amdgpu, wentylator]
aktualizacja: 2026-11-05
zrodlo: ~/KERNEL/product/research/64-termika-bezpieczenstwo.md:17-25,161-173; https://github.com/torvalds/linux/commit/6027db7db773714f2e05df82093276f2a52a1fba; https://github.com/torvalds/linux/commit/44d0d3031e47973ed65fd327669d5e2eaaf6c565
status: aktualne
---
# Jądro 6.8: commit OD sclk po cichu zrzuca krzywą wentylatora (i odwrotnie)

**Na SMU 13.0.0 (Navi31) zegary, krzywa wentylatora i PPT to jedna tablica `OverDriveTable_t`; PMFW traktuje maskę `FeatureCtrlMask` jako pełną listę nadpisań, więc commit samego `s 1 X` przywraca fabryczny wentylator, a commit samej krzywej zdejmuje limit zegara (raport 64, 2026-11-05).**

- Sysfs kłamie: `fan_curve` dalej pokazuje 100%, `OD_SCLK` dalej limit (cache sterownika). Prawdę pokazują tylko `pwm1` i obroty.
- Potwierdzone przez AMD: commity [6027db7db773](https://github.com/torvalds/linux/commit/6027db7db773714f2e05df82093276f2a52a1fba) („preserve committed OD features for SMU 13.0.0/13.0.7”, drm/amd#3625) i [44d0d3031e47](https://github.com/torvalds/linux/commit/44d0d3031e47973ed65fd327669d5e2eaaf6c565); poprawka dopiero w v7.4-rc1, brak w Ubuntu 6.8.0-138 i -149.
- Reguła: jeden proces pisze OD; każdy commit niesie krzywą **i** limit; po commicie weryfikacja fizyczna (RPM/PWM), nie odczyt sysfs.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-wentylator-rdna3]]
- [[lekcja-agent-nie-patrzyl-na-temperatury]]
- [[raport-64-termika]]
- [[amdgpu-moc-i-termika]]
