# Skarbiec: baza wiedzy projektu (`wiki/`)

Stan: 2026-11-22 (porządek wiki i mózg Kernela jak u Jarva). Pierwsza wersja z 2026-10-16: „po prostu baza wiedzy; wszystko dokładnie, ale bez przesady”.

## Co jest
- `wiki/`: vault Obsidiana w 13 częściach z jednej definicji `wiki/tools/czesci.py`: `decyzje/`, `modele/` (jedna notatka na model), `llm/`, `karty/` (jedna na kartę, maszynę albo chmurę), `stos/`, `optymalizacje/` (jedna na technikę, z werdyktem), `testy/`, `metody/`, `lekcje/`, `research/`, `ekosystem/`, `produkt/`, `narzedzia/`. Każda część ma `_hub.md` z blokiem „Najważniejsze”. `archiwum/`: scalone i uchylone notatki (`status: nieaktualne`, z następcą), poza przypomnieniem. W korzeniu: `index.md`, `KONWENCJE.md`, `log.md`, `REKORDY.md`, `KOLEJKA-TESTOW.md`, `ZRODLA.md`, `AUDYT.md` i `kernel-od-a-do-z.md` (pełna mapa Kernela).
- Tabele składane same z pól frontmattera (`wiki/tools/tabele.py`, przy `wiki.py index`): `testy/najlepsze-wyniki` (model × karta × najlepszy wynik, każda liczba ze źródłem) i `optymalizacje/bilans-optymalizacji` (technika, werdykt, zysk, dowód, K-xxx).
- Każda notatka: frontmatter (`typ` z `czesci.py`, `tags`, `aktualizacja`, `zrodlo` z plikiem i liniami, `status`, pola tabel), tytuł, jedno zdanie streszczenia, treść z liczbami z datą, sekcja „Powiązane” (bez linku do huba: hub listuje notatki sam).
- `wiki/tools/wiki.py` (tylko stdlib): `lint [folder]` (frontmatter, streszczenie, martwe linki, sieroty, wzorce sekretów, IPv4, e-maile i porównanie z prawdziwymi kluczami z dysku bez ich wypisywania), `index` (huby, index.md, tabele), `search`. `wiki/tools/porzadki.py`: przenosiny, scalenia, archiwum z przepisaniem linków w całym repo, `wykonaj --sucho`, `cofnij`; `plan_porzadkow.py`: reguły, `duplikaty`, `nieaktualne`.
- `wiki/.obsidian/graph.json`: kolor węzła w grafie = folder.

## Mózg Kernela (od 2026-11-22, ten sam obieg co u Jarva)
- Tożsamość: `~/kernel/tozsamosc/` na serwerze (SOUL = postać, ZASADY = procedury, MAPA = mapa z rdzeniem; ZMIANY = skąd przeszła każda stara zasada). `jarvo sesja gpu wiedza tozsamosc` składa z nich stałą część promptu (rdzeń mapy, nie cała mapa); pełna mapa to `wiki/kernel-od-a-do-z.md`. `AGENTS.md` repo ładuje omp przy zwykłej pracy w `~/KERNEL`; sesja Kernel (`--no-context-files`) go nie ładuje.
- Przypomnienie przed każdą turą (`jarvo/mozg_sesji.py` w repo JARVO, wpis `gpu` w `konfig/sesje.json`, pola `panel.wiedza` i `panel.tozsamosc`): skrzynka dokleja do wiadomości tury blok `<memory-context>` z 5 notatkami tej wiki (silnik skarbca Jarva `wiedza.py` połączony z `kb search --mode bm25`), bez `archiwum/` i bez notatek nieaktualnych. Blok idzie do wiadomości, nie do promptu: stała część zostaje w pamięci podręcznej dostawcy.
- Link od właściciela (Telegram, panel) dostaje sam wiersz w `wiki/ZRODLA.md` (sekcja „Linki od właściciela (wpisywane automatycznie)”) przed turą; link bez analizy po turze dostaje wyciąg odpowiedzi i wraca w przypomnieniu przez 3 tury.
- Mózg panelu Jarvo pokazuje tę wiki jako źródło „Wiedza Kernela” (graf po każdej turze, części z `konfig/mozg.json`). Kontrola: wiersz „Obieg wiedzy Kernel” w `stan-jarva`. Pomiar: `jarvo sesja gpu wiedza ocena <zestaw.json>` (22.11: hit@5 0,50 przed mózgiem, 0,941 po porządku).
- Kopia: wiki jest w tym repo. Cały mózg i stan Kernela ma osobną prywatną kopię co godzinę (repo `kernel-kopia`, `kopia-jarva --kernel`, timer `kopia-kernela.timer`): tożsamość, skrzynka (wiadomości z odpowiedziami, błędy, tury, pobrane linki), dziennik przypomnień, archiwum wszystkich rozmów jako tekst (`~/kernel/archiwizuj.py`: bez myślenia modelu, sekrety i hasła wycięte), migawka wiki, wpis sesji, źródło Mózgu, jednostki systemd, README z odtworzeniem. Bez surowych sesji `.jsonl` i indeksu (odbudowa: `jarvo sesja gpu wiedza indeksuj`). Strażnik sekretów sprawdza każdy plik przed commitem.

## Jak oglądać na Windows
`git pull` repo KERNEL, potem w Obsidianie „Open folder as vault” → `KERNEL/wiki`. Bez Syncthing i chmury, więc bez konfliktów synchronizacji. Pliki `workspace*.json` są w `.gitignore`.

## Research (skrót)
- **Karpathy, „LLM Wiki”** ([gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)):
  - LLM utrzymuje trwałą wiki w Markdown między surowymi źródłami (niezmiennymi) a użytkownikiem; plik schematu (CLAUDE.md/AGENTS.md) opisuje konwencje.
  - Operacje: **ingest** (źródło → streszczenie, aktualizacja stron, index, log), **query** (odpowiedź z cytatami, dobre odpowiedzi wracają do wiki jako strony), **lint** (sprzeczności, nieaktualne tezy, sieroty, brakujące linki).
  - `index.md` to katalog treści, `log.md` to chronologia z prefiksem `## [data] rodzaj | tytuł`.
  - U nas: index, log, lint i schemat (KONWENCJE + AGENTS.md) są, a raw sources to istniejące pliki repo.
- **Obsidian CLI** ([help](https://obsidian.md/help/cli)): oficjalne CLI od instalatora 1.12.7+, ale „Obsidian app must be running”, więc na headless serwerze wymaga desktopowej aplikacji (np. pod Xvfb). Nie jest nam potrzebne: wystarczą `wiki.py` i grep. **Obsidian Headless** ([help](https://obsidian.md/help/headless)) to klient płatnego Obsidian Sync, którego nie używamy.

## Historia
- 2026-10-16: zasiew, 16 folderów (metody, kernele, łatki, rocm, nvidia, karty, modele, eksperymenty, chmura i inne).
- 2026-11-22: porządek (`porzadki.py wykonaj`): 373 notatki przeniesione do 13 części, 37 scalonych, 10 w archiwum; pola tabel (421 wyników, 89 technik), notatki jaroserverai, google-colab, rtx-4080-super, qwen3-5-9b, „Najważniejsze” w hubach. Przypomnienie na 34 pytaniach z historii: hit@5 0,912 → 0,941.
