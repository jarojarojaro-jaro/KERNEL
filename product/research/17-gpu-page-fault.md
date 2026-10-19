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
