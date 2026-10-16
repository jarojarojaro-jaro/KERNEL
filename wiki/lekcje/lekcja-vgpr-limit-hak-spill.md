---
typ: lekcja
tags: [lekcje, kernele, rejestry, wydajnosc]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/12-bit-exact-spekulacja.md:303-316
status: aktualne
---
# Kernel na limicie VGPR: hak we wspólnym szablonie spilluje ścieżkę domyślną

**Haki diagnostyczne bitexact (`ce2105d32`) dodane do wspólnej instancji `flash_attn_ext_kvq<256,8,Q4_0>`, która miała 255/256 VGPR, wywołały 14 spillowanych VGPR (scratch 60 B) w ścieżce domyślnej i −6% tg128 (40.5 vs 43.05 t/s) na 7900 XTX, choć haki działały tylko z env (2026-10-16).**

Poprawka `02813c1c5`: osobna instancja szablonu (`bx_tok`) dla wariantu bitexact; domyślny kernel wrócił do 0 spilli i 43.15/43.16 t/s (= produkcja).

Reguły:
- dodatki przy kernelu na limicie rejestrów jako osobna instancja szablonu, nie `if` w runtime;
- per commit sprawdzać `.vgpr_spill_count` w ISA (`isa.sh`) – offline wskazuje przyczynę bez GPU;
- bisekcja wydajności: ABBA tg128 `-r 5` per commit w osobnym worktree/buildzie.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-commity-bez-pomiaru]]
- [[wylacznik-w-kazdej-latce]]
- [[fattn-kvq]]
- [[2026-10-16-bit-exact]]
