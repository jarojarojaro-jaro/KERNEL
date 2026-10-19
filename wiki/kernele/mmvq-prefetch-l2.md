---
typ: kernel
tags: [kernele, cuda, mmvq, prefetch]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21b-gpu-perf-zasoby.md:291-296; ~/llama-master ggml/src/ggml-cuda/mmvq.cu:30-34,1703-1721; https://github.com/ggml-org/llama.cpp/pull/26705#issuecomment-5569335031
status: do-sprawdzenia
---
# Prefetch L2 w pętli MMVQ: włączony tylko na DGX Spark

**Upstream włącza prefetch L2 w pętli MMVQ tylko dla `GGML_CUDA_CC_DGX_SPARK` (`mmvq.cu:1703`); na GB10 przy 5 kolumnach dał Q4_K +2.89%, Q5_K +3.90%, Q6_K +6.19%, przy 1 kolumnie ~0, a teza „na kartach z większym pasmem nie pomaga” nie ma danych (raport 21b, 2026-10-19).**

Dla nas kandydat do weryfikacji MTP (4–5 kolumn) na 3090/4090/5060 Ti: przełącznik dla `ncols_dst ≥ 2`, pomiar `test-backend-ops -o MUL_MAT perf` ne11 = 1..8 (Q3_K/Q4_K/Q5_K/Q6_K/IQ4_XS), potem spec_sweep ABBA. Kill: < +1% spec_sweep albo regresja przy ne11 = 1. Bitowy (prefetch nie zmienia numeryki).

## Powiązane
- [[kernele/_hub|Kernele]]
- [[mmvq-multikolumnowe]]
- [[pdl-mmvq-trigger]]
