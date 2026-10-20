# compwatch: codzienny wywiad konkurencji

Decyzja: [`wiki/decyzje/2026-10-20-bez-publikacji-localmaxxing.md`](../../wiki/decyzje/2026-10-20-bez-publikacji-localmaxxing.md). Nie publikujemy na LocalMaxxing. Czytamy, co osiągają inni, i każdą nowość zamieniamy w eksperyment.

Skrypt `compwatch.py` uruchamia się raz dziennie i zbiera trzy rodzaje danych:

1. **LocalMaxxing** (publiczne API do odczytu, [R32d](../../product/research/32d-localmaxxing.md)). Pobiera runy dla naszych kart i modeli i porównuje je ze stanem z poprzedniego raportu. Wykrywa:
   - runy szybsze od naszych liczb (`config.json → nasze`, liczby z `wiki/REKORDY.md` i raportów `31-*`);
   - nowy najlepszy run dla danej pary karta/model;
   - silniki, których wcześniej nie było w bazie (także forki, rozpoznawane po `engineRepository`).
2. **GitHub**. Dla śledzonych repo sprawdza wydania, tagi i HEAD domyślnej gałęzi. Porównuje je z commitem zapisanym w `wiki/ZRODLA.md` albo w sekcji „Do bazy wiedzy” raportów `product/research/*.md` (liczy się najnowszy commit, który istnieje w repo) i z HEAD z ostatniego raportu. Do raportu trafiają fragmenty notatek wydań i nagłówki commitów zawierające słowa kluczowe.
3. **Hugging Face**. Nowe repo GGUF od `unsloth`, `bartowski` i `ggml-org` dla modeli z `config.json → models`. W raporcie jest tylko tytuł i data.

Wynik to `product/research/watch/YYYY-MM-DD.md` plus jedna linia w `product/research/watch/INDEX.md`. Pliki powstają tylko wtedy, gdy jest delta. Potem skrypt robi `git pull --rebase --autostash` (tylko gdy origin jest do przodu), commit tych dwóch plików i push. Na górze raportu jest sekcja **„Do sprawdzenia”** z rankingiem według wagi. Każda liczba wydajności dostaje jedną linię „Jabłka do jabłek” z warunkami po obu stronach.

## Uruchomienie

```sh
python3 tools/compwatch/compwatch.py             # normalny przebieg (raport + commit + push przy delcie)
python3 tools/compwatch/compwatch.py --dry-run   # raport na stdout; bez stanu, plików i gita
python3 tools/compwatch/compwatch.py --no-git    # raport i stan, bez commita
python3 tools/compwatch/compwatch.py --force     # raport nawet bez istotnej delty
```

Harmonogram użytkownika to crontab, codziennie o 06:30 czasu lokalnego, z niskim priorytetem:

```
30 6 * * * nice -n 19 /usr/bin/python3 /home/jaro/KERNEL/tools/compwatch/compwatch.py >> /home/jaro/.cache/compwatch/cron.log 2>&1
```

## Stan i limity

- Stan jest poza repo, w `~/.cache/compwatch/`:
  - `state.json`: widziane runy, HEAD i wydania repo, widziane repo HF, liczniki zapytań;
  - `lmx/YYYY-MM-DD/*.json`: surowe odpowiedzi API z danego dnia. Ponowny przebieg tego samego dnia korzysta z nich i nie wysyła zapytań;
  - `cron.log`.

  `COMPWATCH_CACHE=/inny/katalog` przenosi stan, np. do testów.
- **LocalMaxxing:** najwyżej `daily_max` (10) zapytań na dobę. Licznik jest w stanie, a między zapytaniami są 2 s przerwy. Dziś zapytań jest 7. Dane należą do autorów i nie mają licencji, więc służą tylko do wewnętrznej analizy i nie trafiają do produktu (R32d §2).
- **GitHub:** potrzebny jest zalogowany `gh` (`~/.local/bin/gh`). Przebieg to około 10 zapytań GraphQL w paczkach. Bez logowania sekcja GitHub jest pomijana z adnotacją w raporcie, bo limit 60 zapytań na godzinę nie wystarcza na pełny przegląd.
- **HF:** 3 zapytania do publicznego API (`/api/models?author=…&filter=gguf&sort=createdAt`).
- Kiedy powstaje raport:
  - pierwszy przebieg (stan bazowy);
  - dowolna pozycja z wagą ≥ `report_min_score`;
  - albo minęło `digest_days` od ostatniego raportu i zebrały się drobne delty.

  Drobne delty, które nie dały raportu, nie aktualizują stanu, więc kumulują się do następnego raportu.
- Zmiana `wiki/REKORDY.md` albo `31-*.md` od ostatniego raportu daje pozycję „zaktualizuj `nasze`”. Liczby w `nasze` są wpisywane ręcznie, bo tabele rekordów mają zbyt różne formaty, żeby je bezpiecznie parsować.

## Jak dodać źródło

Wszystko jest w `config.json`. Kodu nie trzeba ruszać.

- **Repo GitHub:**
  - najprościej dopisać wiersz z `github.com/owner/repo` do `wiki/ZRODLA.md`. Skrypt zbiera wszystkie takie linki (tier C) i bierze commit z kolumny wersji jako bazę;
  - repo o wyższym priorytecie dopisz do `github.repos` jako `{"slug": "owner/repo", "tier": "A"|"B"|"C"}`. Opcjonalne pola to `name` (etykieta), `ignore_releases: true` (np. llama.cpp, które ma wydanie z każdym buildem) i `release_ignore` (regex tagów do pominięcia);
  - waga tieru jest w `github.tiers`, a słowa kluczowe podbijające wagę w `github.keywords`.
- **Karta:** dopisz do `cards` wpis `{"key", "label", "re", "w"}`. `re` to regex dopasowywany do `gpuName`/`chipFamily`/`chipVariant` z LocalMaxxing. `unverified: true` śledzi też najlepszy run bez weryfikacji. Jeśli karta wymaga osobnego zapytania, dodaj je w `localmaxxing.queries` w granicy 10 zapytań dziennie.
- **Model:** dopisz do `models` wpis `{"key", "re", "tier"}`, gdzie `tier` to `core`, `catalog` albo `candidate`. Ten sam regex działa dla LocalMaxxing (`hfId` modelu bazowego) i dla HF (id repo i tag `base_model`). Modele z katalogu produktu (`app/landing/src/lib/data/models.json`), które nie pasują do żadnego wzorca, są wypisywane w sekcji „Uwagi”.
- **Nasz pomiar:** dopisz do `nasze` wpis `{"card", "model", "tok", "metric", "src"}`. `metric` opisuje warunki i trafia do linii „Jabłka do jabłek”, a `src` ma postać `plik:linia`.
- **Zapytanie LocalMaxxing:** dopisz do `localmaxxing.queries` wpis `{"name", "params"}`. Parametry są takie jak w `GET /api/leaderboard`: `hfId`, `hardwareName`, `verifiedRun`, `since`, `limit` ≤ 200. Łącznie najwyżej 10 dziennie.
- **Nowy typ źródła** (np. otwarty zbiór JSON innego rankingu): dopisz funkcję `*_scan(cfg, state, items, report, first)` wzorem `hf_scan`. Ma tworzyć obiekty `Item(waga, sekcja, tytuł, linia_jabłka_do_jabłek, następny_krok)` i trzymać stan w `state[<klucz>]`. Wywołaj ją w `main()`. Przed dodaniem sprawdź licencję i `robots.txt` źródła.

## Wagi („Do sprawdzenia”)

| pozycja | waga |
|---|---|
| run szybszy od naszego pomiaru na tej samej karcie i modelu | (60 + min(60, % przewagi)) × waga karty × tier modelu × (1 verified / 0.6 bez weryfikacji); kolejny run tego samego silnika ×0.3 |
| nowy najlepszy run na karcie (pierwszy verified +15) | 45 × waga karty × tier modelu |
| przebieg bazowy: najlepszy verified run na karcie, na której nie mamy pomiaru | 70 × waga karty |
| nowy silnik w bazie (nasz model albo XTX/R9700 / inne) | 50 / 25 |
| wydanie w repo | tier (A 50, B 30, C 15) + 2 za każde słowo kluczowe (max +15) |
| same commity | 0.4 × tier + 3 za każdy nagłówek ze słowem kluczowym (max +20) |
| nowe repo GGUF (core / catalog / candidate) | 30 / 15 / 10 |

Tier modelu: core 1.0, catalog 0.6, candidate 0.4.
