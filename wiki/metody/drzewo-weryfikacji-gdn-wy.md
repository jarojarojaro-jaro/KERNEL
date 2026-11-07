---
typ: metoda
tags: [metody, spekulacja, drzewa, gdn]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/product/research/66d-saber-engine-rdna.md:80-99,159; Saber `sgdn_tree.h:1-10`, `spec_tree.rs:13-22,490`, `p27_tree_advl.hip` (c8a1e84); ~/KERNEL/product/research/24s-proza-drzewa.md:8-21
status: do-sprawdzenia
---
# Drzewo weryfikacji na hybrydzie GDN (forma WY)

**Saber weryfikuje drzewo draftów na modelu z GDN: z zatwierdzonego stanu liczy w formie WY wyjście każdego węzła (do 10–16) po zbiorze przodków, zapisuje „record”, a stan dla zaakceptowanej ścieżki aplikuje osobny „advance”; atencja dostaje maskę przodków. Ich symulacja: +7.8% (raport 66d, 2026-11-07).**

- Bezstratne przy T=0. Przy T>0 potrzebna rejekcja wielodraftowa (SpecInfer), inaczej rozkład się zmienia.
- Nasz sufit offline (24s, proza T=1): drzewo statyczne +1.2%, dynamiczne +3.9…4.7%, pod warunkiem kosztu wiersza weryfikacji ≤ 0.57 ms (dziś 0.85).
- Gdzie może wygrać: kod i JSON przy T=0, szacunek +3…8%; czat T=1 0…+4% `[SZACUNEK]`.
- Topka nie ma drzewa (łańcuch + lag/replay GDN). Koszt pełnego wdrożenia 1–2 tygodnie (kernele GDN tree, KV gałęzi, maska przodków w `kvq`).
- Bramka: symulacja CPU na logach MTP (best-first, budżet 4–9 węzłów, top-2 na głębokość), dopiero potem kod.

## Powiązane
- [[metody/_hub|metody]]
- [[raport-24s-drzewa-proza]]
- [[koszt-szerokosci-weryfikacji]]
- [[gdn-replay]]
- [[saber-engine]]
- [[raport-66-synteza]]
