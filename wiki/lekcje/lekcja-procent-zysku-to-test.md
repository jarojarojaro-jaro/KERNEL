---
typ: lekcja
tags: [lekcje, research, kolejka, priorytety]
aktualizacja: 2026-11-26
zrodlo: panel JARO 2026-11-26 21:54 (o YASA: „plus 15–30 procent to nie jest warte uwagi do testów? … przecież to od razu powinno pójść do testów”)
status: aktualne
---
# Lekcja: policzony możliwy zysk ≥ 3–5% to pozycja w kolejce od razu, nie „lekcja”

**Przy YASA policzyłem na naszych liczbach, że rzadka uwaga dałaby Qwenowi +15–30% dekodu przy 96–192k, i zamknąłem to jako wiedzę „na później”, bo przepis autorów wymaga treningu; nie sprawdziłem wersji bez treningu (wybór stron KV jak Quest, który Nib już ma jako `--sparse-pages`), a próg testu JARO to 3–5%.**

- Przyczyna: oceniłem przepis źródła (z treningiem), a nie mechanizm (wybór części KV przy dekodzie), i potraktowałem „zmienia wynik” jako koniec, choć mamy bramkę KLD na zmiany, które niczego nie psują ([[2026-11-26-bramka-kld]]).
- Reguła: gdy rachunek na naszych liczbach daje ≥ 3–5% (próg z [[xtxbench-szybki-ab]]), w tej samej turze powstaje pozycja `K-…` z planem testu i najtańszym wariantem (bez treningu, za przełącznikiem, bramka KLD + igły), a w odpowiedzi podaję numer. „Na później” tylko dla tego, czego nie da się sprawdzić na naszych kartach i modelach.
- Pozycja: K-188.
- Wymuszenie (JARO 21:57: „jak mogłeś tego nie wyłapać”): `wiki.py lint` daje błąd dla każdej notatki `research/` i `llm/` od 26.11 bez sekcji `## Test u nas` z numerem `K-…` albo jawnym „nie da się …” z powodem. Przegląd dzisiejszych notatek tym sitem dał 4 nowe pozycje (K-189…K-192).

## Powiązane
- [[yasa-rzadka-uwaga-kolibri]]
- [[lekcja-uczymy-sie-nie-tylko-predkosc]]
