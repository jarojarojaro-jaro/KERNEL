---
typ: lekcja
tags: [lekcje, spekulacja, mtp]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15b-spekulacja-frontier.md:11,199-209; ~/KERNEL/product/research/15b-sim/results.txt:3-5
status: aktualne
---
# MTP już kopiuje: zmierz P(MTP | lookup), zanim dołożysz drafter z kontekstu

**Na 69 207 pozycjach z prawdziwymi łańcuchami MTP P(draft MTP trafia | lookup trafia) = 0.968 wobec 0.765 bazowo, więc lookup z kontekstu dokłada głównie ogon za pozycją 4, a nadpisywanie draftów MTP lookupem to strata.**

- Łańcuch d2 / d3 / d4 przy trafnym lookupie: 0.938 / 0.914 / 0.899; pełne 4 drafty na długiej kopii: 0.935.
- Nadpisanie głowy (HyperQwen) psuje ~22% przypadków, w których lookup chybia, a MTP trafia: −1…−2% na czacie i kodzie, do −4% na tekście agenta.
Reguła: przed dołożeniem dowolnego drugiego draftera (n-gram, lookup, kopia z kontekstu) policzyć offline warunkową trafność obecnego draftera na pozycjach, gdzie nowy trafia; dokładać tylko to, czego obecny nie pokrywa (tu: ogon i pominięcie kosztu draftu w łańcuchach).

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-jeden-prompt]]
- [[lekcja-mtp-glowica-optimum]]
- [[glowica-mtp]]
- [[2026-10-16-lookup-kopiowalnosc]]
