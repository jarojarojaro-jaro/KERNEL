# 58. Próbkowana ścieżka DFlash2 + rejection i odcięcie draftu po iloczynie prawdopodobieństw

Data: 2026-10-21. Autor: podagent DraftSample. Źródło pomysłów: raport 57e (Splash/DFlash 2) i 57f (Maya `DSPARK_CUM`).
Branch `draft-sample` (`~/wt/draft-sample`, od `topka-int` `cf927413b`), commit `a1aa0c13e`. Build `~/qwen-opt/draft-sample/inst` (`rbuild --local`, `fix-runpath --check` = 0, 0 ścieżek `/wt/` w ldd). Skrypty: `~/qwen-opt/draft-sample/` (kopie w `58-skrypty/`).
Stan: **kod gotowy, test statystyczny CPU przechodzi, joby GPU (`ds.jobs`) przekazane MorningRun. Nie uruchamiałem niczego na GPU.** `[INFERENCE]` = wniosek bez pomiaru.

## TL;DR

1. **`LLAMA_DFLASH_SAMPLE=1` (domyślnie off): selektor DFlash2 losuje ścieżkę zamiast argmaxu, cel weryfikuje rejection samplingiem.**
   - Na każdej pozycji q = softmax(scores / T) po 16 kandydatach, warunkowo względem kandydata wylosowanego na pozycji wcześniej (te same wyniki par co dziś).
   - q trafia do `result_q`, a serwer wybiera wtedy istniejącą ścieżkę `common_sampler_sample_and_accept_n_rejection`: akceptacja z prawd. min(1, p/q), po odrzuceniu losowanie z norm(max(0, p − q)). Rozkład wyjścia jest dokładnie rozkładem celu.
   - Przy T=0 serwer nie ustawia `result_q`, więc zostaje dzisiejszy argmax. **md5 zachłanne nie może się zmienić z konstrukcji.**
   - Przy sprzężonym celu (`LLAMA_SPEC_COUPLED=1`, produkcja) też zostaje argmax, bo weryfikacja sprzężona nie używa q. Ramiona DFlash mają więc `LLAMA_SPEC_COUPLED=0` po obu stronach.
2. **`LLAMA_DRAFT_CUMP=<próg>` (domyślnie 0 = off): draft jest ucinany, gdy iloczyn prawdopodobieństw draftów spadnie poniżej progu.** To reguła Mayi (`MAYA_DS4_DSPARK_CUM`, v1.1.20, `src/ds4/ds4_main.cpp`: `while conf[k] >= conf_min && (cum *= conf[k]) >= cum_min`).
   - Działa na MTP (łańcuch draftu w produkcji i pętla pojedynczych przebiegów) oraz na DFlash i DFlash2.
   - `LLAMA_DRAFT_CUMP_MIN` (domyślnie 1) to liczba draftów zawsze zostawianych.
   - Adaptacyjna głębokość (`--spec-draft-adaptive`) sama wycenia głębokość, więc CUMP jej nie dotyczy.
3. **Test CPU `tests/test-spec-rejection.cpp`: wszystkie 15 asercji OK (200 000 próbek).**
   - Chi-kwadrat wyjścia vs cel na jednej pozycji (5 przypadków: q bliskie p, q daleko od p z tokenem o p = 0, T 0.7/1/1.5, powtórzony id) oraz łączny rozkład dwóch pozycji z selektorem zależnym od poprzednika i celem zależnym od kontekstu (df 104): p = 0.08…0.99.
   - Akceptacja = Σ min(p, q) (|z| ≤ 0.75).
   - Kontrola negatywna (q niezgodne z losowaniem) daje p ≈ 0, więc test ma moc.
4. **Drafter DFlash2 dla Qwen3.8-27B jest na dysku:** `~/models/draft/Qwen3.8-27B-DFlash2-Q4_K_M.gguf`, ten sam co w pomiarze 71.9 t/s (`run-llm.sh qwen dflash`, wiki [[drafter-dflash]]). Ramiona DFlash są w `ds.jobs`. Nic nie pobierałem.
5. **Bramki i ABBA czekają w kolejce (`ds.jobs`, 26 jobów).** Wyniki dopisze MorningRun albo następny raport.

## 1. Jak działało do tej pory

- **MTP w produkcji** (`run-topka.sh`): n=4 (`DRAFT_N`), coupled (`LLAMA_SPEC_COUPLED=1`), lookup 3 W16.
  - Przy jednej sekwencji drafty liczy **jeden graf łańcucha** (`draft_greedy_chain`), w którym każdy przebieg wybiera argmax albo Gumbel-max ze szumem celu (coupled).
  - Warunek łańcucha to `p_min <= 0`, więc **w produkcji nie ma żadnego progu na pozycję**. Długość to stałe n, ewentualnie głębokość profilu spec-route (`dp.depth`, raport 44: proza n=3).
  - Pętla pojedynczych przebiegów (`p_min > 0`, probabilistic, kilka sekwencji) ucina draft, gdy `cur_p[0].p < p_min`.
- **DFlash2:** jeden przebieg bloku, potem `max_element` po wynikach par (`speculative.cpp:1298-1324` w `cf927413b`). `p_min` ucina, gdy softmax(scores) w argmaxie spadnie poniżej progu.
- **Weryfikacja przy T>0:** serwer zawsze podaje `result_q`. Jeśli drafter nie wypełni q (DFlash, MTP greedy/coupled), wraca do sample-and-match. Gotowa ścieżka rejection istniała dotąd tylko dla `draft-simple` i `draft-mtp` z `--spec-draft-sampling probabilistic`.

## 2. Zmiany w kodzie (commit `a1aa0c13e`)

| plik | co |
|---|---|
| `common/sampling.{h,cpp}` | `common_sampler_rejection_step`: jeden krok rejection wydzielony z `common_sampler_sample_and_accept_n_rejection`. Te same losowania w tej samej kolejności (jedno U do akceptacji, drugie po odrzuceniu), te same wyniki float; maskowanie gramatyką normalizuje p w kopii `cand`, jak wcześniej. Funkcja jest czysta, więc da się ją testować bez kontekstu. |
| `common/speculative.{h,cpp}` | `common_speculative_dflash2_pick`: q = softmax(scores/T), losowanie indeksu, scalenie powtórzonych id (masa do pierwszego wpisu, który czyta `prob_of`), zwraca q(token). DFlash2 w `draft()`: tryb `sample` = `LLAMA_DFLASH_SAMPLE && result_q && !coupled && T > 0`. Strumień RNG ścieżki per sekwencja, seed = seed żądania ^ `0x2545f491`, czyli niezależny od strumienia rejection celu (seed ^ `0x9e3779b9`). `p_min` w trybie sample porównuje max q. CUMP: `common_spec_cump_cut` (iloczyn, minimum `LLAMA_DRAFT_CUMP_MIN`) w łańcuchu MTP (włącza wyjście `mtp_draft_conf` grafu łańcucha i cache grafów weryfikacji per szerokość), w pętli MTP (p wybranego tokenu) oraz w DFlash1 i DFlash2. |
| `tools/server/server-context.cpp` | tylko komentarz (`spec_draft_q` wypełnia też DFlash2) |
| `tests/test-spec-rejection.cpp` | test statystyczny (§4) |

Szczegóły, które wpływają na pomiar:
- **Prawdopodobieństwo w CUMP dla MTP** to softmax logitów głowicy draftu (64k słownika draftu) przy T=1 w wybranym tokenie (argmax albo próbka coupled). Ten sam sygnał wycenia adaptacyjna głębokość. Głowica jest nadpewna (komentarz `common_spec_depth_policy`), więc próg na iloczynie `conf` odpowiada niższej rzeczywistej akceptacji `[INFERENCE]`.
- **W łańcuchu MTP CUMP nie oszczędza draftowania** (graf liczy zawsze n przebiegów), tylko szerokość weryfikacji. W pętli i w DFlash przerywa też samo losowanie.
- **Ogon lookup (`LLAMA_SPEC_LOOKUP`≥2) nie dokleja się do draftu z niepustym q** (`post_draft`), więc DFlash2 sample przy T=1 traci ogon lookup. Ramię A (argmax) go ma. To część porównania, nie błąd.
- Koszt `mtp_draft_conf`: dodatkowy softmax po 65 536 na przebieg i kopia D2H n floatów + h ostatniego przebiegu (20 KB) `[INFERENCE: pomijalne, do sprawdzenia w ms/krok ABBA]`.

## 3. Progi CUMP: dlaczego 0.1 / 0.2 / 0.35

- Raport 40 (ABBA proza T=1): n=3 vs n=4 to 26.05 vs 27.37 ms/krok przy ~2.15 tok/krok. Jedna pozycja weryfikacji i jeden przebieg draftu kosztują ~1.3 ms, z czego draft ~0.65 ms (40 §3).
- Ucięcie pozycji k z akceptacją c_k się opłaca, gdy c_k < Δv · (tok/krok) / (ms/krok). W łańcuchu Δv ≈ 0.65 ms, więc próg rzeczywistej akceptacji wynosi ~0.05, a w pętli (z draftem) ~0.10 `[INFERENCE]`.
- Akceptacja MTP na prozie PL T=1 (raport 40): 0.64 / 0.46 / 0.35 / 0.30 per pozycja. Głowica przecenia.
- Wybór 0.1 i 0.2 ma największą szansę na zysk. 0.35 to kontrola, która powinna już ciąć za dużo. Maya używa 0.5 (DSpark, Strix Halo, droższa weryfikacja) i 0.9 (GLM split).

## 4. Test statystyczny (CPU)

`build-hip/bin/test-spec-rejection 200000` (zbudowany w worktree, `HIP_VISIBLE_DEVICES=-1`):
```
pick T=1.0: index ~ softmax(scores/T), chi2 p = 0.6170; sum q = 1.000000; q(id 1) = 0.0339 vs 0.0339   ok
pick T=0.6: chi2 p = 0.6828                                                                           ok
near q, T=1:   output ~ target chi2 p = 0.6137 (df 10); acceptance 0.6581 vs sum min(p,q) 0.6586       ok
near q, T=0.7: chi2 p = 0.8903; acceptance 0.5806 vs 0.5808                                           ok
far q, T=1:    chi2 p = 0.9894; acceptance 0.2442 vs 0.2445                                           ok
far q, T=1.5:  chi2 p = 0.0757; acceptance 0.3507 vs 0.3503                                           ok
repeated id:   chi2 p = 0.4182; acceptance 0.2958 vs 0.2950                                           ok
two positions, T=1.00: joint ~ p1(t1) p2(t2|t1), chi2 p = 0.3600 (df 104), 0.879 drafts accepted/step ok
two positions, T=0.70: chi2 p = 0.6728 (df 104), 0.750                                                ok
negative control (wrong q): chi2 p = 0.00e+00 must be < 1e-4                                         ok
all passed
```
Test używa dokładnie funkcji z serwera: `common_speculative_dflash2_pick` do losowania i `common_sampler_rejection_step` do weryfikacji. Sekwencję dwóch pozycji składa tak jak serwer: po odrzuceniu na pozycji 1 kolejny token pochodzi wprost z celu.

## 5. Bramki GPU (`ds_gate.sh`, wzorzec s53d po audycie 56)

Ustawienia: env jak w s53d/topka (PM4 `=1 WA=2 GUARD=1`, `HSA_USE_SVM=0`, lookup 3 W16, coupled, host-gap) oraz `fusion/greedy.sh` (2 prompty, T=0, 400 tok). Topka zatrzymywana łagodnie (`ds_stop.sh`: bezczynne `/slots`, jeden SIGTERM, 45 s, SIGKILL na końcu).
- `base` → `md5/GATE_PASS`:
  - switche off: plain `c4708318`, MTP `6f14e814` (build = wzorzec);
  - `LLAMA_DFLASH_SAMPLE=1`: plain `c4708318`, MTP `6f14e814`;
  - `LLAMA_DRAFT_CUMP=0.2`: plain `c4708318`.
- `cump THR` (0.2, 0.1, 0.35) → `md5/CUMP_<THR>.PASS`, reguła CONFIG:
  - MTP r1 == r2;
  - `LLAMA_GPU_VERIFY=0` == `=1`;
  - `nt_gap.py` (raport 53) w pierwszym tokenie różnym od `6f14e814`, puszczany tylko gdy md5 się różni. Ocena near-tie z JSON w logu, tak jak w 53. Uwaga: plik ma oba prompty sklejone, więc `nt_gap` liczę dla `--prompt-index 0` i `1`. Miarodajny jest ten, w którego odpowiedzi leży pierwsza różnica.
- `dflash` → `md5/DFLASH.PASS`:
  - DFlash2 n=6 T=0: `LLAMA_DFLASH_SAMPLE=1` == off;
  - CUMP 0.2 r1 == r2, GV0 == GV1, `nt_gap` vs off;
  - odpowiedź off ma > 500 B, czyli drafter się załadował.

## 6. ABBA (`ds_arm.sh` = p100_arm + chat + wariant DFlash)

Każde ramię to świeży serwer przez `run-topka.sh` (dla DFlash kopia z `spec=dflash`, reszta flag produkcyjna) na `inst`, seedy 1,2. Każde wymaga `GATE_PASS` i swojego markera. Etykiety `Aa/Ba/Bb/Ab`.

| prefiks | A | B | benche | marker |
|---|---|---|---|---|
| `ds-c20-` | MTP, CUMP off | MTP, `LLAMA_DRAFT_CUMP=0.2` | prose, prosethink, chat, mvs | `CUMP_0.2.PASS` |
| `ds-c10-` | jw. | `=0.1` | jw. | `CUMP_0.1.PASS` |
| `ds-df-` | DFlash2 n=6, coupled 0, argmax | `LLAMA_DFLASH_SAMPLE=1` | prose, prosethink, chat | `DFLASH.PASS` |
| `ds-c35-` | MTP, CUMP off | `=0.35` | prose, prosethink, chat, mvs | `CUMP_0.35.PASS` |
| `ds-dfc-` | DFlash2 sample | sample + CUMP 0.2 | prose, prosethink, chat, mvs | `DFLASH.PASS` |

Podsumowania:
- `prose_sum.py ~/qwen-opt/draft-sample/logs/prose.jsonl ds-c20- A --mvs .../copy_bench.jsonl`;
- dla prosethink prefiks `think-ds-c20-`;
- chat: `spec_sum.py logs/spec_sweep.jsonl ds-c20-` (nowy: geośrednia ilorazów per prompt, CI bootstrap, dryf A). Sprawdzony na starym `e1ab` (raport 35): +1.39% [−2.36, +5.40], zgodnie z raportem.

Czas: ~26 jobów, 5 ABBA × 4 ramiona × ~12–20 min + bramki ~1 h, razem ≈ 5–6 h GPU `[INFERENCE]`. Kolejność w pliku daje najpierw CUMP 0.2 na MTP (najtańszy kandydat do produkcji), na końcu kontrole (0.35 i DFlash + CUMP).

Kryteria przyjęcia (do decyzji po wynikach):
- **CUMP na MTP:** bramka CONFIG PASS; ABBA prose T=1 > 0 z CI, bez straty na chat/prosethink/mvs; dryf A ≤ 1%; host w normie (prose_sum).
- **DFLASH_SAMPLE:** rozkład jest zachowany (test CPU), więc kryterium to tylko t/s DFlash2 sample vs argmax. Zysk względem MTP produkcji wymaga osobnego porównania (DFlash nadal przegrywa po polsku, 57e).

## 7. Czego nie zrobiłem / ryzyka

- Brak pomiarów GPU (zakaz). Liczby zysku pochodzą wyłącznie z kolejki.
- DSpark i adaptacyjna głębokość bez CUMP. DSpark ma własną głowicę pewności i nie jest w produkcji.
- Coupled + DFlash sample: sprzężenie wyboru ścieżki z szumem Gumbela celu (jak MTP coupled) dałoby zapewne więcej niż rejection `[INFERENCE]`, ale wymaga szumu celu per kandydat. To osobna praca.
- Istniejący test `test-coupled-sampling` nie był uruchamiany. Refaktor rejection zachowuje losowania z konstrukcji, a sprawdza go nowy test i bramka md5.

## 8. Do bazy wiedzy

- `LLAMA_DFLASH_SAMPLE=1` (branch `draft-sample` `a1aa0c13e`): DFlash2 losuje ścieżkę selektora softmax(scores/T) i podaje q do rejection. T=0 i coupled zostają przy argmaxie. Test chi-kwadrat CPU zielony.
- `LLAMA_DRAFT_CUMP=<próg>` (+ `_MIN`, domyślnie 1): odcięcie draftu po iloczynie prawdopodobieństw (reguła Mayi `DSPARK_CUM`) dla MTP (łańcuch i pętla) oraz DFlash. W łańcuchu MTP oszczędza tylko szerokość weryfikacji.
- Produkcyjne MTP nie ma progu na pozycję (`p_min = 0` warunkuje łańcuch), więc CUMP to jedyne ucinanie oparte na pewności.
