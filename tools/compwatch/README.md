# compwatch: codzienny wywiad konkurencji i zwiad

Decyzja: [`wiki/decyzje/2026-10-20-bez-publikacji-localmaxxing.md`](../../wiki/decyzje/2026-10-20-bez-publikacji-localmaxxing.md). Nie publikujemy na LocalMaxxing. Czytamy, co osiągają inni, i każdą nowość zamieniamy w eksperyment.

Skrypt `compwatch.py` uruchamia się raz dziennie i zbiera sześć rodzajów danych:

1. **LocalMaxxing** (publiczne API do odczytu, [R32d](../../product/research/32d-localmaxxing.md)). Pobiera runy dla naszych kart i modeli i porównuje je ze stanem z poprzedniego raportu. Wykrywa:
   - runy szybsze od naszych liczb (`config.json → nasze`, liczby z `wiki/REKORDY.md` i raportów `31-*`);
   - nowy najlepszy run dla danej pary karta/model;
   - silniki, których wcześniej nie było w bazie (także forki, rozpoznawane po `engineRepository`).
2. **GitHub**. Dla śledzonych repo sprawdza wydania, tagi i HEAD domyślnej gałęzi. Porównuje je z commitem zapisanym w `wiki/ZRODLA.md` albo w sekcji „Do bazy wiedzy” raportów `product/research/*.md` (liczy się najnowszy commit, który istnieje w repo) i z HEAD z ostatniego raportu. Do raportu trafiają fragmenty notatek wydań i nagłówki commitów zawierające słowa kluczowe.
3. **Hugging Face**. Nowe repo GGUF od `unsloth`, `bartowski` i `ggml-org` dla modeli z `config.json → models`. W raporcie jest tylko tytuł i data.
4. **Otwarte rankingi** ([R34](../../product/research/34-zrodla-benchmarkow.md)). To otwarte zbiory danych z publicznym odczytem. Logika różnicowania jest ta sama co dla LocalMaxxing: nowe wiersze dla naszych kart i modeli, nowy najlepszy wiersz dla pary karta/model, wynik lepszy od `nasze` oraz nowy silnik. Każda sekcja raportu podaje źródło i licencję.

   | źródło | plik | licencja | zapytań dziennie |
   |---|---|---|---|
   | llm-speed.com | `data/open-dataset.json` (wskaźnik wersji), potem `data/llm-speed-runs-<wersja>.json` tylko przy nowej wersji | CC BY 4.0 | 1–2 |
   | local-llm-benchmarks.dev (kyuz0; R9700, Strix Halo) | `data/results.json` (4.4 MB, pobieranie warunkowe przez ETag) | brak (strona i repo bez LICENSE): tylko analiza wewnętrzna, w raporcie link zamiast republikacji | 1 |
   | llmcheck.net (Apple Silicon) | `data/v1/benchmarks.json`, tylko wiersze `sourced` i `community` (bez estymat) | CC BY 4.0 | 1 |
   | LLM Configurator | `measured-benchmarks.json` | CC BY 4.0 | 1 |

   Pominięte źródła z R34 to te bez API odczytu albo bez zgody w regulaminie: llm-bench.io (`/api` zabronione w robots), llamabench.ai (brak API odczytu), asiai (403), oMLX (brak JSON), OpenBenchmarking (brak licencji, główna domena 403), Anubis (dane bez licencji, metadane niewiarygodne) i Token Atlas (agregat cudzych danych bez licencji).
5. **arXiv** (oficjalne API `export.arxiv.org/api/query`). Kategorie `cs.LG`, `cs.DC`, `cs.PF`, `cs.AR`, `cs.CL` × frazy z `arxiv.query_terms` (spekulacja, KV cache, kernele kwantów i atencji, MoE, llama.cpp/GGUF, ROCm/HIP, kernele CUDA, serwowanie LLM). Okno: od ostatniego zapisanego przebiegu minus `overlap_days` (arXiv ogłasza prace z opóźnieniem), najwyżej `max_days`. Duplikaty odpadają po identyfikatorze arXiv; prace, których id jest już w `wiki/ZRODLA.md`, też. Waga pracy to suma wag wzorców `research_keywords` w tytule (×1.5) i abstrakcie, plus premia za link do kodu.
6. **Blogi inżynierskie (RSS/Atom)** z `rss.feeds`: vLLM, Tri Dao, PyTorch, ROCm (AMD), NVIDIA Technical Blog, Hugging Face, Together AI, Modular, Chips and Cheese. Każdy kanał sprawdzony jednym zapytaniem (poprawny XML, 2026-11-14). Nowe wpisy po `guid`/`id`; trafne to te z mocnym wzorcem z `research_keywords` (kanały `all: true` piszą tylko o inferencji, więc liczy się każdy wpis). Wydania śledzonych repo idą przez GraphQL GitHuba, więc `releases.atom` nie są potrzebne.

Wynik to `product/research/watch/YYYY-MM-DD.md` plus jedna linia w `product/research/watch/INDEX.md`. Pliki powstają tylko wtedy, gdy jest delta. Bez `--no-git` skrypt robi potem `git pull --rebase --autostash` (tylko gdy origin jest do przodu), commit tych dwóch plików i push. Na górze raportu jest sekcja **„Do sprawdzenia”** (top `top_items`) z rankingiem według wagi; sekcje źródeł pokazują tylko deltę od poprzedniego raportu i najwyżej `report_section_max` pozycji. Tabele „najlepszy run per karta” są tylko w przebiegu bazowym. Każda liczba wydajności dostaje jedną linię „Jabłka do jabłek” z warunkami po obu stronach.

## Uruchomienie

```sh
python3 tools/compwatch/compwatch.py             # normalny przebieg (raport + commit + push przy delcie)
python3 tools/compwatch/compwatch.py --dry-run   # raport na stdout; bez stanu, plików i gita
python3 tools/compwatch/compwatch.py --no-git    # raport i stan, bez commita
python3 tools/compwatch/compwatch.py --force     # raport nawet bez istotnej delty
python3 tools/compwatch/compwatch.py --out DIR   # raport i INDEX.md w DIR (poza repo: bez gita), np. test
python3 tools/compwatch/compwatch.py --summary F # podsumowanie przebiegu w JSON (raport, nowe per źródło, top, uwagi)
```

Harmonogram: timer użytkownika systemd na serwerze, który działa całą dobę (bez GPU), codziennie ok. 06:30 z `Persistent=true` (przebieg przegapiony przy wyłączonym serwerze rusza po starcie), `nice 15`, `CPUQuota=50%`. Timer uruchamia opakowanie sesji Kernel (poza repo), które woła `compwatch.py --no-git --summary …` i przy raporcie z nowościami zostawia sesji jedną wiadomość z jego skrótem; raport commituje sesja razem z notatkami. Do 2026-10-20 compwatch szedł z crontaba na maszynie z kartą i po tym dniu nie dał już raportu. Kod działa (przebieg 2026-11-14 bez błędu), więc przyczyną było najpewniej środowisko: cron nie nadrabia przebiegów, gdy maszyna jest wyłączona o 06:30, a zerwane połączenie (`ConnectionResetError`, `RemoteDisconnected`, timeout `gh`) kończyło cały przebieg. Dziś błąd jednego źródła trafia do „Uwag” raportu, a reszta przebiegu idzie dalej.

## Stan i limity

- Stan jest poza repo, w `~/.cache/compwatch/`:
  - `state.json`: widziane runy, HEAD i wydania repo, widziane repo HF, liczniki zapytań;
  - `lmx/YYYY-MM-DD/*.json`: surowe odpowiedzi API z danego dnia. Ponowny przebieg tego samego dnia korzysta z nich i nie wysyła zapytań;
  - `rss` i `arxiv` w `state.json`: widziane wpisy (id, data), ETag/Last-Modified kanałów, czas ostatniego przebiegu arXiv.

  `COMPWATCH_CACHE=/inny/katalog` przenosi stan, np. do testów; `COMPWATCH_OUT=/katalog` działa jak `--out`.
- **LocalMaxxing:** najwyżej `daily_max` (10) zapytań na dobę. Licznik jest w stanie, a między zapytaniami są 2 s przerwy. Dziś zapytań jest 7. Dane należą do autorów i nie mają licencji, więc służą tylko do wewnętrznej analizy i nie trafiają do produktu (R32d §2).
- **GitHub:** potrzebny jest zalogowany `gh` (`gh auth status`). Przebieg to około 20 zapytań GraphQL w paczkach. Bez logowania sekcja GitHub jest pomijana z adnotacją w raporcie, bo limit 60 zapytań na godzinę nie wystarcza na pełny przegląd.
- **HF:** 1 zapytanie na autora z `hf.authors` do publicznego API (`/api/models?author=…&filter=gguf&sort=createdAt`).
- **Otwarte rankingi:** najwyżej 5 zapytań dziennie łącznie (limit `daily_max` dla każdego źródła w `feeds`). Pobieranie jest warunkowe (`If-None-Match` / `If-Modified-Since`). Surowe pliki leżą w `~/.cache/compwatch/feeds/<źródło>/` i są kasowane po 30 dniach.
- **arXiv:** najwyżej `arxiv.max_pages` (4) zapytań po `page_size` (100) wyników, co `spacing_s` (3 s), zgodnie z zasadami API arXiv (1 zapytanie na 3 s).
- **RSS/Atom:** jedno warunkowe GET na kanał (ETag / Last-Modified, 304 = bez zmian).
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
- **arXiv:** frazy w `arxiv.query_terms` (szukane w abstraktach), kategorie w `arxiv.categories`. Ranking i próg trafności to `research_keywords` (`[regex, waga]`, wspólne z RSS), `arxiv.min_strong` (najmocniejszy wzorzec musi mieć co najmniej tę wagę) i `arxiv.min_score`.
- **Blog (RSS/Atom):** dopisz do `rss.feeds` wpis `{"name", "url", "home", "w"}`, opcjonalnie `"all": true` dla kanału tylko o inferencji. Najpierw sprawdź jednym zapytaniem, że adres zwraca poprawny XML.
- **Otwarty ranking (JSON):** dopisz do `feeds` wpis `{"name", "type", "url", "home", "licence", "attribution", "w", "daily_max"}`. Jeśli żaden istniejący adapter nie pasuje, dopisz `feed_<typ>(feed, fs, report)` w `compwatch.py` i zarejestruj go w `FEED_ADAPTERS`. Adapter pobiera dane przez `feed_get` i zwraca wiersze `{id, date, tok, model, gpu, multi, engine, engine_raw, quant, cond, url}`, gdzie `cond` to warunki pomiaru źródła używane w linii „jabłka do jabłek”. Przed dodaniem sprawdź licencję i `robots.txt` źródła.
- **Nowy typ źródła** (inny niż ranking z wierszami pomiarów): dopisz funkcję `*_scan(cfg, state, items, report, first)` wzorem `hf_scan`. Ma tworzyć obiekty `Item(waga, sekcja, tytuł, linia_jabłka_do_jabłek, następny_krok)` i trzymać stan w `state[<klucz>]`. Wywołaj ją w `main()`.

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
| otwarty ranking: wynik lepszy od `nasze` / nowy najlepszy wiersz / nowy silnik | jak dla LocalMaxxing × waga źródła `w` (llm-speed 1.0, kyuz0 0.9, llmcheck 0.6, LLM Configurator 0.5) / 45 × karta × tier × `w` / 25 × `w` |
| praca arXiv | suma wag `research_keywords` (trafienie w tytule ×1.5) + 5 za link do kodu, max 60; próg: najmocniejszy wzorzec ≥ 8 i suma ≥ 14 |
| wpis na blogu | (suma wag `research_keywords` + 15 dla kanałów `all`) × waga kanału `w`, max 50; próg jak dla arXiv |

Tier modelu: core 1.0, catalog 0.6, candidate 0.4.
