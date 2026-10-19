---
typ: research
tags: [research, zrodla, nauka]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21b-gpu-perf-zasoby.md:31-71,305-340
status: aktualne
---
# Lista wafer-ai „gpu-perf-engineering-resources”: ocena

**Dobry spis lektur, ale nie przepis na nasz problem: 5 z 6 działów dotyczy serwerów z dużym batchem, Hoppera/B200 i rozproszenia (NVLink, DeepEP, EPLB, disaggregation), dział AMD to tylko CDNA/Instinct, a o RDNA3, batch 1 na kartach konsumenckich i skwantyzowanym GEMV nie ma nic (raport 21b, 2026-10-19).**

Blackwell Tuning Guide v13.4 dotyczy B200/GB200 (HBM3, L2 126 MB, NVLink 5); dla sm_120 podaje tylko limity (48 warpów/SM, 128 KB shared/SM, 99 KB na blok, 32 bloki/SM). Opis z listy („Tensor memory, Blackwell execution features”) nie zgadza się z treścią – o tensor memory przewodnik milczy, a sm_120 jej nie ma ([[sm-86-89-120]]). Kolejność lektur dla zespołu: raport 21b §6.

## Powiązane
- [[research/_hub|research]]
- [[raport-21b-gpu-perf-zasoby]]
- [[repos-30-przeglad]]
