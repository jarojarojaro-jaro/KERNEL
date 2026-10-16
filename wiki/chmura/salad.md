---
typ: chmura
tags: [chmura, salad, wsl2]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/05-chmura-gpu-do-testow.md:21-23,55,68,136,203,298,365,404
status: aktualne
---
# SaladCloud (domowe PC graczy, WSL2)

**Sieć domowych komputerów do gier: tanie NVIDIA (3060…5090) i pięć klas Radeonów, ale tylko jako kontener w WSL2 bez SSH; nadaje się do sprawdzenia „czy działa u gracza na Windowsie”, nie do strojenia kerneli.**

- Radeony: RX 7800 XT (gfx1101), 7900 XT/XTX (gfx1100), 9060 XT (gfx1200), 9070 XT (gfx1201) za 0.04–0.17 $/h.
- Środowisko: kontener w WSL2, `/dev/dxg`, brak `/dev/kfd` i `/dev/dri`; obraz musi mieć ROCm ≥ 7.1 i `librocdxg` od hosta; bez SSH (web terminal); `rocm-smi` zwraca exit 0 nawet bez GPU.
- NVIDIA: np. 3090 od $0.09/h na najniższym priorytecie; 4 priorytety cenowe i wywłaszczanie.
- Rola w planie (raport 05): walidacja Windows/WSL2, 6 klas × 20 h ≈ $20/mies.; wyniki etykietować jako „WSL2-path”, bo nie są reprezentatywne dla PM4/HIP.
- Dla PM4: w WSL2 pakiet PM4 jest cicho pomijany, więc łatka 0060 musi się tam sama wyłączać.

## Powiązane
- [[chmura/_hub|Chmura]]
- [[wsl2-rocm]]
- [[vast-ai]]
- raport-05-chmura
- [[rx-7900-xtx]]
- [[radeony-do-wynajecia]]: inne źródła Radeonów (Hostkey, GigaGPU)
