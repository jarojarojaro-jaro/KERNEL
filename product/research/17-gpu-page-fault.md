# 17. Page faulty GPU i resety RX 7900 XTX (16–19.10): analiza bez GPU

Data: 2026-10-19. Autor: podagent Pm4FaultAnalysis. Analiza wyłącznie na CPU: `journalctl -k`, logi agentów, transkrypty sesji agentów, kod `hip-pm4.cu`. Na GPU nic nie uruchamiałem.
Kod: worktree `~/wt/pm4fault`, gałąź `pm4-guard` z `amd-opt` @ `f61994f58`, commit **`7cd12f993`** (prototyp strażnika, domyślnie wyłączony, tylko kompilacja: `hip-pm4.cu.o`, `ggml-cuda.cu.o` i `llama-server` w `~/wt/pm4fault/build-hip`).

## 0. Najważniejsze

- **10 resetów GPU w 3 bootach.** 2 to jawne eksperymenty: mikrobench `pdl` z czekaniem na flagę w IB PM4 i `GGML_HIP_PM4_UB`, czyli granice bez synchronizacji. Pozostałe **8 to ta sama awaria w produkcyjnej ścieżce replayu PM4**. Dotyczy `llama-server` z Qwen3.8-27B + MTP: 7× build `coupled` (tryby 0, 1 i 2), 1× build `lookup` (16.10).
- **Podpis tych 8 awarii jest identyczny.**
  - Odczyt `SQC (data)` z **strony 0** (`STATUS 0x00801431`: PERMISSION_FAULTS=3, RW=0, CID=0x0a), w trybie użytkownika. SQ zgłasza `type 2` = MEMVIOL, `priv 0`.
  - Faultuje wiele fal naraz: 10 wypisanych, do 1270 wyciszonych.
  - Wpisy `CB/DB (0x0)` mają STATUS 0. To artefakt: rejestr statusu złapał już pierwszy fault. To nie jest osobny klient.
  - Po **~110–130 ms** pojawia się „MES failed to response msg=3” (REMOVE_QUEUE), potem mode1 reset.
  - **Kolejność jest odwrotna niż w logach serwera.** Najpierw jest fault i reset (0.57–3.20 s po starcie requestu). Komunikat `tape of 823 dispatches did not complete within 10 s` przychodzi dopiero ~10 s później, bo po resecie taśma już nigdy się nie skończy. Timeout jest skutkiem awarii, a nie przyczyną.
- **Co znaczy podpis.** Fala czyta skalarnie z adresu 0..4095 już przy pierwszym dostępie. To wygląda na start dispatchu ze **wskaźnikiem kernargów = 0** w SGPR. Ten wskaźnik pochodzi z `COMPUTE_USER_DATA`/`PGM_RSRC2` ustawianych przez taśmę tuż przed każdym `DISPATCH_DIRECT`.
  - Taśma jest budowana raz i odtwarzana dziesiątki tysięcy razy poprawnie. Sama treść taśmy takiego zera nie daje: `kaddr` i `code_entry` są niezerowe; w prototypie dodałem asercję.
  - Nieaktualny wskaźnik dałby fault pod realnym adresem, nie pod 0. Uderzyłby też tak samo w zwykły `hipGraphLaunch`.
- **Hipoteza nr 1** `[INFERENCE]`, szczegóły w §4.
  - Mechanizm: KFD wywłaszcza kolejkę taśmy w środku IB (eviction kolejek procesu z powodu SVM, userptr albo TTM). Po wznowieniu CP nie ma stanu rejestrów SH, który IB ustawił przed punktem wywłaszczenia. Kolejny dispatch (albo dokończenie przerwanego) startuje z zerowym USER_DATA. To daje SQC fault @0. KFD na VM fault znowu ewikuje kolejki, MES nie umie zdjąć kolejki ze zhalt'owanymi falami w środku IB i robi reset.
  - Za tym przemawia: losowe momenty, tylko taśmy, start dopiero po zapełnieniu cache promptu (≥33 requesty, 16 GiB RAM hosta). W `journalctl` widać workery przywracania kolejek KFD (`restore_userptr_worker` 64×, `svm_range_restore_work` kończący się 156 ms po faulcie z 23:25).
- **PM4 wzmacnia każdą awarię.** Fault w taśmie kończył się resetem w 9 z 10 przypadków. Ten sam typ faultu w zwykłych kolejkach AQL (`moebench` ×3) zabijał tylko proces, bez resetu. Kolejka z IB PM4 i zhalt'owanymi falami jest dla MES niezdejmowalna.
- **Produkcja jest zagrożona.** `~/llama-opt` (build 15.10) ma PM4 domyślnie włączone, ten sam kod i te same flagi `run-llm.sh` (`--cache-ram 16384`, ctx 204800, MTP). W E-X4 wyszło ~1 reset na ~330 requestów (7/2338 w 27 sesjach). Żadnego, zanim cache promptu doszedł do limitu 16 GiB (sweep: request 33, ident: 49); potem ~1/200. Reset GPU zabija też serwer użytkownika (VRAM lost) i zeruje krzywą wentylatora, jak 18.10 o 23:25.
- **Rekomendacja (decyzja Main/użytkownika):**
  1. Teraz `GGML_HIP_PM4=0` w `run-llm.sh` i w blokach agentów, które nie testują PM4. Koszt wg wiki: Qwen MTP 108.8 → 103.7 t/s (−4.7%), LFM 293.6 → 259.3 t/s (−12%).
  2. Potem strzeżony test z §6 na buildzie `7cd12f993` (`GGML_HIP_PM4_GUARD=2`).
  3. Nie wysyłać PM4 do użytkowników produktu, dopóki test nie da 0 faultów na ≥1000 requestów długiej sesji.

## 1. Tabela incydentów

Źródło: `journalctl -k -b -2/-1/0` (boot -2 = 16.10, -1 = 18.10 do 20:26, 0 = od 20:27). Czasy UTC. „+x s” to czas od `launch_slot_` ostatniego requestu (mtime `.server.log` = czas ostatniej linii) do pierwszego faultu.

| # | boot | czas | proces (pid) | VMID | klient / adres | STATUS | co robił proces | klasa |
|---|---|---|---|---|---|---|---|---|
| R1 | -2 | 16.10 15:30:52.78 | `pdl` (brak page faultu, pasid 0x8002) | – | – | – | XtxPm4Pdl X1 `bench1`, wariant **R0 „EOP flag, prefetch, wait”**: własny IB PM4 z czekaniem na flagę. „PM4 IB timeout (signal 1) -- stopping” (`~/qwen-opt/pm4pdl/x1/bench1.log`, 15:30:58). Wyjście procesu → REMOVE_QUEUE (msg 3) i MISC (msg 14) bez odpowiedzi → reset | **eksperyment** (zawieszony IB) |
| R2 | -2 | 16.10 15:35:06.09 | `llama-server` 338733 | 9 | SQC(data) @0 ×10 (+84 wyciszonych) | 0x00901431 | XtxLookupTail greedy `LLAMA_SPEC_LOOKUP=2` MTP, build `~/wt/lookup` (`f61994f58` + lookup), PM4 on; `lk2.mtp.txt` ucięty na 1669 B. **Równolegle** od 15:30:43 `validate.sh` BitExactSpec bez blokady GPU (serwer na 8097; naprawione 15:44). Najpierw MES msg 2 (ADD_QUEUE), potem 3 | ścieżka produkcyjna PM4 + inny proces na GPU |
| R3 | -1 | 18.10 19:47:46.77 | `llama-server` 35402 | 8 | SQC @0 ×4 + CB/DB(st.0) ×6 | 0x00801431 | CoupledSampling run1 `s1-m0` (**tryb 0**), request 36/37, T=0.7, +1.03 s | **produkcyjna** |
| R4 | -1 | 19:56:02.91 | `llama-server` 38863 | 8 | SQC @0 ×10 (+11) | 0x00801431 | run1 `s3-m2` (tryb 2), request 33, **bez eksmisji cache**, +0.61 s | **produkcyjna** |
| R5 | -1 | 19:56:24.44 | `llama-bench` 39986 | 8 | TCP @0x70d9cf64e000… ×10 (+138) | 0x00801031 | XtxPm4Pdl X2 `ab2.log`: `GGML_HIP_PM4_UB=conv,down,mmvq1,router,norm` (granice bez synchronizacji: z definicji złe wyniki; ten zestaw wisi, `x2/comb.err`), LFM tg128 | **eksperyment** (PM4_UB) |
| R6 | -1 | 20:14:17.17 | `llama-server` 47637 | 8 | SQC @0 ×3 + CB/DB ×7 | 0x00801431 | run2 `id-m1-a1` (tryb 1, `ident.py`), request 50, +0.57 s | **produkcyjna** |
| R7 | 0 | 22:42:35.90 | `llama-server` 89774 | 8 | SQC @0 ×4 + CB/DB ×6 | 0x00801431 | `b1-m0-a1` (**tryb 0**), request 74/241, T=1.0, +3.20 s | **produkcyjna** |
| R8 | 0 | 22:57:53.20 | `llama-server` 91923 | 8 | SQC @0 ×1 + CB/DB ×5 (+30) | 0x00801431 | `b1-m0-a2` (tryb 0), request 53, T=1.0, +2.97 s | **produkcyjna** |
| R9 | 0 | 23:25:12.47 | `llama-server` 94275 | 8 | SQC @0 ×10 (+74) | 0x00801431/…30 | `b2-m1-a1` (**tryb 1**, nie 0), request 77, T=1.0, +2.46 s. `svm_range_restore_work` kończy się 23:25:12.631 | **produkcyjna** |
| R10 | 0 | 19.10 00:16:22.41 | `llama-server` 103916 | 8 | SQC @0 ×1 + CB/DB ×4 (+139) | 0x00801431 | `c1-m0-a1` (tryb 0), request 158, T=0.7, +0.69 s | **produkcyjna** |

Page faulty bez resetu (dla pełności):

| czas | proces | klient | co | klasa |
|---|---|---|---|---|
| 16.10 15:31:39 | `moebench` 153101 (VMID 9) | TCP @0x7780f3c26000… | XtxLfmMoe `moebench` (agent poprawił OOB o 15:36 „Fixing OOB”), 14 s po starcie i 47 s po R1 | eksperyment |
| 16.10 15:35:41 | `moebench` 375089 | TCP | ten sam mikrobench | eksperyment |
| 16.10 15:45:12 | `moebench` 378259 (VMID 8) | TCP | ten sam mikrobench | eksperyment |
| 18.10 20:10:24 | `llama-bench` 47244 | TCP @0x74ce38ff3000… | XtxPm4Pdl `comb.err`: ten sam zestaw `PM4_UB`, „tape of 389 dispatches did not complete” | eksperyment |

Starsze: boot -5 (14.10 20:58) `pm4` CPF fault. To był pierwszy prototyp z IB w niewykonywalnej pamięci, już naprawione. Boot -11 (15.09) `python` + reset, poza tym projektem.

Poprawki do wcześniejszych opisów:
- **R9 to tryb 1, nie 0.**
- **R9 nie zbiegł się z kolizją blokad.** Pliki `/tmp/*.lock` mają mtime 23:26 (lista XtxQuickWins z 23:38). Blok `pin1-lfm` czekał od 23:18:32 i ruszył dopiero o 23:25:26 z `vram_used_before 26 MiB`, czyli po resecie.
- **„Serwer użytkownika na 8080” w run1/run2 to najpewniej fałszywy alarm.** `pgrep -f "llama-server.*--port 8080"` łapie powłoki innych agentów, które mają ten wzorzec w swojej linii poleceń. MagnitudeVulkanXtx zmienił to o 20:10 na `pgrep -x`. Od 15.10 w `~/qwen-opt/logs/` nie ma żadnego logu serwera produkcyjnego.
- Bez innego procesu na GPU było 7 awarii coupled. Inny proces na GPU był tylko przy R2.

## 2. Co mówią rejestry

- `GCVM_L2_PROTECTION_FAULT_STATUS` (gfx11):
  - bit 0 MORE_FAULTS;
  - bity 4–7 PERMISSION_FAULTS (3 = brak PTE / niedozwolony);
  - bit 8 MAPPING_ERROR;
  - bity 9–15 CID;
  - bit 16 RW;
  - bity 20–23 VMID.
- Przykłady: 0x00801431 = SQC data, odczyt, VMID 8; 0x00901431 = to samo w VMID 9; 0x00801031 = TCP (wektorowe ładowanie).
- `sq_intr: error … type 2` = `SQ_INTERRUPT_ERROR_TYPE_MEMVIOL`. `priv` = czy fala była w trap handlerze (`kfd_int_process_v11.c`). Dla `llama-server` zawsze `priv 0`, dla `moebench` `priv 1`.
- Na VM fault KFD wywołuje `kfd_set_dbg_ev_from_interrupt(EC_DEVICE_MEMORY_VIOLATION)`. Bez debuggera to eviction kolejek procesu i zdarzenie dla procesu.
  - Stąd zawsze ~110–130 ms od faultu do „MES failed to response msg=3”. 3 to `MES_SCH_API_REMOVE_QUEUE`; MES timeout ≈ 128 ms, kolejne próby co 128 ms.
  - msg 2 = ADD_QUEUE (R2), msg 14 = MISC (R1).
- Czasy względem logów serwera: fault +0.57…+3.20 s po `launch_slot_`, abort „10 s” 10.0 s później, `Aborted (core dumped)` po kolejnych ~3 s (`.out` mtime). We wszystkich 7 awariach coupled fault poprzedza timeout taśmy.

## 3. Cykl życia taśmy (`hip-pm4.cu` + `ggml-cuda.cu`), co może być nieaktualne

- **Budowa:** `ggml_cuda_graph_evaluate_and_capture` przy `cuda_graph_update_required`, czyli po warmupie (2 wywołania bez zmian) i potem po każdej zmianie właściwości węzła.
  - Kolejność: `cudaGraphExecUpdate`, potem `ggml_hip_pm4_free(old)` + `ggml_hip_pm4_build`.
  - Zawartość taśmy: deskryptory kerneli z loadera ROCr; kernargi skopiowane z `hipKernelNodeParams` przechwyconego grafu, ukryte argumenty wyliczone; kernargi w VRAM (`hipMalloc`), IB w wykonywalnej pamięci hosta (pula HSA).
- **Unieważnienie** (`ggml_cuda_graph_update_required`):
  - porównanie całej struktury `ggml_tensor` każdego węzła (wskaźnik `data`, ne/nb, op_params) oraz `data`/ne/nb źródeł;
  - szybka ścieżka `cgraph->uid == graph->uid` pomija porównanie. uid nadaje `ggml_backend_sched_split_graph` przy każdym nowym grafie. Ten sam uid ma tylko graf ponownie użyty przez llama (`can_reuse`), a wtedy alokacje są te same;
  - `sched_reserve()` (np. `set_sampler` przy zmianie samplera, zmiana T) zeruje `gf_res_prev` i tworzy nowy sched, więc kolejny graf ma nowy uid i przechodzi porównanie;
  - obiekt grafu jest kluczowany `nodes[0]` i usuwany po 10 s nieużywania (destruktor zwalnia taśmę).
- **Realokacje:**
  - wzrost KV (n_kv co 256) zmienia ne widoków, więc jest przebudowa;
  - przebudowa compute buffer po reserve zmienia `data`, więc jest przebudowa;
  - restore stanu z `--cache-ram` / checkpointów pisze w istniejące bufory (bez zmiany adresów);
  - `--cache-ram` to tylko RAM hosta;
  - MTP verify i grafy 1-tokenowe to osobne cgraph/klucze (kolizja klucza jest łapana porównaniem);
  - bufory tymczasowe z `ggml_cuda_pool_leg` nie są zwalniane przez życie kontekstu;
  - `h2d_batch` jest wysyłany przed capture na tym samym strumieniu.
- **Czy taśma może trzymać nieaktualny wskaźnik?** Nie znalazłem takiej ścieżki. Gdyby była, `hipGraphLaunch` (te same wskaźniki) też by padał, i to pod realnym adresem (TCP/SQC ≠ 0), nie pod 0.
- **Czy może trzymać NULL kernarg/deskryptor?** Nie z treści taśmy: kernargi to kopia parametrów węzła, a `kaddr`/`code_entry` są niezerowe. Asercja jest teraz w buildzie `7cd12f993`.
- **Timeout 10 s:**
  - start po `cudaStreamSynchronize`, aktywne czekanie na sygnał (`HSA_WAIT_STATE_ACTIVE`, 100% jednego rdzenia), potem `GGML_ABORT`;
  - po resecie GPU sygnał nigdy nie spada, stąd zawsze „did not complete”;
  - przy zawieszonym (nie faultującym) IB, jak R1, dopiero wyjście procesu wymusza REMOVE_QUEUE i reset. Łagodniejsze zakończenie niczego by nie dało, bo kolejki ze spinującymi falami MES i tak nie zdejmie.
- **Historia:** `hip-pm4.cu` ma 3 commity w `amd-opt` (`1153adb69`, `e5ca00ec4`, `2cbcf771a`, 14.10), bez poprawek błędów. Wiki: soak 4 min/model bez zawieszeń; jedyny wcześniejszy fault (CPF, 14.10) był z IB w pamięci niewykonywalnej.

## 4. Hipotezy (ranking)

1. **H1: wywłaszczenie kolejki PM4 w środku IB gubi stan SH** (~60%) `[INFERENCE]`.
   - **Mechanizm.** KFD ewikuje wszystkie kolejki procesu przy:
     - inwalidacji userptr/SVM (MMU notifier: munmap, migracja, kompakcja, swap pamięci zarejestrowanej przez ROCr/ROCclr przy kopiach z pamięci stronicowanej);
     - evictcie TTM;
     - suspendzie.

     Z CWSR wywłaszcza w środku dispatchu. Dla pakietu AQL CP odtwarza stan z pakietu. Dla `DISPATCH_DIRECT` w IB zależy to od rejestrów SH ustawionych wcześniej w IB. Bez shadowingu rejestrów (dla gfx/MCBP wymaga go Mesa) mogą wrócić z MQD jako 0, a wtedy wskaźnik kernargów = 0 i SQC @0 w trybie user.
   - **Za:**
     - (a) podpis pasuje dokładnie;
     - (b) awaria jest tylko w taśmach;
     - (c) momenty losowe: te same seedy dały awarię w requeście 74, 53 i 0/241 (`b1-m0-a1/a2/a3`);
     - (d) w 27 sesjach (2338 requestów) 0 awarii w 901 slotach przed dojściem cache promptu do limitu 16 GiB (sweep: requesty 2–32, ident: 2–48) i 7 w 1410 slotach później (p≈0.07). Same bloki 37-requestowe: 2 awarie w 65 slotach ≥33 vs 0 w 434 (p≈0.02). Wtedy rośnie też presja na RAM hosta (62 GB, 17 GB modelu w page cache);
     - (e) w bootach z awariami KFD na pewno robił eviction/restore kolejek: `amdgpu_amdkfd_restore_userptr_worker hogged CPU … 64 times` (boot 0), `svm_range_restore_work … 32 times` kończący się 23:25:12.631, czyli 156 ms po faulcie R9;
     - (f) R2 miał drugi proces na GPU (eviction TTM/MES).
   - **Przeciw / niewiadome:** brak bezpośredniego dowodu z firmware; nie wiemy, jak często eviction trafia w taśmę bez skutków.
2. **H2: trwałe uszkodzenie kernargów w VRAM przez obcy zapis** (~20%).
   - Taśma trzyma kernargi przez tysiące replayów. Graf HIP pisze je co launch, więc jednorazowy zapis OOB innego kernela w ich alokację zostałby tam „zapamiętany”.
   - Pasuje, jeśli pierwszy dostęp kernela to skalarny odczyt przez wyzerowany wskaźnik. Słabiej tłumaczy losowość i same strony 0.
   - Sprawdza to `GUARD=2` (porównanie i naprawa przed każdym replayem).
3. **H3: uszkodzenie IB w pamięci hosta** (~10%). Zerowy dword `USER_DATA` dałby dokładnie ten podpis. IB leży jednak w osobnym mapowaniu KFD, a nie na stercie. Sprawdza to `GUARD≥1` (memcmp i naprawa).
4. **H4: inne** (~10%), np. błąd MES/CP niezależny od wywłaszczenia.
   - Termika (pamięć 90 °C przed poprawką wentylatora) dałaby losowe bity, nie zera na całym wskaźniku.
   - Sampler/temperatura: awarie przy T=1.0 i 0.7, w trybach 0/1/2.
   - Kod coupled: tryb 0 też pada; R2 to inny build.

## 5. Poprawka i strażnik

**Minimalna poprawka bezpieczeństwa (bez kodu):** `GGML_HIP_PM4=0` dla serwerów (produkcja, bloki agentów), dopóki §6 nie wykaże bezpieczeństwa. Wyniki są bitowo te same (te same kernele), koszt wyłącznie w prędkości (§0).

**Prototyp `7cd12f993` (`~/wt/pm4fault`, `pm4-guard`), `GGML_HIP_PM4_GUARD`, domyślnie 0 = zachowanie bez zmian.** Kernele i argumenty się nie zmieniają, wyniki są bitowe.

- **`GUARD=1`:**
  - przed każdym replayem `memcmp` IB z kopią referencyjną; przy różnicy log (dword, dispatch, kernel) i naprawa;
  - obserwacja zdarzeń KFD SMI własnego procesu (`AMDKFD_IOC_SMI_EVENTS` na własnym `/dev/kfd`, dostępne bez roota): `QUEUE_EVICTION` z przyczyną (SVM/userptr/TTM/suspend), `QUEUE_RESTORE`, `VMFAULT`, `GPU_PRE_RESET`;
  - po każdym eviction/restore przez `GGML_HIP_PM4_GUARD_COOLDOWN_MS` (domyślnie 3000) `ggml_hip_pm4_launch` zwraca `false`. Wtedy `ggml-cuda.cu` odpala zwykły `cudaGraphLaunch` (instancja grafu jest zawsze aktualna; AQL jest bezpieczny przy wywłaszczeniu);
  - każdy eviction, który trafił w trwającą taśmę, jest logowany („during a tape”);
  - co 60 s podsumowanie liczników.
- **`GUARD=2` (diagnostyka):**
  - dodatkowo odczyt kernargów z VRAM (D2H do pamięci pinned) i porównanie przed każdym replayem, naprawa z logiem;
  - znacznik czasu GPU po każdym dispatchu (ten sam, sprawdzony pakiet `COPY_DATA` co `PM4_DEBUG=3`), do bufora hosta per taśma. Przy timeoucie log mówi, na którym dispatchu taśma stanęła (nazwa kernela, grid, numer launchu), plus zaległe zdarzenia KFD;
  - logowane są też wszystkie evictiony między taśmami.
- **Koszt `GUARD=1`:** ~2 odczyty fd + memcmp ~150 KB na taśmę, ~10–20 µs na ~28 ms kroku (<0.1%) `[SZACUNEK]`, plus kroki w trybie grafu w czasie cool-down. `GUARD=2` dodaje D2H ~100–150 KB i sync na taśmę (tylko do testu).
- **Czego strażnik nie robi.** Nie czyni taśmy odporną na wywłaszczenie, tylko omija okresy aktywnych evictionów (heurystyka: zakłada ich skupianie) i daje twarde dane do rozstrzygnięcia H1/H2/H3. Prawdziwa odporność wymagałaby wsparcia CP (shadowing rejestrów SH dla PM4 w kolejce AQL), poza naszym zasięgiem.
- **Uzupełniająco (do rozważenia po §6):** mniej źródeł evictionów w serwerze.
  - Stały, pinned bufor pośredni dla zapisu i odczytu stanu `--cache-ram` zamiast kopii 0.3–0.5 GiB z/do `std::vector` (tak robił odrzucony `LLAMA_STATE_PINNED` z 16f).
  - Arena dla wpisów cache promptu bez munmap przy każdej eksmisji.
- Weryfikacja: kompilacja `hip-pm4.cu.o` i `ggml-cuda.cu.o` bez ostrzeżeń; `llama-server` w `~/wt/pm4fault/build-hip/bin` (§6). Na GPU niczego nie uruchamiałem.

## 6. Bezpieczny plan testu GPU (NIE wykonany, wymaga zgody użytkownika)

Warunki wspólne:
- nikt inny na GPU, sprawdzone przez `lslocks` / `/proc/*/cmdline` z `pgrep -x llama-server`, nie przez `pgrep -f`;
- serwer 8080 zatrzymany;
- krzywa wentylatora sprawdzona (`gpu_od/fan_ctrl/fan_curve`);
- `~/qwen-opt/tools/gpu-guard.sh` uruchomiony przed blokiem. Zatrzyma wszystko przy pierwszym faultcie, ale nie zapobiegnie resetowi, bo ten przychodzi po ~120 ms;
- jeden blok naraz pod `flock /tmp/gpu.lock flock /tmp/quiet.lock`;
- stop po pierwszym faultcie, bez powtórek.

1. **T0, kontrola bez PM4 (ryzyko niskie).**
   - Konfiguracja: build `7cd12f993` zainstalowany (`cmake --install ~/wt/pm4fault/build-hip --prefix ~/wt/pm4fault/inst`). Blok przez `~/qwen-opt/coupled/frozen/arm.sh <label> 0 sweep` z `SEEDS=$(seq -s, 4 23)` i `EXTRA_ENV="ROCM_DIR=$HOME/wt/pm4fault/inst GGML_HIP_PM4=0"`; późniejsze przypisanie `env` nadpisuje `ROCM_DIR` z `arm.sh`. Flagi to `run-llm.sh qwen mtp rocm`, 241 requestów, ~25 min.
   - Oczekiwane: 0 faultów. Faulty w AQL dotąd nie dawały resetu (3/3).
   - Jeśli fault: przyczyna nie jest w PM4 → analiza kernela (journal + `HIP_LAUNCH_BLOCKING`), PM4 zostaje wyłączone.
2. **T1, diagnostyka z PM4 i strażnikiem (ryzyko średnie: w E-X4 ~1 reset / 330 requestów, z cool-down powinno być mniej).**
   - Konfiguracja: jak T0, ale `EXTRA_ENV="ROCM_DIR=$HOME/wt/pm4fault/inst GGML_HIP_PM4_GUARD=2"` (PM4 włączone, cool-down domyślnie 3000 ms), ten sam blok 241 requestów. Przed testem zamienić `busy()` w `arm.sh` na `pgrep -x`.
   - Oczekiwane:
     - logi `guard: KFD queue eviction <trigger> between tapes` (oczekuję userptr/SVM po zapełnieniu cache, ≥request ~33);
     - podsumowania co 60 s;
     - **0 linii „IB … repaired” / „kernarg … repaired”** (inaczej H3/H2 potwierdzone, z nazwą dispatchu);
     - liczba „eviction during a tape”.
   - Jeśli fault mimo to: log nazwie dispatch i zdarzenie KFD tuż przed. Losowy kernel + eviction przed nim = H1 potwierdzone; ten sam kernel = błąd kernela/kernargów.
3. **T2, tylko jeśli T1 czyste (ta sama konfiguracja):** soak ≥1000 requestów (4 bloki po 241 + `pm4_soak.py`).
   - Kryterium dopuszczenia PM4 z `GUARD=1` do produkcji: 0 faultów oraz udział kroków w trybie grafu (cool-down) < 10% (koszt < 0.5% t/s).
   - Jeśli eviction „during a tape” występuje, a faultu nie ma, H1 dotyczy tylko wąskiego okna. Wtedy zostaje `GUARD=1`.
   - Jeśli którykolwiek fault: PM4 zostaje wyłączone w serwerach na stałe, a zostaje tylko w `llama-bench` do pomiarów.
4. **Opcjonalnie, celowa reprodukcja H1 (wysokie ryzyko, tylko za osobną zgodą):** mikrobench z taśmą ~800 dispatchy w pętli i drugim wątkiem, który co ~10 ms wymusza inwalidację userptr własnego procesu (`hipHostRegister` + `madvise(MADV_DONTNEED)` na tym zakresie).
   - Kontrola tego samego z `GGML_HIP_PM4=0`: oczekiwane 0 faultów.
   - Wariant PM4: H1 przewiduje szybki SQC fault @0 i reset. Daje to dowód, ale kosztuje reset.

## 7. Czy użytkownicy produkcji są zagrożeni

- **Tak.** Serwer `~/llama-opt` ma tę samą ścieżkę PM4 domyślnie włączoną i te same flagi.
- Ryzyko rośnie z:
  - długością sesji (cache promptu zapełnia 16 GiB, w E-X4 dopiero od ~33 requestów);
  - presją na RAM hosta;
  - drugim procesem GPU (R2).
- Skutek: reset całego GPU (VRAM lost, serwer pada, zerowana krzywa wentylatora). To nie tylko błąd procesu.
- PM4 zamienia każdy fault taśmy w reset (9/10), więc także przyszłe błędy eksperymentalnych kerneli puszczanych przez PM4 są groźniejsze niż w zwykłym grafie.
- Do produktu (aplikacja użytkownika) PM4 nie może trafić domyślnie włączone bez kryterium z §6 T2.

## 8. Do bazy wiedzy

| folder | tytuł | treść (liczby ze źródłami) |
|---|---|---|
| `eksperymenty/` | `2026-10-19-page-faulty-gpu-analiza.md` | 10 resetów (16–19.10): 2 eksperymenty (`pdl` R0 15:30:52, `GGML_HIP_PM4_UB` 19:56:24), 8× `llama-server` Qwen MTP z taśmą PM4 823 dispatchy: SQC(data) @0, STATUS 0x00801431/0x00901431, `sq_intr type 2` (MEMVIOL) `priv 0`, ~120 ms później MES msg 3 i mode1 reset; fault 0.57–3.20 s po starcie requestu, timeout taśmy 10 s później (`journalctl -k -b -2/-1/0`, `~/qwen-opt/coupled/logs*/`). E-X4: 7 resetów na 2338 requestów, 0 w 901 slotach przed zapełnieniem cache promptu (16 GiB), 7 w 1410 później. |
| `lekcje/` | `lekcja-pm4-zamienia-fault-w-reset.md` | Fault w taśmie PM4 kończył się resetem GPU 9/10 razy (MES nie zdejmuje kolejki z IB i zhalt'owanymi falami), fault w zwykłej kolejce AQL (`moebench` ×3, 16.10) tylko zabijał proces. Eksperymentalne kernele testować z `GGML_HIP_PM4=0`. |
| `lekcje/` | `lekcja-timeout-tasmy-to-skutek.md` | „tape … did not complete within 10 s” przychodzi ~10 s po faultcie i resecie (mtime `.server.log` vs `journalctl`); przyczyny szukać w `journalctl -k` z dokładnym czasem, nie w ostatniej linii serwera. |
| `lekcje/` | `lekcja-pgrep-f-lapie-powloki.md` | `pgrep -f "llama-server.*--port 8080"` trafia w powłoki innych agentów z tym wzorcem; fałszywe „8080 busy” zmyliło diagnozę E-X4 (18.10 19:47–20:14). Używać `pgrep -x llama-server` + `/proc/<pid>/cmdline` (MagnitudeVulkanXtx, 20:10). |
| `rocm/` | `dekodowanie-page-fault-amdgpu.md` | Pola `GCVM_L2_PROTECTION_FAULT_STATUS` gfx11 (CID bity 9–15: 0x0a SQC data, 0x08 TCP, 0x04 CPF; VMID 20–23; RW 16); wpisy `CB/DB (0x0)` ze STATUS 0 = artefakt; `sq_intr type` 0 EDC_FUE, 1 ILLEGAL_INST, 2 MEMVIOL, 3 EDC_FED, `priv` = w trap handlerze; VM fault → KFD eviction kolejek; MES msg 2 ADD_QUEUE, 3 REMOVE_QUEUE, 14 MISC, timeout ~128 ms. |
| `rocm/` | `kfd-smi-eventy.md` | `AMDKFD_IOC_SMI_EVENTS` na własnym `/dev/kfd` (bez roota, tylko zdarzenia własnego procesu + globalne VM fault/reset): `QUEUE_EVICTION` z przyczyną (SVM, userptr, TTM, suspend), `QUEUE_RESTORE`; maska `KFD_SMI_EVENT_MASK_FROM_INDEX`, linie tekstowe `"%x %lld -%d %x %d"`. Użyte w `GGML_HIP_PM4_GUARD` (`7cd12f993`). |
| `rocm/` | aktualizacja `pm4-replay.md` | Sekcja „Awarie”: przyczyna najpewniej wywłaszczenie kolejki w środku IB (H1, `[INFERENCE]`), alternatywy H2/H3; strażnik `GGML_HIP_PM4_GUARD=1/2` (gałąź `pm4-guard` @ `7cd12f993`, domyślnie off); rekomendacja `GGML_HIP_PM4=0` w serwerach do czasu testu §6. |
| `decyzje/` | `2026-10-19-pm4-w-serwerach.md` | Propozycja: `GGML_HIP_PM4=0` w `run-llm.sh` i blokach agentów (koszt Qwen −4.7%, LFM −12%), powrót tylko po T1+T2 z §6 (0 faultów na ≥1000 requestów, cool-down < 10% kroków). Do akceptacji użytkownika. |
| `lekcje/` | poprawka `lekcja-nie-odtwarzac-lockow.md` | Reset 23:25 (R9) nie wynikał z kolizji blokad: pliki `/tmp/*.lock` odtworzone ~23:26, blok `pin1-lfm` ruszył 23:25:26 przy `vram_used_before 26 MiB`. R9 to ta sama awaria PM4 co pozostałe. |
| `research/` | `raport-17-gpu-page-fault.md` (hub) | Link do raportu; status: przyczyna nieudowodniona (H1 najbardziej prawdopodobna), strażnik gotowy do strzeżonego testu, produkcja zagrożona. |

## 9. Analiza szczegółowa (19.10, faza 1: tylko CPU)

Autor: podagent Pm4Fix. Metoda: kod `hip-pm4.cu`, źródła Linux v6.8 (amdgpu/amdkfd), ROCr/libhsakmt/CLR (ROCm 7.0.0 i `rocm-systems` develop, z którego budowany jest TheRock), kfdtest, tinygrad, Mesa/PAL, `journalctl -k`, `/proc/vmstat`, logi serwera z E-X4. **Na GPU nic nie uruchamiałem** (decyzja użytkownika: najpierw analiza). Kod tylko jako prototypy skompilowane bez uruchomienia: commit **`b7fb3fe85`** na `pm4-guard` (`~/wt/pm4fault`), domyślne zachowanie bez zmian.

System: jądro Ubuntu `6.8.0-138-generic`, amdgpu z drzewa jądra (bez DKMS), MES fw `0x80`, MES KIQ `0x104`, `cwsr_enable=1`, `queue_preemption_timeout_ms=9000`; ROCm `core-10.0` (HIP 7.15, libhsa-runtime64 1.21) w `/opt/rocm`.

### 9.0 Najważniejsze

- **Nowy, konkretny kandydat na przyczynę (H1′) = H1 + brakujący obowiązkowy bit.**
  1. **Defekt w taśmie.** Każdy `DISPATCH_DIRECT` taśmy startuje fale z `COMPUTE_PGM_RSRC1.PRIV=0`, bo RSRC1 kopiujemy z deskryptora kernela. AMD wymaga na GFX11 `PRIV=1` przy każdym dispatchu compute jako obejścia błędu CWSR (DEGFX11_12113). Firmware CP robi to sam dla pakietów AQL; własny dispatch PM4 musi to zrobić sam. Źródła:
     - F. Kuehling (AMD) o awariach tinygrad: *„The GFXv11 GPU line requires a workaround to set COMPUTE_PGM_RSRC1.PRIV=1 when dispatching a compute kernel. Normally this is handled by the AQL DISPATCH packet. However, since the Tinygrad implementation leverages a custom runtime, it requires this workaround in its PM4-based dispatch.”* ([gist](https://gist.github.com/fxkamd/ecaaab72694696602b6f350edaab9d8d));
     - kfdtest: *„For some special asics in the list of DEGFX11_12113 COMPUTE_PGM_RSRC needs priv=1 to prevent hardware traps”* ([Dispatch.cpp#L146-L154](https://github.com/ROCm/ROCT-Thunk-Interface/blob/rocm-6.2.0/tests/kfdtest/src/Dispatch.cpp#L146-L154)); lista układów obejmuje 11.0.0, czyli gfx1100 ([KFDBaseComponentTest.cpp#L170-L181](https://github.com/ROCm/ROCT-Thunk-Interface/blob/rocm-6.2.0/tests/kfdtest/src/KFDBaseComponentTest.cpp#L170-L181)); commit [507637e](https://github.com/ROCm/ROCT-Thunk-Interface/commit/507637ed5b82197eecbf483cdc1234939766549a) *„For software trap in GFX11, COMPUTE_PGM_RSRC1 must have PRIV = 1.”*;
     - tinygrad: `# Set rsrc1.priv=1 on gfx11 to workaround cwsr.` ([ops_amd.py#L288-L289](https://github.com/tinygrad/tinygrad/blob/v0.10.0/tinygrad/runtime/ops_amd.py#L288-L289));
     - KFD dla GC 11.0.0–11.0.3 dodaje kolejki z `trap_en = 0` (`kfd_dbg_has_cwsr_workaround`, [kfd_debug.h#L104-L108](https://github.com/torvalds/linux/blob/v6.8/drivers/gpu/drm/amd/amdkfd/kfd_debug.h#L104-L108), [kfd_device_queue_manager.c#L227-L229](https://github.com/torvalds/linux/blob/v6.8/drivers/gpu/drm/amd/amdkfd/kfd_device_queue_manager.c#L227-L229)). Handler CWSR dla gfx11 ma komentarz: *„If traps are enabled then return to the shader with PRIV=0. Otherwise retain PRIV=1 for subsequent context save requests.”* ([cwsr_trap_handler_gfx10.asm#L1091-L1093](https://github.com/torvalds/linux/blob/v6.8/drivers/gpu/drm/amd/amdkfd/cwsr_trap_handler_gfx10.asm#L1091-L1093)).

     Fale taśmy nie są więc bezpiecznie zapisywane i odtwarzane przez CWSR, gdy KFD wywłaszcza kolejkę w trakcie dispatchu `[INFERENCE: mechanizm w firmware jest zamknięty]`.
  2. **Wyzwalacz.** KFD ewikuje wszystkie kolejki procesu w losowych chwilach. W naszym serwerze najpewniej robi to głównie **SVM**:
     - HIP przy każdej kopii z/do pamięci stronicowanej (stan `--cache-ram`, wpisy po 520 MiB, łącznie 16 GiB) zostawia **trwałe, zmapowane na GPU zakresy SVM**;
     - jądro migruje te strony (kompakcja: 7.13 mln stron od startu bootu 0) i wyrzuca je do swapu;
     - każde takie unieważnienie to `svm_range_evict` → `kgd2kfd_quiesce_mm` → REMOVE_QUEUE wszystkich kolejek, także taśmy w środku IB (§9.3).

     Dochodzą do tego ewikcje userptr (pamięć hosta z puli ROCr, w tym nasz IB) i TTM (inny proces na GPU, R2).
- **Za H1′ (poszlaki, bez dowodu na GPU):**
  - podpis awarii: SQC czyta stronę 0, naraz wiele fal, `priv 0`;
  - faulty AQL (`moebench`, 16.10, ten sam boot co R2) mają `priv 1`, czyli firmware rzeczywiście daje falom AQL PRIV=1, a falom taśmy nie;
  - resetem kończą się tylko faulty taśmy. MES w R3–R10 za każdym razem nie umie zdjąć tej samej kolejki: `doorbell=0x100a`, „Failed to evict queue 7” jako pierwsza, czyli najnowsza z 8 kolejek procesu. W R1 (`pdl`, 4 kolejki) analogicznie najnowsza „queue 3”, `0x1806`, czyli tam własna kolejka PM4. To najpewniej kolejka taśmy, tworzona po kolejkach HIP `[INFERENCE]`;
  - w R2 zawiesił się **ADD_QUEUE** (msg 2), wysłany ok. 110 ms przed timeoutem, czyli praktycznie w chwili faultu. ADD_QUEUE wysyła tylko restore po ewikcji (albo tworzenie kolejki), nigdy reakcja na fault. Fault zbiegł się więc z przywracaniem kolejek po ewikcji (tam najpewniej TTM przez drugi proces na GPU `[INFERENCE]`);
  - awarie zaczynają się dopiero po zapełnieniu cache (16 GiB zmapowanego SVM i największa presja na pamięć);
  - workery restore SVM i userptr pracują w każdym bootcie z awariami.
- **To, co zlecenie nazywało poprawką H1** („każdy dispatch samowystarczalny”), **już jest w taśmie.** Każdy dispatch ustawia od nowa wszystkie rejestry, które czyta (§9.1), więc samo to awarii nie tłumaczy. Brakuje obejścia GFX11 i kilku detali zgodności z referencyjnym dispatchem PM4 AMD.
- **Poprawka (prototyp `GGML_HIP_PM4_WA=2`, koszt oczekiwany ~0):**
  - `PRIV=1`;
  - bez `ORDERED_APPEND_ENBL`;
  - `COMPUTE_RESTART_X/Y/Z = 0` przed każdym dispatchem;
  - polityka cache IB = 0.

  Do tego usunięcie głównego źródła ewikcji przez env (`HSA_USE_SVM=0` albo `GPU_PINNED_MIN_XFER_SIZE`). `GUARD` zostaje jako druga linia obrony i dziennik.
- **Rekomendacja bez zmian:** `GGML_HIP_PM4=0` w serwerach, dopóki S4 i S6 z §9.5 nie przejdą.

### 9.1 Stan, na którym polega dispatch taśmy, vs dispatch AQL

Pakiety taśmy (`ggml_hip_pm4_build`, `hip-pm4.cu` @ `7cd12f993`, numery rejestrów to offsety SH od `0x2C00`):

| kiedy | pakiet | rejestry i wartości |
|---|---|---|
| początek IB | `ACQUIRE_MEM` (zakres systemowy) | GCR: GL2 WB+INV, GLM, GL1, GLV, GLK, GLI |
| przed dispatchem i>0 | `EVENT_WRITE CS_PARTIAL_FLUSH` (`0x407`), `ACQUIRE_MEM` | GCR `0x380` = GLK_INV, GLV_INV, GL1_INV |
| każdy dispatch | `SET_SH_REG 0x20C` | `COMPUTE_PGM_LO/HI` = `code_entry>>8`, `>>40` |
| | `SET_SH_REG 0x212` | `COMPUTE_PGM_RSRC1` = z deskryptora (**PRIV=0**); `RSRC2` = z deskryptora, z podmienionym LDS_SIZE (**TRAP_PRESENT=0**; ABI: „Must be 0 … set by the CP if the runtime has installed a trap handler”, [AMDGPUUsage#L5243-L5249](https://github.com/llvm/llvm-project/blob/llvmorg-19.1.0/llvm/docs/AMDGPUUsage.rst#L5243-L5249)) |
| | `SET_SH_REG 0x228` | `COMPUTE_PGM_RSRC3` = z deskryptora |
| | `SET_SH_REG 0x218` | `COMPUTE_TMPRING_SIZE` = 0 (kernele ze scratch są odrzucane) |
| | `SET_SH_REG 0x207` | `COMPUTE_NUM_THREAD_X/Y/Z` = blockDim |
| | `SET_SH_REG 0x215` | `COMPUTE_RESOURCE_LIMITS` = 0 |
| | `SET_SH_REG 0x240` | `COMPUTE_USER_DATA_0..5` = V# segmentu prywatnego `0,0,0,0` (jeśli kernel go deklaruje), wskaźnik kernargów lo/hi (`GGML_ASSERT` ≠ 0) |
| | `DISPATCH_DIRECT` | grid w grupach, inicjator = COMPUTE_SHADER_EN, FORCE_START_AT_000, **ORDERED_APPEND_ENBL (bit 3)**, CS_W32_EN |
| koniec IB | `CS_PARTIAL_FLUSH`, `ACQUIRE_MEM` (zakres systemowy) | (GUARD=2 / DEBUG≥2: `COPY_DATA` ze znacznikiem czasu) |
| pakiet AQL | vendor `AMD_AQL_FORMAT_PM4_IB` | `INDIRECT_BUFFER` (adres, `ndw`, VALID, **polityka cache 3**), `dw_cnt_remain=10`, bajty 24–55 = 0 (tam, gdzie pakiet kernela ma `kernel_object` @32 i `kernarg_address` @40), sygnał zakończenia; nagłówek z barrier, acquire/release system |

Czego taśma nie ustawia, czyli na czym polega:
- `COMPUTE_START_X/Y/Z`: zastępuje je FORCE_START_AT_000 (radv robi tak samo);
- **`COMPUTE_RESTART_X/Y/Z`: nigdy nie są zapisywane.** kfdtest ([#L186-L190](https://github.com/ROCm/ROCT-Thunk-Interface/blob/rocm-6.2.0/tests/kfdtest/src/Dispatch.cpp#L186-L190)) i tinygrad ([#L117](https://github.com/tinygrad/tinygrad/blob/v0.10.0/tinygrad/runtime/ops_amd.py#L117)) zerują je przed każdym dispatchem;
- `COMPUTE_DISPATCH_PKT_ADDR`, `DISPATCH_SCRATCH_BASE`: niepotrzebne, bo kernele z dispatch_ptr, queue_ptr albo scratch są odrzucane (maska właściwości 0, 3, 10);
- `COMPUTE_STATIC_THREAD_MGMT_SE0..7`, `USER_ACCUM`, `DISPATCH_INTERLEAVE`: wartości z MQD (maska CU z KFD), tak samo jak dla AQL;
- VMID, `SH_MEM_*`, TBA/TMA (trap handler), obszar CWSR: ustawiane per kolejka/proces przez KFD/MES.

Wniosek: **każdy rejestr, który dispatch czyta, jest ustawiany przed nim w tym samym IB.** Nic nie zależy od stanu z poprzedniego dispatchu ani taśmy. Proponowana w H1 poprawka „wszystko re-emitować” niczego tu nie zmieni.

Co dla dispatchu AQL robi CP/ROCr:
- **Pakiet od CLR:** nagłówek KERNEL_DISPATCH z barrier i acquire/release w zakresie agenta, wymiary, rozmiary, `kernel_object`, `kernarg_address`. Źródło: [rocvirtual.cpp#L2440-L2465, #L5119-L5125](https://github.com/ROCm/rocm-systems/blob/develop/projects/clr/rocclr/device/rocm/rocvirtual.cpp#L5119-L5125).
- **CP wypełnia user SGPR** według bitów `enable_sgpr_*`: V# scratch z kolejki, dispatch ptr, queue ptr, kernarg ptr „directly copied from the kernarg_address in the kernel dispatch packet”, dispatch id, flat scratch ([AMDGPUUsage#L5543-L5622](https://github.com/llvm/llvm-project/blob/llvmorg-19.1.0/llvm/docs/AMDGPUUsage.rst#L5543-L5622)).
- **CP uzupełnia pola deskryptora** oznaczone „CP is responsible”: PRIORITY, TRAP_PRESENT. Na GFX11 dokłada też obejście PRIV=1.

Różnice wobec referencyjnych dispatchy PM4:

| element | taśma (`WA=0`) | AQL (CP) | kfdtest PM4, gfx11 | tinygrad PM4, gfx11 | znaczenie |
|---|---|---|---|---|---|
| RSRC1.PRIV (bit 20) | 0 | 1 (obejście w firmware) | 1 | 1 | **kluczowe dla CWSR na GFX11** |
| RSRC2.TRAP_PRESENT | 0 | ustawia CP (KFD: `trap_en=0` na 11.0.0–3) | 1 | 0 | niejasne; tinygrad działa bez tego |
| inicjator bit 3 ORDERED_APPEND_ENBL | 1 | – | 0 (`0x21\|0x8000`) | 0 | dopisek GDS ordered append; sterownik: „wave IDs … wrong after suspend/resume” ([gfx_v11_0.c#L5346-L5355](https://github.com/torvalds/linux/blob/v6.8/drivers/gpu/drm/amd/amdgpu/gfx_v11_0.c#L5346-L5355)) |
| `COMPUTE_RESTART_X/Y/Z` | niezapisywane | firmware | 0 | 0 | po przerwanym dispatchu mogą zostać niezerowe `[INFERENCE]` |
| granica między dispatchami | `CS_PARTIAL_FLUSH` + `ACQUIRE_MEM` | bariera AQL + fence | `RELEASE_MEM` + `WAIT_REG_MEM`: *„EVENT_WRITE.partial_flush causes problems with preemptions in GWS testing”* ([#L251-L261](https://github.com/ROCm/ROCT-Thunk-Interface/blob/rocm-6.2.0/tests/kfdtest/src/Dispatch.cpp#L251-L261)) | `CS_PARTIAL_FLUSH` | GWS nie używamy, tinygrad działa z partial flush |
| polityka cache IB | 3 (wartość nieudokumentowana; `nvd.h` zna 0 LRU, 1 Stream, 2 Bypass) | ROCr: 0 | 2 | – | kosmetyka/zgodność |
| typ kolejki | AQL + pakiet vendor PM4_IB | AQL | kolejka PM4 (`HSA_QUEUE_COMPUTE`) | kolejka PM4 (`KFD_IOC_QUEUE_TYPE_COMPUTE`) | **DISPATCH_DIRECT w IB w kolejce AQL nie jest nigdzie testowany przez AMD.** ROCr używa `ExecutePM4` tylko do cache i PC sampling, bez dispatchy |

### 9.2 Ewikcja i przywracanie kolejek: KFD + MES na gfx11 (Linux v6.8)

**Ewikcja:**
- `kfd_process_evict_queues` najpierw emituje zdarzenie SMI QUEUE_EVICTION ze znacznikiem czasu startu, potem woła `evict_process_queues_cpsch` ([kfd_process.c#L1829-L1833](https://github.com/torvalds/linux/blob/v6.8/drivers/gpu/drm/amd/amdkfd/kfd_process.c#L1829-L1833));
- dla każdej aktywnej kolejki idzie `remove_queue_mes`, czyli `MES_SCH_API_REMOVE_QUEUE` z samym doorbellem i kontekstem gangu ([kfd_device_queue_manager.c#L1096-L1160](https://github.com/torvalds/linux/blob/v6.8/drivers/gpu/drm/amd/amdkfd/kfd_device_queue_manager.c#L1096-L1160), [mes_v11_0.c#L222-L239](https://github.com/torvalds/linux/blob/v6.8/drivers/gpu/drm/amd/amdgpu/mes_v11_0.c#L222-L239));
- SUSPEND/RESUME nie są używane;
- czy MES zapisuje fale (CWSR), czy czeka na ich koniec, decyduje firmware. CWSR jest uzbrojony przez MQD (`QSWITCH_MODE`, obszar ctx-save).

**Przywracanie:**
- `restore_process_queues_cpsch` → `add_queue_mes`, czyli ADD_QUEUE z tym samym MQD i tba/tma;
- `trap_en = !kfd_dbg_has_cwsr_workaround()`, co na gfx1100 daje **0**.

**MQD** ([kfd_mqd_manager_v11.c#L123-L279](https://github.com/torvalds/linux/blob/v6.8/drivers/gpu/drm/amd/amdkfd/kfd_mqd_manager_v11.c#L123-L279)):
- sterownik zeruje MQD i ustawia tylko pola kolejki (PQ, EOP, AQL control, persistent state, quantum, ctx-save, maski CU);
- **pól dispatchu nie dotyka nigdy:** `compute_pgm_*`, `compute_user_data_0..15`, `compute_restart_*`, `compute_dispatch_initiator`, `compute_relaunch`, `cp_hqd_ib_*`;
- ich zapis i odtworzenie przy ewikcji to wyłącznie sprawa firmware (zamkniętego);
- w źródłach nie ma słowa o IB PM4 wewnątrz kolejki AQL.

**Co jest testowane przez AMD:**
- `KFDCWSRTest.BasicTest` przerywa dispatch w kolejce PM4 od 10 do 1000 razy (dequeue/requeue) i sprawdza „reg mangling”. Robi to z PRIV=1 na gfx11;
- `KFDEvictTest` robi ewikcję TTM w trakcie dispatchu, także w kolejce PM4.

Kombinacja „DISPATCH_DIRECT z IB w pakiecie vendor kolejki AQL + PRIV=0 + CWSR” jest **poza** testowanym i udokumentowanym obszarem.

**Opóźnienia** ([kfd_svm.c#L46](https://github.com/torvalds/linux/blob/v6.8/drivers/gpu/drm/amd/amdkfd/kfd_svm.c#L46), [amdgpu_amdkfd_gpuvm.c#L47](https://github.com/torvalds/linux/blob/v6.8/drivers/gpu/drm/amd/amdgpu/amdgpu_amdkfd_gpuvm.c#L47), [kfd_priv.h#L700-L704](https://github.com/torvalds/linux/blob/v6.8/drivers/gpu/drm/amd/amdkfd/kfd_priv.h#L700-L704)):

| typ ewikcji | restore po | minimalny odstęp między ewikcjami |
|---|---|---|
| userptr | 1 ms; worker przeplanowuje się (`'R'`), dopóki pamięć jest nieważna | brak |
| SVM | 1 ms | brak |
| TTM | 100 ms | 10 ms |

**Fault:**
- VM fault (`EC_DEVICE_MEMORY_VIOLATION`) → `kfd_set_dbg_ev_from_interrupt` → `kfd_dqm_evict_pasid` ewikuje kolejki procesu ([kfd_debug.c#L238-L240](https://github.com/torvalds/linux/blob/v6.8/drivers/gpu/drm/amd/amdkfd/kfd_debug.c#L238-L240));
- REMOVE kolejki taśmy z zatrzymanymi falami nie kończy się;
- po ok. 107–128 ms od pierwszego wpisu o faultcie przychodzi timeout MES (R2 110.6 ms na ADD_QUEUE; na REMOVE_QUEUE: R3 126.0, R4 107.0, R6 124.4, R7 128.1, R8 123.2, R9 126.3, R10 119.6 ms), a potem mode1 reset.

Kolejne próby w trakcie resetu odbijają się co 124–129 ms. Odstępy krótsze niż to (R4, R10, R2) sugerują, że komenda MES była w drodze już w chwili zapisu faultu, czyli trwała ewikcja albo restore. To słaba poszlaka, bo czas timeoutu MES nie jest stały.

### 9.3 Źródła ewikcji w naszej konfiguracji

1. **SVM, główne** (źródła: odpowiedź ClrPinnedXfer, cytaty poniżej). Łańcuch:
   - kopia z/do pamięci stronicowanej ≥ `pinnedMinXferSize_` (64 KiB w develop, 1 MiB w 7.0.0) idzie ścieżką „pinned”, w kawałkach po 32 MiB ([rocblit.cpp#L1045-L1047](https://github.com/ROCm/rocm-systems/blob/develop/projects/clr/rocclr/device/rocm/rocblit.cpp#L1045-L1047));
   - `pinHostMemory` → `hostLock` → `hsa_amd_memory_lock_to_pool` → libhsakmt, która na dGPU gfx9+ **rejestruje przez SVM API** (`HSA_USE_SVM` domyślnie włączone; [fmm.c#L5043-L5048](https://github.com/ROCm/rocm-systems/blob/develop/projects/rocr-runtime/libhsakmt/src/fmm.c#L5043-L5048), [openclose.c#L244-L245](https://github.com/ROCm/rocm-systems/blob/develop/projects/rocr-runtime/libhsakmt/src/openclose.c#L244-L245)), z `ACCESS_IN_PLACE`, czyli od razu z mapowaniem na GPU;
   - **unlock zostawia zakres SVM** (deregister to no-op; [fmm.c#L4857-L4859](https://github.com/ROCm/rocm-systems/blob/develop/projects/rocr-runtime/libhsakmt/src/fmm.c#L4857-L4859), ROCm 7.0.0 [fmm.c#L4053-L4055](https://github.com/ROCm/ROCR-Runtime/blob/rocm-7.0.0/libhsakmt/src/fmm.c#L4053-L4055); ROCr: „Lock leaves a userptr registration or an SVM registration”);
   - w naszym runtime jest `HSA_USE_SVM`, a nie ma `HSA_SVM_HOST_UNREGISTER_DEBUG` (sprawdzone `strings` na `libhsa-runtime64.so.1`, `libhsakmt.a`).

   Skutek w serwerze:
   - zapis stanu do cache (`llama_state_seq_get_data_ext` → `ggml_backend_tensor_get` per tensor do `std::vector` 520 MiB) i odczyt (`set_data`) zostawiają na każdym wpisie zmapowany zakres SVM. Po ~31 requestach (16384/520.8) to 16 GiB;
   - `munmap` wpisu (eksmisja najstarszego przy każdym requeście, `load()` zwalnia wpis po odtworzeniu) idzie ścieżką UNMAP: mapowanie znika z GPU bez ewikcji kolejek, zostaje praca odroczona. Stąd `svm_range_deferred_list_work hogged CPU` do 128× na boot;
   - **każde inne unieważnienie** (migracja przez kompakcję, swap-out, split THP, madvise) idzie przez `svm_range_evict`. Przy XNACK off: *„First eviction, stop the queues”* → `kgd2kfd_quiesce_mm(mm, KFD_QUEUE_EVICTION_TRIGGER_SVM)` ([kfd_svm.c#L1872-L1924](https://github.com/torvalds/linux/blob/v6.8/drivers/gpu/drm/amd/amdkfd/kfd_svm.c#L1872-L1924)). Potem `svm_range_restore_work`;
   - dzieje się to w kontekście kcompactd/kswapd, czyli **asynchronicznie wobec serwera i w środku taśmy**.

   Aktywność jądra w bootcie 0 (od 18.10 20:27, obejmuje R7–R10; `/proc/vmstat` 19.10 ~02:30):

   | licznik | wartość |
   |---|---|
   | `pgmigrate_success` | 7 130 366 stron (~27 GiB) |
   | `compact_daemon_wake` | 57 |
   | `compact_isolated` | 14.3 mln |
   | `pswpout` | 102 898 stron (~400 MiB) |
   | `pgsteal_kswapd` | 26.1 mln |
   | `thp_split_pmd` | 441 |

   THP `madvise`, `numa_balancing=0`, `compaction_proactiveness=20`, RAM 62 GiB (58 GiB buff/cache), swap 7 GiB.

   To tłumaczy korelację z zapełnieniem cache (§4 d): po ~33 requestach zmapowanego SVM jest najwięcej (16 GiB), a presja na RAM (17.5 GB modelu w page cache i 16 GiB anonimowych) uruchamia kswapd/kcompactd.
2. **userptr.** Pamięć „fine-grained” z `hsa_amd_memory_pool_allocate` i z `hipHostMalloc` to w libhsakmt anonimowy `mmap(MAP_SHARED)` z BO userptr (`HSA_USERPTR_FOR_PAGED_MEM` domyślnie włączone, [fmm.c#L3014-L3086](https://github.com/ROCm/rocm-systems/blob/develop/projects/rocr-runtime/libhsakmt/src/fmm.c#L3014-L3086)). Dotyczy to **naszego IB**, bufora postępu GUARD, sygnałów i hostowych buforów llama (bufor wyjścia).
   - Kompakcja albo swap tych stron daje ewikcję userptr: każde zdarzenie, bez filtra ([amdgpu_hmm.c#L100-L115](https://github.com/torvalds/linux/blob/v6.8/drivers/gpu/drm/amd/amdgpu/amdgpu_hmm.c#L100-L115)).
   - W bootcie 0 `restore_userptr_worker` przekraczał 10 ms CPU 64 razy (raporty przy 4/8/16/32/64: 20:56, 21:16, 21:39, 22:40, 00:14).
3. **TTM:** VRAM zabierany przez inny proces (R2, `validate.sh`). W R2 MES zawiesił się na ADD_QUEUE, czyli na restore.
4. **suspend:** runtime PM. Wyłączone przez `gpu-powercap.service`, w trakcie przebiegów nieistotne.

**Zdarzeń KFD SMI z 8 awarii nie ma.** Strażnika wtedy nie było, a nie-root widzi tylko zdarzenia własnego procesu. Jedyny ślad ewikcji to liczniki „hogged CPU” workerów (liczą tylko przebiegi >10 ms, raport przy potęgach 2). R9: `svm_range_restore_work` (32. raport) o 23:25:12.631, 156 ms po faultcie.

**Jak uniknąć:**
- `HSA_USE_SVM=0`: libhsakmt rejestruje przez BO userptr, a te są zwalniane przy unlock. Nie zostają trwałe zakresy; okno ekspozycji trwa tylko podczas kopii, kiedy taśma nie działa. Wyłącza też SVM API (`hipMallocManaged`, którego llama nie używa).
- `GPU_PINNED_MIN_XFER_SIZE=<MiB większe od największej kopii>`, np. 1024: kopie idą przez bufor staging (1 MiB, `GPU_STAGING_BUFFER_SIZE`), bez rejestracji. Koszt: czas zapisu i odczytu 520 MiB stanu. Dziś odstęp `alloc` → `launch_slot_` to ~0.31 s; trzeba zmierzyć.
- W kodzie: stały bufor pośredni dla stanu (jak odrzucony `LLAMA_STATE_PINNED`, 16f).
- **`mlock` nie pomaga:** zablokowane strony nadal może przenieść kompakcja (`compact_unevictable_allowed=1`), a munmap i tak unieważnia. Sysctl `compaction_proactiveness=0` / `compact_unevictable_allowed=0` wymaga roota i tylko zmniejsza ryzyko.
- **Mniejsze `--cache-ram`** zmniejsza obszar i presję, ale nie do zera.
- **IB nie da się przenieść do GTT przez publiczne API** ROCr (tylko VMem albo VRAM). Do VRAM tak: opcja 4 w §9.4.

### 9.4 Opcje naprawy (ranking)

| # | opcja | efekt oczekiwany | koszt | ryzyko |
|---|---|---|---|---|
| 1 | **`GGML_HIP_PM4_WA=2`** (`b7fb3fe85`): `PRIV=1` + inicjator bez ORDERED_APPEND + `RESTART_X/Y/Z=0` + polityka IB 0 (`WA=1` = samo PRIV, do bisekcji) | fale taśmy zapisywane i odtwarzane przez CWSR jak fale AQL, kfdtest i tinygrad. `[INFERENCE]` Fault w taśmie zabija proces zamiast resetować GPU (jak AQL z `priv 1`) | +5 dwordów na dispatch (~16 KB IB dla 823 dispatchy); t/s ~0, do zmierzenia | niskie–średnie; zalecenie AMD, ale nieprzetestowane u nas |
| 2 | **`HSA_USE_SVM=0`** albo **`GPU_PINNED_MIN_XFER_SIZE`** w `run-llm.sh` | znika główne źródło ewikcji w długich sesjach; mniej zatrzymań wszystkich kolejek (także AQL) i mniej CPU w workerach restore | czas zapisu/odczytu stanu (zmierzyć) | niskie (tylko env) |
| 3 | `GGML_HIP_PM4_GUARD=1` w produkcji (cool-down) | dziennik i ominięcie serii ewikcji; nie zatrzyma ewikcji w środku taśmy | <0.1% `[SZACUNEK]` | niskie |
| 4 | IB i bufory GUARD w VRAM (pula GPU z flagą executable) | usuwa ewikcje userptr od naszej taśmy | mały kod; CP czyta IB z VRAM | średnie (nowa ścieżka) |
| 5 | Kolejka PM4 KFD zamiast pakietu vendor w kolejce AQL (jak kfdtest/tinygrad) | jedyna kombinacja testowana przez AMD z CWSR | duży kod: surowe ioctl KFD, bo `libhsa-runtime64` z core-10.0 nie eksportuje `hsaKmt*` (`nm -D`: 0 symboli) | średnie–wysokie |
| 6 | `RELEASE_MEM`+`WAIT_REG_MEM` zamiast `CS_PARTIAL_FLUSH` (kfdtest) | tylko jeśli 1 nie wystarczy | droższa granica, czyli zysk PM4 | średnie |
| 7 | `DISABLE_DISP_PREMPT_EN` (bit 17; PAL: „when CWSR is disabled”) | nieudokumentowane przy włączonym CWSR | – | nie polecam |
| 8 | `GGML_HIP_PM4=0` | stan bezpieczny | Qwen −4.7%, LFM −12% | brak |

Prototypy w `b7fb3fe85` (skompilowane `hip-pm4.cu.o`, `ggml-cuda.cu.o`, `llama-server`, bez ostrzeżeń; nieuruchomione):
- `GGML_HIP_PM4_WA=0/1/2` jak wyżej, domyślnie 0;
- `GGML_HIP_PM4_GUARD`:
  - działa także przy `GGML_HIP_PM4=0` (tylko obserwacja na ścieżce grafu HIP);
  - każde zdarzenie dostaje czas ścienny (do `journalctl`), położenie względem taśmy („during a tape (x ms after its submit)”, ze znaczników `CLOCK_BOOTTIME` zdarzenia) i przyrost liczników `/proc/vmstat` od poprzedniego zdarzenia (migracja, kompakcja, swap, split THP, reclaim);
  - restore przeplanowany jest oznaczany `'R'`;
  - przy `=2` dochodzą zdarzenia `UNMAP_FROM_GPU` (adres i rozmiar zakresu SVM: dowód, które bufory HIP zarejestrował);
- `GGML_HIP_PM4_EVICT_TEST_MS=<n>` (tylko test): wątek co ~n ms robi `madvise(MADV_DONTNEED)` na 2 MiB zablokowanych przez `hsa_amd_memory_lock`. To deterministyczna ewikcja SVM wszystkich kolejek, z restore po ~1 ms.

### 9.5 Minimalna, najbezpieczniejsza sekwencja testów GPU (do decyzji użytkownika)

Wspólne:
- warunki z §6;
- build `b7fb3fe85`;
- jeden blok naraz, `flock` i `gpu-guard`;
- stop przy pierwszym faultcie, bez powtórek;
- po każdym kroku `journalctl -k -b 0` + log strażnika.

`EVICT_TEST` wymaga `GGML_HIP_PM4_GUARD_COOLDOWN_MS=0` tam, gdzie taśmy mają działać mimo ewikcji.

| krok | konfiguracja | hipoteza | oczekiwane | stop | maks. czas | ryzyko |
|---|---|---|---|---|---|---|
| S1 | `llama-bench` LFM tg128, `GGML_HIP_PM4=0 GGML_HIP_PM4_GUARD=2 GGML_HIP_PM4_EVICT_TEST_MS=100`; potem to samo z `HSA_USE_SVM=0`; na koniec greedy md5 Qwen/LFM z wstrzykiwaniem | `hsa_amd_memory_lock` + madvise ewikuje wszystkie kolejki (SVM, przy `HSA_USE_SVM=0` userptr); ścieżka AQL to znosi | ~10 par eviction/restore na s, restore ~1–2 ms, spadek t/s, md5 = `c4708318`/`6f14e814` | dowolny fault: ścieżka AQL też niebezpieczna, stop całości | 10 min | niskie (bez PM4) |
| S2 | T0′: blok 241 requestów (frozen `arm.sh` … `0 sweep`, seedy 4–23), `GGML_HIP_PM4=0 GGML_HIP_PM4_GUARD=2` (sama obserwacja) | w normalnej pracy są ewikcje SVM, głównie po zapełnieniu cache, w parze z przyrostem `pgmigrate`/`pswpout`; `UNMAP_FROM_GPU` po 32 MiB przy eksmisji wpisów | liczba i triggery ewikcji na request, czas restore | fault | 30 min | niskie |
| S3 | S2 + `HSA_USE_SVM=0` (osobno: `GPU_PINNED_MIN_XFER_SIZE=1024`) | bez trwałych zakresów SVM ewikcje SVM znikają | ewikcje SVM ≈ 0; zmierzony koszt zapisu stanu (`alloc` → `launch_slot_`) i TTFT | fault albo regresja TTFT > 20% | 30 min | niskie |
| S4 | `llama-bench` LFM tg128 (taśma 304 dispatche), `GGML_HIP_PM4_WA=2 GUARD=2 COOLDOWN_MS=0 EVICT_TEST_MS=50`, 2 min; potem greedy md5 z tym samym | H1′: z PRIV=1 ewikcja w środku taśmy jest bezpieczna | ≥1000 ewikcji „during a tape”, 0 faultów, md5 bez zmian | pierwszy fault: WA nie wystarcza, PM4 zostaje off, dalej opcja 5 | 10 min | średnie (możliwy reset) |
| S5 | jak S4, ale `WA=0` | przyczynowy dowód H1′: bez PRIV ewikcja w taśmie daje SQC @0 | fault w ciągu sekund | pierwszy fault (oczekiwany) | 2 min | **wysokie: oczekiwany reset GPU**; tylko za osobną zgodą, można pominąć |
| S6 | T1/T2: obciążenie produkcyjne, PM4 on, `WA=2`, `GUARD=1`, z i bez `HSA_USE_SVM=0`: 241, potem ≥1000 requestów; ABBA t/s Qwen MTP i LFM vs produkcja | poprawka trzyma w realnym obciążeniu | 0 faultów, liczba ewikcji w taśmach, koszt `WA=2` ≈ 0 | fault | 4 × 30 min | średnie |

Gdyby S4 dał fault, następny krok to opcja 5 albo PM4 tylko w `llama-bench`. Wtedy S5 i S6 odpadają.

### 9.6 Rekomendacja dla produkcji

- Do czasu S4 i S6: **`GGML_HIP_PM4=0`** (bez zmian względem §0).
- Po S3: rozważyć `HSA_USE_SVM=0` (albo `GPU_PINNED_MIN_XFER_SIZE`) w `run-llm.sh` **niezależnie od PM4**. Każda ewikcja zatrzymuje wszystkie kolejki serwera (także AQL) i obciąża CPU w workerach restore, a długie sesje z `--cache-ram 16384` wywołują je w nieznanej dziś liczbie (S2 to zmierzy).
- Powrót PM4 do serwerów tylko z `GGML_HIP_PM4_WA=2` (po S6 zmienić domyślną wartość na 2) i `GGML_HIP_PM4_GUARD=1`.

### 9.7 Do bazy wiedzy

| folder | tytuł | treść (liczby ze źródłami) |
|---|---|---|
| `rocm/` | `gfx11-pm4-dispatch-priv.md` | Własny `DISPATCH_DIRECT` (PM4) na GFX11 musi ustawić `COMPUTE_PGM_RSRC1.PRIV=1` (bit 20, obejście CWSR DEGFX11_12113). CP robi to tylko dla pakietów AQL. Źródła: gist F. Kuehlinga (tinygrad), kfdtest `Dispatch.cpp#L146-L154` + commit `507637e`, tinygrad `ops_amd.py#L288-L289`; KFD `trap_en=0` dla GC 11.0.0–11.0.3. Nasza taśma tego nie miała (`WA=0`); prototyp `GGML_HIP_PM4_WA=1/2` (`b7fb3fe85`). |
| `rocm/` | `hip-kopie-stronicowane-zostawiaja-svm.md` | CLR kopiuje pamięć stronicowaną ≥64 KiB/1 MiB przez „pin” w kawałkach po 32 MiB. libhsakmt rejestruje to przez SVM API (`HSA_USE_SVM` domyślnie), a unlock zakresu nie usuwa. Każdy bufor stanu `--cache-ram` (520 MiB) zostaje zmapowany na GPU do `munmap`. Migracja lub swap tych stron (boot 0: 7.13 mln stron zmigrowanych, 103 tys. wyrzuconych do swapu) ewikuje wszystkie kolejki procesu (trigger SVM). Obejścia: `HSA_USE_SVM=0`, `GPU_PINNED_MIN_XFER_SIZE`. |
| `rocm/` | `kfd-ewikcja-kolejek-gfx11.md` | Triggery SVM/userptr/TTM/suspend; restore po 1/1/100 ms, przy TTM minimalny odstęp 10 ms. MES: REMOVE_QUEUE/ADD_QUEUE z tym samym MQD; sterownik nie zapisuje pól dispatchu MQD (`compute_pgm_*`, `user_data`, `restart`, `cp_hqd_ib_*`), robi to firmware. `hipHostMalloc` i pule fine-grained ROCr to BO userptr na `MAP_SHARED`. „hogged CPU” workerów restore to jedyny ślad ewikcji w `journalctl`. |
| `rocm/` | aktualizacja `kfd-smi-eventy.md` | Formaty v6.8: `9 <boottime_ns> -<pid> <node> <trigger>`, `a <ts> -<pid> <node> [R]`, `b <ts> -<pid> @<page>(<pages>) <node> <trigger 0/1/2>` (UNMAP_FROM_GPU tylko dla SVM). Znacznik czasu z `CLOCK_BOOTTIME`, emitowany przed ewikcją. |
| `lekcje/` | `lekcja-wlasny-pm4-musi-robic-to-co-firmware.md` | Własny dispatch PM4 omija wszystko, co CP robi dla pakietu AQL: pola „CP is responsible” (PRIV, TRAP_PRESENT, user SGPR), obejścia sprzętowe, stan przy wywłaszczeniu. Przed wdrożeniem porównać pakiety z kfdtest/tinygrad/radv i przetestować wywłaszczenie (wstrzyknięta ewikcja), nie tylko soak. |
| `lekcje/` | `lekcja-test-wywlaszczenia.md` | Soak 4 min bez awarii nic nie mówi o odporności na wywłaszczenie: ewikcje przychodzą z migracji stron jądra po zapełnieniu pamięci (godziny). Wymuszać je deterministycznie (`madvise(MADV_DONTNEED)` na zakresie z `hsa_amd_memory_lock`, `GGML_HIP_PM4_EVICT_TEST_MS`). |
| `kernele/` | aktualizacja `pm4-replay.md` | Sekcja „Awarie”: kandydat na przyczynę to brak `PRIV=1` (obejście GFX11) w połączeniu z ewikcją SVM/userptr w środku taśmy (`[INFERENCE]`, raport 17 §9); różnice wobec kfdtest/tinygrad (ORDERED_APPEND_ENBL, RESTART, polityka cache IB 3); prototypy `GGML_HIP_PM4_WA`, `GUARD` z obserwacją przy PM4=0, `EVICT_TEST_MS`; plan S1–S6. |
| `decyzje/` | aktualizacja `2026-10-19-pm4-w-serwerach.md` | PM4 w serwerach off do czasu S4+S6 (§9.5). Kandydat na zmianę niezależną od PM4: `HSA_USE_SVM=0` albo `GPU_PINNED_MIN_XFER_SIZE` po pomiarze S3. Decyzja użytkownika. |
| `research/` | aktualizacja hubu raportu 17 | Status: przyczyna wskazana w źródłach (PRIV na GFX11 + ewikcja SVM z kopii HIP), nieudowodniona na GPU; prototypy `b7fb3fe85`; sekwencja S1–S6. |
