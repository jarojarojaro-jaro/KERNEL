---
typ: repo
tags: [repo, llama-cpp, fork, kwanty]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/10-post-training.md:329-331; ~/KERNEL/wiki/modele/bonsai.md:5-15
status: aktualne
---
# PrismML-Eng/llama.cpp (fork pod Bonsai)

**Fork llama.cpp od PrismML potrzebny do formatów PQ2_0 i PTQ1_0 modelu Ternary Bonsai 2 27B; u nas klon „prism” testowany na RTX 3060.**

Ternary Bonsai 2 27B to Qwen3.8-27B w trytach {−1,0,+1} z FP16 skalą na grupę 128 w obróconej bazie Hadamarda; raport 10: 1.76 bpw, 5.93 GB, 98.2% średniej FP16 na 20 benchmarkach. Formaty PQ2_0/PTQ1_0 wymagają forka; upstream od b11555 obsługuje `Q2_0`, a nasz `pq2_to_q2.py` robi bezstratny repack PQ2_0 → Q2_0. Pomiar na RTX 3060 (2026-10-16): perplexity wikitext-2 prism PQ2_0 i PTQ1_0 8.6154 ± 0.17549 vs upstream Q2_0 8.6171 ± 0.17553. Metoda treningu Bonsai nie jest ujawniona.

## Powiązane
- [[repo/_hub|repo]]
- [[ik-llama-cpp]]
- [[llama-cpp-fork]]
- [[bonsai]]
- [[rtx-3060]]
