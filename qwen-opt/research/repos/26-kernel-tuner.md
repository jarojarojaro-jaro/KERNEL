# 26 — Kernel Tuner (KernelTuner/kernel_tuner)

Repo: https://github.com/KernelTuner/kernel_tuner (płytki klon, commit `8e71bbf`, 2026-10-08). Artykuł o energii:
https://arxiv.org/abs/2211.07260 („Going green…”, Schoonhoven, Veenboer, van Werkhoven, Batenburg). Niczego nie uruchamiałem.
Ścieżki bez prefiksu odnoszą się do repo. `mmvq.cu` to `~/llama-master/ggml/src/ggml-cuda/mmvq.cu`.

## 1. Co to jest

To pythonowy framework do autotuningu: bierze kernel, słownik parametrów czasu kompilacji (`tune_params` → `#define` albo
argumenty szablonu), kompiluje każdą konfigurację, opcjonalnie sprawdza jej poprawność i mierzy ją, a po przestrzeni
chodzi jedną z ok. 20 strategii (brute force, BO, GA, SA, PSO, pymoo NSGA‑II…). Ma też cache wyników, tryb symulacji
i obserwatory (moc/energia przez NVML/amdsmi/PMT). Licencja Apache‑2.0. Projekt jest aktywny: wersja 1.5.0 z 2026‑08‑20,
ostatni merge 2026‑10‑08 (`CHANGELOG.md:5-13`). Rozwijany głównie pod NVIDIA (sterowanie zegarem i limitem mocy tylko
przez NVML). Backend HIP i `AMDSMIObserver` doszły w 1.3–1.4 (`CHANGELOG.md:17-24`), a jedyne przykłady HIP to
`examples/hip/vector_add*.py`.

## 2. Kluczowe techniki (z dowodami)

| # | Technika / mechanizm | Dowód | Uwagi (moje) |
|---|---|---|---|
| T1 | Parametry jako `#define` dopisywane przed źródłem (+`#line 1`). `defines` może być słownikiem lub funkcją od `params`. Parametry mogą też trafić do nazwy szablonu (`"k<my_type>"`) | `kernel_tuner/util.py:950-1053`, `doc/source/templates.rst:57-71` | Pasuje do naszych makr `#ifndef MMVQ_R3_*` (`mmvq.cu:10-23,271-284,348,1419-1440`) |
| T2 | Przestrzeń z ograniczeniami: `restrictions` jako lista wyrażeń lub funkcja, solver `python-constraint` (opcjonalnie pySMT/pyATF) | `interface.py:341-359`, `searchspace.py:13,237-500` | Pozwala odrzucić konfiguracje przed kompilacją |
| T3 | Strategie: BO (GP z sklearn; domyślnie `multi-ultrafast`, Matern32, 20 próbek LHS na start, `max_fevals` 100), GA (pop 26, 90 pokoleń, z uwzględnieniem ograniczeń), SA, PSO, MLS, dual annealing, pymoo (wielokryterialne) | `strategies/bayes_opt.py:27-45,116`, `strategies/genetic_algorithm.py:12-18`, `interface.py:403-422`, `strategies/pymoo_minimize.py:5-13` | BO koduje wartości porządkowo (indeks wartości → [0,1], `bayes_opt.py:48-61`) i zakłada brak szumu (`alpha=1e-10`, `bayes_opt.py:367-369`) |
| T4 | Budżety `max_fevals` / `time_limit` dla każdej strategii | `interface.py:431-447` | |
| T5 | Cache JSON z kontynuacją przerwanej sesji (klucz = indeksy parametrów) oraz **tryb symulacji**: replay strategii na pełnym cache bez GPU | `runners/sequential.py:83-125`, `doc/source/cache_files.rst:13-14`, `runners/simulation.py` | Strategię można wybrać „na sucho” |
| T6 | Weryfikacja: `answer` + `atol` albo własne `verify(ref, ans, atol)`. `Tunable` daje inną referencję dla każdej konfiguracji. `AccuracyObserver` zapisuje błąd (RMSE, max rel…) jako metrykę i wtedy wyłącza domyślne odrzucanie | `core.py:565-627`, `accuracy.py:13-66,189-337` | Błąd może być celem/ograniczeniem, a nie tylko bramką |
| T7 | Metryki użytkownika (np. GB/s z `time`) i cele wielokryterialne `objectives={"time":False,"energy":False}` → front Pareto w `env["best_config"]` | `interface.py:459-474,662-667,851-853`, `util.py:585-611` | |
| T8 | Pomiar domyślny: `iterations=7`, **jedno uruchomienie na parę zdarzeń**, `synchronize` przed każdym, wynik to średnia. Bez flushowania cache. Pierwsza konfiguracja jest uruchamiana na rozgrzewkę i odrzucana | `core.py:440-461`, `observers/hip.py:28-36`, `runners/sequential.py:89-96` | Dla nas kluczowa wada (§3, §5) |
| T9 | Tryb „ciągły” dla obserwatorów mocy: kernel w pętli przez ≥ `continuous_duration` (1 s), energia przeskalowana na jedno wywołanie | `core.py:463-484,526-531`, `observers/amd.py:172-226` | Tak można mierzyć stan ustalony przy limicie mocy |
| T10 | `AMDSMIObserver`: energia z licznika `amdsmi_get_energy_count`, moc = Δenergii/Δt, próbki zegarów, temperatury hotspot/VRAM, napięcia i aktywności, całkowane trapezami | `observers/amd.py:74-169,229-401` | Działa tylko na odczyt. Nie steruje zegarem ani limitem (§5) |
| T11 | Strojenie zegara i limitu mocy jako parametrów (`nvml_gr_clock`, `nvml_pwr_limit`) i model moc–częstotliwość z artykułu „Going green” | `core.py:486-502`, `energy/energy.py:5-6,40-89`, `doc/source/vocabulary.rst:26-27` | Tylko NVML/NVIDIA |
| T12 | Strojenie kodu hosta: `lang="C"`; funkcja C zwraca `float`, który staje się „time”. Obiekt `.so` jest budowany dowolnym kompilatorem (`compiler=`) | `backends/compiler.py:182-308,338-370`, `doc/source/hostcode.rst` | **Furtka, przez którą podepniemy własny harness** (§4) |
| T13 | `kernel_source` może być funkcją `params → str` (generator kodu) | `util.py:752-754` | Hook na budowanie wariantu po stronie Pythona |
| T14 | Integracja: `store_results` (top 3% dla każdego `device_name` i `problem_size`), `TuneResults.get_best_config(gpu, problem_size)`, `create_device_targets` → nagłówek `#ifdef TARGET_<gpu>` | `integration.py:52-96,99-217,220-299` | Nagłówek ma **jedną** konfigurację na GPU, nie na kształt (`integration.py:228-231`) |
| T15 | Strojenie równoległe przez Ray: jeden aktor na GPU (`num_gpus=1`) | `runners/parallel.py:29-48,191-195` | Na 1 GPU nie zrównolegla kompilacji |

### Backend HIP: dojrzałość (stan z kodu)
- Kompilacja tylko przez **hiprtc** (`backends/hip/hip.py:186-228`): `--offload-arch=<gcnArchName>` oraz opcje użytkownika.
  Nie da się użyć hipcc. Kernel musi się kompilować jako samodzielny string, a nagłówki hosta z ggml (`common.cuh` → `ggml.h`,
  STL) są pod hiprtc ryzykowne `[WNIOSEK]`.
- Architektura brana z urządzenia **0** zamiast `self.device` (`hip.py:199-200`). Przy jednej karcie bez znaczenia.
- Wycieki: `hiprtcDestroyProgram` jest wołany tylko przy wyjątku (`hip.py:230-233`), brakuje `hipModuleUnload` i `hipFree`
  (grep: brak). Przy setkach konfiguracji rośnie zużycie pamięci, ale da się to przeżyć.
- Argumenty to tylko tablice numpy (`hipMalloc` + kopia) i skalary (`hip.py:129-171`). Bez `DeviceArray` i bez tekstur (`hip.py:376-380`).
- `RegisterObserver` wymaga `dev.num_regs`, a ustawiają go tylko backendy CUDA (`observers/register.py`, `backends/nvcuda.py:327-329`),
  więc na HIP nie ma VGPR/spilli.
- Zależność `hip-python` jest przypięta do testpypi `^6.3.3` (`pyproject.toml:96`). Zgodność z ROCm 10.0 jest niepewna `[WNIOSEK]`.
- Testy HIP: jeden plik, 161 linii, vector_add (`test/test_hip_functions.py`). Ocena: **działa dla samodzielnych, prostych
  kerneli, ale nie jest dojrzałe pod nasz przypadek** (kernele osadzone w ggml, ograniczone pamięcią, trwające µs).

## 3. Przeniesienie na AMD/HIP/RDNA3

| Technika | Da się? | Jak u nas / co się nie przeniesie |
|---|---|---|
| T1/T2 makra + ograniczenia | Tak | Nasze pokrętła już są makrami. Ograniczenia typu `RPB*NC <= 32`, „bez spilli” (z `-Rpass-analysis=kernel-resource-usage`, czyli tam, gdzie na HIP brakuje RegisterObserver) |
| T3 BO/GA | Tak, ale z głową | Przestrzenie MMVQ są małe (dziesiątki–setki), a koszt jest zdominowany przez **kompilację** `mmvq.cu`, nie przez pomiar. BO opłaca się dopiero przy iloczynie przestrzeń × kształty (§4). Parametry kategoryczne (polityka cache GLC/DLC/SLC) są w BO porządkowe, więc trzeba je ułożyć sensownie albo stroić osobno |
| T5 cache + symulacja | Tak, w 100% | Brute force raz na jednym kształcie, potem replay BO/GA/random z `max_fevals` 20–60 bez GPU, żeby wybrać strategię dla pozostałych kształtów |
| T6 weryfikacja | Tak | Referencja = hash wyjścia bazowej konfiguracji (jak `mmvq-bench/mm_dump`). Pokrętła zachowujące kolejność sum (RPB „same lanes”, `mmvq.cu:1362-1366`) → wymóg bitowej zgodności. Pokrętła zmieniające redukcję (nwarps, split) → `AccuracyObserver` (max rel) jako metryka, a decyzja po KLD w modelu |
| T8 pomiar natywny HIP | **Nie dla nas** | Jedno uruchomienie na parę zdarzeń, ciepły cache (wagi < 96 MB MALL siedzą w Infinity Cache), średnia z 7. Nasze MMVQ trwają 2–30 µs i są ograniczone pamięcią, więc taki pomiar mierzy cache i narzut zdarzeń. Trzeba podpiąć nasz harness „na zimno” (`mmvq_bench`, `kbench.sh` + rocprofv3) przez T12 |
| T9/T10 energia, stan ustalony | Częściowo | `AMDSMIObserver` działa z backendem C, ale z `device_id=0` podanym jawnie (backend C nie ma UUID/PCI w `env`, więc autodetekcja rzuci `ValueError`, `amd.py:285-293`). Moc i energia pochodzą wyłącznie z licznika energii. `current_power_usage` istnieje, ale nie jest używany (`amd.py:92-102` vs `356-372`). Czy Navi31/SMU13 udostępnia licznik przez amdsmi: `[WNIOSEK]` raczej tak, do sprawdzenia jednym wywołaniem |
| T11 zegar/limit jako parametr | Nie | Brak odpowiednika dla amdsmi w KT, a zapis `power1_cap` u nas wymaga roota (`NOTES.md:110-113`) |
| T12/T13 host‑code + generator | Tak | Szkielet całej integracji (§4.0) |
| T14 nagłówek celów | Częściowo | `create_device_targets` daje jedną konfigurację na GPU, a my chcemy tablicę per (typ, ncols, kształt). Własny emiter na bazie `get_best_config(gpu, problem_size)` |
| T15 Ray | Nie | 1 GPU = 1 worker. Równoległa kompilacja wariantów musi być nasza (xargs -P, `nice`) |

## 4. Pomysły dla nas

### 4.0 Proponowany setup (dokładnie, bez uruchamiania)

**Zasada:** KT robi wyłącznie przestrzeń, strategię, cache, weryfikację i zapis wyników. Kompilację i pomiar robi nasz
istniejący łańcuch (`compile_commands.json` + `mmvq_bench`/`kbench.sh`), czyli ten sam kod i tę samą ścieżkę dispatchu co
w produkcji. Nie potrzeba `hip-python`. Wystarczy `kernel_tuner` + numpy/scipy/scikit‑learn w `~/qwen-opt/.venv`
(instalacja dopiero za zgodą użytkownika; brief zabrania jej teraz).

1. **Budowa wariantu (CPU, równolegle, `nice`):** dla zestawu makr `M` wziąć komendę `mmvq.cu` z
   `build-hip/compile_commands.json` (wpis `ggml/src/ggml-cuda/mmvq.cu`; jest tam `-O3 --offload-arch=gfx1100 -x hip -c`), dodać
   `-D<k>=<v>` oraz `-Rpass-analysis=kernel-resource-usage` (log VGPR/SGPR/scratch/occupancy). Potem zlinkować
   `libggml-hip.so` z `ggml/src/ggml-hip/CMakeFiles/ggml-hip.dir/link.txt`, podmieniając tylko `mmvq.cu.o`, do `/tmp/ktv/<sha(M)>/`.
   Hash zależy **tylko od makr**, więc jeden wariant obsługuje wszystkie kształty. Warianty ze scratch > 0 → `InvalidConfig`
   (odcinamy je przed GPU). Opcjonalnie strażnik `-DMMVQ_TUNE_ONLY_TYPE/NCOLS`, który wycina pozostałe instancjacje z
   `mmvq.cu`. Mała łatka, czas kompilacji spada z minut do sekund `[WNIOSEK]`.
2. **Pomiar (GPU, pod `flock /tmp/gpu.lock`):** dodać do `mmvq_bench.cpp` tryb `--one TYPE K N NCOLS`. Wypisuje medianę µs
   na MUL_MAT (już jest „na zimno”: kopie > 512 MB, `mmvq_bench.cpp:26-30`) i 64‑bitowy hash wyjścia pierwszej kopii (jak `mm_dump`).
3. **Stub dla KT (`lang="C"`):** `kernel_source` jako funkcja (T13), która woła krok 1 i zwraca mały plik C:
   ```c
   #include <stdio.h>
   #include <stdint.h>
   extern "C" float run(uint64_t *hash) {
     FILE *p = popen("env LD_LIBRARY_PATH=/tmp/ktv/<sha>:/opt/rocm/core-10.0/lib "
                     "/home/jaro/qwen-opt/mmvq-bench/mmvq_bench --one q4_K 5120 17408 5", "r");
     float us = 1e30f; unsigned long long h = 0;
     if (!p || fscanf(p, "%f %llx", &us, &h) != 2) us = 1e30f;
     if (p) pclose(p);
     hash[0] = h;
     return us * 1e-3f;               /* KT traktuje "time" jako ms */
   }
   ```
   Wywołanie:
   ```python
   res, env = tune_kernel("run", stub, problem_size=(N,), arguments=[np.zeros(1, np.uint64)],
       tune_params={"MMVQ_R3_RPB_N8": [1, 2, 4, 8], "MMVQ_R3_NW_MULTI": [1, 2, 4],
                    "MMVQ_R3_WAVES_KQ": [4, 5, 6, 8, 10, 12, 16], "MMVQ_R3_X_CPOL": [0, 1, 3, 5],
                    "MMVQ_R3_PIPE_Q6K": [0, 1]},
       restrictions=["MMVQ_R3_RPB_N8 * MMVQ_R3_NW_MULTI <= 8"],
       lang="C", defines={}, iterations=3,
       answer=[np.array([REF_HASH], np.uint64)],
       verify=lambda ref, out, atol=None: ref[0][0] == out[0][0],   # tylko dla pokręteł bitowo neutralnych
       strategy="bayes_opt", strategy_options={"max_fevals": 60, "time_limit": 3600},
       cache=f"kt/mmvq_q4K_5120x17408_n5.json",
       metrics={"GB/s": lambda p: WBYTES / (p["time"] * 1e-3) / 1e9},
       observers=[], quiet=False)
   store_results("kt/mmvq-gfx1100.json", "mmvq", "", tune_params, (K, N, NC), res, env)
   ```
   Ograniczenie w przykładzie jest ilustracyjne: realne wynikną z rejestrów, a odfiltruje je krok 1.
   Pułapki: (a) **nie włączać `AMDSMIObserver` z trybem ciągłym na tym stubie**. KT wylicza liczbę powtórzeń jako
   `1 s / time` (`core.py:465`), a jedno wywołanie stubu trwa ~1 s (start procesu), więc wyszłyby minuty na
   konfigurację. Energię mierzy `mmvq_bench --one` w swojej pętli i zwraca ją przez drugi element tablicy wyjściowej.
   (b) `iterations=3`, bo mediana jest liczona w środku. (c) Pierwsza konfiguracja idzie na rozgrzewkę i jest
   odrzucana (`sequential.py:89-96`), co jest OK.
4. **Wybór strategii bez GPU:** na jednym kształcie (Q4_K 5120×17408, n=5) zrobić brute force po przestrzeni po odcięciu
   spilli, potem `simulation_mode=True` z tym cache: BO vs GA vs random przy 20/40/60 fevals. Jeśli BO dojdzie do ≤1%
   od optimum w 40 fevals, używamy BO na pozostałych kształtach, w przeciwnym razie brute force.
5. **Emiter tablicy:** `kt_emit.py` czyta `kt/mmvq-gfx1100.json`, dla każdego (typ, ncols) liczy optimum per kształt
   (`get_best_config(gpu, problem_size)`) i **zachłannie scala do ≤2–3 różnych konfiguracji**, minimalizując
   Σ wywołań/token × t(kształt, konfiguracja). Wagi bierze z rocprofv3 (np. `research/lfm-decode.md:35-49`), a nie z
   `_select_best_common_config` KT (ten sumuje surowe czasy bez wag, `integration.py:304-337`). Wynik zapisuje do
   `mmvq-r3-table.inc` (constexpr + dispatch po `nrows`/`K`), co ogranicza liczbę instancjacji szablonu.
6. **Bramka w modelu:** top‑3 z mikrobencha → `variant.sh` + `prof_serve.sh` + `verify_mmvq.py` (rocprofv3 w modelu),
   bo mikrobench mylił się co do Q6_K i GLC|DLC (`NOTES.md:247-248`). Na końcu greedy md5 / KLD jak dotąd.

### 4.1 Eksperymenty

| # | Co | Gdzie | Zysk `[SZACUNEK]` | Koszt | Ryzyko | Pomiar |
|---|---|---|---|---|---|---|
| E1 | **LFM n=1 MMVQ per kształt:** rows/block {1,2,4}, nwarps (podział K między fale) {1,2,4}, waves_per_eu dla małych startów 512×2048 (k/v, 274–317 GB/s), 2048×2048 (q/o/out_proj, ~550–590 GB/s) i 1536×2048 ekspertów. Dziś jest jedna globalna wartość: 2 wiersze; 4 wiersze pomagały dużym kształtom, a psuły małe (o‑proj 5.3 → 6.6 µs, `lfm-decode.md:141-142`). To dowód, że optimum zależy od kształtu | `calc_nwarps` / `calc_rows_per_block` dla RDNA3 n=1 (`mmvq.cu:1290-1309,1367-1413`) + tabela z kroku 5 | Przy 512 wierszach i K=2048 to tylko ~5 fal/CU, więc podział K ×2–4 powinien podnieść pasmo małych startów o 15–30%. Klasa „małych” to ~250–350 µs/token (`lfm-decode.md:42-48`), więc **−0.05…−0.12 ms/token (1–3%)** | 1–2 dni | nwarps zmienia kolejność redukcji, więc nie jest bitowo zgodny; potrzebny KLD | rocprofv3 tg, ms/token przeplatane A/B |
| E2 | **Qwen wielokolumnowe (n=5) per kształt:** waves_per_eu i RPB osobno dla 1280‑blokowych (5120 wierszy) i 4352‑blokowych (17408) startów. NOTES: „W=6 za mało fal dla 1280 bloków” (`NOTES.md:250`), czyli kompromis na wspólnym makrze | `mmvq_max_waves_per_eu`, `calc_rows_per_block` (`mmvq.cu:1400-1456`) | 1–3% czasu MMVQ z 22.1 ms/weryfikację → **−0.2…−0.6 ms/krok** | 2–3 dni (główny koszt to budowa wariantów) | Rozjazd mikrobench–model (bramka 4.0.6) | `verify_mmvq.py`, ms/krok |
| E3 | **FA‑kvq: split i nwarps per przedział n_kv:** dziś `nsplit = 2*nsm/(ntiles_x*nblocks_z)` bez zależności od długości KV i `nwarps=8` na sztywno. Zamienić na makra `FATTN_KVQ_SPLIT_MUL ∈ {1,2,3,4,6,8}`, `FATTN_KVQ_NWARPS ∈ {4,8,16}`, `waves_per_eu`; tabela dla (D=256/64, ncols 1/5, n_kv 2k/8k/32k/96k) | `fattn-kvq.cu:541-545,639` | Przy 94k FA to kilka ms/krok (`stepcost.md:66`: ~2.3 ms przy 100k `[INFERENCE]` tam). 10–20% z tego → **−0.2…−0.5 ms/krok przy długim kontekście** | 1–2 dni + bench FA „na zimno” (KV > 96 MB) | Split zmienia combine, więc nie jest bitowy; `test-backend-ops -o FLASH_ATTN_EXT` + KLD | `long_ctx_bench`, llama-bench d32768/d98304 n1/n5 |
| E4 | **Strojenie świadome limitu mocy:** końcowe top‑3 z E1–E3 zmierzyć w stanie ustalonym (pętla ≥2 s przy 285 W, energia/J na wywołanie z amdsmi w `mmvq_bench --one`). Przy remisie czasu (±1%) wybrać niższą energię: przy limicie mocy oszczędność waty w MMVQ to wyższe sclk dla WMMA/FA w tym samym kroku | Pole `energy` w stubie; `objectives={"time":False,"energy":False}` → Pareto (T7) | Mały, 0–1% kroku `[SZACUNEK]`, ale za darmo przy okazji | 0.5 dnia | Licznik energii SMU13 może mieć rozdzielczość ~ms, więc pętla musi być długa | ms/krok przy 285 W, `amd-smi metric -p` |
| E5 | **Mniejsze fuzje z jednym, dwoma pokrętłami** (`MMVQ_MOE_DOWN_RPB` `mmvq.cu:3308`, rozmiar bloku rms_norm/q8_1, norm+router): brute force w KT tylko dla dyscypliny (cache, bitowa weryfikacja hashem, wyniki per kształt) | odpowiednie `#ifndef` | Po kilka µs/token | niski | niskie | rocprofv3 |

**Pomysły poza schematem:**
- **Kompilacja jako ograniczenie:** `-Rpass-analysis=kernel-resource-usage` w kroku 1 daje VGPR, occupancy i scratch dla
  każdego wariantu jeszcze przed GPU. Z tych danych można wytrenować tani filtr (np. reguła „scratch > 0 albo occupancy < X
  → pomiń”), który odetnie 30–60% przestrzeni `[SZACUNEK]`. To substytut brakującego `RegisterObserver` dla HIP.
- **Pre‑build sterowany strategią:** BO jest sekwencyjne, ale GA ocenia całe populacje (`genetic_algorithm.py:48`), więc
  przed każdą generacją można zbudować 26 wariantów równolegle na 8 rdzeniach. Wtedy przy kompilacji dominującej koszt
  GA jest zwykle tańszy w zegarze ściennym niż BO `[WNIOSEK]`.
- **Ten sam setup dla parametrów runtime** (bez kompilacji): `GGML_HIP_MMVQ_N1_ROWS`, ewentualny env dla splitu FA,
  `-ub`. Stub woła `llama-bench`. **Ostrzeżenie:** GP w KT zakłada brak szumu (`alpha=1e-10`), a nasze e2e ma ±0.3 ms,
  więc lepiej brute force po małej siatce niż BO.

## 5. Krytyka

- **Natywny pomiar KT nie nadaje się do naszych kerneli** (`core.py:440-461`). Jedno uruchomienie na parę zdarzeń, ciepły
  cache, średnia zamiast mediany, `synchronize` przed każdym uruchomieniem. Dla kerneli 2–30 µs ograniczonych pamięcią,
  przy 96 MB MALL, ranking wyjdzie inny niż „na zimno”. Ten sam problem mieliśmy już z naszym mikrobenchem, a i tak
  musimy kończyć w modelu.
- **Backend HIP jest „portem CUDA”**: tylko hiprtc, wycieki modułów i programów, brak liczby rejestrów, urządzenie 0 na
  sztywno przy kompilacji (`hip.py:199-233`). Dokumentacja obserwatorów nie wymienia nawet HIP (`doc/source/observers.rst:24`).
  Część „energy” (model moc–częstotliwość, strojenie zegara i limitu) jest tylko dla NVML (`energy/energy.py:5-6`, `core.py:486-502`).
- **BO ma tu ograniczoną wartość.** Kodowanie porządkowe, brak modelu szumu, domyślnie 20 próbek LHS na start
  (`bayes_opt.py:44`): przy przestrzeniach rzędu 100–700 i `max_fevals` 60 to już 1/3 budżetu. U nas wąskim gardłem jest
  kompilacja, a nie liczba pomiarów. Bez równoległej budowy wariantów KT niewiele przyspieszy.
- `create_device_targets` i `_select_best_common_config` wybierają jedną konfigurację na GPU, sumując surowe czasy bez wag
  (`integration.py:228-231,304-337`). Do tabeli per kształt to się nie nadaje, trzeba własnego emitera.
- Nie należy oczekiwać „magii” autotuningu. Nasze pokrętła są już ręcznie przestrojone (`NOTES.md:241-256`, łatki 0021/0022/0052),
  a NI=8/NI=2 i RPB=8 dały wynik negatywny (`NOTES.md:103`). Realny zapas jest tylko tam, gdzie wspólne makro jest
  kompromisem między kształtami (E1–E3). Szacunkowo 1–3% dla LFM i ~1–2% dla Qwena, a przy długim kontekście więcej (E3).
- Plusy: dojrzała księgowość eksperymentów (cache z kontynuacją, tryb symulacji, weryfikacja per konfiguracja, Pareto),
  aktywny rozwój, Apache‑2.0.

## 6. Werdykt

**Średnia.** Backend HIP i natywny pomiar KT nie pasują do naszych kerneli, ale jako sterownik przeszukiwania (furtka
`lang="C"` + nasz pomiar „na zimno” + cache, symulacja, weryfikacja hashem) daje uporządkowaną drogę do strojenia
per kształt. Tam realnie zostało 1–3% (E1/E2) i więcej przy długim kontekście (E3).
