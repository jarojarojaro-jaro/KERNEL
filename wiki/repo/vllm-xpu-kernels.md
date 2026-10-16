---
typ: repo
tags: [repo, intel, gdn]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/repos/11-vllm-xpu-kernels.md:1-22; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:21
status: aktualne
---
# vllm-project/vllm-xpu-kernels

**Kernele vLLM na Intel GPU w SYCL (HEAD `6b30c9b9`, 2026-10-14); bierzemy pomysł fuzji q/k-norm + RoPE + zapis KV; werdykt: niska.**

Decode attention z GQA w wymiarze M (KV czytane raz na głowę KV), split-K z osobną redukcją, KV fp8 ze skalą per tensor, kernele Gated DeltaNet. Dla nas: fuzja q/k-norm + RoPE + zapis KV (L6) oraz stan GDN w fp16 (Q7, szacunek −0.15…−0.3 ms/krok), który zmienia numerykę i wymaga najpierw dowodu offline.

## Powiązane
- [[repo/_hub|repo]]
- [[flashinfer]]
- [[tokamax]]
- [[arc-b580-i-mac]]
- [[repos-30-przeglad]]
