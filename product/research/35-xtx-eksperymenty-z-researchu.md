# 35. XTX: krótkie eksperymenty z raportów 32a/32b/32c/32f (głębokość MTP, checkpointy, kary, świeże starty, bitexact + adaptacja)

Data: 2026-10-20. Autor: podagent XtxLab. Karta: RX 7900 XTX (gfx1100, ROCm 10.0), ustawienia fabryczne, `gpu-guard.sh` aktywny.
Wszystkie pomiary GPU szły przez kolejkę `~/qwen-opt/queue/run-jobs.sh` (pliki `x35-a.jobs`, `x35-b.jobs`, `x35-c.jobs`), z jawnym env PM4 (`GGML_HIP_PM4=1 WA=2 GUARD=1 HSA_USE_SVM=0`) w każdym zadaniu. Kolejka nie zgłosiła ani jednego błędu amdgpu (page fault, reset, timeout ringu).
Binarka: zainstalowana topka `~/llama-topka` (topka `9056cea22` + host-gap). Serwer na ramię startował świeżo przez `run-topka.sh qwen` (MTP + lookup 3 W16, coupled, host-gap, GPU verify, ctx 204800, KV q4_0).
Skrypty: `~/qwen-opt/xtxlab/` (kopia: `product/research/35-skrypty/`). Logi: `~/qwen-opt/queue/logs/{e1,e1ab,e2,e3,e4,e5}-*.log`. Wiersze danych: `~/qwen-opt/xtxlab/logs/*.jsonl` i `*.server.log`.

Konwencje: `[INFERENCE]` oznacza wniosek bez pomiaru. CI to 95% bootstrap po promptach (prompt = jednostka, `xsum.py`). „ms/krok” i „tok/krok” liczone ze statystyk draftu w `timings`.

**Pułapka PM4, złapana na starcie.** `run-jobs.sh` eksportuje `GGML_HIP_PM4=0`, a `run-topka.sh` zachowuje odziedziczoną wartość (`${GGML_HIP_PM4:-1}`). Pierwszy przebieg E1 (`logs-pm4off-void/`) poszedł więc bez PM4: n=4 136.2 t/s zamiast 144.4. Przerwałem go i odrzuciłem dane. `x_arm.sh` ustawia teraz env PM4 sam. Lekcja do wiki niżej.

## 0. Werdykty

| # | eksperyment | wynik | werdykt |
|---|---|---|---|
| E1 | głębokość MTP n=4…7 | T=0 reasoning-v1: n=5 **+6.8%** (144.4 → 154.2 t/s), n=6 +7.8%, n=7 +8.4%; code-v1: n=5 +2.7%, n=7 −0.6%. Czat T=1, ABBA n=5 vs n=4: **+1.4% [−2.4, +5.4]**. `mvs` −2.1% [−5.3, +1.2]. n=6/7 na czacie: −2.7% [−5.7, +2.1] / −7.2% [−9.6, −4.8] | **profil konfiguracyjny `DRAFT_N=5` (opt-in) dla klasy T=0 reasoning**. Domyślne n=4 bez zmian. Bramki md5 przeszły, nowa referencja `d71a2c04` |
| E2 | koszt checkpointów stanu GDN w TTFT | ~150–180 ms na checkpoint (216–252 MiB). Świeży prompt: 2 checkpointy, 12–14% TTFT przy 2k, 3.8% przy 8k, 1.0% przy 32k. **Tura agenta po trafieniu w cache: 41–81% czasu promptu**. Wyłączenie checkpointów skraca TTFT 2k o 576 ms (−22%) | **warto wdrożyć (próg ≥10% przekroczony)**: async/VRAM checkpoint, bez duplikatu po restore, przenoszenie zamiast kopiowania w cache promptu |
| E3 | kary a akceptacja MTP (czat T=1) | akceptacja 54.5% → 52.7% (presence 1.5, −1.8 pp) i 53.1% (repeat 1.05, −1.4 pp); t/s −3.1% / −1.9%; ms/krok bez zmian | **nie wdrażać kar po stronie draftu** (próg ≥5 pp nieosiągnięty, sufit ≤3% t/s) |
| E4 | rozrzut prefillu przy świeżych startach | 10 startów llama-bench pp512: 1134.7–1137.2 t/s, rozrzut **0.22%**, brak bimodalności | **brak problemu MES na gfx1100**, nic do zrobienia |
| E5 | bitexact + adaptacyjna głębokość | przebieg 1: build nie skompilował się (`t.pos`, merge), kolejka poszła bez binarki. Po poprawce `3ec2fb535`: bitexact plain = MTP = MTP+adapt ×2 = GV=0 = `74952fd5`, tbo OK; domyślne MTP `a6328731` ≠ `6f14e814` (zamierzony reset `pending_h`) | **poprawność PASS; A/B szybkości niewykonane** (limit 10 min GPU), nie wdrażać przed ABBA |
| E7 | KLD Qwen3.6-35B-A3B (raport 33) | E7_WIERSZ | E7_WERDYKT |
| E6 | KLD EXL3-SC 3.0/4.0 | potrzeba ~30 GB EXL3 + referencji BF16 (54 GB) | **zablokowane łączem**, nie zaczęte |
| E8 | rozgrzewka promptu przed 1. żądaniem (39a E1) | 1. żądanie 2k: −182 ms (−6.7%), ABBA 4/4; md5 zmienia się (Qwen plain/MTP, LFM) | **nie wdrażać z klienta** (stratne); bezstratnie tylko w serwerze z `llama_memory_clear(…, true)` |

Wdrożone: tylko opis profilu `DRAFT_N=5` w nagłówku `~/qwen-opt/run-topka.sh` (opt-in, bez zmiany wartości domyślnej). Binarka `~/llama-topka` bez zmian. Topka nie była restartowana.

## 1. E1: głębokość draftu MTP (32f §TL;DR 3, plan E1)

**Hipoteza (32f):** na klasie `reasoning-v1` przy T=0 przewaga konkurencji to głównie głębokość draftu. Teza 32f: n=6–7 da +12–17% na tej klasie i 0 na czacie T=1.

**Setup.**
- Prompty kanoniczne LocalMaxxing pobrane z publicznego API (`/api/agent-context`; sha256 zgodne z `canonicalPrompts`): `reasoning-v1` (330 tok.) i `code-v1` (260 tok.). Zapis w `~/qwen-opt/xtxlab/{reasoning-v1,code-v1}.txt`. Nic nie wysyłaliśmy (decyzja 2026-10-20).
- `reason_bench.py`: thinking on, T=0, 512 tokenów, 1 rozgrzewka + 3 nonce (`[LocalMaxxing cache-bust nonce: …]`). Liczby z `timings` po stronie serwera, md5 tekstu per nonce.
- Czat: `spec_sweep.py` T=1, seedy 1,2 (6 promptów PL/EN × 400 tok.). Edycja kodu: `copy_bench.py --set mvs` T=0 1024 tok.
- Konfiguracja produkcyjna topki, zmieniane tylko `DRAFT_N`, świeży serwer na ramię.

**Skan (kolejność n4 n7 n6 n5 n4, `x35-a`):**

| n | reasoning-v1 t/s | tok/krok | ms/krok | akc. | code-v1 t/s | tok/krok | czat T=1 (geomean 6 promptów) | ms/krok czatu |
|---|---|---|---|---|---|---|---|---|
| 4 | **144.4** / 144.4 | 3.98 | 27.56 | 0.728 | 124.1 / 124.2 | 3.38 | 116.4 (2 przebiegi) | 27.6 |
| 5 | 154.2 (+6.8%) | 4.47 | 28.95 | 0.696 | 127.4 (+2.7%) | 3.66 | – | – |
| 6 | 155.6 (+7.8%) | 4.73 | 30.37 | 0.621 | 128.3 (+3.4%) | 3.86 | 113.3, −2.7% [−5.7, +2.1] (pl-kod +9%, en-code −7%) | 30.2 |
| 7 | 156.6 (+8.4%) | 5.00 | 31.96 | 0.585 | 123.4 (−0.6%) | 3.91 | 108.0, −7.2% [−9.6, −4.8] | 31.9 |

- Każdy dodatkowy poziom kosztuje ~1.45–1.6 ms/krok (draft + kolumna weryfikacji). Przy T=1 tok/krok rośnie słabo (en-chat 2.69 → 2.80 przy n=7), więc głębokość tam przegrywa.
- T=0 jest deterministyczne: dwa przebiegi n=4 dały identyczne t/s z dokładnością 0.1 i te same md5. To samo n=5 w trzech serwerach (skan, ABBA a/b): 154.2 / 154.2 / 154.1.
- **Teza 32f się nie potwierdza w skali.** Zamiast +12–17% mamy +7–8%. Mnożnik mal rośnie (3.98 → 5.00), ale krok drożeje o 16%.

**ABBA n=4 vs n=5 (`x35-b`, n4 n5 n5 n4):**

| klasa | n=4 | n=5 | Δ t/s [CI] | Δ tok/krok | Δ ms/krok |
|---|---|---|---|---|---|
| czat T=1 (6 × seedy 1,2, geomean) | 115.9 | 117.5 | **+1.4% [−2.4, +5.4]** | +7.1% [+3.9, +10.9] | +5.7% [+5.2, +6.5] |
| `mvs` T=0 (4 pliki) | 433.7 | 424.6 | **−2.1% [−5.3, +1.2]** | +1.1% | +3.2% [+0.3, +6.3] |
| reasoning-v1 T=0 | 144.4 | 154.2 | **+6.8%** (deterministyczne, 3/3) | +12.3% | +5.1% |
| code-v1 T=0 | 124.1 | 127.3 | **+2.6%** (3/3) | +8.3% | +5.3% |

**Bramki n=5** (`e1_md5.sh`, `fusion/greedy.sh` z nowym `DRAFT_N`; produkcja: `reason_bench`):
1. deterministyczność: greedy MTP n=5 `d71a2c04` dwa razy; reason_bench n=5 te same md5 w 3 serwerach;
2. GPU verify off == on: greedy `d71a2c04` = `d71a2c04`; reason_bench GV=0 te same 6 md5 (t/s −0.5%, czyli zysk GPU verify);
3. wygrana na swojej klasie: +6.8% / +2.6% (T=0 reasoning/code); na czacie i `mvs` brak istotnej regresji (CI obejmuje 0);
4. **zmiana konfiguracji z nową referencją md5**: n=5 daje inny tekst greedy niż n=4 (`d71a2c04` vs `6f14e814`; reasoning-v1 `022f4aed…` vs `841d5e2f…`). Szerokość weryfikacji zmienia numerykę (patrz 24q). Na `mvs` tekst n=5 = n=4 (te same md5).

**Werdykt E1.** n=5 nie wygrywa wyraźnie na czacie i lekko traci na `mvs`, więc nie zostaje domyślne. Na klasie T=0 reasoning wygrana jest wyraźna i deterministyczna, a bramki 1–4 przechodzą. Dlatego n=5 trafia do `run-topka.sh` jako opisany profil opt-in: `DRAFT_N=5 run-topka.sh qwen`. n=6/7 dają na reasoning tylko +1.0/+1.6 pp więcej, a kosztują czat (−2.7/−7.2%) i code-v1 (n=7), więc odpadają.

## 2. E2: udział checkpointów stanu w TTFT (32a §4 nr 1, 32b nr 2)

**Hipoteza:** 2 checkpointy po 94–104 ms na prompt (pomiar 2026-10-18), co daje −8% TTFT przy 2k i −25…30% na turze agenta po trafieniu w cache.

**Setup.** `LLAMA_CKPT_TIMING` z gałęzi `quickwins` nie trafił do topki. Topka ma jednak równoważny `LLAMA_SERVER_AP_TIMING=1`: synchronizacja przed checkpointem i czas `ap ckpt create`, `ap ckpt restore`, `ap save`. Dzięki temu obyło się bez buildu.
- Ramiona ABBA: A = produkcja (`AP_TIMING=1`), B = `--ctx-checkpoints 0`.
- `ttft.py`: świeże prompty 2k/8k (3 powtórzenia) i 32k (1).
- `replay.py`: prawdziwy system prompt + narzędzia omp, scenariusz `plain` z turą +500 tokenów, 2 przebiegi.
- Skrypty `ttft.py` i `replay.py` z commitu `7369380bf:qw/`.

**Koszt pojedynczego checkpointu:** 144–182 ms przy 216–252 MiB (`*.server.log`), czyli ~1.5 GB/s. Jest więcej niż 2026-10-18, bo stan wzrósł (150–170 → 216–252 MiB) `[INFERENCE: dodatkowy stan topki: lookup/spec]`.

**Świeże prompty (mediany, A1/A2 vs B1/B2):**

| prompt | TTFT A (ms) | TTFT B bez checkpointów | Δ | w tym kopie checkpointów (A) | udział kopii w prompt_ms |
|---|---|---|---|---|---|
| 2k | 2652 / 2628 | 2068 / 2060 | **−576 ms (−21.8%)** | 2 × ~152 = 298–321 ms | 12.2–14.2% |
| 8k | 8526 / 8513 | 7918 / 7925 | −598 ms (−7.0%) | 304–322 ms | 3.8–4.0% |
| 32k | 34535 / 34506 | 33975 / 33980 | −543 ms (−1.6%) | 348–358 ms | 1.0% |

Różnica A−B jest większa niż same kopie. Pozostałe ~250 ms to dwa dodatkowe podziały ubatcha (n−4−ub, n−4) oraz zapis poprzedniego stanu do cache RAM przy zmianie promptu. Ten zapis to `ap save: … alloc 343–350 ms (buf 128–130, ckpt copy 215–220)`: kopiowanie 436 MiB checkpointów host→host przy każdym nowym, niezwiązanym prompcie.

**Tura agenta (replay omp, trafienie w cache, A1/A2 identyczne co do liczby checkpointów):**

| krok | nowe tokeny | prompt_ms | checkpointy | restore | udział (ckpt + restore) w prompt_ms |
|---|---|---|---|---|---|
| S1-start (zimny) | 7357 | 7568–7594 | 3 × ~150 = 444–459 ms | – | 6% |
| S1-grow (+wynik narzędzia) | 602 | 1176–1209 | 3 = 442–463 ms | 36–45 ms | **41%** |
| S2-start (nowa sesja, ten sam system) | 63 | 527–543 | 2 = 293–305 ms | 42–44 ms | **64%** |
| S2-turn2 (krótka tura) | 27 | 570–601 | 3 = 429–451 ms | 33–39 ms | **81%** |

Część checkpointów to duplikaty. Po `ckpt restore … n_past 7337` serwer od razu tworzy checkpoint na tej samej pozycji 7337 (`superseding`), a w S2-start na 7278. Przy krótkich turach to ~150 ms czystej straty.

B (bez checkpointów) nie nadaje się do porównania na replayu: bez checkpointów stan rekurencyjny nie da się cofnąć, więc każda tura liczy cały prompt od nowa (6.9–7.5 s zamiast 0.5–1.2 s). To potwierdza, że checkpointy są niezbędne, a problemem jest tylko koszt ich kopii.

**Werdykt E2: warto wdrożyć, próg ≥10% przekroczony wielokrotnie** (12–14% świeżego 2k, 41–81% tur agenta). Kolejność pracy wg zysku i ryzyka `[INFERENCE]`:
1. Nie odtwarzać checkpointu na pozycji, z której właśnie zrobiono restore (stan identyczny): −150 ms na turę, kilka linii w `create_checkpoint`.
2. `prompt_save`: przenosić (`std::move`) checkpointy slotu do cache zamiast je kopiować: −215 ms przy każdej zmianie promptu/sesji.
3. Kopia D2D do bufora VRAM (~224 MiB, ~0.3 ms przy ~800 GB/s), a D2H w tle na strumieniu kopiującym (wzorzec Maya #253). Zysk −290…−450 ms na turę agenta, koszt +224–450 MiB VRAM (1–2 sloty stagingowe).

Bezstratność: to tylko kopie bajtów stanu. Bramka: md5 greedy + test restore == żywy serwer.

## 3. E3: kary samplera a akceptacja MTP (32a E3)

**Hipoteza:** kary (presence/repeat) działają tylko po stronie celu, więc draft je ignoruje i akceptacja spada. Próg wdrożenia kar w drafcie: spadek ≥5 pp.

**Setup.** Jeden serwer, kary per żądanie, kolejność P0 P1 R R P1 P0 (`x_arm.sh e3 pen`). spec_sweep T=1, seedy 1,2, 6 promptów:
- P0: bez kar;
- P1: `presence_penalty` 1.5;
- R: `repeat_penalty` 1.05.

| ramię | akceptacja (średnia 12 komórek) | tok/krok | t/s geomean | Δ t/s [CI] | ms/krok |
|---|---|---|---|---|---|
| P0 | 54.5% | 3.169 | 115.5 | – | 27.45 |
| P1 presence 1.5 | 52.7% (**−1.8 pp**) | 3.066 | 111.9 | −3.1% [−6.8, +1.3] | 27.39 |
| R repeat 1.05 | 53.1% (**−1.4 pp**) | 3.098 | 113.2 | −1.9% [−3.9, −0.1] | 27.35 |

- ms/krok bez zmian, więc kary nie zrzucają GPU verify ani szybkiej ścieżki top-k na pełny wiersz.
- Per prompt: presence 1.5 obniża akceptację na en-code (−10% t/s) i pl-proza, a podnosi na pl-kod (+6%). To efekt innego tekstu, nie tylko niedopasowania draftu.

**Werdykt E3: nie wdrażamy kar po stronie draftu.** Spadek 1.4–1.8 pp to mniej niż próg 5 pp. Cała strata t/s (≤3%) jest sufitem takiej pracy, a część to inny tekst, a nie niedopasowanie draftu.

## 4. E4: rozrzut prefillu przy świeżych startach (32a E2)

**Hipoteza (strata, gfx12):** MES przypisuje kolejkę do potoku przy pierwszej pracy. Na R9700 10/32 startów ma −13% prefillu. Sprawdzamy, czy XTX też ma bimodalny rozkład.

**Setup.** `e4_fresh.sh`: 10 osobnych procesów `llama-bench` topki (pp512, `-r 5`, FA, KV q4_0, PM4 env), seria 66 s.

| start | 1…10 |
|---|---|
| średnia powtórzeń 2–5 | 1134.7, 1135.1, 1135.4, 1136.1, 1135.4, 1135.1, 1136.1, 1135.1, 1136.6, 1137.2 t/s |
| pierwsze powtórzenie | 990.8–994.1 t/s (zawsze ~−12.6%, w każdym starcie) |

**Werdykt E4:** rozrzut między startami wynosi 0.22% (min 1134.7, max 1137.2), więc bimodalności nie ma. Problem MES/potoków z gfx12 nie występuje na gfx1100 przy naszym jednym strumieniu. Niższe pierwsze powtórzenie to rozgrzewka w procesie, a nie efekt startu. Nic do zrobienia.

## 5. E5: adaptacyjna głębokość na bitexact przy krótkim kontekście (32b nr 1)

**Setup.** Worktree `~/wt/bxadapt` (topka + adapt-spec `a69537d37` + batch-invariant `c09ac6aab..365af3e5e`), bramka `xtxlab/e5_gate.sh` (kolejka `x35-c.jobs`): test-backend-ops MUL_MAT/FLASH_ATTN_EXT z `LLAMA_SPEC_BITEXACT=1`, potem greedy md5 (`fusion/greedy.sh`, 2 prompty na serwer): bez przełączników = topka (plain `c4708318`, MTP `6f14e814`), a z bitexact plain == MTP == MTP + `LLAMA_SPEC_DEPTH_ADAPT=1` (2×) == to samo bez GPU verify. Po PASS: ABBA (A = topka, B = bitexact + adapt), czat T=1 + krótkie dokumenty.

**Przebieg 1 (20:38, rc=1): build się nie skompilował.** `common/speculative.cpp:2107: 't' was not declared`. Commit `fa88de6c3` (reset `pending_h` dla pozycji 0) przy przeniesieniu na kod topki zachował nazwę zmiennej z gałęzi bitexact (`t.pos[0]`). Łańcuch (`x35-chain.sh`) nie sprawdzał `build rc=2` i puścił kolejkę. Brakowało więc `llama-server` we wszystkich ramionach („No such file”), bramka padła, a ramiona A/B pominięto. Porażka była po stronie builda, nie numeryki.

**Poprawka (mała, oczywista):** `t.pos[0]` → `batch_in.tokens[k].pos[0]`, commit `3ec2fb535` w `~/wt/bxadapt`. Rebuild przyrostowy, ponowna bramka (21:32, 318 s GPU):

| sprawdzenie | wynik |
|---|---|
| test-backend-ops MUL_MAT / FLASH_ATTN_EXT (BITEXACT=1) | 2486/2486, 4060/4060 OK |
| bez przełączników, plain | `c4708318` = topka ✓ |
| bez przełączników, MTP n=4 | `a6328731` ≠ topka `6f14e814` ✗ (powód niżej) |
| bitexact plain / MTP / MTP+adapt ×2 / MTP+adapt GV=0 | wszystkie `74952fd5` ✓ (= referencja z raportu 12 §244) |
| adaptacja aktywna | `draft depth from acceptance: depths 2..6` |

**Diagnoza jedynego ✗.** Reset `pending_h` przy pozycji 0 działa w każdym trybie (raport 12 §75: „niezależnie od trybu”). `greedy.sh` wysyła 2 prompty na jeden serwer. W topce drugi prompt dostaje stary stan ukryty z końca pierwszego, a w bxadapt dostaje h=0. Inne drafty dają inne N weryfikacji, a domyślna weryfikacja nie jest niezmiennicza względem N, więc tekst się zmienia. To zamierzona zmiana zachowania (determinizm między requestami), nie regresja. Kryterium bramki „switches off = 6f14e814” było źle postawione dla tej gałęzi. Właściwe kryterium to „plain = c4708318 i bitexact wszędzie równe”, i ono przechodzi.

**Werdykt E5:** poprawność **PASS** (bitexact + adaptacyjna głębokość daje bit w bit ten sam tekst co plain, także bez GPU verify). **A/B szybkości nie zostało wykonane.** Ramiona ABBA to 4 × do 10 min GPU, a limit to ≤10 min GPU na pomysł i jedna powtórka (zużyte ~5.3 min). Kolejka `x35-c.jobs` jest gotowa: wystarczy `touch /tmp/x35/E5_PASS` i uruchomić ramiona e5-A/B. Nie wdrażać przed tym A/B. Raport 12 mierzył bitexact na plain tg128 −2.8%, a sens E5 to pytanie, czy adaptacja głębokości to odrabia. Dodatkowo nowe domyślne MTP md5 `a6328731` trzeba by przyjąć jako referencję, gdyby gałąź szła do topki.

**Lekcja procesowa:** `x35-chain.sh` uruchamia kolejkę po nieudanym buildzie. Każdy łańcuch build → GPU powinien kończyć się na `rc≠0` (`|| exit`), bo inaczej zużywa okno GPU na pustych ramionach.

**Pułapka PM4 (lekcja, naprawione w `2a46550`: `QUEUE_PM4_SAFETY`).** `run-jobs.sh` domyślnie eksportował `GGML_HIP_PM4=0`, a `run-topka.sh` brał `${GGML_HIP_PM4:-1}`. Każdy job w kolejce, który uruchamiał `run-topka.sh` bez jawnego env, cicho jeździł bez PM4 (−5.7%: 136.2 vs 144.4 t/s). Teraz `run-jobs.sh` oznacza swoje domyślne 0 przez `QUEUE_PM4_SAFETY=1`, a `run-topka.sh` wraca wtedy do profilu produkcyjnego. Audyt (wszystkie `*.sh`/`*.jobs` w `~/qwen-opt` wołające `run-topka.sh` i STARTy w `queue.log` od 2026-10-19 21:20, kiedy weszło domyślne 0):
- jawne env PM4 mają `gpuverify/gv_arm.sh`, `hostgap/hg_arm.sh`, `coupled2/c2_arm.sh`, `adaptspec/as_env.sh`, `bench-final/fb_arm.sh` (ramię T), `normfuse/lib.sh`, `agentpath/block.sh`, `xtxlab/x_arm.sh`, więc raporty 24m/24o/24p/24q/bench-final są czyste;
- bez jawnego env: `multistream/arm.sh`, `re/hybtail_bench.sh`, `hipfire/hold.sh`, `pm4fix/s6.sh`, `topka/arm.sh`. Wszystkie są sprzed 2026-10-19 21:20, kiedy kolejka nie eksportowała jeszcze 0, i od tego czasu nie szły w kolejce;
- **PM4-off były:** (1) pierwszy przebieg E1 tego raportu (`logs-pm4off-void/`, odrzucony); (2) okna testowe użytkownika `user-window` z 2026-10-20 00:38 i 14:07 (`user-window.sh` przed poprawką 19:35 nie ustawiał PM4). Jeśli użytkownik notował wtedy t/s topki, były zaniżone o ~5–6%. `topka-keeper`/`topka-restart` działają poza kolejką, więc produkcja nie była dotknięta.

## 6. E7 i E6: jakość kwantów (raport 33, raport 32c nr 1)

**E7 (Qwen3.6-35B-A3B UD-IQ4_XS, raport 33).** Pierwsze pobieranie (0.1–0.2 MB/s) zginęło razem z sesją na 1.10 GB. Wznowione 21:30 przez `curl -C -` (nice 19), łącze ~10 MB/s. Równolegle idzie referencja Q8_0 (36.9 GB, dla KLD). Protokół: `xtxlab/e7_kld.sh` (upstream `llama-master` `f61994f58`, PM4=0, bo to nie nasz fork):
- KLD IQ4_XS względem Q8_0: wiki.test.raw 100 × 512 i PL proza 20 × 2048 (zamiast korpusu czatu PL, który wymaga wygenerowanych odpowiedzi Q8);
- baza Q8_0 z `--n-cpu-moe 22`, bo nie mieści się w 24 GB;
- smoke `llama-bench -ncmoe 0,21,28 -d 0,32768` (KV q4_0).

Uruchamia się samo przez `xtxlab/e7_dl.sh`: pobiera, sprawdza rozmiar, potem kolejka `x35-e7.jobs`. Wyniki: `/tmp/x35/e7/`. IQ4_XS jest kompletny (17 730 509 792 B, 22:13). Pierwsze pobieranie Q8_0 zostało ucięte z 23.7 GB do zera: **`curl -C - --retry` przy ponowieniu używa offsetu z pierwszego startu i nadpisuje plik od początku**. `e7_dl.sh` robi więc pętlę świeżych `curl -C -` bez `--retry`.

E7_WYNIKI

**E6 (EXL3-SC 3.0/4.0, raport 32c nr 1):** niezaczęte. Wymaga ~30 GB EXL3 + referencji BF16 (54 GB) i exllamav3 1.6.3 (poprawki ROCm/gfx1100, CompWatch 2026-10-20). Przy obecnym łączu to ~2.5 h samego pobierania, więc osobne zadanie.

## 6b. E8: rozgrzewka ścieżki promptu przed pierwszym żądaniem (raport 39a E1, Maya #285)

**Setup.** Kolejka `x35-e8.jobs`, topka `~/llama-topka`, jawne PM4 produkcyjne. Rozgrzewkę udaje klient: jedno żądanie `/completion` z 1100 tokenami, `n_predict 4`, `cache_prompt false`, zaraz po `/health`.
- Bramka `xtxlab/e8_gate.sh`: `greedy.sh` (nowy `WARM=1`, domyślnie wyłączony) na Qwen plain + MTP n=4 i LFM plain, porównanie zimny vs rozgrzany.
- Pomiar: ABBA ×2 (A1 B1 B2 A2 A3 B3 B4 A4), każde ramię to świeży `run-topka.sh qwen` + `ttft.py --sizes 2048 --reps 4`.
- GPU: 103 s bramka + 8 × ~57 s ≈ 9.2 min.

**Szybkość (wall 2k, ms):**

| ramię | 1. żądanie | 2.–4. (min) | 1. − min |
|---|---|---|---|
| A (zimny) 1/2/3/4 | 2733 / 2705 / 2690 / 2723 | 2611 / 2594 / 2600 / 2647 | +122 / +111 / +90 / +76 (śr. **+100**) |
| B (rozgrzany) 1/2/3/4 | 2575 / 2509 / 2517 / 2521 | 2648 / 2590 / 2597 / 2612 | −73 / −81 / −80 / −91 |

Pierwsze żądanie 2k: A średnio 2713 ms, B 2531 ms, czyli **−182 ms (−6.7%)**, 4/4 pary. Kryterium 39a (A ≥ 80 ms, B ≤ 30 ms) jest spełnione. Kolejne żądania nie różnią się między ramionami. W B pierwsze żądanie jest nawet szybsze od kolejnych (~−80 ms); `[INFERENCE]` kolejne płacą coś, czego pierwsze po rozgrzewce nie płaci (np. checkpoint).

**Bramka md5: FAIL we wszystkich trzech.** Qwen plain `c4708318` → `8e089652` (pierwszy rozjazd przy znaku 69), MTP `6f14e814` → `fab508be`, LFM plain `894e56e4` → `cf3a7436` (znak 1760). Rozgrzewka zmienia tekst pierwszego żądania nawet w plain. `[INFERENCE]` Mechanizm jak w raporcie 12: zamaskowane wiersze KV nie są dokładnym no-op w WMMA/FA. Po rozgrzewce w komórkach poza aktualnym promptem leżą stare dane zamiast zer świeżego bufora. Do tego dochodzi stan `pending_h` MTP.

**Werdykt E8: nie wdrażać jako domyślne `run-topka.sh`.** Zysk jest realny (−182 ms TTFT pierwszego 2k raz na proces), ale bramka bezstratności nie przechodzi, więc rozgrzewka po stronie klienta odpada. Bezstratna wersja wymaga zmiany w serwerze: rozgrzewka przed READY, potem `llama_memory_clear(mem, /*data=*/true)` (zeruje bufory KV/stanu, nie tylko metadane), reset `pending_h` i stanu spekulacji, czyszczenie checkpointów slotu i cache RAM. Potem ta sama bramka (`greedy.sh WARM=1` musi dać `c4708318` / `6f14e814` / `894e56e4`). To build + ~10 min GPU, czyli osobny pomysł z raportu 39a nr 1.

## 7. Do bazy wiedzy

- **Głębokość MTP zależy od klasy ruchu.** Na T=0 reasoning n=5 daje +6.8% (n=7 +8.4%). Na czacie T=1 n=5 jest neutralne, a n=6/7 szkodzą. Stąd opt-in `DRAFT_N=5` w `run-topka.sh` (domyślne 4 bez zmian, potwierdzone w nagłówku `run-topka.sh:20-24`).
- **Checkpointy stanu GDN kosztują ~150–180 ms każdy.** W turze agenta po trafieniu w cache to 41–81% czasu promptu. To kandydat do wdrożenia (async/VRAM).
- **Kary (presence/repeat) obniżają akceptację MTP o 1.4–1.8 pp.** To za mało, żeby robić kary po stronie draftu.
- **gfx1100 nie ma bimodalności prefillu przy świeżych startach** (0.22%). Pierwsze powtórzenie jest ~12.6% wolniejsze w każdym procesie (rozgrzewka).
- **Bitexact + adaptacyjna głębokość jest poprawne** (plain = MTP = MTP+adapt = `74952fd5`, także bez GPU verify). Reset `pending_h` przy pozycji 0 zmienia domyślne MTP md5 przy kilku promptach na serwer (`6f14e814` → `a6328731`), co jest oczekiwane. A/B szybkości jeszcze nie zrobione.
- **Lekcja: łańcuch build → kolejka GPU musi przerywać się na `rc≠0`.** Inaczej okno GPU idzie na ramiona z brakującą binarką (E5, przebieg 1).
- **Lekcja PM4: domyślne 0 kolejki przeciekało do `run-topka.sh`** (−5.7% bez ostrzeżenia). Naprawione w `2a46550` (`QUEUE_PM4_SAFETY`). PM4-off były tylko: void E1 i okna `user-window` 2026-10-20 00:38 i 14:07 ([[lekcja-pm4-zawsze-jawnie]]).
- **Merge'e gałęzi na kod topki kompilować przed kolejką.** `fa88de6c3` na bxadapt nie kompilował się (nazwa zmiennej z innej bazy).
- **Rozgrzewka promptu: −182 ms (−6.7%) TTFT pierwszego żądania 2k po starcie, ale z klienta jest stratna.** Zmienia greedy md5 Qwen plain/MTP i LFM, bo stan bufora KV po rozgrzewce wpływa na numerykę zamaskowanych wierszy. Bezstratnie tylko w serwerze z `llama_memory_clear(..., true)` i resetem stanu spekulacji (E8).
- **`curl -C - --retry` nie jest wznawialne między ponowieniami:** retry wraca do offsetu z pierwszego startu i nadpisuje plik. Do dużych pobrań używać pętli świeżych `curl -C -`.
