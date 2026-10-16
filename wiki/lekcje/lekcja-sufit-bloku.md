---
typ: lekcja
tags: [lekcje, spekulacja, konkurencja]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/16i-magnitude-co-robia-dobrze.md:13,144-176
status: aktualne
---
# Na kopii wygrywa sufit bloku, nie kernel

**Magnitude bije nas na code-edit (157.0 vs 105.7 t/s, pad.cu, 3090) tylko dlatego, że jedno przejście wag daje im 8 tokenów, a nam 5: obie strony przyjmują prawie wszystko (894/897 vs 816/828), a ich krok jest wolniejszy (50.2 vs 46.5 ms) (2026-10-16).**

Reguła: zanim zaczniemy szukać „lepszych kerneli” konkurenta, rozłożyć wynik na tok/krok × ms/krok. Gdy akceptacja jest bliska 100%, zysk daje tylko podniesienie sufitu (ogon z lookupu, szerszy drafter), a nie optymalizacja weryfikacji.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-benchmark-kopia]]
- [[lekcja-mtp-juz-kopiuje]]
- [[lekcja-drafter-gleboki-vs-mtp]]
- [[2026-10-16-magnitude-rozklad-wygranej]]
