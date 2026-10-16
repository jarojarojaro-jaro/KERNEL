---
typ: kernel
tags: [kernele, gdn, fuzje]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:263-266; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:102-103,120; ~/KERNEL/qwen-opt/NOTES.md:321
status: aktualne
---
# Fuzje GDN Qwena (0027, 0028, 0045)

**Mniejsze fuzje wokół warstwy Gated DeltaNet: bramkowana norma wyjścia, SSM_CONV razem z alpha/beta i normalizacja q/k w prefillu.**

| łatka | co | zysk | wyłącznik |
|---|---|---|---|
| 0027 (K2, 2026-10-13) | silu(z)·(rms_norm(x)·w) + q8_1 jednym kernelem | 2.68 + 1.84 µs → 1.87 µs | `GGML_HIP_NORM_GATE` |
| 0028 (K2) | SSM_CONV + alpha/beta GDN jedną siatką | 4.68 + 4.90 µs → 5.54 µs (~0.33 ms/krok) | `GGML_HIP_GDN_CONV_AB` |
| 0045 (K5, 2026-10-14) | prefill: normalizacja l2 q/k raz na (głowa, token) | pp2048 1082 → 1108 (+2.4%) | brak (build) |

Bez 0028 K2 dawało 32.50 ms/krok zamiast 32.17 (Qwen). Wszystkie bitowe; 0027 używa `ggml_cuda_no_contract`, żeby kompilator nie zmienił kontrakcji. Rodzina F8 w raporcie 07: tylko modele rodziny qwen35 (GDN).

## Powiązane
- [[kernele/_hub|Kernele]]
- [[fuzje-weryfikacji]]: prolog GDN (A4)
- [[gdn-replay]]
- [[gdn-fast]]
- [[qwen3-8-27b]]
