---
typ: research
tags: [research, termika, rx-7900-xtx, amdgpu]
aktualizacja: 2026-11-05
zrodlo: ~/KERNEL/product/research/64-termika-bezpieczenstwo.md:1-40,161-173
status: aktualne
---
# Raport 64: czy bezpiecznie obniżyć sclk na XTX

**Research tylko do odczytu (2026-11-05, Sapphire PULSE RX 7900 XTX, jądro 6.8.0-138, PMFW 78.130.0): sam limit `OD_SCLK` nie szkodzi karcie, ale na jądrze 6.8 commit OD gubi krzywą wentylatora i odwrotnie.**

Werdykt:
- Limit sclk 2400…1800: tak, po poprawkach (jeden zapisujący, każdy commit niesie krzywą i `s 1`, weryfikacja fizyczna przez `pwm1`/RPM). 1600 i 1200 bez zysku sprawności.
- `power1_cap` 272–303 W: najprostsza dźwignia, nie dotyka tablicy OD; > 303 W — nie.
- Profil zasilania, undervolt, zegar pamięci: nie ruszać.
- Termika dziś zdrowa: 283–288 W, wentylator 100%: hotspot 63–68 °C, edge 47–50 °C, VRAM 70–74 °C; repaste niepotrzebny.

Błąd sterownika opisany w [[lekcja-od-commit-gubi-krzywa]]. Instalacja eco: [[2026-11-06-xtx-eco-instalacja]].

## Powiązane
- [[research/_hub|research]]
- [[raport-63-synteza]]
- [[raport-17-gpu-page-fault]]
- [[amdgpu-moc-i-termika]]
- [[2026-11-05-termika-eco-test]]
