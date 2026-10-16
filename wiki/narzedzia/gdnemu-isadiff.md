---
typ: narzedzie
tags: [narzedzia, isa, emulator, gdn]
aktualizacja: 2026-10-16
zrodlo: ~/wt/gdn6-isa/gdnemu.py:1-12 (wc -l: 869); ~/wt/gdn6-isa/isadiff.py:1-3 (wc -l: 58); ~/wt/bx-isa/ (mmvqemu.py, isadiff_bx.py, gdnseq.py); ~/KERNEL/product/research/12-bit-exact-spekulacja.md:98
status: aktualne
---
# gdnemu.py i isadiff.py (dowód bitowości z ISA)

**Symboliczny emulator gfx11 wave32 wykonujący skompilowany ISA kerneli GDN bez GPU oraz `isadiff.py`, który sprawdza, że każdy kernel bazowy jest bajtowo identyczny w nowym buildzie.**

gdnemu (869 linii): stan całkowity konkretny, każdy float z pamięci to symboliczny liść, każda instrukcja float buduje hash-consowany węzeł DAG; dwa kernele są bitowo identyczne iff każde słowo wyjścia to ten sam węzeł. Kanonikalizacja tylko przez tożsamości ścisłe w IEEE-754 RNE (przemienność, fma(a,b,c)=fma(b,a,c), a−b=a+(−b)…). isadiff (58 linii) porównuje kod, deskryptor `.amdhsa_kernel` i metadane po przenumerowaniu etykiet. Rozszerzenia w `~/wt/bx-isa`: `mmvqemu.py`, `isadiff_bx.py` (862/862 kerneli MMVQ identycznych), `gdnseq.py`. Użyte w rundzie 6 i raporcie 12.

## Powiązane
- [[narzedzia/_hub|narzedzia]]
- [[llama-bx-diff]]
- [[kt-harness]]
- [[emulator-isa]]
- [[opt-gdn6]]
