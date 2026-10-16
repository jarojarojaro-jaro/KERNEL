---
typ: repo
tags: [repo, galezie, mmq]
aktualizacja: 2026-10-16
zrodlo: ~/wt/mmq6/REPORT.md:1-25
status: aktualne
---
# Gałąź opt-mmq6 (epilog MMQ, łatka 0070)

**Gałąź `opt-mmq6` @ `ae1ef6a97` (2026-10-15): epilog skal Q4_K/Q5_K w MMQ RDNA3 w operacjach f32 parowalnych w VOPD, bitowo te same sumy; w raporcie oznaczone jako NIEZMIERZONE.**

Diagnoza z ISA bazowego (Q4_K, J=128, krok k01 = 16 WMMA): na lane 64 `v_fma_mix_f32`, 64 `v_cvt_f32_i32`, 64 fmac i 64 kolejne `v_fma_mix_f32`; `v_fma_mix` i `v_cvt` nie mogą dual-issue. Zmiana: skale kroku k01 poszerzane raz do f32 (32 `v_cvt_f32_f16`), dalej VOPD. Wyłącznik `GGML_HIP_MMQ_EPI=0`. Commit wszedł do `amd-opt` jako 0070; na CUDA wymagał guarda (`cuda-compat`).

## Powiązane
- [[repo/_hub|repo]]
- [[galezie-rund]]
- [[opt-qwen5]]
- [[mmq-epilog]]
- [[runda-6]]
- [[runda-6-raporty]]
- [[lekcja-commity-bez-pomiaru]]
