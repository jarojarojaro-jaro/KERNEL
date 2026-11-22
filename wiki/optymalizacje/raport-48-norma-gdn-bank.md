---
typ: optymalizacja
tags: [optymalizacje, gdn, xtx]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/48-norma-n4-gdn-bank.md:1-58
status: aktualne
technika: drugi bank stanu GDN
werdykt: odrzucone
zysk: E0 −0,4% (v1/v2); v3 nierozstrzygnięty
dowod: raport-48-norma-gdn-bank
model: qwen3-8-27b
karta: rx-7900-xtx
---
# Raport 48: rms_norm 4 vs 5 wierszy, drugi bank stanu GDN

**Normy 4-wierszowe wolniejsze przez rozruch zegara po bezczynności, nie w decode; bank GDN v1/v2 bitowo zgodny, ale E0 −0.4% → nie; v3 nierozstrzygnięty (przebieg zaburzony hostem).**

- v3: host lookup 13–15 ms vs 6.9 ms, dryf A1→A2 +2.5% → [[lekcja-higiena-pomiaru]].

## Powiązane
- [[raporty-2026-10-20-21]]
- [[pamiec-stanu-gdn]]
- [[rmsnorm-dpp]]
