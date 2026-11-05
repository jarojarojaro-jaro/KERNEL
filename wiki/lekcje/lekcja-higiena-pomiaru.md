---
typ: lekcja
tags: [lekcje, pomiar, abba]
aktualizacja: 2026-11-05
zrodlo: ~/KERNEL/product/research/48-norma-n4-gdn-bank.md:42-58; ~/KERNEL/product/research/50b-mmvq-q5k.md:79; ~/KERNEL/product/research/49-mmvq-ogon-1024.md:68; ~/KERNEL/product/research/63a-silniki-lokalne.md:124-136
status: aktualne
---
# Higiena pomiaru: CPU przez cpuheavy --quiet, ABBA nieważne przy hoście >7 ms lub dryfie >1%

**Raport 48 v3: przy konkurencji hosta lookup trwał 13–15 ms zamiast 6.9 ms, dryf A1→A2 +2.5% przewyższył każdy efekt – przebieg nierozstrzygnięty; reguła: ciężkie CPU tylko przez `cpuheavy --quiet`, ABBA nieważne, gdy czas hosta > ~7 ms albo dryf A1/A2 > 1%.**

- Reguła wpisana w kryteria 49/50b/50c (`50b:79`).
- Ciepły vs zimny (Strata PR #4366, R63a): ogłoszone +39% prefillu (1400 → 1950 t/s) okazało się porównaniem rozgrzanego przebiegu z zimnym; po ABBA na świeżych bootach +2–4% zimno, +4–6% ciepło. Reguła: ABBA na świeżych procesach, ten sam stan cache, nowy prompt w każdym pomiarze.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-obciazenie-cpu]]
- [[pomiar-abba]]
- [[raport-48-norma-gdn-bank]]
