---
typ: research
tags: [research, konkurencja, nvidia]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/16d-magnitude-vs-nasz.md:1-176
status: aktualne
---
# Raport 16d: Magnitude vs nasz fork vs upstream (X1 z 15c) + KLD Nemotrona

**Head-to-head na 3090 i 5060 Ti: przewaga naszych kerneli na NVIDIA bez draftera +30–40% i w prefillu +18–35%, a słabością są głębokie drafty – Magnitude wygrywa kopią/edycją kodu dzięki DFlash2 (7.3–7.8 tok/krok vs sufit 5 MTP n=4).**

- Wyniki: [[2026-10-16-magnitude-vs-fork]]. Luki Magnitude: [[magnitude]]. Mechanizmy: [[raport-16i-magnitude]].
- Harness Magnitude (prose-repeat 64k) liczy dekod 121.3 t/s, choć ich `timings` dają 80 `[INFERENCE: część pracy liczona jako TTFT]`; fork 71.5, upstream 58.5.
- Jakość: KLD Magnitude niemierzalne (brak logitów w API); proxy – prefiks/ratio kopii identyczne dla wszystkich silników.
- Wniosek dla planu: kandydaci – tańsza weryfikacja 16 tokenów, adaptacyjna głębokość, spec-copy/n-gram; raporty publiczne zawsze rozdzielają kopię i nowe pisanie.
- KLD Nemotrona `TOPK_MOE_NP2`: PASS ([[2026-10-16-nemotron-3090]]).

## Powiązane
- [[research/_hub|research]]
- [[raport-15c-nowe-silniki]]
- [[raport-14-nemotron-3090]]
- [[lekcja-benchmark-kopia]]
