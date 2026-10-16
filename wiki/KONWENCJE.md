---
typ: meta
tags: [meta]
aktualizacja: 2026-10-16
zrodlo: wiki/tools/wiki.py
status: aktualne
---
# Konwencje wiki

**Jak pisać i utrzymywać notatki, żeby lint przechodził, a Obsidian pokazywał wszystko bez konwersji.**

## Notatka
```
---
typ: model|karta|rocm|nvidia|kernel|latka|metoda|eksperyment|lekcja|narzedzie|chmura|repo|research|produkt|firma|decyzja
tags: [<folder>, temat-1, temat-2]
aktualizacja: RRRR-MM-DD
zrodlo: ścieżka:linie; URL
status: aktualne|do-sprawdzenia|nieaktualne
---
# Tytuł

**Jedno zdanie streszczenia.**

Treść 50–200 słów: liczby z datą i warunkami pomiaru.

## Powiązane
- [[hub folderu]], 2+ sąsiadów, 1+ notatka z innego folderu
```

## Zasady
- Nazwa pliku: małe litery ASCII, kebab-case, bez kropek, unikalna w całym vaulcie (`qwen3-8-27b.md`, `2026-10-12-rocm-vs-vulkan.md`).
- Linki: `[[nazwa]]`, `[[nazwa|tekst]]` albo `[[folder/nazwa|tekst]]`. Linkuj tylko do istniejących notatek (lint zgłasza martwe linki). Pliki repo spoza wiki: link markdown ze ścieżką względną (`[NOTES.md](../../qwen-opt/NOTES.md)`); pliki spoza repo: ścieżka w backtickach.
- Folder = kategoria = tag = kolor w grafie. `typ` wynika z folderu (tabela w `tools/wiki.py`).
- Liczby dokładnie ze źródła, z datą. Niepewne → `status: do-sprawdzenia`. Zastąpione → `nieaktualne` (nie kasujemy historii).
- `decyzje/` ma pierwszeństwo przed resztą.
- Repo jest publiczne: zero sekretów, adresów IP, e-maili, sald, ID maszyn. Lint to sprawdza, także względem prawdziwych kluczy z dysku.
- Huby (`_hub.md`) i listy w `index.md` generuje `python3 tools/wiki.py index`; ręcznie pisze się tylko wstęp nad znacznikiem AUTO.

## Utrzymanie
1. Po zakończonym zadaniu główny agent poprawia lub dodaje notatki (podagenci tylko czytają).
2. `python3 tools/wiki.py index && python3 tools/wiki.py lint` → 0 błędów.
3. Wpis w [[log]]: `## [RRRR-MM-DD] ingest|update|lint | co`.
4. Nowa liczba w notatce → wiersz w [[AUDYT]] (notatka, liczba, wiersz źródła, OK/poprawione); `AUDYT.md` jest zwolniony z limitu słów.

## Powiązane
- [[index|Strona główna]]
- [[log]]
- [[decyzje/_hub|Decyzje]]
