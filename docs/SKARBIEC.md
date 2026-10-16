# Skarbiec: baza wiedzy projektu (`wiki/`)

Stan: 2026-10-16. Wersja uproszczona z decyzji użytkownika: „po prostu baza wiedzy; wszystko dokładnie, ale bez przesady”.

## Co jest
- `wiki/`: vault Obsidiana, 16 kategorii = 16 folderów z `_hub.md`, strona główna `index.md`, zasady `KONWENCJE.md`, dziennik `log.md`.
- Każda notatka: frontmatter (`typ`, `tags`, `aktualizacja`, `zrodlo` z plikiem i liniami, `status`), tytuł, jedno zdanie streszczenia, treść z liczbami z datą, sekcja „Powiązane”.
- `wiki/tools/wiki.py` (tylko stdlib): `lint [folder]` (frontmatter, streszczenie, martwe linki, sieroty, wzorce sekretów, IPv4, e-maile i porównanie z prawdziwymi kluczami z dysku bez ich wypisywania), `index` (listy w hubach i w index.md), `search`.
- `wiki/.obsidian/graph.json`: kolor węzła w grafie = folder.
- `AGENTS.md` w katalogu głównym repo: omp ładuje go automatycznie przy pracy w `~/KERNEL` (provider `agents-md`). Sesje startowane z innego katalogu (np. `/tmp`) go nie widzą. Wtedy pomaga kopia w `~/.omp/agent/AGENTS.md` albo hook niżej (decyzja użytkownika).
- `wiki/tools/omp-hook/wiki-context.ts`: opcjonalny hook `before_agent_start`. Wstrzykuje tytuły decyzji i 3–5 pasujących notatek, maks. ~1600 znaków. **Niezainstalowany.** Instalacja: skopiować do `~/.omp/agent/hooks/pre/`.

## Jak oglądać na Windows
`git pull` repo KERNEL, potem w Obsidianie „Open folder as vault” → `KERNEL/wiki`. Bez Syncthing i chmury, więc bez konfliktów synchronizacji. Pliki `workspace*.json` są w `.gitignore`.

## Research (skrót)
- **Karpathy, „LLM Wiki”** ([gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)):
  - LLM utrzymuje trwałą wiki w Markdown między surowymi źródłami (niezmiennymi) a użytkownikiem; plik schematu (CLAUDE.md/AGENTS.md) opisuje konwencje.
  - Operacje: **ingest** (źródło → streszczenie, aktualizacja stron, index, log), **query** (odpowiedź z cytatami, dobre odpowiedzi wracają do wiki jako strony), **lint** (sprzeczności, nieaktualne tezy, sieroty, brakujące linki).
  - `index.md` to katalog treści, `log.md` to chronologia z prefiksem `## [data] rodzaj | tytuł`.
  - U nas: index, log, lint i schemat (KONWENCJE + AGENTS.md) są, a raw sources to istniejące pliki repo.
- **Obsidian CLI** ([help](https://obsidian.md/help/cli)): oficjalne CLI od instalatora 1.12.7+, ale „Obsidian app must be running”, więc na headless serwerze wymaga desktopowej aplikacji (np. pod Xvfb). Nie jest nam potrzebne: wystarczą `wiki.py` i grep. **Obsidian Headless** ([help](https://obsidian.md/help/headless)) to klient płatnego Obsidian Sync, którego nie używamy.

## Stan zasiewu (2026-10-16)
Wypełnione: metody, kernele, łatki, rocm, nvidia, karty, modele, eksperymenty, chmura, część narzędzi, decyzji i lekcji. Puste huby, do uzupełnienia według `KONWENCJE.md`: repo, research, produkt, ludzie-firmy.
