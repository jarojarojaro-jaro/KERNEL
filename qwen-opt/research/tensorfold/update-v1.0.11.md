# TensorFold: aktualizacja badania (0efbd447 / v1.0.8 → 2984ea01 / v1.0.11)

Klon `~/research/TensorFold`, `git fetch` 2026-10-14. `origin/main` = `2984ea01` (merge #841, 10-14 16:07 +0100). Nowe tagi:
- silnik: `v1.0.9` (10-13 16:14), `v1.0.10` (10-13 23:42), `v1.0.11` (10-14 11:42; same poprawki bezpieczeństwa `--cortheon`);
- aplikacja desktop/mobile (nowy katalog `app/`): `v1.0.0-beta.5` (10-13) i `v1.0.0-beta.6` (10-14). Silnika nie dotyczą.

Delta liczy 469 commitów, 1856 plików i +317k linii. Prawie wszystko to aplikacja: `app/` to ok. 1440 plików. Silnik zmienił się w 242 commitach (bez merge'y i bez `app/`): `zig/src` 193 pliki, `zig/kernels` 25 plików (Metal i CUDA).
- **Zero zmian HIP w `main`**: `git diff 0efbd447 origin/main -- zig/src/hip zig/kernels/hip` jest puste.
- Wątki: 280 issues/PR zaktualizowanych od 10-11, 316 komentarzy od 10-12.
- Do klonu dociągnąłem tylko refy PR-ów (`refs/remotes/pr/N`). Pliki śledzone są nietknięte.
- Nic nie było budowane ani uruchamiane.
- `#N` = https://github.com/ashhart/TensorFold/issues/N (PR-y mają tę samą numerację).

Arytmetyka naszych modeli:
- Qwen: 28.9 ms/krok przy 104 t/s, więc **1 ms/krok ≈ +3.5%**.
- LFM: 4.10 ms/token, więc **0.1 ms ≈ +2.5%**. Granica kernela kosztuje ok. 2.5 µs, czyli usunięcie 1 launchu na warstwę (×40) daje ok. 0.1 ms.

---

## 1. Oś czasu delty

| Kiedy (10-2026) | Co | Dowód |
|---|---|---|
| 10-11..12 | Gałęzie społeczności, rebase'owane na 1.0.9: Metal 27B (#711 scan in-place, #712 atencja decode, #713 drafter), Nemotron CUDA (passy promptu po 4096 wierszy #720, background prefill #723, wspólne kernele norm #736) | `20b37cd6`, `64cc7b01`, `3eedf0b8`, `6d63e7da`, `c6a64a34` |
| 10-12..13 | Nemotron CUDA: „loads in flight” w kernelach decode (#771), batched heads i wspólne rundy (#768/#770, dotyczy wielu strumieni), kalibracja kosztów okna z prawdziwego tekstu | `37da3ce8`, `aeaaa638`, `da676b0d`, `2fd26556`, `0e081cfe` |
| 10-13 | **v1.0.9**: tokenizer z cache segmentów (#767), lone driver dla logprobs/JSON/budżetów myślenia, M6, `--cortheon` (research w serwerze) | `72b45368` |
| 10-13 | **v1.0.10**: mieszane szerokości oQ na Macach (#755/#756/#773/#774/#784/#786/#788), NVFP4 prompt +4–7.5% (#805), shared residual norm (#796) | `6c5e5192` |
| 10-13..14 | `app/`: aplikacja Electron i mobilna (beta.5/.6) | `c126fe16`, #828/#834/#841 |
| 10-14 | **v1.0.11**: fuzzing i poprawki parserów Cortheon | `3a6d1f14` |
| 10-14 (otwarte) | **HIP: 9 nowych slice'ów Flash Next** (#810–#818). **LFM2.5-24B-A2B na Metal** (#820–#823). Router/topk MoE z loadami w locie (#833). 27B CUDA z jądrami wspólnymi (#608 + #734/#746/#797/#798). Windows + Qwen3.5 CUDA (#836). Intel XPU 27B (#802) | patrz §2 |

## 2. Co nowego, po obszarach

### 2.1 AMD / HIP / gfx11 (wszystko poza `main`)

- **Stan:** stos Qwen3.5-HIP (#617/#621/#626/#631/#655/#697) nadal jest otwarty. Stał w kolejce „first in line for 1.0.7” (#491, komentarz 10-10), a minęły 1.0.7–1.0.11 i nic z niego nie weszło. Nowych liczb dla 27B na HIP nie ma. Aktualne są te z poprzedniego badania (W7800 plain 25.8–27.2 tok/s, #490).
- **Flash Next na HIP (#810–#818, BlivionIaG):** 2×W7800 (gfx1100, TP2, 3-bit) i 4×V620 (gfx1030, TP4). Pomiary autora.
  - **#813, kernele routingu MoE:**
    - `tf_moe_route` liczył starty ekspertów jedną pętlą wątku 0 po 513 ekspertach. Według commita `fd3baad5` ta pętla to „most of the launch's 32 us … 48 times a token”. Teraz jest to block scan: **30.8 → 6.9 µs**.
    - `tf_select_decode` liczy teraz jednego eksperta na wątek przy 512 wątkach: **25.5 → 14.7 µs**.
    - Decode: V620 90.0 → 97.0 tok/s (code), W7800 98.0 → 105.9.
  - **#818, grafy (`e3ee03bb`):** rundy odtwarzają grafy według kształtu (sloty i wiersze strumieni). Grafy są cięte na kolektywach. Kształt jest nagrywany przy drugim wystąpieniu. **Wejścia hosta idą jednym zbiorczym uploadem.** Efekt: V620 92.5 → 97.0, W7800 100.8 → 105.9 tok/s.
  - **#812:** plan MoE dla decode jest liczony z faktycznych par: 12 pozycji zamiast 198 w kubełku potęgi 2. Bez liczb prędkości.
- **Numeryka WMMA (dyskusja w #491, 10-12):**
  - gfx11: kafel #621 trzyma bity łańcucha dot2. `refs/pr/621:zig/kernels/hip/tiles/matrix_gemm.hpp:3`: „codes are exact in BF16, so WMMA sums match the dot2 chain bit for bit”.
  - gfx12 (R9700, jkuepker): to założenie nie zachodzi. WMMA zgadza się z łańcuchem dot2 na 33–99.9% wyjść.
  - WMMA vs dot2 na projekcjach 27B (gfx1201, ms na forward, 64 warstwy):

    | wiersze | 4096 | 512 | 64 | 16 | 8 | 4 | 1 |
    |---|---|---|---|---|---|---|---|
    | przyspieszenie WMMA | 2.36× | 2.38× | 1.89× | 1.95× | 1.28× | 0.87× | 0.55× |

  - Decyzja maintainera HIP: kolejność WMMA jest dozwolona per klasa, przy trzech warunkach: ta sama kolejność przy każdej liczbie wierszy, najgorsza kolumna wobec FP64 nie gorsza niż dot2, przebieg fidelity na modelu. Ostatnie słowo należy do ashhart.
  - BlivionIaG ma też „faster WMMA kernels” na gfx11, które sumują we własnej kolejności. **Liczb nie podał.**
- Drobne: ROCm 7.2.1 trzyma bitcode w `lib/llvm/lib/clang/22/lib/amdgcn/bitcode` (#491).

### 2.2 Qwen3.x-27B / GDN / MTP / DFlash / drzewa

- **Metal (`main`, M5 Ultra, pomiary kontrybutora jkuepker), `CHANGELOG.md:56-58`:**
  - #711: scan stanu GDN in-place. Był już w poprzednim badaniu.
  - #712: łańcuch wierszy decode atakuje własne klucze w kernelu prefiksu. Znika kernel tail, repack i gate: **7 → 4 dispatche na warstwę atencji**.
  - #713: pierwszy command buffer draftera startuje po 6 operacjach zamiast 40. Klucze w atencji draftera ładowane są po 4 przed złożeniem. Szeroki top-k jest podzielony na 16 threadgroup.
  - Łącznie: greedy code 406.1 → 417.0, proza 100.6 → 103.6. Sampled 294.0 → 316.9 / 86.2 → 89.0 tok/s.
- **CUDA 27B (#608 otwarty; jądra #746/#797 jschmied, pomiary BobClawblaw na RTX 5090 i jschmied na GB10): przepis na jednowierszową atencję decode przy długim kontekście.**
  - Przy 4.7k kontekstu „shared” było 2× wolniejsze od Triton (56.3 vs 27.0 µs/wywołanie). Przyczyna: grupy po 2048 kluczy dawały 32 warpy w locie, a Triton miał ok. 144.
  - Grupy po 512 kluczy: shared 56.3 → 16.9 µs, part 21.3 → 8.1 µs.
  - Bloki jednowarpowe pobierają 2 kafle do przodu (3 etapy `cp.async`).
  - Merge wydaje loady 16 partiali przed składaniem: 9.68 → 3.98 µs.
  - Atencja razem: 83.6 → 29.1 µs/wywołanie (Triton 59.7). Decode przy 4.8k: 72.6 → 77.9 tok/s (#608, komentarze 10-13..14).
  - Rozmiar grupy wchodzi w kolejność sumowania, więc bity zmieniły się raz: dNLL +0.0009, argmax 99.32%.
- **Lekcja numeryczna (#608, jschmied 10-13):** dwa celowe błędy przechodzą bramkę teacher-forced (NLL / argmax / KL na 4092 wierszach):
  - częstotliwości RoPE × 1.0039: +0.0012 / 99.07% / 0.00103;
  - norma q/k dzieląca przez D−1: +0.0008 / 99.17% / 0.00070.

  Test per kernel z granicą FP64 łapie oba od razu: 58,563× i 1.43× tolerancji. Wniosek autorów: KL/NLL to tylko test integracji. Linię trzyma referencja per kernel plus mutacja.
- **GDN „delta log” (#836, Windows + Qwen3.5 CUDA, otwarty):**
  - Każdy wiersz okna loguje `g[nv]`, `delta[nv][DK]` (fp32) i `k[nk][DK]` (`refs/pr/836:zig/kernels/cuda/qwen35.cuh:36-41`). Dla 27B to ok. 28 KiB na wiersz i warstwę, plus ogon conv.
  - Commit to tylko aktualizacje rzędu 1 wzdłuż zaakceptowanej ścieżki: `state = state*g; state = fma(k, delta, state)` (`qwen35_keep.cu:8-31`). Nie liczy już ani `S·k`, ani wyjścia.
  - Gałąź drzewa odbudowuje stan rodzica ze stanu bazowego i logu przodków (`qwen35.cu:183-205`). Łańcuch trzyma stan w rejestrach.
  - RTX 4090: 27B z DFlash2 134/83 tok/s przy T=1 (code/chat), 132/102 greedy, plain ok. 40.
- **4-bitowy KV z Hadamardem dla 27B CUDA (#799, propozycja):**
  - Wiersz 144 B: grupy po 32 wartości, kody 4-bit plus skala fp16.
  - Wobec bf16: KL średnio 0.0034 / 0.0055 / 0.0018 przy 1k / 16k / 49k, top-1 96.9–99.2%, PPL 8.91 vs 8.92.
  - Decode +14% przy 28k (3090).
  - Słabe punkty podane uczciwie: przy 159k model raz chybił dokładny lookup wśród prawie identycznych rekordów; matematyka 15/20 vs 18/20, ale to porównanie nieczyste.
  - Liczby fidelity pochodzą z portu Python, nie z Zig.
- **Intel Arc Pro B70 (#802):** 27B GPTQ int4.
  - Plain 34.9 tok/s. Z DFlash2 142–165 code, 90 chat.
  - llama.cpp na tej samej karcie: SYCL 27.6, Vulkan 17.0 (Q4_0).
  - Prefill bf16 2049 tok/s; opcja W4A8 2757; W4A4 na wagach rotowanych Hadamardem 3022.
  - Sprzętowo nieprzenośne (XMX). W4A8 to dokładnie to, co już mamy (MMQ int8).
- **#790:** natywny 27B przy 4 strumieniach dzieli rundy kopiami zamiast drzewami DFlash2: 2.91 vs 5.42 tok/rundę. Dotyczy wielu strumieni, nie nas.

### 2.3 MoE decode (LFM2.5-24B-A2B, launch-bound)

- **LFM2.5-24B-A2B na Metal (#820 issue, PR-y #821/#822/#823, BlivionIaG, M4 Pro 48 GB, otwarte).** To pierwsza zewnętrzna implementacja naszego modelu poza llama.cpp i mlx-lm.
  - **Decode MoE w 4 dispatchach** (`refs/pr/822:zig/src/families/lfm2/forward.zig:213-234`): `route_logits` → `route_select` → `encodeTwinGlu` (gate+up+SwiGLU, indeksowane pickami) → `encodeTwinIndexed` (down).
  - Combine ekspertów (ważenie i residual) wchodzi do **normy następnej warstwy** (`forward.zig:51-62`, `lfm2_combine_norm`).
  - Warstwa conv to in_proj → conv → out_proj. Razem ok. 9–10 dispatchy na warstwę, wobec naszych 8 launchy. **Strukturalnie nie są dalej niż my.**
  - Prędkość (4-bit, ich pomiary):

    | | TensorFold | mlx-lm |
    |---|---|---|
    | Decode po 2k, in-process | 124.5 | 115.8 |
    | Decode po 32k | 86–88 | 79 |
    | Decode serwowany | 129.1 | 102.9 |
    | Prefill 2k | 1304 | ≈ to samo |
    | Prefill 131k | 607 | 610 |

  - [WNIOSEK] Szacunkowa frakcja pasma: ok. 1.5 GB aktywnych bajtów × 124.5 ≈ 190 GB/s z 273, czyli ok. 68%. U nas 1.8 GB × 244 ≈ 440 GB/s z 960, czyli ok. 46%. Różnicę tłumaczy koszt granicy kernela (u nas 2.5 µs × 416), nie lepsze GEMV.
  - **Spekulacja n-gram na tym modelu jest bitowo dokładna.** Drafted == plain na 3/3 promptach. Akceptacja 216/216 na jednym promptcie, 10/30 na drugim, trzeci bez draftów.
  - Koszty okien 1..16 wierszy są mierzone przy starcie (`backend.zig:56-83`, najszybszy z 3 po rozgrzaniu zegarów). Rundy plain konkurują z draftowanymi (`plain_guard`, `backend.zig:53`). Tabeli kosztów nie opublikowano.
  - Rollback conv przez snapshot na wiersz (`state.zig`, `snapshots`). Nasz T1 (lagged conv) jest lepszy.
  - Fidelity wobec mlx-lm (NLL, 6 komórek): natywny czasem wyżej, maksymalnie +0.0138.
- **Nemotron CUDA, pojedynczy wiersz decode („loads in flight”).**
  - Diagnoza (#627, jschmied 10-14): przy 1 wierszu natywny CUDA przegrywał z przechwyconym Triton o 0.35 ms/krok. Gap zamyka się przy 4 wierszach.
  - Na launch: router 16.4 vs 7.2 µs, topk 7.0 vs 3.1, add_moe_norm 8.9 vs 3.7, attn_chunk przy 1 wierszu 18.7 vs 11.6. Łańcuch boczny MoE (router → topk → plan → eksperci) jest ścieżką krytyczną.
  - `37da3ce8` (w 1.0.9, `CHANGELOG.md:73`): suma MoE ładuje 8 slotów przed dodawaniem; scan ładuje wejścia wszystkich kroków do LDS przed krokami; atencja wielowierszowa prefetchuje kafel. Decode +1.9–2.4%; +3% przy 56k i +5% przy 112k. Kolejność sum bez zmian, bitowo.
  - #833 (otwarty): router liczy blok po 16 ekspertów, a wszystkie loady 16 B idą naraz. Router 16.4 → 9.0 µs, topk 7.0 → 4.3, add_moe_norm 8.9 → 5.5. Krok bez draftów **9.544 → 9.293 ms (−2.6%)**, bitowo.
- **Kalibracja kosztów okna dla MoE** (`0e081cfe`, `CHANGELOG.md:66`):
  - Okna mierzone na własnym łańcuchu głowicy MTP zapętlały się („the river bank, the river…”). Powtórzone tokeny dzielą ekspertów, więc okna 8–11 wierszy wychodziły **o 7–10% tańsze** niż w prawdziwym dekodowaniu.
  - Teraz draftami w oknie są kolejne tokeny prawdziwego tekstu. Tabela zgadza się z dekodowaniem do 2.8%.
- **Prefill MoE w passach po 4096 wierszy** (#720, `CHANGELOG.md:62`): każdy pass czyta ekspertów raz na 2× więcej wierszy. Przy 8/16/32/64k: **+7.2 / 6.8 / 6.3 / 5.4%** (GB10).
- **Background prefill dla MoE** (`c724dd9d`, `CHANGELOG.md:65`):
  - Startuje dopiero po 150 ms bezczynności, w chunkach ≤ 256 wierszy, i ustępuje nowemu żądaniu.
  - Powód: „on a MoE every prompt chunk reads most of the experts' weights, so even a 20-row pass held a GB10 for about 45 ms”.
- Nemotron trzyma shared expert na strumieniu bocznym (fork/join, `cuda_forward.zig:17-18,299-300`). LFM nie ma shared experta, więc to nie ma zastosowania.

### 2.4 Inne: kernele, numeryka, metoda

- **Mutacja ukryta przez dane jednostajne** (#833): odwrócenie łańcucha sumy kwadratów w `add_moe_norm` przechodziło test glue na wejściach jednostajnych, nawet przy 2×4096 wierszach. Wyszło dopiero na 2048 wierszach log-uniform (2^-8..2^8).
- **Tokenizer z cache segmentów** (#767, `CHANGELOG.md:69`): czas serwera przed passem promptu 12.6 → 1.6 ms przy 12k tokenów, 41.5 → 2.3 ms przy 35k.
- **Liczba kafli jako stała kompilacji** w promptowych ekspertach NVFP4 (#805, `CHANGELOG.md:42`): znika gałąź na kafel, prompt +4–7.5%.
- **Wspólne normy CUDA** (#736/#796): 1/sqrt jako IEEE div+sqrt (nie approx). Normy gated przy rozmiarach decode na blokach 32-wątkowych.
- **Metoda.** Lean check (pliki ≤ 600 linii, komentarze jednoliniowe) i goldeny serwera są w CI PR-ów (`94ab8f8a`). Liczby kontrybutorów dalej są cytowane jako ich („We have not re-run them”, #802).

## 3. Co to zmienia w naszych wcześniejszych wnioskach (tensorfold/README.md)

| Wcześniej | Teraz |
|---|---|
| „Własne kernele HIP TensorFold: nie przenosić” (W7800 ok. 49% pasma) | **Bez zmian.** Nic nie weszło do `main`, brak nowych liczb 27B na gfx1100. Nowe mikrooptymalizacje (#813: scan zamiast pętli wątku 0) nie dotyczą naszego LFM: llama.cpp `mmvq_id` dla 1 tokenu nie planuje tras, a top-k mamy w kernelu z ostatnim blokiem. |
| Drzewa nad GDN możliwe (stany węzłów w rejestrach), ale dziś się nie opłacają | **Tańsza implementacja (delta log, #836):** gałąź = stan bazowy plus aktualizacje rzędu 1 z logu przodków, w istniejącym kernelu łańcucha. Koszt eksperymentu z bocznymi liśćmi MTP spada, opłacalność bez zmian: kolumna verify ok. 1 ms, a na Nemotronie łańcuchy wygrywały z drzewami. |
| S4 lagged state (nasze #1) | Zrobione u nas. Delta log daje wariant replayu bez redukcji `S·k`/wyjścia (§4, #8). Mały zysk. |
| Głębokość wyceniana kosztem (#5): +6–7% u nich | U nas T2 równo albo gorzej (NOTES 2026-10-14). Nowa pułapka dotyczy **tylko MoE**: kalibracja na powtórzonych tokenach zaniża koszt o 7–10%. Dla gęstego Qwena bez znaczenia, **dla n-gramów na LFM krytyczne**. |
| Background warm pass (#6) | Teraz także na CUDA, z regułami dla MoE: start po 150 ms bezczynności, chunki ≤ 256, ustępowanie. Wartość dla TTFT bez zmian, dochodzi gotowa polityka dla LFM. |
| MoE launch-bound: lewar w fuzjach | Spójne z nami. W tej delcie głównym lewarem TensorFold przy 1 wierszu jest **latencja pojedynczego kernela** (wszystkie loady w locie przed zależnymi sumami): −0.25…0.35 ms/krok na GB10. U nas liczy się tylko czas ponad ok. 2.5 µs na granicę (§4, #2). |
| Atencja decode przy długim kontekście | Konkretny przepis z #746 (§2.2). Wzmacnia nasz plan instancji kvq dla q8_0 w LFM (round2 §4). |
| KV 4-bit | #799 daje niezależne liczby: 4-bit z Hadamardem ma KL 0.002–0.006 wobec bf16 do 49k. To argument do decyzji użytkownika q4_0 vs q8_0 dla LFM (q8_0 kosztuje u nas +30% przy 98k). Decyzja należy do użytkownika. |
| Bramka jakości: KLD / greedy | **Uzupełnić:** KL/NLL nie łapie realnych błędów kernela (#608). Dla każdej zmiany niebitowej potrzebny jest test per kernel z referencją i mutacją. Testy fuzji powinny używać danych log-uniform (#833). |

## 4. Eksperymenty dla nas, ranking według oczekiwanego zysku

| # | Eksperyment | Model / gdzie | Zysk [SZACUNEK] | Koszt | Ryzyko | Pomiar |
|---|---|---|---|---|---|---|
| 1 | **Prefill LFM z większym `-ub`** (1024/2048/4096). Przy ub 512 każdy z 64 ekspertów dostaje średnio ok. 32 wiersze, więc MMQ chodzi na wąskich kaflach. TensorFold #720: 2048 → 4096 daje +5–7% na MoE 128 ekspertów | `run-llm.sh lfm`, llama-bench `-p 4096,16384 -ub ...` | prefill **+5–15%**, decode 0 | 15 min | VRAM (19.3 GB przy 131k; dla Qwena ub 2048 dało OOM) | llama-bench pp + `rocm-smi` VRAM przy ctx 131072 |
| 2 | **Długi kontekst LFM (KV q8_0):** instancja q8_0 `flash_attn_ext_kvq` albo bitowy wariant vec z 4 głowami Q na blok (round2 §4), wg przepisu #746: (a) chunki kluczy dobrane tak, żeby było ≥ ok. 150 wave'ów w locie na 96 CU; (b) prefetch 2 kafli; (c) loady partiali w combine wydane przed foldem | `fattn-kvq.cu`, `fattn-vec.cuh` | 98k: **−1.1 ms (+19%)** wersja niebitowa, ok. połowa w wersji bitowej; 32k −0.3 ms; krótki kontekst 0 | 2–4 dni | numeryka (wersja WMMA f16). Wymaga testu per kernel z mutacją, nie tylko KLD | llama-bench tg przy d 0/8k/32k/98k; test-backend-ops vs CPU f64; logit hash dla wersji bitowej |
| 3 | **„Loads in flight” w małych kernelach decode LFM:** `norm_router_topk` (4.92 µs × 38), `flash_attn_ext_vec` (8.55 × 10), `rms_norm_mul_rope` (3.07 × 20), `set_rows q8_0` (2.72 × 20). Wszystkie loady do rejestrów przed zależnymi sumami, ta sama kolejność sum. Pętle o stałej liczbie iteracji z `#pragma unroll`. W ISA sprawdzić łańcuchy `global_load` → `s_waitcnt vmcnt(0)` | `topk-moe.cu` (fuzja 0053), `norm.cu`, `fattn-vec.cuh` | Liczy się tylko nadwyżka ponad ok. 2.5 µs na granicę: ok. 90 µs w routerze i ok. 60 µs w atencji. Realnie **−50…100 µs/token (+1.2–2.5%)** | 1–2 dni | niskie (bitowo, logit hash) | rocprofv3 µs/wywołanie, ab.sh tg128 |
| 4 | **N-gram / copy spec dla LFM (kod i edycje):** TensorFold pokazuje, że na tym modelu jest bitowo dokładne, a rundy plain konkurują z draftowanymi. Tabelę kosztów weryfikacji k = 1..8 kolumn mierzyć na **prawdziwym tekście**, nie na powtórzeniach (lekcja `0e081cfe`). Draft tylko wtedy, gdy `E[tok]/cost(k)` > plain | `common/ngram-*`, `speculative.cpp`; multi-kolumnowy `mmvq_id` (sprawdzić, czy istnieje dla 2–8 kolumn) | kod i edycje: **+30–100%** na turach kopiujących (TensorFold: 216/216 na jednym promptcie); czat 0, jeśli jest guard | średni | regres czatu bez guardu; k kolumn czyta do 4k różnych ekspertów na warstwę | offline: akceptacja n-gramów na logach; potem tabela kosztów LFM k = 1..8 |
| 5 | **Jeden zbiorczy upload wejść grafu** (12 kopii ok. 32 µs/token, round2 §5). TensorFold #818 robi „host inputs staged in one upload” | `ggml-backend` async inputs (łatka 0029) | **−25 µs/token (+0.6%)** LFM, Qwen ok. 0.1% | niski | niskie | rocprofv3: liczba `copyBuffer`, tg128 |
| 6 | **Background warm pass po odpowiedzi** z regułami MoE z TensorFold: start po ≥ 150 ms bezczynności, chunki ≤ 256 wierszy, ustępowanie nowemu żądaniu | `server-context.cpp`, idle slot | TTFT tury następnej **−50%** (TensorFold #723), decode 0 | średni | niskie | `cache_bench.py`, TTFT 2. tury |
| 7 | **GDN replay z delta logu** (S4): logować `delta`, `g`, `k` przy verify; replay `pk` wierszy jako same aktualizacje rzędu 1, bez `S·k` i wyjścia. Najpierw zmierzyć udział prefiksu replay w kernelu GDN | `gated_delta_net.cu` (łatki 0033–0036) | **0…0.3 ms/krok (do +1%)**, tylko jeśli replay jest dziś widoczny w profilu | 1 dzień | niskie (ta sama sekwencja operacji na stanie, bitowo) | rocprofv3 GDN µs przy pk = 0 vs pk = 4 |
| 8 | **Higiena testów:** dane log-uniform (2^-8..2^8) w nowych przypadkach test-backend-ops dla fuzji z redukcjami. Mutacja per nowy kernel (np. odwrócony łańcuch sumy musi oblać) | `tests/test-backend-ops.cpp` (NORM_ROUTER_TOPK, MOE_DOWN_REDUCE, SHORTCONV) | 0% prędkości, mniejsze ryzyko cichych zmian kolejności | niski | brak | test musi oblać na mutacji |
| 9 | **Czas tokenizacji w llama-server** dla promptów 30k/94k (każde żądanie tokenizuje całość). Jeśli > 20 ms, cache segmentów jak w #767 | `server` | TTFT −0…40 ms na turę | niski (pomiar) | niskie | log timings serwera |
| 10 | **Qwen, długi kontekst:** liczba wave'ów w locie w `fattn-kvq` przy 94k (dziś `nsplit = 2·nsm/(ntiles·nblocks_z)`, `fattn-kvq.cu:541`) i loady w `flash_attn_combine_results` przed foldem | `fattn-kvq.cu` | +0…2% przy 94k | niski | niskie | tg przy 94k. Uwaga: heurystykę splitu kvq sprawdza też agent RepoVllmXpu |

Kolejność: najpierw #1 (15 min), potem #3 i #5 (tanie, bitowe), dalej #2 (największy zysk przy długim kontekście), #4 (po offline'owej akceptacji n-gramów), #6. #7 tylko po pomiarze.

## 5. Krytyka

- **Większość delty to produkt, nie prędkość:** aplikacja `app/` (ok. 1440 plików), bezpieczeństwo i parsery Cortheon, mieszane szerokości oQ na Macach, Windows, Intel XPU, DeepSeek-V4.1 (ok. 30 PR-ów jayleaton/akol1).
- **HIP stoi.** Stos slice'ów rośnie (9 nowych), a merge nie ma od ponad tygodnia. Liczby HIP dla 27B są nieaktualne i słabe wobec naszego forka. Nowe liczby gfx1100 dotyczą Flash Next przy TP2/TP4, czyli nie naszego przypadku.
- **Liczby pochodzą głównie od kontrybutorów:** GB10, 5090, M4 Pro, B70, każda konfiguracja z jednej maszyny. ashhart ich nie powtarza. Tok/s na 5090 są liczone z timingów 0.01 s (±0.5). #833/#627 to jeden GB10 z Triton jako punktem odniesienia.
- **LFM2 na Metal:**
  - tylko M4 Pro; spekulację sprawdzono na 3 promptach po 256 tokenów;
  - brak opublikowanej tabeli kosztów okien i brak porównania z llama.cpp;
  - baza mlx-lm jest słaba; NLL natywny bywa wyższy od obu wariantów mlx-lm.

  Dla nas to dowód wykonalności (spekulacja na LFM jest dokładna), nie dowód zysku.
- **#799:** fidelity pochodzi z portu Python, bramka Zig dopiero zaproponowana. Wynik matematyki 15/20 nie jest wyjaśniony.
- **#802:** porównanie z llama.cpp na innym kwancie (Q4_0 vs GPTQ int4). Prefill zawdzięcza XMX, nie metodzie.
- **Kontrakt bitowy dalej kosztuje.** #608 pokazał, że „bit w bit z Triton” jest nieosiągalne bez kopiowania układów wątków jednej wersji kompilatora. Projekt przechodzi więc na granice FP64 per kernel. To w praktyce zbliża go do naszej polityki „bitowo albo KLD plus test per kernel”.

## 6. Werdykt

**Średnia** dla LFM2.5, niska dla Qwen3.8: w samym `main` nie ma nic dla HIP. Wartość jest w otwartych PR-ach i komentarzach:
- przepis na atencję decode przy długim kontekście (#746);
- „loads in flight” jako lewar przy 1 wierszu MoE (#771/#833);
- pułapka kalibracji kosztów okien dla MoE;
- passy promptu MoE (#720);
- dowód, że spekulacja n-gram na naszym LFM2.5 jest dokładna (#822).

Żadna z tych rzeczy nie zmienia kolejności naszego planu dla Qwena.
