---
typ: repo
tags: [repo, trwale-kernele]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/repos/16-mkernel.md:1-22; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:26
status: aktualne
---
# uccl-project/mKernel

**Wielo-GPU trwałe kernele z UC Berkeley (HEAD `97e916b`, 2026-10-01); zostają tylko wzorce synchronizacji; werdykt: niska.**

Trwała siatka = liczba SM z rolami według `blockIdx`, zależności per blok wierszy zamiast bariery siatki, liczniki „ostatni kafel podnosi flagę”, kolejka gotowych zadań w kernelu, flagi epokowe bez zerowania. Dla nas wzorce do L4 (trwały kernel MoE w LFM): liczniki gotowości, epoki, ładowanie wag przed czekaniem.

## Powiązane
- [[repo/_hub|repo]]
- [[deepgemm]]
- [[pplx-kernels]]
- [[fuzje-lfm-moe]]
- [[repos-30-przeglad]]
