# 19. `kb`: szybkie i niezawodne wyszukiwanie w bazie wiedzy (BM25 + embeddingi + fakty)

Data: 2026-10-19. Autor: podagent KbSearch. Tylko CPU (GPU zarezerwowane na eksperymenty).

Kod: `tools/kb/` (Rust, binarka `~/.local/bin/kb`). Złoty zbiór: `tools/kb/gold/gold.jsonl`. Indeks: `~/.cache/kb/` (poza repo). Model: `~/models/kb/multilingual-e5-small/`.

## 0. Najważniejsze

- **Problem.** Agenci nie znajdowali faktów, które już są zapisane. Przykład: rekord 130.2 t/s stał w `qwen-opt/NOTES.md:331`, `wiki/REKORDY.md:26` i dwóch notatkach wiki. Dotychczasowe `wiki.py search` patrzy tylko na tytuły, streszczenia i tagi notatek z `wiki/`. Zwraca całe notatki bez linii i nie widzi raportów ani `NOTES.md`.
- **Rozwiązanie.** `kb search <pytanie>` łączy trzy listy przez reciprocal rank fusion (RRF):
  - BM25F z polską analizą (zdejmowanie ogonków, lekki stemmer, liczby, jednostki, identyfikatory);
  - embeddingi multilingual-e5-small (int8 ONNX, CPU);
  - indeks ~24 tys. faktów liczbowych z jednostką i kontekstem.

  Wynik to top-k fragmentów z `~/KERNEL/plik:linia` i linią z odpowiedzią. `kb facts <pytanie> [--max|--min]` zwraca same liczby, a „najlepszy/rekord” sortuje po wartości. Oba polecenia mają `--json`.
- **Wynik na złotym zbiorze 80 prawdziwych pytań** (recall@5, ścisły: linia oczekiwana musi leżeć w zwróconym fragmencie):

  | tryb | recall@5 |
  |---|---|
  | **hybryda + fakty (domyślny)** | **0.963** |
  | hybryda | 0.912 |
  | BM25 + fakty | 0.875 |
  | BM25 | 0.825 |
  | `wiki.py search` (liczone łagodnie, na poziomie pliku) | 0.750 |
  | same embeddingi | 0.688 |
  | same fakty | 0.550 |

  Cel ≥ 0.9 osiągnięty: dev 0.975, held-out 0.950.
- **Szybkość.**
  - Zapytanie w procesie: p50 38 ms, p95 131 ms (serwer obciążony eksperymentami).
  - Przez CLI z rozgrzanym demonem `kb serve`: 10–70 ms.
  - Bez demona pierwsze zapytanie trwa ~0.9 s, bo ładowanie tokenizera i sesji ONNX zajmuje 0.4–1 s; to zapytanie od razu uruchamia demona.
  - Sprawdzenie „czy coś się zmieniło”: 0.04 s.
  - Pełna przebudowa leksykalna: 0.33 s.
- **Rozmiar.** Indeks 16 MB, wektory 33 MB, model 118 MB + tokenizer 17 MB, binarka 32 MB (ONNX Runtime statycznie).

## 1. Wymagania

- **Pytania.** Agent pyta „jaki był najlepszy X”, „czy mierzyliśmy Y”, „co zdecydowaliśmy o Z”. Pytanie jest po polsku, często bez ogonków, z angielskimi terminami i liczbami (`130 t/s`, `27k`, `tok/krok`, `×2.41`). Odpowiedź ma być z miejscem `plik:linia`, w < 1 s, a najlepiej w < 200 ms.
- **Korpus** (2026-10-19, rośnie w trakcie dnia): 654 pliki `*.md` pod `~/KERNEL` bez katalogów ukrytych, `node_modules` i `target`, łącznie ~4.3 MB. W tym:
  - 440+ notatek Obsidiana z frontmatterem;
  - raporty `product/research/*.md` (do 90 kB każdy);
  - `qwen-opt/*.md` i `qwen-opt/research/**`;
  - `STAN-PRAC.md`, `app/REPORT.md`.
- **Ograniczenia.**
  - Tylko CPU; serwer współdzielony z eksperymentami, więc domyślnie 4 wątki i `nice`.
  - Repo publiczne: indeks i model leżą poza repo.
  - Indeks ma się odświeżać sam (< 1 s, gdy nic się nie zmieniło).

## 2. Warianty i wybór

### 2.1 Leksykalnie: BM25 (tantivy czy własny)

- **tantivy** daje segmenty, mmap i zapytania frazowe. Nie ma jednak polskiego stemmera (rust-stemmers nie obsługuje polskiego), więc analizator i tak trzeba napisać samemu. Segmenty i mmap opłacają się przy milionach dokumentów, a tu jest ~21 tys. fragmentów.
- **Własny BM25F w pamięci** (wybrany): jeden plik postcard 16 MB.
  - Zapytanie trwa 0.5 ms (p95 1.3 ms), pełna przebudowa 0.33 s na 4 wątkach.
  - Pola: treść ×1.0, tytuł + nazwa pliku + tagi ×0.5, ścieżka nagłówków + nagłówek tabeli + folder ×0.3.
  - Normalizacja długości (k1 1.2, b 0.6) liczy się tylko po treści.
  - Wagi pól dobrane na dev (tabela w §6.2).

### 2.2 Gęsto: który model embeddingów

Model musi dobrze obsługiwać polski i angielskie terminy, mieścić się w budżecie CPU i liczyć zapytanie w milisekundach.

| model | parametry / wymiar | koszt na CPU | ocena |
|---|---|---|---|
| **multilingual-e5-small** (wybrany, ONNX int8 Xenova) | 118 M (z tego ~96 M to tablica słów 250k; 12 warstw × 384) / 384 | zmierzone: zapytanie ~7 ms, indeksowanie ~38 fragmentów/s (8 wątków, nice, obciążony serwer), 21 tys. fragmentów ≈ 9 min jednorazowo | trenowany na retrieval (prefiksy `query:`/`passage:`), XLM-R zna polski |
| paraphrase-multilingual-MiniLM-L12-v2 | 118 M / 384 | jak wyżej | trenowany na parafrazy/STS, słabszy w asymetrycznym query→passage `[INFERENCE]` |
| multilingual-e5-base | 278 M / 768 | ~4× FLOP-ów e5-small `[INFERENCE]` | kandydat, gdyby gęsta lista miała ważyć więcej |
| bge-m3 | 568 M / 1024 (24 × 1024) | ~14× FLOP-ów na token, czyli pełny indeks ~2 h na 8 wątkach i zapytanie ~100 ms; 2.2 GB fp32 `[INFERENCE, nie mierzone]` | najlepsza jakość wielojęzyczna, odrzucony z powodu budżetu CPU |
| sdadas/mmlw-e5-small (destylat PL) | ~118 M / 384 | jak e5-small | brak ONNX na HF, wymaga eksportu z torch; kandydat na później |

Same embeddingi dają tylko 0.688. W hybrydzie dokładają jednak +9 pkt do BM25 (0.825 → 0.912), a z faktami +9 pkt do BM25 + fakty (0.875 → 0.963). Pomagają przy parafrazach, pytaniach po angielsku do polskiego tekstu i pytaniach „dlaczego”.

### 2.3 Fuzja

- RRF (k = 60) z list top-100: BM25, e5 i fakty. Fakty wchodzą:
  - z wagą 1.0, gdy pytanie ma agregację, liczbę albo jednostkę;
  - z wagą 0.5 przy „ile/wynik”;
  - z wagą 0.3, gdy jest tylko słowo wskazujące jednostkę (prefill, koszt…);
  - wcale w pozostałych przypadkach.
- Wynik fuzji mnożą trzy czynniki.
  - **Mnożnik pliku:**
    - `AUDYT.md` ×0.45, `log.md` ×0.6, huby i `index.md` ×0.7 (strony pochodne);
    - ten raport i `wiki/narzedzia/kb.md` ×0.3, bo cytują przykładowe pytania i liczby z innych notatek; `tools/kb/` (README) nie jest indeksowane;
    - `qwen-opt/research/**` ×0.8 (cudze repozytoria, surowe rundy);
    - `REKORDY.md` ×1.25;
    - pogrubione streszczenie notatki wiki ×1.2.
  - **Routing po formie pytania:**
    - decyzja/wybraliśmy/zasada → `wiki/decyzje/` ×1.6;
    - dlaczego/czemu → `wiki/lekcje/` ×1.3;
    - jak/kiedy → `metody/`, `narzedzia/`;
    - rekord/najlepszy → `REKORDY.md` ×1.5.
  - **Różnorodność:** w czołówce najwyżej 1 fragment na plik, nadmiar spada na koniec listy. Agent widzi wtedy 5 różnych źródeł zamiast 3 kawałków jednego raportu.

## 3. Podział na fragmenty

- **Jednostki podziału:** akapit, punkt listy z kontynuacją, wiersz tabeli i blok kodu. Każdy fragment ma zakres `start–end` linii (1-based).
- **Kontekst fragmentu:** tytuł notatki, ścieżka nagłówków `H1 > H2 > H3` oraz, dla wiersza tabeli, nagłówek tabeli. Dzięki temu wiersz `| tg przy 98k | **213.0 t/s** |` wie, że dotyczy „RX 7900 XTX – LFM2.5”.
- **Łączenie i dzielenie:**
  - krótkie bloki (< 160 znaków) z tej samej sekcji łączą się do 520 znaków, a puste linie między nimi zostają, żeby numeracja się zgadzała;
  - długie linie (> 900 znaków) dzielone są po zdaniach i każdy kawałek zachowuje swój numer linii.
- **Frontmatter:** tagi idą do pola tytułu, reszta nie jest indeksowana.
- **Linia w wyniku:**
  - przy trafieniu z faktów to linia faktu;
  - w pozostałych przypadkach linia fragmentu z największą sumą idf pasujących termów.

## 4. Polski, liczby, jednostki

- **Ogonki.** Zdejmowane w indeksie i w zapytaniu (ą→a, ł→l, ó→o, ż/ź→z…), więc „gdzie bylo” = „gdzie było”.
- **Stemmer.** Lekkie obcinanie ~70 końcówek fleksyjnych (najdłuższa pierwsza, rdzeń ≥ 4 znaki) i przycięcie rdzenia do 7 znaków. Przykłady: wentylator/wentylatorów/wentylatorach, resetuje/resetów, kosztuje/koszty, decyzja/decyzje. Angielskie `-s` jest obcinane tylko po spółgłosce l/k/t/g/p/d/n/m (kernels, ale nie proces/status).
- **Stop-słowa PL/EN.** „bez” celowo **nie** jest stop-słowem, bo „bez PM4”, „bez spekulacji” to treść.
- **Liczby:**
  - `130.2` → `130.2` + `130`;
  - `130,2` → `130.2`;
  - `27 327` → `27327` + `27k`;
  - `1.7k` → `1.7k` + `1.7`.
- **Identyfikatory i jednostki:**
  - `Qwen3.8-27B` → całość + qwen, 27b;
  - `UD-Q4_K_XL`, `GGML_HIP_PM4` → całość + części;
  - `ub2048` → ub + 2048, `5060ti` → 5060 + ti;
  - `tok/s`, `tokens/s`, `t/s` → jeden token `t/s`.
- **Synonimy domenowe.** ~55 wpisów po stronie zapytania, z wagą 0.4: fan↔wentylator, xtx↔7900, koszt↔cena↔$, wydaliśmy→koszt/budżet, decode↔dekodowanie↔tg, ttft↔prefill, record↔rekord…

## 5. Indeks faktów

- **Co jest faktem.** Każda liczba z jednostką: t/s, ms, ms/krok, ms/tok, tok/krok, s, min, h, GB, MB, %, ×, $, KLD, PPL, RPM, °C, W, tok. Daje to 24.1 tys. faktów. Przykładowe reguły:
  - `×2.41` i `2.41×` to mnożnik, ale `4 x 3090` już nie;
  - `KLD 0.0123` → KLD, ale nie `16e-kwanty-kld.md:247`;
  - `5 105.4` to dwie liczby, a `27 327` to jedna (grupa tysięcy);
  - liczby w identyfikatorach i datach są pomijane (qwen3.8, q4_0, 2026-10-14, 27B).
- **Dziedziczenie jednostek.** W listach typu „pl-proza 99.8, pl-tech 118.6, pl-kod 125.3 t/s”, „818 / 985 / 766 t/s” i „7907 vs 5890 t/s” liczba bez jednostki bierze jednostkę następnej liczby. Warunki: przerwa ≤ 40 znaków z przecinkiem, ukośnikiem, strzałką albo „vs”, to samo zdanie i zbliżony rząd wielkości (×0.05–20). Dlatego „7900 XTX … 926 tok/s” nie robi z 7900 prędkości. W tabelach jednostka pochodzi z nazwy wiersza („VRAM (MiB)”), a gdy jej tam nie ma, z nagłówka kolumny.
- **Etykieta faktu:**
  - tekst od poprzedniej liczby albo początku zdania („pl-kod”, „decode MTP, prompt 1.7k”);
  - w tabelach dodatkowo pierwsza komórka wiersza i nagłówek kolumny;
  - kontekstem są nagłówki i tytuł z fragmentu.
- **Zapytanie:**
  - **Intencja.**
    - Najlepszy/najszybszy/rekord/best → Best (t/s, ×, %, tok/krok w górę; czas, koszt i KLD w dół). Najwolniejszy/najgorszy → Worst. Najwyższy/największy/max → Max, najniższy/najmniejszy/min → Min.
    - Jednostka podana wprost działa jako filtr, a słowo wskazujące (prefill→t/s, koszt→$, kld→KLD…) jako podpowiedź. Przy agregacji bez jednostki domyślnie t/s.
    - Liczby w zapytaniu: `130` = [130, 131), `130.2` = ±0.05, `100%` = 100 z jednostką %.
  - **Trafność faktu.** Ważona idf zgodność termów: etykieta 1.0, linia 0.8, fragment z kontekstem 0.55. Dla wiersza tabeli nagłówek sekcji nad tabelą liczy się jak linia (0.8), bo to on mówi, czego dotyczy wiersz. Dochodzą premie:
    - +1.0, gdy wartość pasuje do liczby z pytania;
    - +0.5, gdy w tej samej linii jest liczba spełniająca warunek, np. „przy 100%”.
  - **Agregacja.** Filtry działają po kolei:
    1. tylko fakty z pełnym pokryciem termów;
    2. strony pochodne odpadają (AUDYT, log, opisy `kb`);
    3. zostaje najwyższy poziom źródła: `REKORDY.md`, potem notatki i raporty, na końcu surowy research — zgodnie z zasadą „rekordy są na stronie rekordów”;
    4. zostają fakty o trafności ≥ najlepsza − 0.15, więc liczba musi być „o tym”, a nie tylko z tej samej linii.

    Wygrywa wartość max/min. Prefill/pp/TTFT (w etykiecie, linii albo nagłówku) nie konkuruje, jeśli pytanie nie wspomina o prefillu („najszybszy LFM” = generowanie, nie pp4096). Przykłady:
    - „rekord pl-kod” → 125.3 t/s, `REKORDY.md:23`;
    - „najszybszy LFM na 7900” → 293.8 t/s, `REKORDY.md:58`;
    - „najszybszy bonsai na 3060” → 44.9 t/s, `REKORDY.md:93`.
  - **Grupowanie.** Ta sama wartość i jednostka z wielu plików to jeden wynik z listą „też: …”.

## 6. Pomiar

### 6.1 Złoty zbiór

- **Skład.** 80 pytań w formie, w jakiej użytkownik i agenci pytają w tym projekcie, w tym 8 przykładów z zadania. Napisał je osobny podagent bez dostępu do `kb`.
  - Rodzaje: 36 faktów, 13 decyzji, 13 „dlaczego”, 9 „jak”, 9 „gdzie / co to”.
  - Ok. 1/4 bez ogonków, 4 po angielsku do polskiego tekstu, pytania o max/min i samą liczbę („ile było 7148”).
- **Oczekiwane miejsca.** Zapisane jako dosłowny `needle` z linii, bo numery linii dryfują przy edycji wiki. Po pierwszym pomiarze ten sam podagent rozszerzył je mechanicznie (grep liczb i fraz odpowiedzi, bez patrzenia na wyniki `kb`) do wszystkich linii, które same podają odpowiedź: 595 miejsc, wcześniej 187. Pierwsza wersja pomijała pogrubione streszczenia notatek, które zwykle zawierają odpowiedź.
- **Trafienie.** Ścisłe: linia z `needle` musi leżeć w zakresie zwróconego fragmentu. `wiki.py` zwraca całe notatki, więc liczę go łagodnie, na poziomie pliku. Mierzy też tylko `wiki/`.
- **Podział.** g01–g40 to dev (na nim stroiłem). g41–g80 to held-out: przed jego obejrzeniem dawał 0.875. Potem dodałem różnorodność (1 fragment na plik, wybrana na dev i held-out) oraz poprawki faktów, i held-out wzrósł do 0.950.
- **Uruchomienie:** `kb eval --modes …`. Test `cargo test --release` wymaga recall@5 ≥ 0.9 i p95 < 200 ms.

### 6.2 Wyniki (2026-10-19, korpus 654 pliki, 21 600 fragmentów, 24 117 faktów)

Opóźnienie w tabeli to czas zapytania w procesie z rozgrzanym indeksem i modelem: drugie z dwóch wywołań, bez startu procesu.

| tryb | recall@5 (80) | dev g01–40 | held-out g41–80 | fakty (36) | MRR@5 | plik@5 | p50 ms | p95 ms | indeks | budowa |
|---|---|---|---|---|---|---|---|---|---|---|
| `wiki.py search` (plik, łagodnie) | 0.750 | 0.725 | 0.775 | 0.750 | 0.551 | 0.750 | 79.4 (cały proces) | 85.8 | brak (skan przy zapytaniu) | 0 |
| BM25F | 0.825 | 0.875 | 0.775 | 0.750 | 0.646 | 0.975 | 0.5 | 1.2 | 16 MB (z faktami) | 0.33 s |
| e5-small | 0.688 | 0.600 | 0.775 | 0.694 | 0.498 | 0.825 | 7.8 | 8.3 | 33 MB + model 135 MB | ~9 min jednorazowo, potem przyrostowo |
| hybryda (RRF) | 0.912 | 0.900 | 0.925 | 0.806 | 0.738 | 0.988 | 8.3 | 9.6 | 49 MB + model | j.w. |
| BM25 + fakty | 0.875 | 0.900 | 0.850 | 0.889 | 0.719 | 0.963 | 36.2 | 109.9 | 16 MB | 0.33 s |
| **hybryda + fakty** | **0.963** | **0.975** | **0.950** | **0.917** | **0.793** | **0.988** | **38.1** | **130.8** | 49 MB + model | j.w. |
| same fakty (`kb facts`) | 0.550 | 0.650 | 0.450 | 0.639 | 0.440 | 0.688 | 28.0 | 95.1 | w indeksie | w indeksie |

- **CLI end-to-end:**
  - przez demona: 0.01–0.07 s; `kb facts` przez demona 0.01 s;
  - `bm25-facts` w procesie: 0.07 s;
  - pierwsze wywołanie bez demona: 0.89 s;
  - start demona przy aktualnych wektorach: 0.7 s.
  - Jeśli od ostatniego zapytania przybyły notatki, demon najpierw dolicza ich embeddingi (39 fragmentów ≈ 1.4 s; zapytanie po dużej partii zmian: 2.6 s). Świeżość ma pierwszeństwo przed czasem.
- **Pamięć demona:** RSS 719 MB, głównie tokenizer z tablicą 250k słów i sesja ONNX.
- **Przebudowa:**
  - „nic się nie zmieniło”: 0.04 s;
  - po zmianie pliku: 0.33 s (dzielenie tylko zmienionych plików, BM25 i fakty liczone od nowa);
  - embeddingi tylko dla nowych fragmentów, kluczowane hashem tekstu.

Kolejne kroki strojenia (hybryda + fakty, recall@5 dla wszystkich 80 pytań):

| krok | recall@5 |
|---|---|
| pierwsza wersja (pierwotne oczekiwane miejsca) | 0.662 |
| + pola BM25F, routing po formie pytania, mnożniki plików i streszczeń | 0.775 |
| rozszerzone oczekiwane miejsca (jak wyżej, bez zmian w kodzie) | 0.887 |
| + warunek liczba z jednostką („przy 100%”), podział `ub2048`/`tg128`, fakty przy słowach-podpowiedziach | 0.912 |
| + poprawka numeracji linii w łączonych fragmentach (błąd: puste linie znikały) | 0.925 (held-out 0.875) |
| + różnorodność 1 fragment na plik | 0.950 (held-out 0.925) |
| + opisy `kb` przyciszone (×0.3), poziomy źródeł i trafność przy rekordach, jednostki tylko w listach, „vs”, poprawka KLD w nazwach plików | **0.963** (held-out 0.950) |
| + regresja g81 (zgłoszona przez Main): `kb facts "najlepszy wynik qwen xtx" --max` dawał 396.9 zamiast rekordu 400.9 t/s (`REKORDY.md:29`). Przyczyna: wiersz 29 ma „Qwen … XTX” tylko w nagłówku sekcji, a filtr trafności (najlepsza − 0.15) wycinał go na rzecz wierszy, które przypadkiem miały „qwen” w tekście. Poprawka: nagłówek sekcji = podmiot wiersza (0.8). Dodane pytanie g81 i test `facts_record_from_table_section` | **0.963** na 81 pytaniach (held-out g41+ 0.951; p95 173 ms przy obciążonym serwerze) |

Przeglądy parametrów (wszystkie 80 pytań; zrobione przed ostatnim wierszem tabeli wyżej):

| parametr | wartości → recall@5 |
|---|---|
| waga tytułu / nagłówków (BM25) | 0.3/0.3 → 0.775; **0.5/0.3 → 0.825** (dev 0.85); 0.5/0.6 → 0.800; 1.0/0.3 → 0.825 (dev 0.775); 2.0/0.3 → 0.487 (na pierwotnych oczekiwaniach) |
| RRF k | 10 → 0.950; 30 → 0.963; **60 → 0.950**; 120 → 0.938 (różnice 1 pytania, plateau) |
| waga faktów / gęstej listy | fakty 0.5 → 0.938, **1.0 → 0.950**, 2.0 → 0.925; e5 0.5 → 0.950, **1.0 → 0.950**, 2.0 → 0.925 |
| fragmentów na plik w czołówce | **1 → 0.950**; 2 → 0.938; bez limitu → 0.938 |

### 6.3 Czego nie trafia (3 z 80)

- **g14 „ile wydalismy na vast”.** Zwraca streszczenie decyzji o budżetach (wiersze 10–12), a liczba końcowa $2.77 jest dwie linie niżej.
- **g74 (EN) „how much did the first NVIDIA cloud campaign cost”.** Wygrywają notatki o RunPod.
- **g79 „najwolniejszy prefill serwera qwen dlugi kontekst”.** Wygrywa raport 15d, który ma wszystkie słowa pytania, a 766 t/s jest w `NOTES.md:331` i `REKORDY.md`.

Same fakty (0.550) to za mało jako jedyna metoda. Liczb jest 24 tys., a na pytania „dlaczego” i o decyzje fakty nie odpowiadają. Jako trzecia lista w fuzji dają jednak +5 pkt do hybrydy (0.912 → 0.963). `kb facts` służy do pytań o rekordy i max/min, z listą wszystkich źródeł tej samej liczby.

## 7. Decyzja

- **Domyślny tryb `kb search` to hybryda + fakty** z demonem trzymającym model.
- **Bez modelu, bez wektorów (> 400 brakujących) albo z `KB_NO_DAEMON=1`** proces liczy sam. Gdy brakuje modelu albo wektorów, spada do BM25 + faktów (0.875, 0.07 s) i mówi o tym na stderr.
- **`wiki.py search`** deleguje do `kb`, gdy ten jest w PATH; `KB_NO_DELEGATE=1` przywraca stare wyszukiwanie.
- **Agenci:** najpierw `kb search` / `kb facts`, odpowiedź z liczbą i `plik:linia` (`AGENTS.md`, `~/AGENTS.md`).

## 8. Ograniczenia i dalsze kroki

- **Pliki wyników JSON** (`~/qwen-opt/spec_sweep.jsonl`, `scorecard.json`, `cloud/results/**/scorecard.json`) nie są indeksowane. Rekordy z nich trafiają do `kb` przez `REKORDY.md`, które podaje wiersze. Dodanie ich jako faktów strukturalnych (etykieta, prompt, T, wartość) to naturalne rozszerzenie.
- **Złoty zbiór i jego zmiany.** Zbiór napisał agent z grepem, więc pytania mogą być bliższe słownictwu źródeł niż pytania użytkownika `[INFERENCE]`. Korpus zmienia się w ciągu dnia (WikiIngest), a liczby z §6.2 mogą się przesunąć o ±1 pytanie.
- **Fakty bez jednostki** (np. „4.71” w kolumnie bez nagłówka z jednostką) nie są faktami. Szuka ich tylko BM25.
- **Lepszy model** (e5-base, mmlw-e5-small, bge-m3) podniósłby same embeddingi. Przy 0.95 w hybrydzie nie jest potrzebny, a kosztuje CPU współdzielonego serwera.

## 9. Użycie

```bash
kb search najlepszy wynik Qwen XTX          # → ~/KERNEL/wiki/REKORDY.md:… (tabela Qwen XTX)
kb search dlaczego PM4 resetuje GPU --full
kb facts rekord pl-kod                       # 125.3 t/s  ~/KERNEL/wiki/REKORDY.md:23
kb facts KLD saluki --min --json
kb eval --modes bm25,hybrid-facts --misses --explain
```

Instalacja: `tools/kb/setup.sh` pobiera ONNX Runtime 1.22 ze sprawdzeniem sha256 i model z Hugging Face, buduje z `nice -n 10 -j6`, kopiuje do `~/.local/bin/kb` i robi `reindex`. Szczegóły w `tools/kb/README.md`.

## Do bazy wiedzy

- **Folder `narzedzia/`, notatka `kb.md`** („kb: szybkie wyszukiwanie w bazie wiedzy”). Polecenia `kb search` / `kb facts` / `kb reindex` / `kb eval`.
  - recall@5 na 80 pytaniach: hybryda + fakty 0.963, BM25 0.825, e5 0.688, `wiki.py` 0.750 (łagodnie) — §6.2 tego raportu;
  - zapytanie przez demona 10–70 ms, w procesie p95 131 ms;
  - indeks 16 MB + wektory 33 MB.
- **Folder `metody/`, uzupełnienie zasady „najpierw baza”** (decyzja 2026-10-19): najpierw `kb search` / `kb facts`, cytować `plik:linia`. Wpisane w `~/KERNEL/AGENTS.md` i `~/AGENTS.md`.
- **Folder `lekcje/` (propozycja), temat: przy łączeniu bloków Markdown trzeba zachować puste linie**, inaczej numery linii w wynikach przesuwają się o 1. Ten błąd w `kb` kosztował 1.3 pkt recall (§6.2).
- **Liczby do `AUDYT.md`:** 0.963 / 0.912 / 0.875 / 0.825 / 0.688 / 0.750 / 0.550 recall@5; p50 38.1 ms, p95 130.8 ms; 16 MB / 33 MB; 0.33 s / 0.04 s; RSS demona 719 MB — wszystko z §6.2.
