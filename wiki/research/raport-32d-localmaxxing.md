---
typ: research
tags: [research, konkurencja, benchmarki]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/32d-localmaxxing.md:1-20
status: aktualne
---
# Raport 32d: LocalMaxxing – API, weryfikacja, plan wpisów

**Na RX 7900 XTX nie ma ani jednego runu `verifiedRun: true`; „Verified” to kontrola spójności, którą przechodzi ciepła mapa n-gramów (Bonsai 27B 854.5 t/s) (2026-10-20).**

- 30 runów Qwen3.8-27B na XTX, najwyższy 318.2 t/s (hipfire, merge-sort, mal 14.3).
- Verified 3090 reasoning-v1: upstream plain 41.3, MTP n=3 80.4, vLLM MTP 105.4 t/s.
- Publikacja wstrzymana: [[2026-10-20-bez-publikacji-localmaxxing]].

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-20-21]]
- [[raport-34-zrodla-benchmarkow]]
