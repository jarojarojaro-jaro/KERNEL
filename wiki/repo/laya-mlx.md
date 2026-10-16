---
typ: repo
tags: [repo, modele-decyzyjne]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/10-post-training.md:42,268-294,316-323
status: aktualne
---
# laya-mlx i Laya (model decyzyjny)

**Laya (Convai Innovations) to nieautoregresywny encoder decyzyjny 322–421M, a laya-mlx (mizorewww) jego port MLX; za wolne do decyzji per token.**

Laya: wejście stan + pytania typowane (`choice`/`score`/`noul`), wyjście skalibrowane prawdopodobieństwa w jednym przejściu; checkpointy ModernBERT-large 421M i mmBERT-base 322M; czasy ~33 ms na T4 i 193–464 ms na CPU. laya-mlx (Apache-2.0): 13.4 ms (421M) i 7.4 ms (322M) P50 na M3 Max. Raport 10 (2026-10-16): 7.4 ms to 27% całego kroku Qwena i 2.2× token LFM, ~74× budżetu 0.1 ms na decyzję. Werdykt: sensowne tylko raz na żądanie (router mały ↔ duży model), nie w pętli spekulacji.

## Powiązane
- [[repo/_hub|repo]]
- [[speculators-specforge]]
- [[tensorfold]]
- [[lfm2-5-24b-a2b]]
