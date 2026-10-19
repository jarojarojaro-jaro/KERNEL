---
typ: kernel
tags: [kernele, cuda, pdl, mmvq]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21b-gpu-perf-zasoby.md:168-200; ~/llama-master ggml/src/ggml-cuda/mmvq.cu:1480,1530,1980; ggml/src/ggml-cuda/common.cuh:1913-1916; ~/KERNEL/product/research/23c-re-kernele-nvidia.md:5-8
status: do-sprawdzenia
---
# PDL w MMVQ użyty tylko w połowie (CUDA sm_90+)

**Gęsty `mul_mat_vec_q` woła `ggml_cuda_pdl_sync()` przed jakimkolwiek odczytem wag (`mmvq.cu:1530`) i nigdy nie woła triggera (`ggml_cuda_pdl_lc` jest tylko w `mul_mat_vec_q_moe`, `:1980`), więc PDL ukrywa dziś tylko launch i prolog, a nie rampę strumienia wag (raport 21b, 2026-10-19).**

Zmiana (bitowa z konstrukcji – wagi tylko do odczytu, adres znany przed `pdl_sync`): `ggml_cuda_pdl_lc()` na starcie + `prefetch.global.L2` pierwszych 1–2 iteracji wag przed `pdl_sync` (wariant: ładowanie do rejestrów), przełącznik `GGML_CUDA_MMVQ_PREWAIT=0/1/2`. Szacunek: ~110 gęstych matvec/token LFM × 0.5–2 µs → 5060 Ti +1.1–4.6%, 5090 +2.5–11%; Qwen 5060 Ti +0.7–2.6%. Tylko sm_90+ (5060 Ti, 5090). Przeciw: na XTX prefetch do L2 przed konsumentem nic nie dał ([[lekcja-prefetch-mall-xtx]]).

E1: najpierw `GGML_CUDA_PDL=0/1` (ile PDL daje dziś – nigdy niemierzone), potem zmiana; kill < +1.5% LFM tg128 na 5060 Ti albo różnica md5.

Potwierdzone w SASS (23c, 2026-10-19): MMVQ sm_120a ma `ACQBULK` (`griddepcontrol.wait`) bez `PREEXIT` (`launch_dependents`) – PDL działa tylko po stronie czekania ([[raport-23c-re-kernele-nvidia]]).

## Powiązane
- [[kernele/_hub|Kernele]]
- [[lekcja-pdl-sm120]]
- [[mmvq-prefetch-l2]]
- [[raport-21b-gpu-perf-zasoby]]
