---
typ: lekcja
tags: [lekcje, wyszukiwanie, narzedzia]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/19-kb-wyszukiwanie.md:250-258
status: aktualne
---
# Łącząc bloki Markdown, zachowuj puste linie

**W `kb` łączenie bloków Markdown w fragmenty gubiło puste linie, przez co numery linii w wynikach przesuwały się o 1 – ścisły recall@5 (linia oczekiwana w zwróconym fragmencie) spadł przez to o 1.3 pkt (raport 19, 2026-10-19).**

Reguła: każde narzędzie, które cytuje `plik:linia`, liczy linie na oryginalnym pliku, a przy dzieleniu i łączeniu fragmentów zachowuje puste linie i offsety; test na znanych liniach w złotym zbiorze.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[kb]]
- [[lekcja-dowod-poza-commitem]]
