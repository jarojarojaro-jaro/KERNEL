---
typ: lekcja
tags: [lekcje, pomiar, drafter, maya, inkling]
aktualizacja: 2026-11-28
zrodlo: panel JARO 2026-11-28 19:06 („po co robisz bez draftera skoro zawsze jest używane z drafterem”); K-208, K-211
status: aktualne
---
# Lekcja: celem i wynikiem jest zawsze konfiguracja z drafterem, bez draftera tylko jako wzorzec poprawności

**JARO (2026-11-28): produkcja zawsze działa z drafterem, więc pomiar, cel optymalizacji i raport dotyczą konfiguracji z drafterem; ramię bez draftera wolno uruchomić tylko jako wzorzec bitowej poprawności (odpowiedź T=0 z drafterem musi być identyczna jak bez), nigdy jako liczba do gonienia.**

- Co: w K-208 i w raporcie podałem jako pierwszą liczbę dekod bez draftera (111 vs 133 na 3090) i założyłem K-211 „dekod bez draftera”, choć użytkownik zawsze ma drafter (157 vs 210).
- Dlaczego źle: optymalizacja ścieżki, której nikt nie używa, i raport, który zasłania liczbę produkcyjną.
- Reguła: (1) w raporcie liczba z drafterem pierwsza, bez draftera tylko w nawiasie jako kontrola; (2) pozycje kolejki mają cel z drafterem (wall, reasoning-v1, kontekst); (3) bez draftera tylko do sprawdzenia, że wynik jest bitowo ten sam (tak K-208 znalazł błąd okien sufiksowych).

## Powiązane
- [[decyzje/2026-11-27-zawsze-pelny-kontekst]]
