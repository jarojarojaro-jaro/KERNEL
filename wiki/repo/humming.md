---
typ: repo
tags: [repo, kwanty, nvidia, kernele]
aktualizacja: 2026-10-24
zrodlo: ~/KERNEL/product/research/60d-serving-kernels-cache.md:89-138,216-219; https://github.com/vllm-project/humming (`db930af`); https://vllm.ai/blog/2026-10-21-humming
status: aktualne
---
# Humming (vLLM + Ant Group): kernele GEMM dla kwantów, tylko CUDA

**Biblioteka JIT (Apache-2.0, `humming-kernels`, domyślna w vLLM ≥ 0.29 na CUDA) dla WnA16/W8A8/W4A8/W4A4, dense i MoE. Brak HIP/ROCm i GGUF. Przy M=1 osiąga 610 GB/s = 60% pasma RTX 4090 (W4A16 8192², zimne L2), tyle co Marlin; nasze MMVQ na XTX ma 75.7% (raport 60d, 2026-10-24).**

- Mały M to kafle MMA z M dopełnionym do 8/16 plus Stream-K (`tune/base.py:95-96,334-376`). GEMV nie ma; osobną ścieżkę maintainer odrzucił w [#111](https://github.com/vllm-project/humming/issues/111). Tamże pomiar z zewnątrz: przy M≤4 ograniczenie liczbą instrukcji dequantu F16, a własny GEMV dał 1.36× (CMP 170HX) i 1.13–1.74× (3090).
- Czas płaski do M=16 (55.1–55.5 µs na 4090), więc weryfikacja spekulacji jest „darmowa”, ale przy 60% pasma.
- Triki dequantu: magiczne `0x6400` + `lop3`; symetryczny int → float e0mX; MXFP4 → INT8 z wykładnikiem E8M0 wtopionym w LUT `prmt` (`dequant_fused.cuh:33-54`).
- E2E (blog): DeepSeek-V4.1-Flash, 8× H20, Marlin W4A16 → Humming W4A8 daje +14…+43% wyjścia.
- Dla nas: nic dla XTX; Stream-K w MMQ RDNA3 tylko wzmacnia istniejący pomysł. 3090: najwyżej baseline vLLM.

## Powiązane
- [[repo/_hub|repo]]
- [[inferrous]]
- [[deepgemm]]
- [[mmvq-multikolumnowe]]
- [[raport-60d-serving-kernels-cache]]
