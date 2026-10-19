---
typ: repo
tags: [repo, vllm, megakernel]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21f-inferencex.md:218-276; vLLM PR #61867; blog vLLM 2026-10-16
status: aktualne
---
# vLLM Kimi K3 „specialized decode” (nie megakernel)

**Fuzja w CuTe DSL z komunikacją TP na 16×GB300: 23 → 13 kerneli na warstwę i 130 → 69 µs na warstwę, krok B1 bez spekulacji 7.38 → 3.90 ms (1.89×), czyli `[SZACUNEK]` 8% → 15% pasma HBM – reżim latencji i komunikacji, nie pasma (PR #61867, 2026-10).**

Audyt nagłówków: 842 t/s wymaga syntetycznej AL = 6, a golden AL InferenceX dla K3 DSpark na kodzie to 3.78 (~530 t/s; PR przy ISL 32k i AL 3.78: 483 t/s); „1.8× P90 interactivity na AgentX” porównuje 16 GPU z 8.

Dla jednego konsumenckiego GPU (~70% technik to fuzja z komunikacją multi-GPU): pełny megakernel się nie opłaca (Qwen sufit +3–6% decode ≈ −1…−3% zegara agenta; LFM: X1–X3 z 16a padły). Przenosi się: specjalizacja kerneli pod szerokości weryfikacji M = 5…17, reguła „przed czekaniem ładuj tylko statyczne wagi” ([[pdl-mmvq-trigger]]), bramka numeryczna „szum 1-ulp”, RMSNorm liczony redundantnie w prologu konsumenta.

## Powiązane
- [[repo/_hub|repo]]
- [[raport-15a-monokernel]]
- [[raport-16a-pm4-pdl]]
- [[raport-21f-inferencex]]
