---
typ: lekcja
tags: [lekcje, landing, proces]
aktualizacja: 2026-10-18
zrodlo: komunikat Main do WikiIngest 2026-10-18 (wentylator, Chrome); ~/KERNEL/app/landing/scripts/qa/README.md:3
status: aktualne
---
# Headless Chrome z animowaną stroną pali rdzeń CPU

**Headless Chrome do QA landingu (`.tools/chrome-swgl`, renderowanie programowe) zostawiony otwarty na animowanej stronie zużywał ~90% rdzenia przez 3 godziny (2026-10-18) – obciążenie CPU, które zaburza pomiary GPU na tej samej maszynie.**

Reguła: zamykać Chrome (i proces CDP na porcie 18499) zaraz po każdej rundzie QA landingu; skrypt rundy kończy się `kill` przeglądarki, a przed pomiarami GPU sprawdzić obce procesy CPU.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[landing-qa]]
- [[lekcja-obciazenie-cpu]]
- [[lekcja-uslugi-poza-omp]]
