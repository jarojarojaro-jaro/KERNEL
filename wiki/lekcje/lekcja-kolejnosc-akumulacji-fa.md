---
typ: lekcja
tags: [lekcje, determinizm, fa]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:263
status: aktualne
---
# Kolejność akumulacji w FA zmienia KLD

**Nowy kafel prefillu w Flash Attention zmienił kolejność akumulacji i dał KLD 0.0135; łatka 0043 przywróciła kolejność chunków K i KLD = 0.**

Tryb awarii #2 z raportu 07. Reguła: przy każdej zmianie podziału pracy w redukcji (kafle, split-K, chunki) sprawdzać KLD albo bitowość, bo suma zmiennoprzecinkowa nie jest łączna. 0043 (kolejność chunków K w FA MMA) nie ma przełącznika runtime i działa też na NVIDIA.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[determinizm-fma]]
- [[lekcja-spekulacja-zmienia-numeryke]]
- [[prefill-mmq-fa]]
- [[bramka-kld-kanarki]]
