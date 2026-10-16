---
typ: lekcja
tags: [lekcje, proces, latki]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15f-agentowa-nauka.md:39,160-176
status: aktualne
---
# Dowód rozproszony poza commitem

**Tylko 25/70 commitów łatek ma w treści komplet dowodu (liczba + powtórzenia/przeplot + marker poprawności), 0/70 podaje niepewność, a 25/70 nie ma żadnej liczby – dowody leżą w NOTES.md i `~/wt/*/REPORT.md`, niczym niezwiązane z SHA.**

Wynik E-A (regex po `patches/llama.cpp-amd-opt/*.patch`, heurystyka): liczba z jednostką 45/70, „przed → po” 48/70, przeplot/A-B 32/70, md5 33/70, hash logitów 20/70, test-backend-ops 23/70, KLD 6/70, wyłącznik nazwany 28/70, CI/σ 0/70, UNMEASURED 5/70.
Reguła: każde twierdzenie o łatce ma wiersz w ledgerze powiązany z SHA commita, binarką i CI; scalenie wymaga wiersza CONFIRMED (propozycja [[fabryka-v1]]).

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-label-to-nie-binarka]]
- [[lekcja-commity-bez-pomiaru]]
- [[seria-amd-opt]]
- [[raport-15f-agentowa-nauka]]
