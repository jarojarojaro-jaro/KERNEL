---
typ: research
tags: [research, nvidia, trening]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15a-monokernel.md:11,217-229
status: aktualne
---
# Star Elastic (arXiv 2605.07182)

**Praca NVIDIA o zagnieżdżonych podmodelach Nemotron Nano v3 (30B → 23B/12B z jednego post-trainingu) i osobnym podmodelu dla fazy myślenia; nie dotyczy kerneli, dla nas niska istotność.**

- Nemotron Nano v3 30B/3.6A daje 23B/2.8A i 12B/2.0A przy 160B tokenów; router trenowany end-to-end, curriculum KD.
- „Elastic budget control”: mniejszy podmodel dla thinking, większy dla odpowiedzi – do 16% wyższa dokładność albo 1.9× niższa latencja (vLLM, BF16, batch 16–40).
- RTX Pro 6000: 12B NVFP4 7426 tok/s vs 30B BF16 2178 tok/s (agregat przy dużym batchu, nie batch 1).
Dla nas: zagnieżdżony podmodel tego samego modelu mógłby być drafterem self-spec ze wspólnym KV, ale to nie nasz model; trening to temat raportu 10. Trafił do raportu 15a przez błędny numer arXiv.

## Powiązane
- [[research/_hub|research]]
- [[raport-15a-monokernel]]
- [[raport-10-post-training]]
- [[nemotron-3-5-bolt-74b-a9b]]
