---
typ: research
tags: [research, re, amd, pm4]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/23d-re-runtime-amd.md:5-13,19-30
status: aktualne
---
# Raport 23d: launch na gfx1100 – HIP → AQL → firmware MEC vs nasza taśma PM4

**Firmware MEC czyści bit PRIV z deskryptora i ustawia go z flagi kolejki – potwierdza hipotezę H1′ (PRIV ustawiamy tylko my, `WA=2`); podłoga AQL 2.08 µs na pakiet to praca firmware, taśma PM4 0.46–0.86 µs (2026-10-19).**

- Maska RSRC1 `0xe4aff3ff`, PRIV z `tp+0x2d8` bit 2 (`23d:7`).
- Dwie nowe różnice wobec AQL: inicjator `0x1065 | CS_W32<<15` bez ORDERED_APPEND oraz `COMPUTE_PGM_HI |= 0x100` – niskie ryzyko (`23d:8-12`).
- Koszt launchu AQL nie do obejścia flagami HIP (`23d:13`).
- Notatki szczegółowe: [[mec-fw-dispatch-aql-gfx11]], [[gfx11-pm4-dispatch-priv]]. Wdrożenie WA=2: [[raport-26-kolejka-gpu]].

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[mec-fw-dispatch-aql-gfx11]]
- [[gfx11-pm4-dispatch-priv]]
- [[pm4-replay]]
- [[raport-26-kolejka-gpu]]
