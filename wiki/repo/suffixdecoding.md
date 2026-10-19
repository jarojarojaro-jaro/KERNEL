---
typ: repo
tags: [repo, spekulacja, lookup]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/18-nastepna-fala.md:340-354; https://arxiv.org/abs/2411.04975
status: do-sprawdzenia
---
# SuffixDecoding / ArcticInference: globalne drzewa sufiksów

**Spekulacja bez modelu draftującego z drzew sufiksów budowanych z promptów i wcześniejszych wyjść (także między żądaniami); na workloadach agentowych do ×5.3, ×2.8 względem EAGLE-2/3 (arXiv 2411.04975, w vLLM jako „suffix”).**

Dla nas: pomysł #6 raportu 18 – globalny cache sufiksów między żądaniami, sesjami i agentami, ponad dzisiejszy lookup z kontekstu ([[2026-10-18-lookup-ogon]]); szacunek +5–15% na mieszance agenta, bramka: replay sesji omp ≥ 3%.

## Powiązane
- [[repo/_hub|repo]]
- [[mtplx]]
- [[agr-lookup-zgodny-z-mtp]]
