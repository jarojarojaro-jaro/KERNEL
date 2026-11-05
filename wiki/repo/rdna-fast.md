---
typ: repo
tags: [repo, rdna3, rocm, llama-cpp]
aktualizacja: 2026-11-05
zrodlo: ~/KERNEL/product/research/63c-amd-rocm-llamacpp.md:44-101,397-410; https://github.com/serrynaimo/RDNA-FAST (`4426ca3`, 2026-11-05)
status: aktualne
---
# RDNA-FAST (serrynaimo): fork llama.cpp/ROCmFPX dla RX 7900 XT

**Downstream llama.cpp + ROCmFPX na RX 7900 XT 20 GB, Windows, ROCm 10.1, Swift 1.5 IQ4_XS; większość trików decode mamy w topce mocniej, nowe są 4 rzeczy i lista pułapek ROCm 10 (2026-11-05).**

- Nowe dla nas: **MTP lean reserve** (draft ctx rezerwuje 2 kształty, 784 → 80 MiB), dynamiczny słownik draftu (12 288 stałych + 12 288 top celu), chunked GDN, f16 WMMA GEMM w prefillu.
- Pułapki ROCm 10 / clang 24: LDS bez `__align__(16)`, rozbite szerokie store'y, spille MMQ, runtime raportuje 128 KB LDS ([[lekcja-rocm10-lds-128kb]]).
- Wiarygodność: „best of N” zamiast mediany, baza LM Studio; ujemne wyniki opisane uczciwie. Autor: „nic nie mierzono na XTX”.
- Porównanie: ich proza 59.8 t/s (~72 po przeskalowaniu na XTX) wobec naszych 78.9; w prefillu są ~15% przed nami `[SZACUNEK]`.
- Plan: lean reserve i cap LDS w toku (TopkaQuick63); WMMA GEMM odrzucony (aktywacje bez q8_1 zmieniają wyjście, [[2026-11-05-tylko-bezstratne]]).

## Powiązane
- [[repo/_hub|repo]]
- [[fattn-kvq]]
- [[rocm-10-1]]
- [[rdna3-gfx1100]]
- [[raport-63-synteza]]
