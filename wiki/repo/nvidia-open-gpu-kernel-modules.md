---
typ: repo
tags: [repo, sterownik, pamiec]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/repos/01-nvidia-open-gpu-kernel-modules.md:1-22; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:11
status: aktualne
---
# NVIDIA/open-gpu-kernel-modules

**Otwarte moduły jądra NVIDIA (commit `ca2d03e`, wydanie 615.78.08, 2026-10-07) czytane pod kątem zarządzania VRAM; werdykt: średnia.**

Brak kerneli obliczeniowych; wartość to porównanie zarządzania pamięcią. NVIDIA domyślnie daje strony 2 MB każdej alokacji VRAM ≥ 2 MB, a PMA nie schodzi poniżej 64 KB. Na amdgpu (jądro 6.8) PTE ma 4 KB i pole fragment liczone z wyrównania VA, a libhsakmt wyrównuje koniec, nie początek bufora. Wniosek dla nas: hipoteza na losowe spowolnienie gate+up w LFM (24.3 vs 27.2 µs, L9 w podsumowaniu) to inny układ fizyczny VRAM i TLB w każdym procesie. Tanie testy: wyrównanie bufora wag do 2 MB, `HSA_MAX_VA_ALIGN`.

## Powiązane
- [[repo/_hub|repo]]
- [[atrex-kernel-agent]]
- [[tensara]]
- [[rocr]]
- [[repos-30-przeglad]]
