---
typ: lekcja
tags: [lekcje, pomiar, abba]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/48-norma-n4-gdn-bank.md:42-58; ~/KERNEL/product/research/50b-mmvq-q5k.md:79; ~/KERNEL/product/research/49-mmvq-ogon-1024.md:68
status: aktualne
---
# Higiena pomiaru: CPU przez cpuheavy --quiet, ABBA nieważne przy hoście >7 ms lub dryfie >1%

**Raport 48 v3: przy konkurencji hosta lookup trwał 13–15 ms zamiast 6.9 ms, dryf A1→A2 +2.5% przewyższył każdy efekt – przebieg nierozstrzygnięty; reguła: ciężkie CPU tylko przez `cpuheavy --quiet`, ABBA nieważne, gdy czas hosta > ~7 ms albo dryf A1/A2 > 1%.**

- Reguła wpisana w kryteria 49/50b/50c (`50b:79`).

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-obciazenie-cpu]]
- [[pomiar-abba]]
- [[raport-48-norma-gdn-bank]]
