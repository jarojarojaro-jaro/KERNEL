---
typ: repo
tags: [repo, out-of-core]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/repos/24-falkon.md:1-9; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:34
status: aktualne
---
# FalkonML/falkon

**Biblioteka regresji z jądrem (Nyström + PCG) liczona blokami, także out-of-core (HEAD `04f168e`, 2026-05-13); werdykt: brak.**

Iloczyn macierz jądra × wektor bez materializacji macierzy, na poziomie wywołań torch. Dla inferencji LLM bez wartości: out-of-core / offload wag do RAM nie pomaga, bo PCIe jest 20–40× za wolne na wagi czytane w każdym tokenie.

## Powiązane
- [[repo/_hub|repo]]
- [[keops]]
- [[gpu-kernel-engineer-from-scratch]]
- [[baco-runtime-suspend]]
- [[repos-30-przeglad]]
