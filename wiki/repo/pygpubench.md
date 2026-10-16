---
typ: repo
tags: [repo, pomiar, mall]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/repos/28-pygpubench.md:1-14,53,122-126; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:38
status: aktualne
---
# gpu-mode/pygpubench

**Biblioteka do mierzenia krótkich kerneli niezaufanego kodu (HEAD `286841bf`, 2026-08-18); daje eksperyment z bitem DLC na RDNA3; werdykt: średnia.**

Harness nieprzenośny (tylko CUDA, obrony in-process). Lekcja o polityce cache przeniesiona na RDNA3: bit DLC = „nie alokuj w MALL”; 1-kolumnowe MMVQ (cały dekod LFM, draft MTP Qwena) dziś alokuje w MALL. Eksperyment L3: DLC dla wag n=1, szacunek 0–3%, bitowo, 0.5–1 dnia. Poprawki metodologii: mikrobench widzący MALL, czyszczenie cache odczytem bufora > L2 + MALL (6 + 96 MB).

## Powiązane
- [[repo/_hub|repo]]
- [[tensara]]
- [[mixbench]]
- [[rdna3-gfx1100]]
- [[repos-30-przeglad]]
- [[gpu-mode-reference-kernels]]
