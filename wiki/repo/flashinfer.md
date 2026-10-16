---
typ: repo
tags: [repo, atencja, moe]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/repos/07-flashinfer.md:1-9; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:17
status: aktualne
---
# flashinfer-ai/flashinfer

**Biblioteka kerneli do serwowania LLM (HEAD `2895577`, 2026-10-14, v0.7.2), tylko NVIDIA; bierzemy wzorce atencji; werdykt: średnia.**

Attention (FA2, MLA, XQA), sampling, normy, RoPE, MoE, GDN, JIT pod sm75–sm121, nic pod ROCm. Wzorce dla nas: KV ładowany raz na grupę GQA (L2: atencja decode dla KV q8_0), monomoe, combine w ostatnim bloku, maska przyczynowa liczona w kernelu (Q4, do −0.6 ms/krok przy 94k, szacunek). Odrzucone: sampling bez sortowania na GPU, bo nie jest bitowy z naszym samplerem.

## Powiązane
- [[repo/_hub|repo]]
- [[flashinfer-bench-starter-kit]]
- [[tokamax]]
- [[fattn-kvq]]
- [[repos-30-przeglad]]
