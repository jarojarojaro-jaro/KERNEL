---
typ: eksperyment
tags: [eksperymenty, spekulacja, vulkan]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:122-160
status: aktualne
---
# 2026-10-10: długość draftu MTP, temperatura i DFlash vs MTP

**Sweep na Vulkanie przy 285 W: n=5 bez p_min zostaje dla MTP, temperatura prawie nie ma wpływu, a DFlash na szerszym zestawie nie jest szybszy od MTP (wcześniejsze „120 t/s” to był jeden prompt).**

Tego dnia naprawiono też usypianie karty (BACO: 4.4 zamiast 92 t/s, po naprawie 94.1 / 90.6 / 94.7 t/s) — szczegóły w baco-runtime-suspend.

Draft MTP (spec_sweep, 5 promptów PL/EN, 2 seedy × 400 tokenów, mediana t/s):
- n=5: T=1 80.5, T=0.7 79.5, T=0 81.9; n=3: 75.0; n=5 p_min 0.3: 80.7; n=5 p_min 0.5: 75.0; n=8 p_min 0.5: 47.0;
- n=8 wypada poza kernele MMVQ 2–8 kolumn (weryfikacja 9 tokenów) → 47 t/s;
- krótszy draft podnosi procent akceptacji, nie prędkość; słownik 64k pomija 3.5% tokenów polskiej prozy.

DFlash vs MTP (6 promptów, ctx 204800):

| konfiguracja | T | mediana t/s |
|---|---|---|
| MTP n=5 | 0.0 | 86.3 |
| DFlash n=6 | 0.0 | 90.6 |
| DFlash n=8 | 0.0 | 86.2 |
| MTP n=5 | 1.0 | 81.1 |
| DFlash n=6 | 1.0 | 71.9 |

DFlash nie ma rejection sampling (tylko dopasowanie), więc przegrywa przy T=1. `--spec-draft-sampling probabilistic` dla MTP: bez zysku. Pierwszy przebieg n=8 i MTP po DFlash były zepsute przez wiszący serwer (SIGTERM) — od tego dnia spec_sweep dobija SIGKILL po 15 s.

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[2026-10-09-pierwsze-pomiary]]
- [[drafter-dflash]]
- [[glowica-mtp]]
- [[serializacja-gpu]]
