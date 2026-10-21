---
typ: research
tags: [research, xtx, proza]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/37-proza-100.md:9-38
status: aktualne
---
# Raport 37: stała metryka prozy E0, resztka hosta, górne granice

**E0 (8 promptów × 8 seedów, thinking off) na produkcyjnej topce: 78.93 t/s [75.69, 82.21], 2.158 tok/krok, 27.34 ms/krok – prawdziwa proza to 78.9, nie ~96–104 t/s (2026-10-20).**

- Do 100 t/s brakuje +27%, nie 4%.
- Cięcia hosta (#4a blit, #4b sync query) +0.04% → odrzucone.
- Górna granica bez granic PM4 wokół MMVQ → norma: −2.17 ms (−8.8%), jedyna duża dźwignia.

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-20-21]]
- [[metryka-prozy-e0]]
- [[lekcja-proza-e0-vs-myslenie]]
- [[pm4-replay]]
