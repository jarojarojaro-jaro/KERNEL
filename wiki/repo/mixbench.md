---
typ: repo
tags: [repo, roofline, pasmo]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/repos/23-mixbench.md:1-9; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:33
status: aktualne
---
# ekondis/mixbench

**Mikrobenchmark „mixed operational intensity” (master `a8cab0c`, 2026-08-04) jako plan pomiaru sufitu pasma; werdykt: średnia.**

Jeden kernel czyta bufor i na każdym elemencie robi łańcuch `ci` FMA (33 wartości 0–512), co daje empiryczny roofline. Brak opublikowanych pomiarów dla RDNA3; liczby w repo są z MI210 i RTX 2070, nic nie uruchamialiśmy. Dla nas: zmierzyć sufit pasma dla rozmiaru pojedynczego wywołania (2–50 MB, zimna pamięć); jeśli idealny czytnik też ma ~720 GB/s, kończymy pracę nad pasmem MMVQ.

## Powiązane
- [[repo/_hub|repo]]
- [[pygpubench]]
- [[atrex-kernel-agent]]
- [[sufit-pasma-i-mapa-czasu]]
- [[repos-30-przeglad]]
