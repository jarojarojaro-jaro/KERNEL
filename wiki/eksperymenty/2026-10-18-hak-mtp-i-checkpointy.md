---
typ: eksperyment
tags: [eksperymenty, mtp, prefill, ttft]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/product/research/16f-xtx-szybkie.md:14,117-149; ~/wt/quickwins/qw/e3d.jsonl; ~/wt/quickwins/qw/e3-timing.server.log; commity `7369380bf`, `7f908b4dd` (cofnięty w `caefe1800`)
status: aktualne
---
# 2026-10-18: hak MTP w prefillu i koszt checkpointów (E3 z 16f)

**Sam hak MTP na prompt kosztuje 2.2–2.6% TTFT Qwena (65 / 186 / 768 ms przy 2k / 8k / 32k), więc złożenie go w graf prefillu (15d L4: „−5–7%”) nie jest warte pracy; większym celem są checkpointy stanu (~94–104 ms każdy, 2 na prompt).**

| prompt | bez spekulacji | MTP | MTP, hak pominięty | sam hak |
|---|---|---|---|---|
| 2k | 2235 ms | 2534 | 2469 | 65 ms (2.6%) |
| 8k | 7876 | 8375 | 8189 | 186 ms (2.2%) |
| 32k | 33619 | 35050 | 34282 | 768 ms (2.2%) |

- `LLAMA_CKPT_TIMING=1`: odczyt stanu rekurencyjnego ~94 ms (149.6 MiB, bez spekulacji) i ~104 ms (170.3 MiB z MTP); 2 checkpointy na prompt (n − 4 − ub i n − 4).
- Kopie stanu przez pinned host (`LLAMA_STATE_PINNED`): bez efektu (replay omp 1981 → 1982 ms), cofnięte; ogranicza opóźnienie ~150 synchronicznych `ggml_backend_tensor_get`, nie pasmo `[INFERENCE]`.
- Następny kandydat (niezmierzony): jedna seria `tensor_get_async` z jedną synchronizacją, potencjalnie −150…−200 ms na prompt i turę.

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[raport-15d-prefill-dlugi-kontekst]]
- [[2026-10-18-cache-promptu-agenta]]
- [[glowica-mtp]]
