---
typ: eksperyment
tags: [eksperymenty, spekulacja, lookup, agent]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/15b-spekulacja-frontier.md:160-249; ~/KERNEL/product/research/15b-sim/results.txt:1-20; ~/KERNEL/product/research/16b-lookup-tail.md:10-23
status: aktualne
---
# 2026-10-16: kopiowalność naszych workloadów (symulacja CPU)

**Symulacja CPU na 524 743 tokenach odpowiedzi Qwena i 7.2 M tokenów wyjść agenta omp: lookup z kontekstu trafia 1–17% pozycji czatu i 27–60% wyjść agenta; nadpisywanie głowy (HYB) szkodzi, doklejanie ogona (EXT) pomaga tylko na edycjach.**

Metoda: lookup jak w HyperQwen (sufiks 4..12, kontynuacja do 15), prawdziwe łańcuchy głowicy MTP z `mtp-train/data/ext_p1/chain.bin` (69 207 pozycji) i model skalibrowany dla reszty; koszt kroku z XTX (MTP n=4 27.74 ms, V(W) z `vcost_qwen-k4b.csv`).

| klasa | d1 | ≥ 8 |
|---|---|---|
| spec_sweep EN / PL / kod | 0.13 / 0.07 / 0.07 | 0.03 / 0.00 / 0.01 |
| agent: tekst | 0.16 | 0.025 |
| agent: bash | 0.51 | 0.20 |
| agent: edit hashline | 0.58 | 0.26 |
| agent: edit str_replace | 0.60 | 0.38 |
| agent: write | 0.27 | 0.07 |

Polityki (t/s vs MTP n=4): prawdziwe drafty – HYB-16 −0.9% (wszystkie), EXT-8 0.0%; agent krótki kontekst / ~32k – EXT+CH-16 mieszanka +2.9% / −3.8%, EXT+CH-8 +2.4% / +0.2%; hashline +8.2% (krótki), str_replace +22.9%. Koszt szerokości: V(16) − V(5) = +7.09 ms, V(8) − V(5) = +2.48 ms. Ograniczenia: MTP dla agenta to model (AL 3.2 założone), wyjścia agenta pisał Claude, nie Qwen.

Realizacja na serwerze: [[2026-10-18-lookup-ogon]] (mvs ×2.41 przy W16).

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[raport-15b-spekulacja-frontier]]
- [[lekcja-mtp-juz-kopiuje]]
- [[2026-10-16-mtp-pl-pilot]]
- [[glowica-mtp]]
