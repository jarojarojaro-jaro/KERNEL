---
typ: lekcja
tags: [lekcje, pomiar, spekulacja, konkurencja]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15c-nowe-silniki.md:56-58,72,249,440,444; ~/KERNEL/product/research/15b-spekulacja-frontier.md:10
status: aktualne
---
# Benchmark na kopiowaniu zawyża spekulację

**Zadania „powtórz tekst” albo kopiowanie dokumentu dają 4–6+ tokenów na krok i nic nie mówią o nowym pisaniu; tak powstały liczby Magnitude, tqLLM i HyperQwen.**

- Magnitude: 2.19× vs Ollama na „powtórz fragment Moby-Dick” przy 64k; Qwen3.8-27B na Sparku wymaga ≥ 4.8 tok/rundę (roofline).
- tqLLM: 273.1 t/s przy T=0 i 320 tokenach (LocalMaxxing), 350–365 t/s na kopii, a 131–155 t/s na streszczeniach WikiText.
- HyperQwen: 381 t/s na kopii verbatim, na czacie 133 vs 131.
Reguła: każdy raport prędkości ma dwie klasy obciążenia (nowe pisanie: nasz spec_sweep PL/EN T=1; kopiowanie/edycje) oraz T=0 i T=1 osobno; cudze liczby czytać dopiero po sprawdzeniu promptu.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-jeden-prompt]]
- [[lekcja-baseline-wlasnego-silnika]]
- [[pomiar-abba]]
- [[raport-15c-nowe-silniki]]
