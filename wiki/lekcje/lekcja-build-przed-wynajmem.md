---
typ: lekcja
tags: [lekcje, chmura, koszty]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/product/research/16e-kwanty-kld.md:303
status: aktualne
---
# Binarki budować lokalnie przed wynajmem

**W E1 bootstrap na wynajętej karcie (budowa forka + Prism na 9 vCPU) trwał ~25 min przy GPU 0%; watchdog rodzica słusznie zgłosił „idle” (2026-10-16).**

Reguła: binarki sm_86/sm_120 budować lokalnie (RPATH `$ORIGIN`, jak w raporcie 14) i wypychać przed wynajmem; na instancji tylko pomiary. Zgodne z [[2026-10-16-nie-placimy-za-przestoj]].

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-5060ti-bezczynna]]
- [[cuda-stos]]
- [[harness-chmurowy]]
