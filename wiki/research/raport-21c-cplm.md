---
typ: research
tags: [research, spekulacja, architektura]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21c-copy-paste-lm.md:1-226; https://arxiv.org/abs/2610.19247
status: aktualne
---
# Raport 21c: Copy-Paste Language Models (CPLM) – nie adoptujemy

**CPLM (Godey & Artzi, arXiv 2610.19247, 13.10.2026) to architektura wyjścia trenowana od pretrainingu – pointer po stanach ukrytych kontekstu + token bramki `<copy>` + klucz `<sink>` – a nie optymalizacja inferencji; dekodowanie spowalnia o 1.0–3.8% (Tab. 6), więc jej nie adoptujemy, a z jej intuicji bierzemy tylko regułę AGR dla naszego lookupu.**

- Zysk w ~75% pochodzi z gradientu do backbone'u (stop-gradient −0.008 vs −0.031 nat, Tab. 15); doklejony neural cache na wytrenowanym modelu daje 0 (Tab. 9: PPL 9.17 → 9.17).
- „<3% narzutu” to przepustowość treningu 1.7B (×0.969); pamięć treningu ×1.096; krok dekodowania do ×1.038 (9B, B=128).
- Jakość: wiarygodna przy 135M (3 seedy); od 1.7B jeden seed. Zero-shot +0.37…+0.84 pkt głównie z LAMBADA (bez niej +0.30 / +0.33 / −0.10). Duże wyniki tylko tam, gdzie baseline nie widzi kontekstu (SW-256, needle 14.3 → 99.4). NanoGPT speedrun −11.3% to otwarty PR #379.
- „LM head bottleneck” = utrata gradientu przy V ≫ D w treningu, nie koszt LM head przy dekodowaniu ([[lekcja-lm-head-bottleneck]]).
- Nasze pomiary CPU: [[2026-10-19-sufit-pointera-lookup]], [[2026-10-19-tokeny-spoza-slownika-draftu]]; metoda do wdrożenia: [[agr-lookup-zgodny-z-mtp]].
- Plan: A) CPLM nie; B) AGR2 – mały eksperyment; C) słownik 64k ∪ kontekst – później; D) wyuczony pointer jako drafter – nie.

## Powiązane
- [[research/_hub|research]]
- [[raport-16b-lookup-tail]]
- [[lekcja-mtp-juz-kopiuje]]
- [[2026-10-18-lookup-ogon]]
