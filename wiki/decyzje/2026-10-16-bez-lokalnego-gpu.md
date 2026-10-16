---
typ: decyzja
tags: [decyzje, gpu, lab]
aktualizacja: 2026-10-16
zrodlo: ~/.omp/agent/sessions/-tmp/2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5303,5593
status: aktualne
---
# 2026-10-16: nie testujemy na naszym 7900 XTX

**Użytkownik: najpierw „narazie nie rób testów na naszym gpu” (2026-10-16 00:56 UTC), a po krótkim teście bit-exact (02:46 UTC): optymalizacje tylko na kartach z Vast, 7900 XTX zostawić i nie robić na nim testów.**

Wyjątek: jeden krótki test `llama-bx-diff` (~20 s GPU) za zgodą użytkownika. W tym samym poleceniu: dokończyć optymalizacje na wynajętych kartach i w tym czasie budować aplikację (landing, design, onboarding) bez GPU. Wcześniej był zakaz nocny 2026-10-15 (00:45–02:00). Skutek: poprawka atencji `77240c9b3` i trening MTP czekają na test na Radeonie.

## Powiązane
- [[decyzje/_hub|decyzje]]
- [[2026-10-15-zakaz-gpu-w-nocy]]
- [[2026-10-16-budzety-chmury]]
- [[lekcja-bit-exact-attention]]
- [[rx-7900-xtx]]
