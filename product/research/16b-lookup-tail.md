# 16b. Ogon z lookupu za MTP: log, koszt szerokości, A/B na XTX (15b E1–E3, 16i E-X0–E-X3)

Data: 2026-10-18/19. Autor: podagent XtxLookupTail. Sprzęt: RX 7900 XTX (lokalnie, ROCm, PM4). Koszt $0, bez chmury.
Kod: `~/wt/lookup`, gałąź `lookup-tail` od `amd-opt` @ `f61994f58`:
- `6e12530cc`: lookup z kontekstu obok draftera MTP, tryby 1–3;
- `586f1d596`: kontroler szerokości 5/8/16.

Surowe wyniki i skrypty: `~/qwen-opt/lookup/`. Podsumowania: `logs/e3_summary.txt`, `logs/e4_summary.txt`, `logs/e4_postfix.txt`, `e2/e2_table.txt`, `logs/e1-*.analysis.txt`.

## 0. Najważniejsze

1. **Ogon z lookupu działa i jest duży na edycjach kodu.** Na zestawie code-edit MagnitudeVs (`mvs`, 4 pliki, „zwróć cały plik z jedną zmianą”) przy T=0:
   - MTP n=4: 166.2 t/s;
   - ogon W8 + łańcuchy: 255.6 t/s (+54%);
   - ogon W16 + łańcuchy: 400.9 t/s (**×2.41**).

   Przy T=1: 166.1 → 231.0 (+39%) → 375.8 t/s (×2.26). Źródła: `logs/e3_summary.txt:33,40`, `logs/e4_summary.txt:33,40`.
2. **Tekst greedy się nie zmienia.** Przy T=0 md5 odpowiedzi są identyczne z MTP bez lookupu na 11/11 promptach kopii, edycji i 32k, przy W8, W16 i z kontrolerem (`e3_summary.txt:51-62`, `e4_summary.txt:51-62`). Dodatkowo `greedy.sh` na buildzie końcowym: plain `c4708318`, MTP `6f14e814`, zarówno z `LLAMA_SPEC_LOOKUP=0`, jak i z `=3 W16 ADAPT`.
3. **Na czacie ogon prawie się nie włącza.** Na `spec_sweep` trafia 13–15 kroków na ~4500, a koszt kroku jest w szumie: 28.74 → 28.73 ms (W8) / 28.78 ms (kontroler). Różnice t/s ±1% biorą się z innego tekstu przy T=1. Seedy 1–3 dały −1.1%, seedy 4–9 +0.7% (§4.4).
4. **Koszt szerokości (E2):** V16 − V5 = 6.40 / 7.13 / 9.50 / 12.45 ms przy 2k / 8k / 32k / 64k. Przy 32k mieści się w progu 12 ms z 15b. W16 opłaca się na kopii nawet przy 32k (×1.54 nad W8).
5. **Kontroler szerokości (E-X3) niczego nie wnosi ponad stałe W16.** Na wszystkich zestawach kopii wybiera 16 i mieści się w ±1% od W16. Na czacie też wybiera 16 dla rzadkich ogonów, które potem są złe (29/162 przyjętych). Zalecenie: stałe `LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16`; kontroler zostaje wyłączony (§5).
6. **MTP już kopiuje (potwierdzenie 15b na żywym serwerze).** P(MTP d1 | lookup d1) = 0.995 na kopii (2302 kroki) i 1.000 na czacie. Wartość lookupu leży wyłącznie w ogonie za pozycją 4 i w pominięciu draftu w łańcuchach.

## 1. Implementacja (`common/speculative.cpp`, za przełącznikami, domyślnie wyłączone)

- `struct common_spec_lookup`: przyrostowy indeks n-gramów 4-tokenowych po stronie hosta (hash → ostatnie wystąpienie + łańcuch `prev`).
  - Zapytanie: najdłuższy sufiks 4–12 tokenów, do 64 kandydatów, przy remisie najnowszy. Zwraca do 15 tokenów kontynuacji.
  - Ta sama definicja co symulacja 15b (`15b-sim/lookup_stats.py`). Długość dopasowania serwer = symulacja na **4531/4531** krokach (`logs/e1-*.analysis.txt`, ostatni wiersz).
- Historię synchronizuje `common_speculative_draft()` z `pos0`/`id_last` i z przyjętych draftów (bez kopiowania promptu co krok). Koszt hosta to 5–21 ms na całe 100–2300 kroków, czyli ≤ 10 µs/krok.
- `LLAMA_SPEC_LOOKUP`:
  - `1`: log na sucho (`LLAMA_SPEC_LOOKUP_LOG=plik.jsonl`, `_LOG_PROMPT=1` dopisuje prompt), drafty bez zmian;
  - `2`: ogon. Gdy wszystkie drafty MTP równają się pierwszym tokenom lookupu przy dopasowaniu ≥ `_MMIN` (6), lookup dokleja tokeny do szerokości `_W` (8);
  - `3`: ogon + łańcuchy. Po w pełni przyjętym bloku z ogonem następny blok pochodzi tylko z lookupu, bez draftu MTP, do pierwszego odrzucenia. Działa tylko bez `result_q`, czyli przy próbkowaniu draftu greedy. Przy T=1 serwer ustawia `result_q`, więc łańcuchy się nie włączają i przy T=1 tryby 2 i 3 dają to samo (`e3_summary.txt:18`).
  - Weryfikacja bez zmian, więc tokeny z lookupu są sprawdzane jak każdy draft.
- Szerokość: `need_n_rs_seq()` i `common_speculative_n_max()` biorą max(n_max MTP, W−1). Przy trybach 2–3 włączony jest cache grafu per szerokość (`llama_set_verify_graph_cache`), jak w T2. Przy `LLAMA_SPEC_LOOKUP=0` ścieżka jest nietknięta (md5 = baza).
- `LLAMA_SPEC_LOOKUP_ADAPT=1` (`586f1d596`): drabinka 5/8/16 (≤ W).
  - Akceptacja per głębokość jest liczona za darmo: każda propozycja lookupu jest oceniana po fakcie względem zatwierdzonych tokenów, także na głębokościach niezweryfikowanych. Liczniki z zanikiem 0.99.
  - Wybór maksymalizuje tok/ms. Koszt kroku = zmierzony krok 5-wierszowy + ΔV(w, kontekst) z dopasowania do E2: Δ8 = 2.45 + 0.025·k, Δ16 = 6.2 + 0.1·k, gdzie k = kontekst/1024.

## 2. E1: log na sucho (15b E1)

`LLAMA_SPEC_LOOKUP=1`, serwer produkcyjny (MTP n=4, słownik 64k, ctx 204800). `spec_sweep` 6×3 przy T=1 oraz nowy zestaw „copy”: 6 promptów (edycja pliku 2k/8k, `str_replace` w formacie wywołań narzędzi, edycja hashline po polsku, dosłowne cytowanie sekcji po polsku, refaktoryzacja), T=0 + T=1×3. Generator: `~/qwen-opt/lookup/make_prompts.py`; źródła zamrożone w `src/`.

| zestaw | kroki | tok/krok | lookup proponuje | lookup d1 | r ≥ 8 (kroki) | P(MTP d1 \| lookup d1) | P(MTP d1 \| brak lookupu) | wyzwalacz EXT | pozycje z r ≥ 8 |
|---|---|---|---|---|---|---|---|---|---|
| spec_sweep (czat/proza/kod) | 2230 | 3.09 | 5.0% | 2.3% | 0.4% | 1.000 | 0.772 | 0.4% | **0.5%** |
| copy | 2302 | 4.86 | 93.7% | 92.0% | 83.4% | **0.995** | 0.918 | 83.0% | **83.9%** |

Źródła: `logs/e1-sweep.analysis.txt:8`, `logs/e1-copy.analysis.txt:14`.

- Najsłabszy prompt kopii: hashline-pl, gdzie pozycje z r ≥ 8 to 38% (T=0) / 31% (T=1). Model przepisuje funkcje w innym kształcie niż oryginał.
- Szacunek zysku z logu: W8 to +0.50 tokenu na wygenerowany token, W16 to +1.75. Bazowo jest 4.86 tok/krok, więc daje to odpowiednio ~+2.4 i ~+8.5 tok/krok. Pomiary w §4 to potwierdzają (7.6 i 14.4 tok/krok na `mvs`).
- Kill 15b E1 („< 5% udziału ≥ 8 na ruchu użytkownika”) nie został sprawdzony na prawdziwym ruchu. Tryb 1 jest gotowy do tygodnia logowania produkcji. Na syntetycznym zestawie agentowym udział wynosi 84%.

## 3. E2: koszt szerokości weryfikacji (15b E2, 16i E-X0)

`llama-bench -fa 1 -ctk q4_0 -ctv q4_0 -p 1,5,8,9,16 -n 0 -d …` (`~/qwen-opt/lookup/e2_bench.sh`). Mediana powtórzeń 3–5, bo pierwsze dwa to rozgrzewka grafu, +5…+40 ms (`e2/e2.jsonl`, `samples_ns`).

| kontekst | V1 | V5 | V8 | V9 | V16 | V8 − V5 | V16 − V5 |
|---|---|---|---|---|---|---|---|
| 2k | 22.83 | 24.14 | 26.60 | 27.97 | 30.53 | 2.46 | 6.40 |
| 8k | 23.02 | 24.47 | 27.06 | 28.46 | 31.60 | 2.59 | 7.13 |
| 32k | 23.62 | 25.65 | 28.94 | 30.93 | 35.15 | 3.29 | **9.50** |
| 64k | 24.60 | 27.21 | 31.00 | 34.03 | 39.66 | 3.79 | 12.45 |

Źródło: `e2/e2_table.txt:2-5`.

- Hipoteza 15b („V16 − V5 ≤ 12 ms przy 32k”): **potwierdzona** (9.50 ms). Kill nie zadziałał.
- 16i §3.2 zakładało przy 64k +18 ms na 2 kafle kvq. Pomiar dla W16 daje +12.45 ms ponad W5, czyli mniej.
- Przejście 8 → 9 kolumn (próg K4 WMMA) kosztuje 1.4–3.0 ms, czyli więcej niż kolejne kolumny 9 → 16 (~0.37–0.8 ms/kol.).

## 4. E3/E-X2: A/B na serwerze

Metoda: świeży serwer na ramię (`arm.sh`), ramiona przeplatane (A B C C B A, A B B A …), flagi produkcyjne, `cache_prompt` w obrębie serwera.
- copy: 512 tok., T=0 i T=1 × 3 seedy;
- mvs: 1024 tok., T=0 i T=1 × 2 seedy;
- long: jeden prompt ~30k tokenów (`sampling.cpp` + `server-task.cpp`, „zmień nazwę funkcji, zwróć cały plik”), 512 tok.

Ramiona: A = wyłączone, B = tryb 3 W8, C = tryb 2 W8, W = tryb 3 W16, D = tryb 3 W16 + kontroler.

### 4.1 W8 (E3, `logs/e3_summary.txt`)

| zestaw | A (MTP4) | B: W8 + łańcuchy | C: W8 sam ogon | tok/krok A → B |
|---|---|---|---|---|
| copy T=0 | 163.4 | **230.6 (+41.1%)** | 213.3 (+30.5%) | 4.86 → 7.09 |
| copy T=1 | 160.1 | 208.8 (+30.4%) | 208.1 (+30.0%) | |
| mvs T=0 | 166.2 | **255.6 (+53.8%)** | 230.3 (+38.5%) | 4.92 → 7.66 |
| mvs T=1 | 166.1 | 231.0 (+39.1%) | 231.1 (+39.1%) | |
| long ~30k T=0 | 156.7 | **239.6 (+52.9%)** | – | 4.92 → 7.76 |
| long ~30k T=1 | 154.7 | 208.3 (+34.6%) | – | |

Wiersze źródłowe: `e3_summary.txt:9,18,33,40,22,26`.

- Łańcuchy przy T=0 skracają krok: B 29.9–31.5 ms wobec C 33.1–34.5 ms, bo pomijają draft MTP (~3.6 ms). Akceptacja tokenów łańcucha: 2059/2177 (copy) i 3305/3400 (mvs).
- Wyjątek: hashline-pl, gdzie C > B (180 vs 172 t/s). Łańcuch wypiera tam dobre drafty MTP, gdy lookup się myli.
- Ogon trafia: tryb 2 przyjął 3573/3663 (97.5%) tokenów ogona na copy i 4365/4410 (99.0%) na mvs.

### 4.2 W16 i kontroler (E-X2 / E-X3, `logs/e4_summary.txt`, `logs/e4_postfix.txt`)

| zestaw | B: W8 | W: W16 | D: kontroler | W / B | W vs MTP4 (A z E3) |
|---|---|---|---|---|---|
| mvs T=0 | 255.9 | **400.9** | 401.6 | ×1.57 | **×2.41** (A 166.2) |
| mvs T=1 | 231.3 | 375.8 | 376.5 | ×1.62 | ×2.26 |
| copy T=0 (po naprawie wentylatorów) | 235.8 | 355.0 | 354.5 | ×1.51 | ≈ ×2.12 [łańcuch W/B × B/A] |
| copy T=1 | 213.5 | 316.6 | 316.1 | ×1.48 | ≈ ×1.93 |
| long ~30k T=0 | 242.5 | **373.5** | 373.3 | ×1.54 | ≈ ×2.36 |
| long ~30k T=1 | 210.7 | 336.4 | 336.5 | ×1.60 | ≈ ×2.15 |

- Szczegóły per prompt dla W16 przy T=0 (`e4_summary.txt:3-8`, `29-32`): `mvs` 387.7–410.8 t/s (14.0–14.4 tok/krok, 35.1–36.2 ms/krok); cytat PL 437, edycja 8k 415, `str_replace` 311, hashline-pl 196 t/s (6.24 tok/krok).
- Krok W16 na kopii: 34.6–35.2 ms przy 2–8k i 39.2 ms przy 30k, wobec 29.8 ms dla MTP4.
- Kontroler: na każdym zestawie kopii wybrał 16 (`widths 5:0 8:0 16:662`). Oszacowania P(głębokość 4/8/15) = 0.954/0.930/0.892 (copy), 0.943/0.933/0.924 (mvs), 0.978/0.957/0.935 (long).
- Na mvs W16 przyjmuje 5706/5945 tokenów ogona (96.0%) i 3323/3565 tokenów łańcucha (93.2%).

### 4.3 Porównanie z Magnitude (kontekst z 16i / 16j)
- 16i (3090): Magnitude DFlash2 na code-edit 27B = 7.88 tok/krok przy 50.2 ms. U nas na XTX W8 daje 7.66 tok/krok przy 30 ms, a W16 14.4 tok/krok przy 35.5 ms.
- 16j (XTX, Magnitude przez Vulkan): code 87.7 t/s. Nasze `mvs` W16 to 401 t/s [inne prompty i długość niż xbench code; ten sam typ zadania].
- Prognoza 16i §3.1 dla „MTP4 + ogon 16 wierszy” (×2.07–2.41) zgadza się z pomiarem ×2.26–2.41 na mvs.

### 4.4 Regresja na czacie (`spec_sweep` 6 promptów, T=1)

| seria | A t/s | B (W8) t/s | D (kontroler) t/s | ms/krok A / B / D | ogony |
|---|---|---|---|---|---|
| seedy 1–3, ABBAABBA (`e3_summary.txt:43-49`) | 106.4 | 105.3 (−1.1%) | – | 29.06 / 29.13 / – | 8 na 2258 kroków (13/24 tok. przyjętych) |
| seedy 4–9, ABDDBA (`e4_summary.txt:43-49`) | 106.1 | 106.8 (+0.7%) | 105.3 (−0.7%) | 28.74 / 28.73 / 28.78 | B: 13 na ~4500 (19/39); D: 15 (29/162) |

- Tok/krok zmienia się tylko na promptach, gdzie ogon trafił i rozjechał tekst T=1. Seedy 1–3: pl-proza 2.74 → 2.61, en-tech 3.39 → 3.46. Seedy 4–9: pl-kod 3.35 → 3.52.
  - Przyczyna: szerszy blok weryfikacji liczy logity inną ścieżką kerneli (numeryka batcha, wiki `lekcja-spekulacja-zmienia-numeryke`), więc przy remisach losowanie wybiera inny token.
  - Znak jest losowy: −1.1% przy seedach 1–3, +0.7% przy 4–9. Średnia ważona liczbą seedów: +0.1%.
- Koszt kroku jest w szumie: W8 +0.07 / −0.01 ms, kontroler +0.04 ms. Host lookupu kosztuje ~1 µs/krok.
- Kill 15b E3 („> 0.5% regresji na spec_sweep”): **niespełniony co do kosztu** (ms/krok ±0.2%). Na samych t/s seedy 1–3 przekraczają próg, seedy 4–9 nie. Rozstrzyga ms/krok i tok/krok poza promptami, gdzie zmienił się tekst (wiki `lekcja-szum-t-s-przy-t1`).

## 5. Kontroler szerokości: ocena
- **Zgodność z najlepszą stałą szerokością (kill 16i E-X3: „> 3% gorzej”):** D vs W ±0.2% na mvs/copy/long. Pomiar long przed naprawą wentylatorów dał −0.9%; po naprawie −0.05%. **Zaliczone, ale bez zysku**, bo na naszych zestawach najlepsza jest zawsze 16.
- **Błąd 1:** szacunek „5-row step” na kopii wynosi 34–39 ms, choć prawdziwy krok MTP4 to ~29.8 ms. Mierzone są rzadkie kroki bez ogona, a te na kopii wypadają po chybieniach i zmianach szerokości. Zawyżony koszt bazowy przesuwa wybór w stronę szerszych bloków. Tu nic nie zmienił, przy ≥ 64k może.
- **Błąd 2:** na czacie kontroler wybiera 16 dla 15 ogonów z akceptacją 18% (29/162). Ocena warunkowa „pierwsze 4 trafione” jest za optymistyczna, gdy ogólne P(głębokość 4) wynosi tylko 0.158. Wpływ na t/s jest w szumie (15 kroków na ~4500), ale to strata ~6 ms na każdym takim kroku.
- Wniosek: domyślnie stałe W16 w trybie 3. Kontroler warto naprawić dopiero wtedy, gdy pojawi się workload, na którym 8 bije 16, np. kopia przy ≥ 64k albo słabe kopie typu hashline (dziś i tam wygrywa 16: 196 vs 175 t/s).

## 6. Poprawność i higiena danych
- md5 greedy (`~/qwen-opt/lookup/greedy/`):
  - `off` / `off2`: plain `c4708318`, MTP `6f14e814` (build `6e12530cc` i `586f1d596`);
  - `lk1`/`lk2`/`lk3`/`adapt16`: MTP `6f14e814`. Na tych promptach ogon nie odpala (4 propozycje na 313 kroków).
- Ogon na kopii przy T=0: tekst identyczny ze wszystkimi ramionami (11/11 promptów, W8 i W16). W16 wychodzi poza zakres `LLAMA_SPEC_BITEXACT` (≤ 8 kolumn), więc tej identyczności nie gwarantuje konstrukcja. Na tych promptach po prostu nie było remisu.
- test-backend-ops: nie dotyczy, bo żaden op ggml nie został zmieniony (tylko logika hosta w `common/`).
- KLD: nie dotyczy, bo weryfikacja dokładna.
- Odrzucone pomiary (`logs/discarded/`), ze względu na nakładanie się z innymi zadaniami GPU:
  - `e4-long-W5`, `e4-long-B6`: okno odtworzonych plików locków 23:18–23:30 UTC;
  - `e4-mvs-B6`, `e4-sweep-D3`: resety GPU o 22:42 i 00:16 UTC;
  - `e4-sweep-A1` z pierwszej serii: przerwana seria.
- Pominięte ramiona: 5 ramion e4 zostało pominiętych, bo `pgrep` wykrył serwer na :8080 (bez pomiaru). Powtórki: `I0=10 ./e4_ab.sh long|copy`.
- Warunki termiczne: copy E3 przed restartem, mvs/long/sweep E3 i e4 mvs po restarcie, e4 copy/long/sweep (indeksy ≥ 11 i seria 4–9) po naprawie wentylatorów. Porównania robione są w obrębie serii; ilorazy „vs MTP4” w §4.2 dla copy/long łączą dwie serie (oznaczone ≈).

## 7. Kryteria kill: zestawienie

| eksperyment | kryterium | wynik | werdykt |
|---|---|---|---|
| 15b E1 | udział r ≥ 8 na ruchu < 5% | czat 0.5%, syntetyczny agent 83.9%; ruch użytkownika niezmierzony | otwarte: tryb 1 do tygodnia logów |
| 15b E2 / 16i E-X0 | V16 − V5 @32k > 12 ms | 9.50 ms | przechodzi |
| 15b E3 | < +3% na copy ≤ 8k albo > 0.5% regresji spec_sweep | copy +41% (T=0) / +30% (T=1); ms/krok spec_sweep ±0.2%, t/s −1.1% / +0.7% (tekst T=1) | przechodzi (koszt), t/s w szumie tekstu |
| 16i E-X2 (W8) | mvs < +20% | +53.8% / +39.1% | przechodzi |
| 15b E4 (W16) | < +5% nad W8 na copy albo regresja przy 32k | copy +51%, long ~30k +54% | przechodzi |
| 16i E-X3 (kontroler) | > 3% gorzej niż najlepsza stała | ±0.2% (= W16) | przechodzi, brak wartości dodanej |

## 8. Co dalej
1. Włączyć w produkcji (`run-llm.sh qwen`) `LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16` po decyzji użytkownika. Najpierw tydzień `LLAMA_SPEC_LOOKUP=1` na prawdziwym ruchu omp (kill E1), skrypt `~/qwen-opt/lookup/lk_analyze.py`.
2. Długi kontekst ≥ 64k z W16 na kopii: E2 daje +12.45 ms, czyli wciąż opłacalne przy akceptacji ~0.9 [INFERENCE]. Zmierzyć na `copy64k` z 16j.
3. W16 + `LLAMA_SPEC_BITEXACT`: wymaga bitowo niezależnego K4 WMMA dla 9–16 kolumn (16i #5).
4. CUDA (3090/5060 Ti): weryfikacja > 8 kolumn idzie tam przez MMQ (16i E-C1). Krzywą V(w) trzeba zmierzyć przed obietnicą ×2.
5. Łańcuchy przy T=1: dziś wyłączone, bo drafty MTP niosą `result_q`. Ogon przy T=1 działa i daje ×2.26 na mvs.

## Do bazy wiedzy

| folder | tytuł | treść | liczby (źródło) |
|---|---|---|---|
| `eksperymenty/` | 2026-10-18 ogon lookupu za MTP (`2026-10-18-lookup-ogon.md`) | MTP4 + ogon z lookupu W8/W16 + łańcuchy bez draftera na XTX; tekst T=0 bez zmian; czat bez kosztu | mvs T=0 166.2 → W8 255.6 → W16 400.9 t/s, T=1 166.1 → 231.0 → 375.8 (`~/qwen-opt/lookup/logs/e3_summary.txt:33,40`, `e4_summary.txt:33,40`); long ~30k T=0 156.7 → 239.6 (`e3_summary.txt:22`), W16 373.5 (`e4_postfix.txt:4`); md5 T=0 identyczne 11/11 (`e4_summary.txt:51-62`) |
| `kernele/` lub `metody/` | aktualizacja „koszt szerokości weryfikacji” (`vcost`/`fattn-kvq.md`) | Krzywa V(w, kontekst) na XTX: koszt kolumn 9–16 rośnie z kontekstem (kafle kvq) | V16 − V5 = 6.40 / 7.13 / 9.50 / 12.45 ms przy 2k/8k/32k/64k; V8 − V5 = 2.46…3.79; skok 8 → 9 kolumn 1.4–3.0 ms (`~/qwen-opt/lookup/e2/e2_table.txt:2-5`) |
| `lekcje/` | aktualizacja `lekcja-mtp-juz-kopiuje.md` | Potwierdzone na żywym serwerze: tam, gdzie lookup trafia, MTP też trafia; lookup wnosi tylko ogon i pominięcie draftu | P(MTP d1 \| lookup d1) 0.995 na 2302 krokach kopii, 1.000 na czacie; serwer = symulacja 15b na 4531/4531 krokach (`logs/e1-copy.analysis.txt:14`, `e1-sweep.analysis.txt:8-9`) |
| `lekcje/` | nowa: „Szeroki blok zmienia tekst T=1 nawet przy 0.3% kroków” (`lekcja-ogon-zmienia-tekst-t1.md`) | Kilka ogonów na tysiące kroków zmienia numerykę weryfikacji, a z nią tekst T=1 na 1–2 promptach spec_sweep; t/s skacze ±1% w dowolną stronę przy stałym ms/krok. Regresję czatu oceniać po ms/krok i na wielu seedach. | seedy 1–3: −1.1%, seedy 4–9: +0.7%, ms/krok 29.06 → 29.13 i 28.74 → 28.73 (`e3_summary.txt:49`, `e4_summary.txt:49`) |
| `eksperymenty/` | kontroler szerokości 5/8/16 (wynik zerowy) | Kontroler w stylu Magnitude zawsze wybiera 16 na kopii, więc = stałe W16; szacunek kroku bazowego zawyżony (34–39 vs 29.8 ms); na czacie wybiera 16 dla złych ogonów (29/162) | `~/qwen-opt/lookup/logs/e4_run2.txt` (linie „widths”), `e4_postfix.txt:2-5` |
| `repo/` / `research/` | hub raportu 16b (`raport-16b-lookup-tail.md`) | Link do tego raportu; zalecenie `LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16` dla agentów kodujących, po tygodniu logu `=1` | §0, §7 tego raportu; kod `lookup-tail` @ `6e12530cc`, `586f1d596` |
| `metody/` | zestawy promptów kopii/edycji (`zestaw-copy-mvs.md`) | `copy` (6 promptów, generator `make_prompts.py`, źródła zamrożone w `src/`), `mvs` (4 pliki MagnitudeVs), `long` (~30k); runner `copy_bench.py`, ramiona `arm.sh`/`e3_ab.sh`/`e4_ab.sh` | `~/qwen-opt/lookup/copy_prompts.json`, `make_prompts.py:36-75` |
