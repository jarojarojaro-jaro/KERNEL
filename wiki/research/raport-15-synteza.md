---
typ: research
tags: [research, synteza, ranking]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15-synteza.md
status: aktualne
---
# Raport 15: synteza fali researchu (14, 15a–15f)

**Ranking działań po audycie głośnych twierdzeń: najpierw fabryka v1 i logowanie lookupu, potem ogon lookupu szerokości 8, PM4-PDL dla LFM i port `kvq` na CUDA.**

Audyt: 381 t/s HyperQwen i 273 t/s tqLLM to głównie zadania kopiowania; „nie zmienia wyjścia” w Magnitude to tolerancja, nie bity; PFlash v2 jest szybki, ale stratny (po polsku sonda 1/10). O nas: 36% czasu tokena LFM na XTX to nie strumieniowanie wag; nasze MTP już kopiuje z kontekstu (96.8% zgodności tam, gdzie trafia lookup); długi kontekst na NVIDIA ogranicza atencja. Lista eksperymentów z kosztami czeka na zgodę.

## Powiązane
- [[research/_hub|research]]
- [[research/raport-15a-monokernel|15a]] · [[research/raport-15b-spekulacja-frontier|15b]] · [[research/raport-15d-prefill-dlugi-kontekst|15d]]
- [[metody/fabryka-v1|fabryka v1]]
