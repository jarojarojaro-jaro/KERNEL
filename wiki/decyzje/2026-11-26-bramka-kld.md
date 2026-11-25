---
typ: decyzja
tags: [decyzje, bramki, kld, spekulacja]
aktualizacja: 2026-11-26
zrodlo: panel JARO 2026-11-26 00:30 (odpowiedź na K-007)
status: aktualne
---
# 2026-11-26: bramka KLD zamiast identycznego md5, gdy zmiana niczego nie psuje

**JARO (2026-11-26 00:30), o K-007: „Jak mozesz zmienic na lepiej nie psujac niczego to zawsze to rob po to sa te testy”.**

- Zmiana, która z założenia zmienia md5 przy T=0 (głębokość/szerokość draftu, przywracanie stanu z innym podziałem batcha, chude checkpointy), może wejść, jeśli przejdzie bramkę jakości: KLD wobec produkcji w granicy szumu kolejności sumowania ([[lekcja-kld-szum-kolejnosci]]) i wymuszanie tokenów (ta sama ścieżka tokenów, porównanie rozkładów), a wall.py nie spada w żadnej kategorii o więcej niż 2%.
- Zmiany bitowo identyczne dalej przechodzą md5 jak dotąd.
- Odblokowane: K-006 (chude checkpointy, wpis wspólnego początku), K-017 (głębokość per klasa, +3,4% proza), K-075 (drzewo weryfikacji), K-057 nie jest już potrzebne jako warunek.

## Powiązane
- [[decyzje/_hub|decyzje]]
- [[metody/zgodnosc-bitowa-md5]]
