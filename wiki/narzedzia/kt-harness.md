---
typ: narzedzie
tags: [narzedzia, autotuning, mmvq, gdn]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/tools/kt/kt.py:1-19; ~/wt/tools6/REPORT.md:7-12
status: aktualne
---
# Kernel Tuner harness (kt/)

**Rusztowanie Kernel Tunera dla gorących kerneli dekodu na gfx1100: `mmvq_n1`, `moe_gate_up`, `moe_down`, `gdn`; tylko `tune` dotyka GPU.**

Komendy `kt.py`: `shapes` (kształty z GGUF, CPU), `space` (przestrzenie i konfiguracje produkcyjne), `compile` (offline gfx1100 + VGPR/SGPR/LDS/scratch/occupancy), `fake` (dane i referencje numpy), `stub` (stub C dla KT), `table` (tabela per kształt jako JSON i include C), `tune` (na GPU, pod lockami). Źródła harnessu kompilowane z drzewa `~/wt/tools6` (amd-opt + hak `MMVQ_TUNE_NWARPS_N1`). Pliki: `mmvq_kt.hip`, `gdn_kt.hip`, `kt_mem.hip`, `shapes.json`.

## Powiązane
- [[narzedzia/_hub|narzedzia]]
- [[loo-py]]
- [[kernel-tuner-repo]]
- [[kernel-tuner]]
- [[mmvq-n1-wiersze]]
