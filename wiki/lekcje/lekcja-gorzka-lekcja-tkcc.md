---
typ: lekcja
tags: [lekcje, agenci, metodologia, megakernel]
aktualizacja: 2026-11-05
zrodlo: ~/KERNEL/product/research/63e-metodologia-agenci.md:27-41,242-293
status: aktualne
---
# Gorzka lekcja Together Compiler: przepustowość pomiaru > wiedza ekspercka

**Together (TKCC, 2026-11-04): kuratorowana baza wiedzy obniżyła wynik agentów o 25–31%, 6 strategii eksperckich przegrało z naiwnym „zrób to jak najszybciej” (6.2× vs 4.9×), a sufit wyznacza przepustowość pomiaru (silnik trwały z hot-reloadem: 252× więcej eksperymentów).**

- Strukturalne logowanie badań zjadało do 43% wywołań narzędzi (8% czasu vs < 0.5% przy zwykłym Markdownie).
- Megakernel: na AMD GLM 5.3 +0.22%; bariera siatki 1.5–3.5 µs vs granica z PDL 0.5–1 µs. Zgodne z [[lekcja-megakernel-prefetch-nie-granica]].
- Kernele mierzone na losowych danych kłamią przy MoE i top-k (20 µs → 62 ms na prawdziwych).
- Dla nas: wiki ma być pamięcią wyników (co, w jakich warunkach, jaki wynik), nie narzuconą strategią; przełączanie flag w działającym serwerze zamiast restartu na każde ramię.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[megakernele-prior-art]]
- [[fabryka-v1]]
- [[reward-hacking-inferencji]]
