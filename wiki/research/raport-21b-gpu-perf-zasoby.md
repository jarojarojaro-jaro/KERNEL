---
typ: research
tags: [research, nvidia, rdna3, techniki]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21b-gpu-perf-zasoby.md:1-388
status: aktualne
---
# Raport 21b: zasoby GPU perf (wafer-ai) i Blackwell Tuning Guide na nasze karty

**Mapa technik z listy wafer-ai i Blackwell Tuning Guide v13.4 na XTX i RTX: większość technik sensownych przy batch 1 już mamy albo zmierzyliśmy negatywnie; nowe, tanie i bitowo bezpieczne pozycje dotyczą NVIDIA (PDL w MMVQ tylko w połowie, L2 persisting window, prefetch L2 w MMVQ poza DGX Spark), a najważniejszą niewiadomą jest RTX 5090.**

| # | technika | platforma | zysk | p | dni |
|---|---|---|---|---|---|
| 1 | pomiar 4090/5090 + rozkład przerw | NVIDIA | decyzyjny | 0.8 | 1 (+~$1.5) |
| 2 | [[pdl-mmvq-trigger]] | 5060 Ti, 5090 | LFM +1–4.6% / +2.5–11% | 0.35 | 1.5 |
| 3 | [[mmvq-prefetch-l2]] dla 2–8 kolumn | 3090, 4090, 5060 Ti | weryfikacja MTP 0…+3% | 0.3 | 0.5 |
| 4 | [[l2-persist]] | 4090, 5090, 5060 Ti | LFM +1–2% | 0.4 | 1 |
| 5 | koszt granicy grafu CUDA (X5 z 15a) | 3090, 4090 | decyzyjny | 0.7 | 1 (+$0.5) |
| 6 | [[trwala-siatka-bez-pm4]] | XTX | LFM +8–10% vs PM4-off | 0.3 | 10–12 |
| 7 | cpol 0 dla głowy Q6_K w weryfikacji | XTX | Qwen MTP ~+0.5% | 0.5 | 0.5 |
| 8 | [[physics-floor-check]] w fabryce | wszystkie | wiarygodność | 0.9 | 0.5 |

Nie robić: TMA w GEMV (cp.async już ~92% pasma), FP8/FP4 w dekodzie (te same bajty wag; prefill tylko z NVFP4), FA3/FA4/tcgen05/wgmma/DeepGEMM/multicast (brak na sm_86/89/120), sztuczki AQL/HIP graph na XTX (podłoga 2.08 µs). Eksperymenty E1–E5: PDL trigger (5060 Ti, $0), kampania 4090/5090 (~$1–2), L2 persist, prefetch L2 w MMVQ, koszt granicy na Ampere/Ada + bariera trwałej siatki na XTX. Ocena źródeł: [[wafer-gpu-perf-lista]]; projekcja: [[projekcja-rtx-5090]].

## Powiązane
- [[research/_hub|research]]
- [[raport-15a-monokernel]]
- [[raport-18-nastepna-fala]]
- [[karty-nvidia-parametry]]
