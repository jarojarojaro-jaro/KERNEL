---
typ: archiwum
tags: [archiwum, benchmarki, konkurencja]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21f-inferencex.md:24; InferenceX run 35359530151, PR #3260; ~/KERNEL/wiki/REKORDY.md
status: nieaktualne
wycofano: 2026-11-22
powod: wpis InferenceX to część raportu 21f, nie model
zastapiona_przez: research/raport-21f-inferencex
---
# Qwen3.8-27B na InferenceX (wpis eksperymentalny)

**Na InferenceX Qwen3.8-27B ma eksperymentalny wpis: bf16, 1×H100, vLLM + drafter DSpark k=7, fixed-sequence 1k/1k na losowych tokenach; przy c=1 mediana 86.1 tok/s, p90 67.4, AL ≈ 2.0 (run 35359530151, PR #3260 niescalony, 2026-10-19).**

Nasz XTX (UD-Q4_K_XL + MTP4) daje 109.0 t/s na `spec_sweep` ([[REKORDY]]), czyli ~1.27× przy 3.2× mniejszej liczbie bajtów na token – porównanie orientacyjne (inne kwanty, prompty, T; losowe tokeny obniżają akceptację draftu).

## Powiązane
- [[qwen3-8-27b]]
- [[raport-21f-inferencex]]
