---
typ: repo
tags: [repo, agenci, proces]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/repos/21-ako4all.md:1-14,196-200; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:31
status: aktualne
---
# TongmingLAIC/AKO4ALL i AKO4X

**Protokół dla agenta optymalizującego kernele (commit `bbd0e1c`, 2026-09-15), nie kod kerneli; werdykt: średnia (proces).**

Jeden `SKILL.md` (175 linii) dla Claude Code, szablony `HINTS.md`/`ITERATIONS.md`, evaluator w stylu KernelBench; pętla profil → edycja → bench → log → commit. AKO4X dokłada kampanie wielorundowe ze świeżym sub-agentem dziedziczącym archiwum wariantów. Dla nas: test leave-one-out całego stosu 54 łatek (zrobione, zob. LOO), archiwum per rodzina kerneli z pułapkami „Why/WHEN”, rozdział sygnału (szybki pomiar) od werdyktu (spec_sweep z przeplatanym A/B).

## Powiązane
- [[repo/_hub|repo]]
- [[kernelagent]]
- [[atrex-kernel-agent]]
- [[loo]]
- [[repos-30-przeglad]]
