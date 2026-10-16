---
typ: kernel
tags: [kernele, dpp, norma]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:261; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:100,262; ~/KERNEL/product/research/patch-manifest.json (0025)
status: aktualne
---
# rms_norm·mul(+q8_1) z redukcjami DPP (0025)

**Rozwinięty kernel normy RMS dla 2048–8192 kolumn: wszystkie ładowania naraz i redukcje przez DPP; 5.87 → 4.51 µs przy 5120 kolumnach.**

- Łatka 0025, runda K2 (2026-10-13). Normę łączy z mnożeniem przez wagę i zapisem q8_1 dla następnego MMVQ.
- Pułapka poprawności: rozwinięta suma x·x musi być jawnym łańcuchem `fmaf`; inaczej kompilator kontraktuje inny iloczyn i wychodzi 1 ulp różnicy w ~4% wierszy. Harness bitowy na 2000 wierszy z wartościami skrajnymi.
- Po poprawce: bitowo identyczne.
- Wyłącznik: `GGML_HIP_NORM_FAST=0`.
- Platformy: kod wspólny CUDA/HIP bez strażnika arch; bitowość na nvcc niesprawdzona (manifest).

## Powiązane
- [[kernele/_hub|Kernele]]
- [[argmax-dpp]]
- [[cache-q8-1]]
- [[determinizm-fma]]: lekcja o kontrakcji FMA
- [[zgodnosc-bitowa-md5]]
