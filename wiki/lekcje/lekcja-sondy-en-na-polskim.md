---
typ: lekcja
tags: [lekcje, pl, klasyfikatory]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15d-prefill-dlugi-kontekst.md:12,159-178
status: aktualne
---
# Małe sondy trenowane po angielsku mylą się na polskim

**Sonda żądania PFlash (trenowana po angielsku) w 9/10 polskich przypadków wzięła tytuł wklejonego dokumentu za prośbę użytkownika, choć główna głowica Q/K przeniosła się na polski dobrze.**

Wynik pilota (2026-10-16): top-1 = pytanie PL 1/10, EN 10/10; warianty krzyżowe: pytanie PL do dokumentu EN 2/3, pytanie EN do dokumentu PL 1/3. Słabość zależy od języka pytania i od polskiego tekstu, który „wygląda na prośbę”.
Reguła: przed przyjęciem cudzego klasyfikatora na aktywacjach (sondy, routery, rerankery) zawsze test PL vs EN na naszych tekstach i osobno dla każdego komponentu – główna głowica może się przenosić, a pomocnicza nie.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-jeden-prompt]]
- [[lekcja-kld-protokoly]]
- [[2026-10-16-pflash-pilot-cpu]]
- [[raport-15d-prefill-dlugi-kontekst]]
