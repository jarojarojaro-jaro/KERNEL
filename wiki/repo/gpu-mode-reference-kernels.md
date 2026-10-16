---
typ: repo
tags: [repo, ocena, konkurs]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/repos/09-gpu-mode-reference-kernels.md:1-21; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:19
status: aktualne
---
# gpu-mode/reference-kernels

**Definicje zadań i harness KernelBota GPU MODE (commit `f3295bb6`, 2026-09-17); ranking 2026 to nie źródło technik; werdykt: niska.**

Repo zawiera tylko wzorce PyTorch, `task.yml` i `eval.py`; zwycięskie rozwiązania (RadeonFlow, seb-v) czytano z zewnątrz. Zwycięzcy konkursu 2026 (MI355X) obchodzili testy albo łatali zależności, więc odrzucamy ranking jako źródło technik. Pomysły dla nas: int8 WMMA dla KQ, build z `-mcumode` (Q6), koszt granicy kernela na poziomie pakietów HSA (L1).

## Powiązane
- [[repo/_hub|repo]]
- [[pygpubench]]
- [[kernelbench]]
- [[mikrobench-granicy-kernela]]
- [[repos-30-przeglad]]
