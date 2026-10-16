---
typ: kernel
tags: [kernele, gdn, nie-scalone]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/round6/gdn-bitwise.md:6-17,95-133,176-184; ~/KERNEL/qwen-opt/research/qwen-round5.md:10-16,36-40; ~/KERNEL/qwen-opt/STATUS-NEXT.md:25,35; ~/KERNEL/qwen-opt/NOTES.md:398
status: aktualne
---
# GDN fast (Gated DeltaNet, DPP) — nie scalony

**Szybszy kernel rekurencji Gated DeltaNet Qwena (redukcje DPP zamiast ds_bpermute, nakładanie tokenów t/t+1); bitowo zgodny, ale zysk end-to-end w szumie, więc został na gałęzi `opt-gdn6`.**

**Próba 1 (runda 5, 58e578967, 2026-10-15):** nie bitowa. Restrukturyzacja zmieniła kontrakcję FMA (94 vs 83 FMA w ISA), greedy plain `0b7b073b` zamiast `c4708318`. Wycofana (5b1fdbc2f). Wniosek: jawne `fmaf` zgodne z ISA bazy, stary kernel nietknięty.

**Próba 2 (runda 6, `opt-gdn6`: b4e819237, 0d89ce56c):** osobny kernel `gated_delta_net_fast_cuda`, DPP, peeling ostatniego tokenu, stan przez LDS w kawałkach 16 B (b128). Kernel plain bajt w bajt nietknięty. Instrukcje na falę (decode T=1): 476 → 423. Dowód offline emulatorem ISA, potem GPU 2026-10-15:
- test-backend-ops GATED_DELTA_NET*: 67/67; logity i greedy md5 = baza;
- rocprofv3: decode/weryfikacja 14.49 → 14.27 µs (−1.5%), kernel promptu 153.7 → 132.1 µs (−14%);
- llama-bench Qwen: tg128 +0.15%, pp512 +0.7% (sd ±120).

Werdykt: nie scalony (379 linii za ~0.1%); gałąź zostaje na długi prefill modeli hybrydowych. Wyłączniki: `GGML_HIP_GDN_FAST=0`, `GGML_HIP_GDN_B128=0`.

## Powiązane
- [[kernele/_hub|Kernele]]
- [[gdn-replay]]
- [[emulator-isa]]
- [[runda-6]]
- [[determinizm-fma]]
