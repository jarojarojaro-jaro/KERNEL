---
typ: repo
tags: [repo, moe, gemm]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/repos/03-deepgemm.md:1-22; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:13
status: aktualne
---
# deepseek-ai/DeepGEMM

**Biblioteka kerneli tensor-core DeepSeek (HEAD `1fc9c66`, 2026-10-14); bierzemy harmonogram „Mega MoE” i potok kafli; werdykt: średnia.**

GEMM FP8/FP4/BF16 z JIT (NVCC w runtime), grouped GEMM po osi M, trwały grid = liczba SM, specjalizacja warp-group. „Mega MoE” to cała warstwa MoE w jednym trwałym kernelu: zadanie L2 wydawane dopiero, gdy wszystkie potrzebne L1 zostały pobrane, więc bez zakleszczeń i bez gwarancji współrezydencji. Liczby repo to pomiary DeepSeek (H800/B200). U nas inspiracja dla L4 (trwały kernel MoE w LFM, szacunek −0.2…−0.4 ms/token) i Q2 (potok ładowania kafli w MMQ prefill, szacunek +3–12%).

## Powiązane
- [[repo/_hub|repo]]
- [[flashinfer]]
- [[mkernel]]
- [[prefill-mmq-fa]]
- [[repos-30-przeglad]]
