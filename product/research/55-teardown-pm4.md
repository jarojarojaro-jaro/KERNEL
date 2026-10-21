# 55: page fault przy zatrzymaniu serwera PM4 w trakcie generacji (XTX), 2026-10-21

**Werdykt: przyczyną jest `exit(1)` wołane z handlera sygnału przy DRUGIM SIGTERM. `exit()` uruchamia destruktory modułów HIP i zwalnia code objecty, a wątek główny w tym czasie czeka na taśmę PM4, która wciąż wykonuje się na GPU. Poprawka jest w gałęzi `pm4-teardown`: sygnał obsługuje zwykły wątek, a GPU jest drenowane przed jakimkolwiek zwalnianiem. Działa domyślnie, bez przełącznika.**
- **GPU, runda 1** (`td.jobs`, 13:26–13:57):
  - md5 greedy SAME (`e97a0d66…`, base = fix);
  - 3× SIGTERM: 20/20 bez faultu, wyjście po ~0.3 s;
  - 1× SIGTERM: 20/20 bez faultu, ale serwer sam nie wychodził: 20/20 SIGKILL po ~61 s. Przyczyna i poprawka w sekcji „Runda 2”, test w `td2.jobs`.
- Gałąź `pm4-teardown` (commity `a13fa3034` + `e52b38014`, worktree `~/wt/pm4-teardown`) na `topka` `cf927413b` (linia produkcyjna f9b84bcfa). Build: `~/qwen-opt/teardown/inst/bin/llama-server` (`rbuild --local`, rc 0, bez ostrzeżeń w zmienionych plikach; `fix-runpath.py` → `$ORIGIN`, `--check` 0).
- Pliki: `tools/server/server.cpp`, `server-http.cpp`, `server-http.h`, `ggml/src/ggml-cuda/hip-pm4.cu`, `hip-pm4.cuh`, `ggml-cuda.cu`.

## Zdarzenia
| | 04:07:21 | 12:46:18 |
|---|---|---|
| job | `s53c-A1` (`p100_arm.sh`, build draft-shortlist, przełącznik off) | `s53m-A1` (to samo ramię) |
| kernel | gfxhub page fault, ring 24 vmid 8, `SQC (inst)`, PERMISSION_FAULTS 0x3, RW 0, pid 1293181 | to samo, pid 22639, adres 0x776f5aba5000, potem 5 wpisów CB/DB ze statusem 0 i `sq_intr: error type 2` |
| proces | – | **`traps: llama-server[22639] general protection fault ... in libc.so.6`, w tej samej sekundzie** |
| log serwera | ostatnia linia: task 762 w trakcie generacji, potem 2× `Received second interrupt, terminating immediately.` | to samo: generacja tasku 762, 2× `Received second interrupt` |

Oba logi: `~/qwen-opt/draft-shortlist/logs/s53-A1.launch.log` i `s53m-A1.launch.log`. Serwer dostał **co najmniej 3 SIGTERM w kilka ms**:
- `cancel.sh` wysyła SIGTERM do potomków runnera;
- `p100_arm.sh` ma `trap 'exit 1' TERM` i `trap stop EXIT`, a `stop()` robi `pkill -f "llama-server.*--port $PORT"`;
- serwer sam dostaje też SIGTERM od `cancel.sh`.

Lekcja z 04:07 przypisywała fault SIGKILL-owi. Log serwera pokazuje jednak, że wcześniej zadziałała ścieżka `exit(1)`.

## Przyczyna (kod przed poprawką, `topka` cf927413b)
1. `tools/server/server.cpp:28-37` – `signal_handler`:
   - pierwszy sygnał woła `shutdown_handler` (`:500-504`), czyli `server_context::terminate` (`server-context.cpp:4891`), a potem `server_queue::terminate` (`server-queue.cpp:132-136`). To mutex i `notify_all` w kontekście sygnału, a więc nie async-signal-safe;
   - **drugi sygnał robi `exit(1)` (`server.cpp:33`) natychmiast, na dowolnym wątku.**
2. Pętla główna kończy się dopiero na granicy kroku: `process_new_tasks` sprawdza `running` (`server-queue.cpp:138-144`, `:366-370`). Krok MTP+weryfikacja w trakcie generacji trwa ~12 ms i ma kilka taśm. Wątek główny siedzi wtedy w `ggml_hip_pm4_launch` (`hip-pm4.cu:1039-1119`, wersja przed poprawką): taśma wysłana pakietem vendor AQL na własną kolejkę HSA (`:1085-1103`), a host kręci się na sygnale ukończenia (`:1106`).
3. `exit(1)` uruchamia handlery `atexit`. Wśród nich jest `__hip_module_dtor` każdego modułu HIP: clang rejestruje go przez `atexit` w konstruktorze modułu. Ten destruktor woła `__hipUnregisterFatBinary`: code objecty kerneli są wyładowywane, a ich pamięć zwalniana i odmapowywana z VM GPU. Fale taśmy pobierają wtedy instrukcje spod zwolnionego adresu, co daje **SQC (inst), PERMISSION_FAULTS 0x3**.
   - HIP synchronizuje tylko własne strumienie, a o naszej kolejce HSA nic nie wie.
   - [INFERENCE] dokładnej kolejności zwalniania wewnątrz HIP nie śledziłem (wymagałoby to GPU).
4. Destruktory statyczne biegną równolegle z żywym wątkiem głównym i wątkami HTTP. To tłumaczy GP fault w libc w tej samej sekundzie. `exit()` z handlera sygnału może się zakleszczyć na zamkach (malloc, loader), stąd „nie wyszedł w 45 s” i SIGKILL o 12:46.
5. Dlaczego dopiero teraz: wystarczy jeden SIGTERM, a pętla staje na granicy kroku, taśma jest synchroniczna i nic nie wisi. Fault wymaga ≥2 sygnałów **w trakcie generacji**, a taki wzór powstał dopiero przy połączeniu `cancel.sh` z `stop()` w `p100_arm.sh`.

Własność obiektów: IB taśmy (`hsa_amd_memory_pool_alloc`, pula hosta), kernargi (VRAM) i bufory guard należą do `ggml_hip_pm4_tape`. Zwalnia je `ggml_hip_pm4_free` z destruktora `ggml_cuda_graph` (`common.cuh:1358-1365`), czyli dopiero przy zwalnianiu kontekstu. Kolejka HSA i sygnał (`pm4_device`) żyją do końca procesu. Code objectów taśma nie posiada: adres `code_entry` pochodzi z code objectów załadowanych przez HIP, a te znikają w destruktorach modułów HIP. Właśnie to wyścig `exit()` zwalnia pod pracującą taśmą.

## Poprawka (gałąź `pm4-teardown`, domyślnie włączona, bez przełącznika)
**Serwer** (`tools/server/server.cpp`):
- `:69-94`: handler SIGINT/SIGTERM jest async-signal-safe. Zapisuje tylko numer sygnału do nieblokującego pipe'a (z `FD_CLOEXEC`); bez zamków, alokacji i `exit()`.
- Osobny wątek `signal_thread_main` czyta pipe i woła `on_shutdown_signal` (`:42-66`):
  - **pierwszy sygnał** loguje `received signal N: stopping at the next step boundary...` i zatrzymuje pętlę na granicy kroku (`terminate`, jak dotąd);
  - **kolejny sygnał nie pomija drenażu**: czeka na `gpu_drained`, maksymalnie 30 s (log), i dopiero potem robi `std::_Exit(1)`. `_Exit` nie wywołuje `atexit` ani destruktorów statycznych, więc nie wyładowuje code objectów; resztę sprząta jądro;
  - jeśli drenaż nie skończy się w 30 s: log `GPU drain not finished...` i `_Exit`. Wtedy zachowanie jest jak przy SIGKILL, bez user-space'owego wyładowania kodu.
- `:98-108` i `:633`: po wyjściu z `start_loop()`, PRZED `clean_up()` i destruktorami, `server_quiesce_gpu()` woła `ggml_backend_quiesce` każdego backendu, ustawia `gpu_drained` i loguje `GPU drained before teardown (x ms)`.
- Router (`:521`) nie liczy nic na GPU, więc ma `gpu_drained` od startu. Windows: handler konsoli działa we własnym wątku i woła `on_shutdown_signal` bezpośrednio.

**ggml-hip:**
- `hip-pm4.cu:327-357` (`:334` flagi, `:355` `pm4_atexit`): `g_pm4_stopping` i licznik `g_pm4_inflight`.
  - `ggml_hip_pm4_launch` (`:1105-1110`) zwiększa licznik przed sprawdzeniem `stopping` i zmniejsza go dopiero po zobaczeniu sygnału ukończenia taśmy (RAII).
  - Para jest sekwencyjnie spójna: albo launch widzi `stopping` i oddaje `false`, a wywołujący puszcza HIP graph (te same kernele, bitowo te same wyniki), albo drenaż widzi taśmę w locie.
  - `ggml_hip_pm4_build` przy `stopping` nie buduje nowych taśm.
- `ggml_hip_pm4_shutdown(why, verbose)` (`:826-846`) wyłącza replay PM4 do końca procesu. Potem czeka z limitem 12 s (> 10 s limitu taśmy w launchu), aż licznik spadnie do 0, oraz na sygnał ukończenia ostatniej taśmy każdej kolejki (słowo samego GPU). Loguje `ggml_hip_pm4: teardown: tape replay off, last tape completed (waited x ms)`, a przekroczenie limitu też idzie do logu.
- `ggml_hip_pm4_drain()` (`:822`) to drenaż bez wyłączania replay. Woła go `ggml_hip_pm4_free` (`:812-820`) przed zwolnieniem IB i kernargów oraz `~ggml_backend_cuda_context` (`ggml-cuda.cu:702-713`), który dodatkowo synchronizuje swoje strumienie przed zwolnieniem grafów, taśm i buforów. Uśpienie serwera zwalnia kontekst, ale replay zostaje włączony.
- `hip-pm4.cu:639-643`: `atexit(pm4_atexit)` jest rejestrowany przy pierwszej kolejce taśm, czyli po konstruktorach modułów HIP. `exit()` z dowolnego miejsca najpierw wyłącza replay i czeka na taśmę, a dopiero potem destruktory HIP wyładowują kod. To obrona w głąb na każde inne `exit()` w procesie.
- `ggml-cuda.cu:7364-7378`: `ggml_backend_cuda_quiesce` (proc `ggml_backend_quiesce`) robi `ggml_hip_pm4_shutdown("teardown", true)` i `cudaDeviceSynchronize` na każdym urządzeniu (błąd tylko logowany).

**Generacja bez zmian, md5 greedy niezmienione z konstrukcji:**
- przed sygnałem jedyna różnica na ścieżce gorącej to `fetch_add`/`fetch_sub` i `load` atomika na launch taśmy (~ns) oraz `load` w `ggml_hip_pm4_free`;
- kernele, argumenty, kolejność i synchronizacja się nie zmieniają;
- `stopping` ustawia się dopiero po zakończeniu pętli (albo w `exit()`), a dokończenie bieżącego kroku przebiega jak dawniej.

Potwierdzenie na GPU: job `td-md5-*` w `td.jobs`.

## Plan reprodukcji i weryfikacji (`~/qwen-opt/teardown/td.jobs`; runda 1 wykonana 13:26–13:57, `td-old-3sig` nie uruchomiony)
`td.sh` ustawia jawnie PM4=1, WA=2, GUARD=1, HSA_USE_SVM=0, `LLAMA_SERVER_YIELD_FAST=2`, `GGML_HIP_PM4_MIN_DISPATCH=16` i `GGML_HIP_PM4_LAZY_EXEC=1`, kasuje `QUEUE_PM4_SAFETY` i używa produkcyjnej konfiguracji `run-topka.sh qwen`. Base to `~/wt/topka-int/build-hip`, to samo drzewo bez poprawki.
1. `td-md5-base`, `td-md5-fix`, `td-md5-cmp`: greedy T=0, 400 tokenów, porównanie `cmp`.
2. `td-fix-3sig`: 20 iteracji, w każdej:
   - świeży serwer;
   - generacja 4000 tokenów;
   - po losowych 1–4 s od startu generacji **3× SIGTERM co 5 ms** (wzór z 04:07 i 12:46);
   - do 60 s na wyjście (SIGKILL, jeśli trzeba, logowany);
   - linia wyniku z czasem wyjścia, rc i liniami drenażu;
   - `journalctl -k --since <start iteracji>`. **Pierwszy fault kończy job (exit 3) i zapisuje `FAULTS.txt`.**
3. `td-fix-1sig`: to samo z pojedynczym SIGTERM.
4. `td-old-3sig`, **ostatni**: base z 3× SIGTERM. Oczekiwany fault przy pierwszych iteracjach potwierdza, że reprodukcja trafia w błąd. Kończy się na pierwszym faulcie, a kolejka staje (reguła sprzętowa), dlatego nic po nim nie biegnie.

Kryterium: fix 40/40 bez faultu, w logu `received signal ... again` → `GPU drained ...`, rc 1 po drenażu; base faultuje. Jeśli base nie faultuje w 20 próbach, wynik fixu nie jest rozstrzygający: zwiększyć N albo dodać sygnały.

## Runda 2: jeden SIGTERM nie kończył procesu (td-fix-1sig)
Log każdej iteracji (`~/qwen-opt/teardown/logs/td-fix-1sig-*.server.log`):
- `received signal 15` o +9.949 s;
- `GPU drained before teardown (0.1 ms)` o +9.965 s, czyli pętla stanęła na granicy kroku po 16 ms;
- `cleaning up before exit...`, a potem cisza do SIGKILL po 60 s.

Pierwszy sygnał działał więc poprawnie: krok, drenaż i wyłączenie PM4 przeszły. Wątek drenażu niczego nie blokował. Zawieszenie było PO drenażu, w `ctx_http.join()` (`server.cpp`), które zamyka pulę wątków HTTP i czeka na handlery:
- handler `/v1/chat/completions` (bez streamu) czeka w `rd.wait_for_all(req.should_stop)` (`server-context.cpp:5108`), a ta funkcja odpytuje co 1 s `server_response_reader::next` (`server-queue.cpp:617-624`);
- `should_stop` było wyłącznie `req.is_connection_closed` (`server-http.cpp:685/736/757`);
- klient wciąż był podłączony, a zatrzymana pętla nie wyśle już wyniku, więc handler czekał w nieskończoność.

To samo jest w starym kodzie [INFERENCE: base z 1 sygnałem nie testowany]. Właśnie to w praktyce prowokowało drugi sygnał, a z nim `exit(1)` i fault.

Poprawka (`e52b38014`):
- **`server_http_context::stop()` ustawia flagę `stopping`**, a `should_stop` każdego żądania to teraz „połączenie zamknięte LUB serwer się zatrzymuje”:
  - `server_http_req::should_stop` jest wartością, nie referencją;
  - lambda `request_should_stop` w `server-http.cpp`;
  - `clean_up()` woła `ctx_http.stop()` przed `join()`, więc handler wraca przy najbliższym odpytaniu (≤ 1 s) i `join()` się kończy;
  - asercje `GGML_ASSERT(req.should_stop())` w ścieżkach streamu pozostają prawdziwe.
- **Watchdog pierwszego sygnału** (`server.cpp`, `on_shutdown_signal`) to siatka bezpieczeństwa:
  - 5 s po drenażu wywołuje `_Exit(1)` z logiem `teardown still running 5 s after the GPU drain...`;
  - bez drenażu w 30 s również `_Exit` z logiem;
  - GPU jest wtedy bezczynne i nie biegną destruktory modułów HIP;
  - wspólne `force_exit()` (jeden wywołujący, flush logu) obsługuje też kolejny sygnał.

Oczekiwane w `td2.jobs` (10× jeden SIGTERM, tylko poprawiona binarka): `received signal 15` → `GPU drained` → wyjście < 5 s, rc 0, bez SIGKILL, kernel log czysty.

Uwaga build: cel `llama-server` ma krok „Provisioning UI assets”, który sam próbuje pobrać web UI z HF (b11634: sha256 failed, potem „latest”). Ja tego nie uruchamiałem ręcznie. Na przyszłość warto budować bez pobierania UI.

## Otwarte
- SIGKILL w trakcie taśmy: jądro (KFD) zdejmuje kolejki przed zwolnieniem BO. [INFERENCE] to bezpieczne, ale nie było testowane osobno. Poprawka w user space SIGKILL-a nie dotyczy.
- `p100_arm.sh` `stop()` z `pkill` i `cancel.sh` dalej wysyłają wiele sygnałów. Z poprawką to nieszkodliwe, a starsze buildy (produkcja f9b84bcfa) do czasu wdrożenia trzeba zatrzymywać jednym SIGTERM, gdy są bezczynne (obecny `cancel.sh`).

## Do bazy wiedzy
- `lekcje/` „Nie zabijaj serwera PM4 w trakcie taśmy”: aktualizacja przyczyny. To nie SIGKILL, tylko drugi SIGTERM i `exit(1)` z handlera; poprawka w `pm4-teardown` (zrobione).
- `lekcje/` „Nigdy `exit()` z handlera sygnału w procesie z GPU”: `exit` uruchamia `atexit`, w tym destruktory modułów HIP (wyładowanie kodu), podczas gdy inny wątek ma pracę na GPU. W handlerze tylko zapis do pipe'a, a wymuszone wyjście dopiero po drenażu i przez `_Exit`.
- `kernele/pm4-replay`: taśma nie posiada code objectów (`code_entry` z modułów HIP), więc jej życie musi się skończyć przed wyładowaniem modułów. Drenaż: `ggml_hip_pm4_shutdown` / `ggml_backend_quiesce`.
- `eksperymenty/` 2026-10-21 „55 teardown PM4”: gałąź `pm4-teardown`, `~/qwen-opt/teardown/` (`td.sh`, `td.jobs`, `inst/`).

## Dopisek 2026-10-21 (rodzic): cancel.sh nie dokłada drugiego SIGTERM
Nowy `cancel.sh` z 12:50 sam wysyłał SIGTERM do serwera po zatrzymaniu klientów — a trap EXIT skryptu ramienia
wysyła już jeden, więc dokładał dokładnie ten drugi sygnał, który odpala `exit()` w handlerze. Poprawka: cancel.sh
nigdy nie wysyła serwerowi TERM; zatrzymuje klientów/wrappery (ich trapy wysyłają jeden SIGTERM), czeka do 90 s,
a jeśli serwer żyje — SIGKILL (handler nie działa, `exit()` się nie wykonuje). Smoke na sztucznym drzewie procesów
(fake `bin/llama-server` liczący sygnały): serwer dostał **1** SIGTERM, zero osieroconych procesów.
`sr_arm.sh`: stop() czeka na bezczynne sloty, potem jeden SIGTERM i do 45 s.

## Runda 2 — wynik GPU (td2.jobs)
1× SIGTERM w trakcie generacji, poprawiona binarka (`e52b38014`): **10/10 czysto**. Wyjście po ~1.3 s, rc 0, bez SIGKILL, kernel log czysty. Do mergu do `topka-int` idzie `pm4-teardown` HEAD `e52b38014` (MorningRun).
