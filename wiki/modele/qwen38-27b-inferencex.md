---
typ: model
tags: [modele, benchmarki, konkurencja]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21f-inferencex.md:24; InferenceX run 35359530151, PR #3260; ~/KERNEL/wiki/REKORDY.md
status: do-sprawdzenia
---
# Qwen3.8-27B na InferenceX (wpis eksperymentalny)

**Na InferenceX Qwen3.8-27B ma eksperymentalny wpis: bf16, 1×H100, vLLM + drafter DSpark k=7, fixed-sequence 1k/1k na losowych tokenach; przy c=1 mediana 86.1 tok/s, p90 67.4, AL ≈ 2.0 (run 35359530151, PR #3260 niescalony, 2026-10-19).**

Nasz XTX (UD-Q4_K_XL + MTP4) daje 109.0 t/s na `spec_sweep` ([[REKORDY]]), czyli ~1.27× przy 3.2× mniejszej liczbie bajtów na token – porównanie orientacyjne (inne kwanty, prompty, T; losowe tokeny obniżają akceptację draftu).

## Powiązane
- [[modele/_hub|Modele]]
- [[qwen3-8-27b]]
- [[raport-21f-inferencex]]
