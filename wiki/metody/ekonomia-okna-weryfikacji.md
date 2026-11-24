---
typ: metoda
tags: [metody, spekulacja, inkling, dspark]
aktualizacja: 2026-11-24
zrodlo: zwiad 2026-11-24 (podagent ZwEngines): Splash 1.7.2 release notes, vllm-redshift CHANGELOG, LocalMaxxing API, basalt docs/models/inkling2.md, priory SpecCtl Mai
status: aktualne
---
# Ekonomia okna weryfikacji: koszt okna 8 względem zwykłego kroku w silnikach Inklinga (2026-11-24)

**Okno 8 tokenów kosztuje: Splash M5 Pro 1,9 kroku (48,3/25,6 ms), vllm-redshift R9700 ~2,2 (28,9/~13 ms), Maya na 3090 2,9 (c[8] = 11,89 + 1,57·7 ms przy 7,8 ms); XTX niezmierzone (K-139 E1).**
- Dlatego R9700 (640 GB/s) z DSpark na code-v1 T=0 ma 144,6 t/s przy własnym dekodzie 72–78, a basalt na 5090 wygrywa DSpark nawet przy T=0,6 (347 vs 264).
- Na bajt w zwykłym dekodzie XTX = R9700 (0,117 t/s na GB/s); różnica jest w oknie i głowicy draftera, nie w kernelach wag.
- Dźwignie z kodu innych: tania głowica draftera (basalt 2-bit screen, MTPLX głowica tylko dla draftera), okno wybierane co rundę z tokenów/ms (basalt `draft_policy.hpp`, NInfer `cost_model.h`, Maya `SpecCtl`), budzenie po `p_top1` (NInfer), stała szerokość jako kontrola (MTPLX +22%).


## Powiązane
- [[ashhart-skills-infra]]
- [[maya-ik2-inkling]]
- [[KOLEJKA-TESTOW]]
