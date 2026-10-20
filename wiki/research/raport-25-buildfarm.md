---
typ: research
tags: [research, buildy, vast, rbuild]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/25-buildfarm.md:7-24,37-45,67-70; ~/KERNEL/product/research/26-kolejka-gpu-wieczor.md:15
status: aktualne
---
# Raport 25: zdalny serwer buildów (Vast) i `rbuild`

**`~/qwen-opt/tools/rbuild <worktree>` buduje na zdalnym 24 vCPU: pełny build topki 232–271 s, przyrostowo 9–12 s, wynik bitowo identyczny z lokalnym (109/109 plików `bin/`); kolejka 26 potwierdziła binarki (MUL_MAT 822/822, FA 567/567, md5 bez zmian) (2026-10-19).**

- Maszyna $0.094/h, ~1.2 h ≈ $0.11 (`25:15`). Lokalny pełny build `-j2` trzymał quiet.lock ~50 min (`25:24`).
- Pułapka: ccache zmienia `__hip_cuid_*` (zależy od ścieżki wyjścia) – TU HIP bez ccache (`25:37-39`).
- Ten sam ROCm 10.0.0~pre4 z debów rocmradeon/apt/26.14; obraz `rocm/dev-ubuntu-24.04:10.0.0-full` to inne wydanie (`25:28-29,69`).
- Ochrona: `buildfarm*` pomijane przez `idle-watch.py` i `down.sh --all`, bo teardown innego agenta skasował serwer (`25:45`).
- Decyzje: [[2026-10-19-buildy-przez-rbuild]], [[2026-10-19-chmura-bez-destroy-all]].

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[2026-10-19-buildy-przez-rbuild]]
- [[2026-10-19-chmura-bez-destroy-all]]
- [[vast-ai]]
