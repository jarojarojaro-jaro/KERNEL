---
typ: narzedzie
tags: [narzedzia, meta, lint]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/wiki/tools/wiki.py:1-8; ~/KERNEL/wiki/KONWENCJE.md
status: aktualne
---
# wiki.py (narzędzie tej bazy wiedzy)

**Skrypt tylko ze stdlib do utrzymania wiki: `lint` (błędy → kod wyjścia 1), `index` (odświeża listy w `_hub.md` i `index.md`), `search` (deleguje do [[kb]], gdy `kb` jest w PATH; bez niego tytuły, streszczenia, tagi).**

Lint sprawdza frontmatter (`typ`, `tags`, `aktualizacja`, `zrodlo`, `status`), martwe linki, sieroty (notatki linkowane tylko z huba) i sekrety (także względem prawdziwych kluczy z dysku). Folder = kategoria = tag = kolor w grafie Obsidiana; `typ` wynika z folderu. Po każdej zmianie: `python3 tools/wiki.py index && python3 tools/wiki.py lint`.

## Powiązane
- [[narzedzia/_hub|narzedzia]]
- [[kb]]
- [[reactor-monitor]]
- [[greedy-check]]
- [[2026-10-16-prosta-baza-wiedzy]]
- [[AUDYT]]
- [[2026-10-16-wiki-jeden-agent]]
