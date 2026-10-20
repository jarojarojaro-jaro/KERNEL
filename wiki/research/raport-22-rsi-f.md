---
typ: research
tags: [research, rsi, fabryka]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/22-rsi-f.md:9-14,21-23,67-94
status: aktualne
---
# Raport 22: RSI-F – pętla samodoskonalenia na fabryce v1

**Kod RSI-F z bramkami sprzętowymi H0–H11 gotowy i przetestowany na CPU (112 testów OK), ale pilot P0 (karta 0070) nie dał werdyktu pomiarowego – trzy podejścia padły na harnessie, kolejce i pauzie GPU (2026-10-19).**

- Bramki H0–H11 egzekwowane kodem: :8080 przez `ss`, `GGML_HIP_PM4=0` w każdym bloku, `cpuheavy` + `taskset` (`22:21-23`).
- P0: seq 5 `INVALID` (harness ≠ lock), seq 7 `VOID` (topka wstała na :8080, potem OOM przy wznowieniu), trzeci run zabity przy pauzie GPU (`22:71-78`).
- Poprawka projektowa: fabryka nigdy nie wznawia topki – robi to tylko keeper ([[2026-10-19-topka-tylko-keeper]], `22:91`).
- H7 hashuje tylko OD_SCLK/OD_MCLK/OD_VDDGFX_OFFSET + limit mocy (`22:90`), zgodnie z [[2026-10-20-karta-fabrycznie]].
- Metoda: [[petla-rsi-f]].

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[petla-rsi-f]]
- [[fabryka-v1]]
- [[raport-21h-rsi]]
- [[2026-10-19-topka-tylko-keeper]]
- [[2026-10-20-karta-fabrycznie]]
