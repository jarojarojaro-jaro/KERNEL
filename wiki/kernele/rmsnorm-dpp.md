---
typ: kernel
tags: [kernele, dpp, norma]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:261; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:100,262; ~/KERNEL/product/research/patch-manifest.json (0025); ~/KERNEL/product/research/48-norma-n4-gdn-bank.md:10-16; ~/KERNEL/product/research/51-male-kernele.md:10-40
status: aktualne
---
# rms_norm·mul(+q8_1) z redukcjami DPP (0025)

**Rozwinięty kernel normy RMS dla 2048–8192 kolumn: wszystkie ładowania naraz i redukcje przez DPP; 5.87 → 4.51 µs przy 5120 kolumnach.**

- Łatka 0025, runda K2 (2026-10-13). Normę łączy z mnożeniem przez wagę i zapisem q8_1 dla następnego MMVQ.
- Pułapka poprawności: rozwinięta suma x·x musi być jawnym łańcuchem `fmaf`; inaczej kompilator kontraktuje inny iloczyn i wychodzi 1 ulp różnicy w ~4% wierszy. Harness bitowy na 2000 wierszy z wartościami skrajnymi.
- Po poprawce: bitowo identyczne.
- Wyłącznik: `GGML_HIP_NORM_FAST=0`.
- Platformy: kod wspólny CUDA/HIP bez strażnika arch; bitowość na nvcc niesprawdzona (manifest).

## Aktualizacja 2026-10-21
- Norma 5-wierszowa ~4.5 µs w każdym scenariuszu (praca kernela, nie zimne wagi); sufit ≤0.26 ms/krok ([[raport-51-male-kernele]]).
- Normy 4-wierszowe wolniejsze tylko w izolowanych grafach (rozruch zegara) ([[raport-48-norma-gdn-bank]]).

## Powiązane
- [[kernele/_hub|Kernele]]
- [[argmax-dpp]]
- [[cache-q8-1]]
- [[determinizm-fma]]: lekcja o kontrakcji FMA
- [[zgodnosc-bitowa-md5]]
