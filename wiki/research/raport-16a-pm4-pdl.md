---
typ: research
tags: [research, pm4, megakernel]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/product/research/16a-pm4-pdl.md:1-161
status: aktualne
---
# Raport 16a: PM4-PDL i prefetch wag na XTX (X1–X3 z 15a)

**Wszystkie trzy eksperymenty z raportu 15a odpadły na lokalnym XTX ($0, gałąź `pm4-pdl` @ `3a008359b`, przełączniki domyślnie wyłączone): X1 mikrobench PDL −0.11 µs (próg 0.5), X2 górna granica +12% w LFM, ale realnie ~+3%, X3 prefetch do MALL w szumie.**

- Qwen MTP nie był mierzony (żaden eksperyment nie wygrał); do produkcji nic nie idzie, domyślna taśma bez zmian (304 dispatche).
- Korekta 15a: szacunek S1 PM4-PDL (+9…+15%, ranking A z oczekiwaniem +5…+15%) był za wysoki – górna granica bez synchronizacji to +12%, realnie ≈ +3%.
- Dalej (jeśli w ogóle): kernel dataflow (15a C/D, trwały blok MoE) albo fuzja gate+up → down.

Notatki: [[2026-10-18-pm4-pdl-x1]], [[2026-10-18-pm4-ub-lfm]], [[lekcja-handoff-rdna3]], [[lekcja-prefetch-mall-xtx]].

## Powiązane
- [[research/_hub|research]]
- [[raport-15a-monokernel]]
- [[raport-16g-lfm-moe-pasmo]]
- [[pm4-replay]]
