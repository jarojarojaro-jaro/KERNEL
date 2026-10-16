---
typ: repo
tags: [repo, gemm]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/repos/12-blocksparse.md:1-22; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:22
status: aktualne
---
# openai/blocksparse

**Biblioteka kerneli blokowo-rzadkich OpenAI (HEAD `89074c5`, 2020-07-13), martwa od 2020; werdykt: niska.**

Matmul i atencja blokowo-rzadka przez LUT budowany na hoście, maska w bloku jako bitmapa, kernele SASS tylko Maxwell/Pascal (pomiary OpenAI na Titan X Pascal). Dla nas gotowy wzorzec pętli z prefetchem kafla dla MMQ (Q2). Odrzucone: split-K pod spinlockiem, bo jest niedeterministyczny.

## Powiązane
- [[repo/_hub|repo]]
- [[how-to-optimize-in-gpu]]
- [[deepgemm]]
- [[mmq-epilog]]
- [[repos-30-przeglad]]
