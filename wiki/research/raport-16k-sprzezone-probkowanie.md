---
typ: research
tags: [research, spekulacja, sampler]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/16k-sprzezone-probkowanie.md:1-180
status: aktualne
---
# Raport 16k: sprzężone próbkowanie draftu (E-X4)

**Agent CoupledSampling przeniósł sprzężone próbkowanie Magnitude do forka za `LLAMA_SPEC_COUPLED` (domyślnie wył.): dowód i testy bezstratności przechodzą, zysk MTP przy T=1 nierozstrzygnięty (+0…+3.6%), A/B przerwane przez resety GPU.**

- Schemat z literatury: drafter-invariant speculative decoding przez sprzężenie Gumbela (arXiv 2408.07978), P(trafienie) ≥ (1 − TV)/(1 + TV); DFlash bez sprzężenia traci przy T=1 ~16–20%.
- Decyzja raportu: nie włączać domyślnie; kod zostaje w `opt-coupled`. Wartość niezależna od zysku MTP: spec == plain przy każdym T w trybie bitexact, fundament dla DFlash2 przy T=1, op [[gumbel-max]] dla przyszłego readoutu.
- Wyniki: [[2026-10-18-sprzezone-probkowanie-mtp]]; metoda: [[sprzezone-probkowanie-draftu]].

## Powiązane
- [[research/_hub|research]]
- [[raport-16i-magnitude]]
- [[2026-10-16-badamy-magnitude]]
- [[lekcja-ustalony-seed-to-nie-powtorzenie]]
