---
typ: repo
tags: [repo, gdn, dsl]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/repos/17-tilegym.md:1-22; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:27
status: aktualne
---
# NVIDIA/TileGym

**Przykładowe kernele NVIDIA w CUDA Tile (commit `c742afc`, 2026-10-09), z łatkami dla Qwen3.5 i LFM2; werdykt: niska.**

Repo nie publikuje żadnych liczb wydajności. GDN decode „decode_vstream” liczy wyjście ze stanu sprzed aktualizacji, więc dwie redukcje po stanie biegną równolegle (bitowo; u nas część Q3). Chunked GDN używa dokładnego solve przy kluczach z normą L2; chunked GDN (WY) odrzucony, bo na gfx1100 dał −39% (Strata #888). Audyt „siatka w pełnych falach”.

## Powiązane
- [[repo/_hub|repo]]
- [[auto-gpu-kernel]]
- [[cutile-python]]
- [[gdn-fuzje-k2]]
- [[repos-30-przeglad]]
