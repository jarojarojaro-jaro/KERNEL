---
typ: research
tags: [research, nvidia, cuda, enigma, vast, mtp]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/product/research/67-nvidia-vast-kampania.md; 67b-wybor-modeli-nvidia.md; 67c-nvidia-backlog-testow.md; ~/qwen-opt/cloud/results/nv67-*
status: aktualne
---
# Raport 67: kampania NVIDIA na Vast (Enigma) — trzy części

**Trzy raporty jednej kampanii: 67 = wyniki z 17 wynajętych kart, 67b = wybór modeli i kontekstu per klasa VRAM, 67c = pełny backlog testów NVIDIA wyciągnięty z bazy wiedzy.**

- **67 wyniki:** 262 144 z MTP na 4090 (79,1 t/s, +67,6%) i 5090 (86,9 t/s, +44,7%); 16 GB: warianty 27B z MTP OOM, potrzebny zapas ≥0,7 GiB na doładowanie kerneli CUDA; b11856→b12110 ±1% poza 3070 (−8%); `p-min` szkodzi. Zestawy PASS/FAIL i koszt $3,47.
- **67b modele:** 32 GB UD-Q6_K, 24 GB UD-Q4_K_M/XL przy 262 144, 16 GB ISTA IQ3_XXS-mtp bez MTP (200–217k), 12 GB Saluki-MTP 151k, 8–10 GB LFM2.5 z ekspertami w RAM. Gemma 4 odrzucona; Saluki ma CC BY-NC od 2026-11-05.
- **67c backlog:** 15 tematów z całej bazy, m.in. kernel `kvq` na CUDA (+25–37% przy 64k, nieuruchomiony), dobór typów KV, topka2 vs upstream, MTP n, batch 256, wątki z limitu cgroup, grafy i PDL na sm_120.

Poprawki w Enigmie z tej kampanii: `memory.ts` (model pamięci upstream MTP), `optimize.ts` (MTP n=3, `--spec-draft-n-ubatch 64`, batch 256), `catalog/index.ts` (zmierzony odstęp nvidia-smi→CUDA per karta, zapas 300 MiB na doładowanie kerneli, zmierzone plany 262 144).

## Powiązane
- [[research/_hub|research]]
- [[2026-11-07-kampania-nvidia-vast]]
- [[2026-11-06-final-mode]]
- [[glowica-mtp]]
- [[raport-27-3090-final]]
