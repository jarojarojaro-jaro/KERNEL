---
typ: research
tags: [research, nvidia, rtx-3090, topka]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/24e-nvidia-runda.md:9-14,18-27,33-37
status: aktualne
---
# Raport 24e: runda NVIDIA – topka na CUDA (RTX 3090), L2 prefetch, TensorFold 1.1.0

**Topka na CUDA (lookup W16 + cache share) daje na 3090 code-edit 320.6 vs 125.8 t/s (×2.55) i kopię 64k 245 vs 81.5 t/s (×3.0) przy czacie bez zmian; `GGML_CUDA_MMVQ_L2PF` −0.4…−0.8% – kill; TensorFold 1.1.0 przegrywa (2026-10-19).**

- Z lookupem wyłączonym topka = 3090-opt bitowo (6/6 md5) (`24e:10`).
- Różnica wobec AMD: na CUDA `LOOKUP=3` zmienia greedy md5 na 1/6 promptów (en-code), bo partie 5 i 17 tokenów idą innymi kernelami (`24e:11`).
- TensorFold 1.1.0 (MLX-4bit + DFlash2): czat 73.9 vs 77.3, kopia 107 vs 245 t/s, prefill 64k 317 vs 69 s (`24e:14`).
- PDL na sm_86 no-op; evict-first nie zbudowany (`24e:13`). Finał 3090: [[raport-27-3090-final]].

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[raport-27-3090-final]]
- [[tensorfold]]
- [[raport-16d-magnitude-vs-nasz]]
