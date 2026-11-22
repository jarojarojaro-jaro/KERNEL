---
typ: meta
tags: [meta]
aktualizacja: 2026-11-22
zrodlo: wiki/tools/czesci.py; wiki/tools/tabele.py; wiki/tools/wiki.py; wiki/tools/porzadki.py; wiki/tools/site/build.py
status: aktualne
---
# Konwencje wiki

**Jak pisać i utrzymywać notatki, żeby lint przechodził, a Obsidian pokazywał wszystko bez konwersji.**

## Notatka
```
---
typ: <typ części z tools/czesci.py, tabela niżej>
tags: [<folder>, temat-1, temat-2]
aktualizacja: RRRR-MM-DD
zrodlo: ścieżka:linie; URL
status: aktualne|do-sprawdzenia|nieaktualne
---
# Tytuł

**Jedno zdanie streszczenia.**

Treść 50–200 słów: liczby z datą i warunkami pomiaru.

## Powiązane
- 2+ sąsiadów, 1+ notatka z innej części (BEZ linku do huba: hub listuje swoje notatki sam)
```

## Części (jedna definicja: `tools/czesci.py`)
| folder | typ | co tam jest | pola tabel |
|---|---|---|---|
| `decyzje/` | decyzja | decyzje i korekty właściciela, wiążą | — |
| `modele/` | model | jedna notatka na model (też drafter): rozmiar, kwant, gdzie działa | model, rozmiar, kwant, karty, wyniki |
| `llm/` | llm | trening, dostrajanie, edycje wag, jakość modeli | — |
| `karty/` | karta | jedna notatka na kartę, maszynę albo chmurę | karta, vram, pasmo, gdzie, stan, wyniki |
| `stos/` | stos | nasz fork, ROCm/HIP/PM4/KFD, CUDA, sterowniki | — |
| `optymalizacje/` | optymalizacja | jedna technika, kernel albo łatka z werdyktem | technika, werdykt, zysk, dowod, karta, model, k |
| `testy/` | test | eksperymenty i pomiary z datą, metoda pomiaru | model, karta, wynik/wyniki, k |
| `metody/` | metoda | jak pracujemy | — |
| `lekcje/` | lekcja | lekcje z błędów | — |
| `research/` | research | raporty, zwiady, linki właściciela z werdyktem | — |
| `ekosystem/` | ekosystem | cudze silniki, repo, firmy, ludzie | — |
| `produkt/` | produkt | Enigma: plan, strona, aplikacja | — |
| `narzedzia/` | narzedzie | nasze skrypty i narzędzia | — |
| `archiwum/` | archiwum | scalone i wycofane (`status: nieaktualne`, `zastapiona_przez`), poza przypomnieniem | — |

Nowa część albo zmiana opisu: tylko w `tools/czesci.py`; KONWENCJE, huby, lint i aplikacja WWW czytają ją stamtąd.

## Pola tabel (frontmatter, format w `tools/tabele.py`)
- `wynik: <model> | <karta> | <liczba> <jednostka> | <metryka>; <warunki> | RRRR-MM-DD` (kilka: lista `wyniki:` z punktami `  - …`); `model` i `karta` to nazwy notatek z `modele/` i `karty/`.
- Technika: `technika`, `werdykt: przyjete|odrzucone|w-toku`, `zysk: +5,6% fill 255k (466,3 → 492,5 t/s)`, `dowod: notatka albo plik:wiersz`, `k: K-xxx`.
- Wartości bez „: ” w środku. Liczba tylko z pomiaru, który stoi w notatce albo w jej `zrodlo` (żadnych szacunków).
- `python3 tools/wiki.py index` składa z pól [[najlepsze-wyniki]] (model × karta × metryka), [[bilans-optymalizacji]] i blok „Wyniki z notatek” w notatce każdego modelu i karty; bloków `TABELE` nie edytuje się ręcznie.

## Zasady
- Nazwa pliku: małe litery ASCII, kebab-case, bez kropek, unikalna w całym vaulcie (`qwen3-8-27b.md`, `2026-10-12-rocm-vs-vulkan.md`).
- Linki: `[[nazwa]]`, `[[nazwa|tekst]]` albo `[[folder/nazwa|tekst]]`. Linkuj tylko do istniejących notatek (lint zgłasza martwe linki). Pliki repo spoza wiki: link markdown ze ścieżką względną (`[NOTES.md](../../qwen-opt/NOTES.md)`); pliki spoza repo: ścieżka w backtickach.
- Folder = część = tag = kolor w grafie. `typ` wynika z części (`tools/czesci.py`).
- Liczby dokładnie ze źródła, z datą. Niepewne → `status: do-sprawdzenia`. Zastąpione → `python3 tools/porzadki.py archiwizuj X --powod … --nastepca Y` (przenosi do `archiwum/`, `status: nieaktualne`; nie wraca w przypomnieniu, historii nie kasujemy). Duplikat → `porzadki.py scal B A`.
- `decyzje/` ma pierwszeństwo przed resztą.
- Repo jest publiczne: zero sekretów, adresów IP, e-maili, sald, ID maszyn. Lint to sprawdza, także względem prawdziwych kluczy z dysku.
- Huby (`_hub.md`) i listy w `index.md` generuje `python3 tools/wiki.py index`; ręcznie pisze się tylko wstęp nad znacznikiem AUTO, a blok „Najważniejsze” części przez `python3 tools/porzadki.py streszczenie <część> "…"` (do 1500 znaków, liczby ze źródłem).
- Nie linkuj do huba części w „Powiązane”: nazwa części w linku dopasowywała każde pytanie z tym słowem do każdej notatki części i obniżała trafność przypomnienia.

## Utrzymanie
1. Po zakończonym zadaniu główny agent poprawia lub dodaje notatki (podagenci tylko czytają).
2. `python3 tools/wiki.py index && python3 tools/wiki.py lint` → 0 błędów.
3. Wpis w [[log]]: `## [RRRR-MM-DD] ingest|update|lint | co`.
4. **Nowy najlepszy wynik → od razu wiersz w [[REKORDY]]** (data, warunki: skrypt, T, kontekst, flagi, build/commit; źródło `plik:wiersz`; czy w produkcji) – decyzja użytkownika 2026-10-19.
5. Nowa liczba w notatce → wiersz w [[AUDYT]] (notatka, liczba, wiersz źródła, OK/poprawione); `AUDYT.md`, `REKORDY.md`, `ZRODLA.md` i `log.md` są zwolnione z limitu słów.
6. **Nie badamy drugi raz tego samego** (decyzja użytkownika 2026-10-19). Przed każdym researchem: `kb search <nazwa/URL>` + rejestr źródeł [[ZRODLA]]. Jeśli źródło już było badane → tylko DELTA od zapisanej wersji/commitu/daty (co nowego), bez powtarzania wniosków. Po researchu dopisz wiersz do [[ZRODLA]] (źródło, wersja/commit, data, raport, werdykt, co sprawdzić następnym razem).
   Od włączenia przypomnienia w skrzynce (`docs/SKARBIEC.md`): link od właściciela (Telegram, panel) trafia sam do [[ZRODLA]], sekcja „Linki od właściciela (wpisywane automatycznie)”, z werdyktem „czeka na analizę” (skrzynka, przed turą; blok `<memory-context>` mówi, czy link jest nowy, czy już był i gdzie). Po analizie wpisz w tym wierszu werdykt, notatkę i liczby albo zapisz analizę gdzie indziej z adresem linku (wtedy wiersz zastępczy znika sam po turze). Wiersz z „bez analizy w wiki; odpowiedź …” to wyciąg odpowiedzi wpisany automatycznie: uzupełnij go.
7. Aplikacja WWW bazy (strona główna, kategorie, wyszukiwarka, oś czasu, graf, raporty): `python3 tools/site/build.py` (kilka sekund) → `~/.cache/wiki-graph` (serwowane w LAN); cron przebudowuje ją codziennie zaraz po compwatch.

## Powiązane
- [[index|Strona główna]]
- [[log]]
- [[wiki-py]]
