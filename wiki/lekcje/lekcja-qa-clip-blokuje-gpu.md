---
typ: lekcja
tags: [lekcje, kolejka, landing]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/app/landing/scripts/qa/README.md:13; ~/KERNEL/product/research/53-draft-shortlist.md:75
status: do-sprawdzenia
---
# qa:clip pod quiet.lock blokuje kolejkę GPU

**`bun run qa:clip` (każda strona × 6 szerokości) to długa praca CPU; puszczona pod quiet.lock trzyma blokadę i kolejka GPU stoi – długie łańcuchy CPU dzielić na osobne kroki `cpuheavy`.**

- To samo dla długich łańcuchów CPU pod jednym `cpuheavy --quiet` (raport 53).

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-kolejka-fifo-bilety]]
- [[landing-qa]]
