---
typ: repo
tags: [repo, megakernel, rocm, vllm]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15a-monokernel.md:9-10,34-48,50-92
status: aktualne
---
# vLLM MonoKernel (RFC #60904)

**Jeden trwały kernel na warstwę dekodera bez bariery siatki: siatka 256 CTA × 512 wątków (1 CTA na CU MI355X), zależności przez „tagged pairs”, wagi niezależne od wejścia ładowane przed czekaniem, bounded waits; na razie tylko ROCm.**

- GLM-5.2-MXFP4 na 8× MI350X (TP8): czas tokenu batch 1 / 8: 13.70 / 17.33 → 5.92 / 11.44 ms, launche 2459 → 210 (RFC). Baza to niestrojony vLLM: 5–8% pasma HBM, MonoKernel 12–24% – reżim latencji, nie pasma. Wobec ATOM #2435: TPOT 6.897 → 5.380 ms (−22%). Harness `perf_ab.py` usunięty z PR, brak surowych logów.
- Mechanizm: zadanie `t` etapu biegnie na CTA `(base+t) % 256`; producent zapisuje `(wartość, tag epoki)` jednym 8/16-bajtowym store’em, konsument polluje payload (1 obieg pamięci zamiast 2 jak w Hazy); `pre_poll` chroni przed zalaniem pamięci przez czekających; bounded waits ze słowem błędu (GPU nie wisi).
- MoE w jednym launchu: każde CTA redundantnie liczy RMSNorm, kwant FP8 i top-8; wagi shared expert przed pollem. Lekcja z DSv4.1 (#60397): wspólny scratch dla różnych szerokości dawał wyścig; stres 100K replayów bit w bit.
- Co-residency: przy < 256 CU ścieżka się nie włącza („a partitioned GPU deadlocks”).
- Status: RFC otwarty, scalony tylko DSv4.1; maintainerzy sceptyczni wobec interfejsu.
Dla nas: wzorce tagged pairs, prefetch przed czekaniem i bounded waits; na konsumenckim GPU bezpieczniejszy dynamiczny indeks zadania z atomika.

## Powiązane
- [[repo/_hub|repo]]
- [[megakernele-prior-art]]
- [[mkernel]]
- [[raport-15a-monokernel]]
- [[pm4-replay]]
