---
typ: research
tags: [research, repo, przeglad]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:1-93
status: aktualne
---
# Przegląd 30 repozytoriów (REPOS-PODSUMOWANIE)

**Przegląd 30 repo o kernelach GPU + aktualizacja TensorFold (2026-10-14): werdykty, ranking eksperymentów dla LFM i Qwena oraz lista odrzuconych pomysłów.**

Punkt odniesienia: Qwen3.8-27B 104 t/s (krok 28.9 ms, MTP), LFM2.5-24B-A2B ~240 t/s (4.1 ms/token, KV q8_0, 416 kerneli/token, ~2.5 µs na granicę kernela w grafie HIP). Liczby z repo to ich pomiary, zyski dla nas to szacunki.
- Najwyższe werdykty: hipfire (średnia–wysoka; PM4 replay: 219.6 → 251.8 t/s), lucebox (DFlash2 blok 16), pygpubench (bit DLC), KernelBench/KernelAgent/AKO4ALL (proces).
- LFM: L1 replay tokenu jako bufor poleceń (+10–30% szac.), L2 atencja decode KV q8_0, L3 DLC dla MMVQ n=1, L4 trwały kernel MoE.
- Qwen: Q1 DFlash2 blok 16 (kod 175–300 t/s zamiast ~110–130 szac.), Q2 potok kafli MMQ, Q3 GDN.
- Metodologia: sufit pasma, ATT, bramka poprawności, kanarki KLD, LOO 54 łatek, Kernel Tuner.
- Odrzucone: TileLang/cuTile/Triton (brak iu8), chunked GDN (−39%), out-of-core, split-K pod spinlockiem.

## Powiązane
- [[research/_hub|research]]
- [[repo/_hub|wszystkie repo]]
- [[hipfire]]
- [[lucebox]]
- [[raport-07-metody]]
- [[lfm-runda-4-pm4]]
