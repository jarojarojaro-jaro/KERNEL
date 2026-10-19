---
typ: metoda
tags: [metody, wyszukiwanie, agenci]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/19-kb-wyszukiwanie.md:224-230; ~/KERNEL/AGENTS.md:8
status: aktualne
---
# Najpierw baza: `kb search` / `kb facts` przed pytaniem i pomiarem

**Zasada od 2026-10-19 (`AGENTS.md`, wiersz 8, i `~/AGENTS.md`): zanim agent zapyta albo zacznie mierzyć, szuka w bazie – `kb search <pytanie>` albo `kb facts <pytanie> [--max|--min]` – i odpowiada liczbą z `plik:linia`; `wiki.py search` deleguje do `kb` (`KB_NO_DELEGATE=1` przywraca stare).**

Powód: przed `kb` agenci nie znajdowali faktów już zapisanych (rekord 130.2 t/s w `NOTES.md:331`), bo stare wyszukiwanie widziało tylko tytuły i streszczenia notatek. `kb facts` służy do pytań o rekordy i max/min i podaje wszystkie źródła tej samej liczby; dla pytań „dlaczego” i o decyzje lepsze jest `kb search` ([[raport-19-kb-wyszukiwanie]]).

## Powiązane
- [[metody/_hub|Metody]]
- [[kb]]
- [[REKORDY]]
- [[2026-10-16-wszystko-do-bazy-wiedzy]]
