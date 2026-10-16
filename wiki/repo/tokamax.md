---
typ: repo
tags: [repo, jax, gdn]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/repos/15-tokamax.md:1-22; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:25
status: aktualne
---
# openxla/tokamax

**Kernele Google/DeepMind w JAX + Pallas (HEAD `b500ee4`, 2026-10-14), kod inference tylko pod TPU; werdykt: niska.**

Ragged dot / MoE z wyrównanym startem kafli, swap-AB dla wag kwantyzowanych, maska rozkładana na `is_causal` + granice per wiersz. Repo nie podaje prawie żadnych liczb wydajności. Dla nas: conv1d w kernelu GDN (−48 kerneli/krok Qwena) oraz testy „5 tokenów naraz = 5 pojedynczych”.

## Powiązane
- [[repo/_hub|repo]]
- [[flashinfer]]
- [[vllm-xpu-kernels]]
- [[conv-lag]]
- [[repos-30-przeglad]]
