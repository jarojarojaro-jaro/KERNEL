---
typ: lekcja
tags: [lekcje, gpu, polecenia]
aktualizacja: 2026-11-23
zrodlo: panel JARO 2026-11-23 05:48 („jak skończysz wszystko wyłącz serwer”) i 14:51 („czemu go zamknąłeś, jak jeszcze były testy do zrobienia”)
status: aktualne
---
# Lekcja: „skończ wszystko i wyłącz” = najpierw każdy czekający test, potem wyłączenie

**2026-11-23 06:15 wyłączyłem jaroserverai, choć runda 13 Gemini była gotowa do pomiaru, a K-135 i dalsze kernele Mayi czekały; JARO musiał sam włączyć serwer.**

- Reguła: przed wyłączeniem maszyny lista „co jeszcze da się zmierzyć teraz” musi być pusta (gotowe kody do bramki, nowe pozycje K z wysokim priorytetem, rozpoczęte rundy); każdą z nich wykonuję, zapisuję i dopiero wtedy wyłączam.
- „Wszystko” w poleceniu właściciela obejmuje też to, co doszło w trakcie (nowa runda Gemini, pozycje ze zwiadu).

## Powiązane
- [[lekcja-nie-ruszam-skrzynki-nowe]]
- [[KOLEJKA-TESTOW]]
