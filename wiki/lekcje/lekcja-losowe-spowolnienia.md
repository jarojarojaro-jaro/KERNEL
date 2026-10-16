---
typ: lekcja
tags: [lekcje, pomiar, lfm]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:278; ~/KERNEL/qwen-opt/NOTES.md:359; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:56
status: aktualne
---
# Losowe spowolnienia per proces

**Gate+up w LFM trwał 24.3 albo 27.2 µs w 4 z 8 profili, także na buildzie bez zmian; A/B trzeba robić na wielu procesach, nie na jednym.**

Tryb awarii #17. Hipotezy z przeglądu repo (L9): inny układ fizyczny VRAM i TLB w każdym procesie (NVIDIA open-gpu-kernel-modules), eviction KFD; gdy trafia, kosztuje ~0.11 ms/token. Część rozrzutu tłumaczyła siatka 3072 bloków (zob. siatka pełna fala).

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-siatka-pelna-fala]]
- [[lekcja-szum-t-s-przy-t1]]
- [[nvidia-open-gpu-kernel-modules]]
- [[fuzje-lfm-moe]]
