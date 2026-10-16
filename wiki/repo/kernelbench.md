---
typ: repo
tags: [repo, ocena, agenci]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/repos/04-kernelbench.md:1-22; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:14
status: aktualne
---
# ScalingIntelligence/KernelBench

**Benchmark kerneli pisanych przez LLM (HEAD `423217d9`, 2026-03-05); bierzemy lepszą bramkę poprawności; werdykt: średnia (proces).**

Cztery poziomy zadań (100 operatorów, 100 fuzji, 50 architektur, 20 modeli HF), poprawność przez `torch.allclose` na wielu seedach, tolerancja 1e-4 fp32 i 1e-2 fp16/bf16, testy adwersarialne (reuse bufora z wynikiem referencji, modyfikacja wejść, inny strumień) i statyczny checker oszustw. Dla nas: diff listy kerneli przy A/B, zatruwanie buforów NaN, hash logitów w trybie wsadowym, A/A i kolejność ABBA.

## Powiązane
- [[repo/_hub|repo]]
- [[kernelagent]]
- [[tensara]]
- [[pomiar-abba]]
- [[repos-30-przeglad]]
