---
typ: rocm
tags: [rocm, amdgpu, moc]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:107-126,146,170; ~/KERNEL/qwen-opt/README.md:32-33; ~/KERNEL/product/research/16g-lfm-moe-pasmo.md:76-81
status: aktualne
---
# Sterownik amdgpu: limit mocy, termika, usypianie

**Karta pracuje z limitem 285 W i wyłączonym usypianiem (runtime PM); bez tego model ląduje w RAM i działa ~4 t/s.**

Stan karty (NOTES, 2026-10-09):
- `power1_cap` domyślnie 303 W, zakres sterownika 272–350 W; najniżej bez OverDrive 272 W (tylko −10%);
- przy dekodowaniu karta siedzi na limicie (~305 W, `THROTTLE_STATUS: THROTTLED`);
- zapis limitu wymaga roota; OverDrive wyłączony (`pp_od_clk_voltage` nie istnieje, potrzebny `amdgpu.ppfeaturemask=0xffffffff` + restart);
- przy prefillu 196k tokenów: edge 66°C, junction 106°C, VRAM 76°C, 281 W; różnica edge–junction ~40°C (typowo 15–25°C), podejrzenie pasty / docisku.

Ustawienia produkcyjne (`gpu-powercap.service`, root): limit 285 W i `power/control=on`. W trakcie pomiarów przy 285 W: junction 85–88°C (max 90), edge 64–67°C.

Runtime suspend (BACO, 2026-10-10): bez monitora amdgpu usypia kartę po 5 s bezczynności i przenosi VRAM do GTT; model działa wtedy przez PCIe: 4.4 zamiast 92 t/s. Bez roota `run-llm.sh` trzyma kontekst KFD (`gpu-keepawake`). Po naprawie: 94.1 / 90.6 / 94.7 t/s także po 20 s bezczynności.

Limit mocy jako optymalizacja (−20% mocy za ≤5% t/s) odłożony na prośbę użytkownika.

Objaw limitu 285 W przy optymalizacji kerneli: [[lekcja-limit-mocy-285w]] (2026-10-18).

## Powiązane
- [[rocm/_hub|ROCm]]
- [[baco-runtime-suspend]]
- [[amd-smi]]
- [[rx-7900-xtx]]
- [[2026-10-09-limit-mocy-odlozony]]
