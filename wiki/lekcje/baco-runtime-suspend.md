---
typ: lekcja
tags: [lekcje, sterownik]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:122-126
status: aktualne
---
# Usypianie karty (BACO) wyrzuca model z VRAM

**Bez aktywności amdgpu usypia kartę po 5 s (runtime PM/BACO) i przenosi VRAM do RAM; model działa wtedy przez PCIe: 4.4 zamiast 92 t/s.**

Objaw (2026-10-10): `vram_used` 35 MB, `gtt_used` 23.8 GB. Naprawa: `power/control=on` (`gpu-powercap.service`, root) albo bez roota trzymanie kontekstu KFD (`gpu-keepawake` w `run-llm.sh`). Po naprawie przy 285 W: 94.1 / 90.6 / 94.7 t/s także po 20 s bezczynności. Produkt powinien wykrywać pomiar < 10% oczekiwanego (raport 04).

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[amdgpu-moc-i-termika]]
- [[run-llm-sh]]
- [[rx-7900-xtx]]
