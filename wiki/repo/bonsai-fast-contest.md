---
typ: repo
tags: [repo, spekulacja, gdn, dflash, llama-cpp, cuda, mlx]
aktualizacja: 2026-10-24
zrodlo: ~/KERNEL/product/research/60b-apple-engines-bonsai.md:3.4-3.6,4; https://www.yukon.org/cudafast?benchmark=bonsai2-9b&platform=cuda; https://www.yukon.org/mlxfast?benchmark=bonsai2-9b&platform=mlx; github.com/Layr-Labs/cudafast-bonsai2-9b-engine PR 9,24,73,74,147; github.com/Layr-Labs/mlxfast-bonsai2-9b-engine PR 227,231,424,431,433,467
status: aktualne
---
# Konkurs cuda.fast / mlx.fast: Bonsai 2 9B

**Tygodniowy konkurs Yukon + PrismML (zamknięty 2026-10-22): Ternary Bonsai 2 9B single-stream; CUDA (llama.cpp, DGX Spark) 85.9 → 576.7 tok/s, MLX (M5 Max) 144.8 → 959.6 tok/s; techniki w opisach PR, większość już mamy.**

- Wynik `prefill^0.25 × decode^0.75`; tolerancja near-tie ≤ 40/1000. Spekulacja DFlash2 przy głębokości 15 (~10 tok/rundę) dała +117%, resztę kernele.
- CUDA, ArthurOstapenko (#73, #74): 150.6% → 316.2%, decode 284.3 → 513.4 tok/s. Leniwe cofanie GDN (#9, decode +7.5–8.3%; u nas [[gdn-replay]]), pierścień TMA + L2 `evict_first` na wagach (×1.033), fuzja granicy warstwy weryfikacji, kopie wag kafelkami (#24: 230–236 vs 200–210 GB/s, +3.4 GiB).
- MLX: drafter przekwantowany w pamięci do 4 bitów (#227: wynik 3.34 → 3.84), drzewo 15 węzłów w tej samej 16-wierszowej weryfikacji (#424: 122 → 113 rund), restart gałęzi GDN od zapisanego stanu (#433), taśma delt GDN (#467: ×1.02), sito głowicy draftu na pół K (#431).
- Repo MIT; w compwatch (CUDA A, MLX B).

## Powiązane
- [[repo/_hub|repo]]
- [[prism-llama-cpp]]
- [[bonsai]]
- [[drafter-dflash]]
- [[raport-24s-drzewa-proza]]
- [[raport-60b-apple-bonsai]]
