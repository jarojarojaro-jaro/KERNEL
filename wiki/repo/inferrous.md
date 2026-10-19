---
typ: repo
tags: [repo, rust, nvidia]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21g-nowe-silniki.md:56-89,276-282; https://github.com/bitemyapp/inferrous (`405bfd3`)
status: aktualne
---
# inferrous (bitemyapp): silnik w Ruście z kernelami w Ruście

**Badawczy silnik (Apache-2.0/MIT, 2 commity, 3 gwiazdki) z 31 kernelami napisanymi w Ruście (cuda-oxide → PTX, sm_120), tylko Qwen3-8B W8A8 na RTX PRO 6000 Max-Q: 182.3 / 178.2 / 170.5 t/s (prompt 5 / 129 / 512) wobec vLLM Humming 144.4 / 143.3 / 142.9 – rzetelne 84% pasma, ale bez porównania z llama.cpp i z własną bramką zgodności z PyTorch, która nie przechodzi (rel. L2 logitów 9–11%) (raport 21g, 2026-10-19).**

- Dekod na DP4A, KV i głowica BF16, jedno żądanie, tylko greedy, kontekst ≤ 4096. 7.88 GB/krok.
- Runda 6 „keep DRAM busy”: 252 kernele latencyjne = 642 µs z 5755 µs kroku; prefetch L2 z 16 dodatkowych CTA chowa 80–85% ich czasu, łącznie z PDL +6.5…7.8%. Dla nas nowe tylko na NVIDIA (na XTX analogiczny „touch” dał szum, [[lekcja-prefetch-mall-xtx]]).
- Bezstratna głowica BF16 → 12 bit (75.8% bajtów) – nie dla nas, nasze głowice są skwantowane.
- Werdykt: brak dla produktu; przestroga: [[lekcja-bit-exact-wobec-siebie]].

## Powiązane
- [[repo/_hub|repo]]
- [[pdl-mmvq-trigger]]
- [[raport-21g-nowe-silniki]]
