# 32a. Project Maya v1.1.17, Strata po `e88ee39d` (0.2.1–0.2.1.3) i Gyro-S: delta

Data: 2026-10-20. Praca tylko na CPU (bez GPU, chmury i subagentów). Robię wyłącznie deltę względem poprzednich triaży: Maya v1.1.16 `abc09c7` (R21g + ZRODLA), Strata `e88ee39d` (R21n), Gyro HF `aa0a0c3e` (R21n).

Źródła:
- Maya: klon `~/qwen-opt/research-src/project-maya`, tagi `v1.1.16` `abc09c7` → `v1.1.17` `8d9a9b5` (2026-10-20 06:33). Jest już też `v1.1.18` `14bbeb3` (10-20 16:52).
- Strata: klon `~/qwen-opt/research-src/strata-020`, `e88ee39d` → `origin/main` `cbfd5b92` (v0.2.1.3). Release notes z API GitHub.
- Gyro: karta HF `aa0a0c3e` → `05758344` (10-19 22:06) oraz PR halo-box/strix-llama.cpp #195.

## TL;DR

1. **Maya v1.1.17 nie ma nowych kerneli dla naszego stosu.**
   - „1000+ tok/s prefill DeepSeek na 3090” to naprawa regresji, nie nowa technika. Grupy TP zapadały się do szerokości 1, bo bloki 256 wartości u ekspertów nie dają się podzielić. To wyłączało chunki 8192, więc prompt szedł oknami po 16 tokenów (×10.2: 99 → 1010 tok/s).
   - Do skopiowania są dwa wzorce systemowe (pkt 2 i 3).
2. **Kopia checkpointu stanu w tle, nakładana na następny prompt** (Maya #253): bezstratnie, bo to tylko kopie, i bezpośrednio pasuje do naszego zmierzonego kosztu. Mamy 2 checkpointy po ~94–104 ms na każdy prompt (`2026-10-18-hak-mtp-i-checkpointy`). **Sufit to −150…−200 ms TTFT na każdą turę**: −8% przy 2k i do −25…−30% przy krótkich turach agenta po trafieniu w cache `[INFERENCE]`.
3. **`--spec-follow` (Maya v1.1.18 #266)**: A/B prędkości na wymuszonej, identycznej kontynuacji. Drafty liczą się tylko wtedy, gdy zgadzają się z plikiem tokenów. Usuwa to szum akceptacji z przeskoków przy niemal-remisach (near-tie) przy porównaniach zmian, które nie są bitowo identyczne (inne kwanty, CUDA vs ROCm, różne karty w katalogu). Nie mamy takiego narzędzia.
4. **Strata 0.2.1.x (128 commitów bez merge'y)**:
   - silnik ma +964/−57 linii w 26 plikach, w tym testy;
   - dla dyskretnego gfx1100 nic nie zmienia się domyślnie;
   - ciekawe jest tylko odkrycie, że MES kładzie 2 zajęte kolejki na ten sam potok obliczeniowy (prompt −13% w ~1/3 świeżych startów na R9700). U nas to tani test bimodalności świeżych startów;
   - reszta to aplikacja, Docker, `strata bench run` (standard-v1) i drobne rzeczy dla słabszych PC (iGPU 780M, rdzenie LP-E, sonda dysku, mniejsza rezerwa VRAM).
5. **Gyro-S:**
   - wagi bez zmian (karta `05758344` dopisuje tylko silniki);
   - Gyro jest **tylko dla Qwen3.8-Flash-Next** (arch `qwen4exp`). Dla 27B nie istnieje, a enkoder jest niepublikowany;
   - mainline i nasz fork tego nie ładują (typy 143–149, `GGML_TYPE_COUNT = 43`);
   - nowość: **PR halo-box/strix-llama.cpp #195** (+5098/−3, CPU/Vulkan/HIP), czyli gotowa implementacja w llama.cpp do ewentualnego portu;
   - KLD Gyro-S 0.401 (ref Q8_0) wobec 0.012 naszego 27B UD-Q4_K_XL (ref BF16, ten sam protokół agentionai): ~33× gorzej;
   - **nie dla XTX (24 GB) ani dla Maców 16 GB.** Ma sens tylko jako pozycja katalogu dla 32 GB (5090, R9700).

## 1. Project Maya v1.1.16 → v1.1.17

Git: 19 commitów, 79 plików, +6552/−746. **17 commitów społeczności ✓** (`git log --format=%an v1.1.16..v1.1.17`). Pozostałe 2 to właściciel: #295 „Peasant Smith” (+3633/−668, cała praca DeepSeek, kary i poprawki) oraz commit wersji.

### 1.1 Tabela twierdzeń

| Twierdzenie | Źródło | Werdykt | Dowód |
|---|---|---|---|
| DeepSeek: prompty w chunkach 8192, 7×3090 Maya-S, 32K: 99 → 1010 tok/s (#279 waxinz) | release notes | **częściowo** | Mechanizm potwierdzony w kodzie: `src/ds4/ds4_model.cu` (#295, komentarz „the experts' blocks took the groups' width down to 1 (a 256-value type's: Maya's quants), which left every prompt in windows of 16”). To **naprawa regresji**, nie nowa technika: TP dla 256-wartościowych bloków spadało do 1 GPU na grupę warstw, a to wyłączało chunki. Sam #279 to 11 linii ostrzeżenia (`40c8582`); poprawkę zrobił właściciel w #295. „7×3090” to podział warstw (pipeline), nie TP. Liczba niepowtarzalna u nas (×10.2 = 1010/99). |
| „Long prompts read each expert once”: 16K czyta 264 GB zamiast 736 GB | release notes, #295 | **potwierdzone w kodzie, liczby niesprawdzone** | Tryb layer-major (`DS4_LAYER_MAJOR`, `DS4_LAYER_CACHE_MB`): warstwa po warstwie przez wszystkie chunki, stan chunku w pamięci hosta, cache warstwy w RAM. Stosunek 736/264 = 2.79×, co pasuje do ~3 chunków `[INFERENCE]`. Dotyczy tylko ekspertów czytanych z SSD/RAM. |
| Maya-S DeepSeek jako jeden zestaw 6 plików, 339.5 GB (było 381), Engram w Q6_K „bez mierzalnej straty” | release notes | **rozmiar potwierdzony; jakość częściowo** | HF `peasantsmith/DeepSeek-V4.1-Flash-1017-Maya-GGUF` @ `276e0bad`: 6 plików GGUF = 339.478 GB ✓. KL 0.087 / top-1 93.5% „jak wcześniej w granicach szumu”, ale README tego samego tagu podaje 92.6% (`README.md:54`), a ZRODLA dla 1.1.16 KL 0.12. Liczby nie są spójne między wydaniami, a protokół (held-out, długość) nie jest podany. |
| EXL3 3.5 bit, TP do 8 GPU, swapy cache na wątkach (#276 needmorevram) | release notes | **częściowo (atrybucja)** | PR #276 **niezmergowany** (`merged=false`, API); treść weszła w #295 właściciela. `DS4_CACHE_THREADS` domyślnie 1, bo „4 measured no faster” (komentarz w `ds4_model.cu`). |
| Pomijanie lekkich ekspertów (opt-in) | release notes | **potwierdzone, stratne** | `MAYA_DS4_DISK_SKIP_W`: komentarz w kodzie „CHANGES THE ANSWERS”. Odpowiednik Xolotl (R28). Dla nas nie, bo łamie bezstratność. |
| GLM: repetition/frequency/presence penalty na każdej ścieżce dekodu, także w draftach i przy T=0 (#273) | release notes, #295 | **potwierdzone** | `include/strata/kernels/sampler.hpp`: wiersz t okna weryfikacji liczy karę z historii i draftów 1..t. Testy `test_penalties_greedy`. Bez kar tokeny są identyczne jak wcześniej (gałąź `penalty_last_n <= 0`). |
| GLM Volta: routowani eksperci promptu jako GEMM FP16 cuBLAS, 27K: 41.3 → 33.4 s (#254) | release notes | **częściowo** | Komentarz w commicie `9b1da20` podaje inne liczby: 39.7/39.9 → 31.7/31.8 s (−20%). Zmienia bity: KL 0.015 vs MMQ. Tylko sm_70, bo Turing+ ma MMQ na int8 tensor cores. |
| Rekurencja KDA na 4 blokach na głowę (#199): kda_rec 4.7/5.1 → 3.5 s | commit `71caf54` | **potwierdzone (kod); dla nas już jest** | Podział po niezależnych kolumnach wartości, różnice do 1e-7. **Nasz GDN już dzieli kolumny po `blockIdx.z`**: `~/llama-master/ggml/src/ggml-cuda/gated_delta_net.cu:67,388` (`grid(H, n_seqs, S_v/(cols_per_warp·num_warps))`). |
| Krótkie tury: batched path od 8 tokenów zamiast 32 (#232) | commit `38e9a6f` | **częściowo** | Z komentarza w kodzie: 1041/648/521 → 488/405/577 ms. Trzecia tura **pogorszyła się o 11%**. Średnia −33% przy n=3 i dwóch rundach, bez rozrzutu. |
| Snapshot jako checkpoint, gdy następna tura zaczyna się zaraz po nim (#253) | commit `95ed276` | **potwierdzone (kod)** | `ckpt_save_snapshot`: kopia stanu KDA do RAM na **wątku pobocznym, w trakcie następnego promptu**. Snapshot zostaje nienaruszony do następnego `snapshot_save`, który czeka na kopię. Bez tego edycja ostatniej wiadomości przy 13.5K liczyła wszystko od nowa (20.8 s). Wyłącznik `STRATA_GLM_CKPT_TURN=0`. |
| CPU-expert deferral +21–26% dekodu na V100 (#252) | release notes | **potwierdzone, stratne** | Komentarz „LOSSY” (`f45c32c`). Nie dla nas. |
| 17 PR społeczności | release notes | **potwierdzone** | Lista w §1.2. |

### 1.2 Lista 17 PR społeczności i trafność dla nas

| PR | Autor | Co | Dla nas |
|---|---|---|---|
| #279 | waxinz | ostrzeżenie o oknach 16 tokenów | wzorzec UX: **ostrzegaj przy starcie, gdy szybka ścieżka jest wyłączona i dlaczego** |
| #254 | merbanan | Volta: ciężcy eksperci FP16 cuBLAS | nie (sm_70, MoE) |
| #233 | merbanan | scorer indeksera DSA na FP16 tensor cores | nie (DSA) |
| #215 | merbanan | wspólny ekspert w podbatchach 2048 | nie (MoE) |
| #199 | merbanan | rekurencja KDA ×4 bloki na głowę | już mamy (podział kolumn w GDN) |
| #232 | merbanan | batched path od 8 tokenów | słabe; nasz próg MMVQ/MMQ jest osobno strojony (24n/24r) |
| #253 | merbanan | snapshot → checkpoint w tle | **tak: wzorzec do async checkpointów (§4, nr 1)** |
| #252 | merbanan | deferral CPU-ekspertów, affinity (stratne) | nie |
| #197 | merbanan | okno weryfikacji DFlash na jednym węźle NUMA | nie (jedno gniazdo) |
| #236 | handmade0octopus | sloty rozmów zaparkowane w RAM | już mamy (`--cache-ram`, `LLAMA_SERVER_CACHE_SHARE_MIN`, 16f) |
| #262 | chenyb999-zhcn | grupowe WMMA dla ekspertów promptu na Volcie | nie |
| #250 | cryptedy | zwalnianie modelu po bezczynności | produkt (Podkręt: przełączanie Qwen ↔ LFM) |
| #269 | eugenrepp | odczyty GPU z sysfs amdgpu | nie |
| #249 | rkarp | VS Build Tools 2026 | nie |
| #183 | izabera | HIP > 2 GPU | nie |
| #255 | andrewprock | build HIP tylko dla wybranych archów | już mamy (buildfarm 25) |
| #264 | sociolog | testy EXL3 względem exllamav3 | wzorzec: test z niezależną implementacją referencyjną ([[lekcja-bit-exact-wobec-siebie]]) |

Prefill chunking, sampler i długie prompty: z PR społeczności dla nas liczą się tylko #253 (checkpoint) i #279 (ostrzeżenie). Kary w draftach są w #295 właściciela (§4, nr 3).

### 1.3 Bonus: v1.1.18 (`14bbeb3`, 10-20, poza zakresem zlecenia)

- **#266 `--spec-follow`**: każde żądanie dekoduje dany ciąg tokenów zamiast własnych wyborów. Ścieżki MTP/DFlash2 zachowują tylko drafty zgodne z tym ciągiem. Licznik `glm follow:` mówi, ile razy własny wybór modelu by się różnił. Po co: „near-tie flip changes the text and with it the draft acceptance and the speed” (`docs/SETTINGS.md`, `MAYA_GLM_SPEC_FOLLOW`).
- #270: przy dwóch GPU bez NVLink czekająca karta liczy część MoE. #261: P100 sm_60 się buduje (to poprawia nasz `[INFERENCE]` z R21g o braku kompilacji, bo teraz jest obsługiwane). #217: Responses API.
- Maya wciąż nie ma gęstego modelu. Na XTX są tylko testy kerneli EXL3 (`CHANGELOG.md:153`), bez pomiaru prędkości.

## 2. Strata `e88ee39d` → 0.2.1.3 (`cbfd5b92`)

Git: 150 commitów (128 bez merge'y: Niko1221 123, społeczność 5), 377 plików, +19 591/−1 568. Podział: aplikacja `apps/` +3 989, testy +4 267, docs +702, **silnik (`src include cmake sycl metal third_party`) +964/−57 w 26 plikach** (z testami jednostkowymi). Reszta to CLI, benchmark, setup i serwer. Wydania: 0.2.1 (10-20 09:40, silnik 0.1.46), 0.2.1.1 (Windows Terminal), 0.2.1.2 (Strix Halo Windows, silnik 0.1.46.1), 0.2.1.3 (Terminal 0.1.46.2).

| Twierdzenie (0.2.1) | Werdykt | Dowód / uwagi | Dla nas |
|---|---|---|---|
| R9700/RX 9000: kolejki GPU otwierane w stałej kolejności; bez tego 10/32 świeżych startów czyta 4K < 2000 tok/s (szybki start ~2290), z poprawką 0/32 | **potwierdzone (kod), gfx12 only** | `b35a9816`, `3f1fa67f` `src/program/generate.cpp`: MES przypisuje kolejkę do potoku przy pierwszej pracy; dwie zajęte kolejki (obliczenia i staging ekspertów) na jednym potoku dają −13% promptu. Rozwiązanie: 2 strumienie `nn` na wątku głównym przed innymi wątkami. Przy 5 kolejkach (`nnnnh`) dekod spada o 2–3.6%. Domyślnie tylko gfx1200/1201 na Linuksie (`STRATA_HIP_QUEUE_PRIME`). | **test bimodalności świeżych startów na XTX** (§5 E2). Nasz upstreamowy decode jest jednostrumieniowy (`common.cuh:1715` tworzy strumienie leniwie), ale GPU verify, MTP i async checkpoint mogą dołożyć kolejkę. |
| Radeon 780M (gfx1103, Linux): „matrix-core prompt set” domyślny, prompt ×1.60 (1K) / ×2.03 (4K), dekod bez zmian | **częściowo** | `eb7eac25`, `arch_defaults.cpp`. To zestaw 5 przełączników zmieniających bity (WMMA w uwadze, GEMM FP16 128×256, …). Właściciel raz go wycofał do opt-in (`dab7ee72`), potem włączył dla 780M. Tożsamość sprawdzona tylko na greedy ids 6/6 par. Dyskretne gfx1100 dostają nic (`igpu_default_env`). | nie (nasz prefill gfx1100 to MMQ/rocWMMA llama.cpp); ewentualnie katalog: mini-PC 780M |
| Strix Halo: tabela hipBLASLt domyślnie, prompt 250.9 → 528.9 (×2.11) | **niepotwierdzone przez nich** | „We have no Strix Halo and did not repeat it” (release notes). Zmienia bity (KL 0.016 na R9700). Na gfx1201 +1% promptu i −2% dekodu, więc tam opt-in (`hipblaslt_tuning.py:29-36`). | nie: nasze kwanty idą przez MMQ, hipBLAS(Lt) dotyczy tylko GEMM f16/bf16 |
| Dwie karty NVIDIA, kilka żądań: jedna grupa seryjna, +12…16% agregatu | potwierdzone (ich A/B, 5 par) | `f680a80d`; gorzej (−10%), gdy eksperci siedzą w CPU | nie (jeden użytkownik, jedna karta) |
| Karta bez ekranu: rezerwa VRAM 512 MiB zamiast 1536 | potwierdzone (kod); prędkości nie mierzyli sami | raport #3215: 80 vs 50 tok/s, ale tylko przez to, że rezerwa zjadała cache ekspertów | produkt: **reguła „fit” Podkręta** (ile VRAM rezerwować na kartach bez ekranu) |
| Pakiety `experts.bin` (Linux): prefetch I/O i bramka dekodu, gdy page cache mieści ≥55% ekspertów: dekod ×1.21–1.38 | potwierdzone (ich A/B, 5/5 par) | `ecf2bdcb`, 3060 12 GB, cgroup 32 GB | tylko dla MoE offload (R28) |
| Sonda dysku (96 × 1 MiB) wybiera page cache albo O_DIRECT (#3237) | częściowo | „Untested on a fast drive”. Na ich dyskach 1.6–3.1 GB/s zawsze wygrywa cache | nie |
| Rdzenie LP-E (`cpu_lowpower`) liczone jako E: 255H 15 → 10 workerów, raport −35% | **niepotwierdzone** | „We have no such CPU and ran unit tests only” | nie (dekod na GPU) |
| Rozgrzewka hipBLAS tylko przy jednakowych archach (#3204) | potwierdzone (kod) | `4e76d6c9` | nie |
| Stopka czatu = tokeny wyjścia / czas dekodu (było „632 tok/s” przy 50–75) | potwierdzone | release notes | **produkt: ta sama pułapka w UI Podkręta** (tury z tool-call) |
| `strata bench run` standard-v1: 34 zamrożone żądania + SHA-256, T=1, thinking, short/4k/16k ×3, sanity 12, concurrency | potwierdzone (kod) | `strata_cli/bench_standard.py:1-60`. Profil tylko `qwen3.8-flash-next-thinking`, `BENCHMARK_PROTOCOL.md` wciąż szkic. Prędkości z `timings` serwera, TTFT z zegara klienta. | produkt: format wyników społeczności dla katalogu; nie porównuje 27B |
| Harness i Terminal (zakres zlecenia) | — | Po `e88ee39d`: tablica zadań (Schedule/Board), `user_args` nie są nadpisywane, przełącznik MTP, poprawki Windows. Rdzeń harnessu (`dsh`) i `strata connect` opisał już R21n §1. | konkurencja UX, bez zmian względem R21n |

**Pomysły kernelowe i offloadowe przenośne na nasz stos:** brak nowych dla dyskretnego gfx1100 i sm_86/89/120. Jedyna obserwacja o sprzęcie AMD to rozmieszczenie kolejek przez MES.

## 3. Gyro-S: delta i odpowiedzi na pytania

| Pytanie | Odpowiedź | Dowód |
|---|---|---|
| Co się zmieniło od `aa0a0c3e`? | Tylko karta (`05758344`, 10-19). „Files unchanged”, doszły silniki Strata 0.2.0 i strix-llama.cpp oraz wiersz Strix Halo 36.1 t/s (vs 31.7 na forku agentionai, +14%). Z tabeli zaleceń dla kart 16–24 GB zniknęło `--n-cpu-moe N`, zostało tylko „Strata's expert cache”. | `diff` README `aa0a0c3e`/`05758344` |
| Format | Trellis z rodziny QTIP + obrót Hadamarda: TQK6/TQK7 (typy 145/146; 1.625/1.875 bpw) w S, TQ2_T (144) w M, TQP5–7 (147–149) w L. Szczegóły w R21n §2. | R21n; PR #195 (tabela typów) |
| Czy ładuje mainline / nasz fork? | **Nie.** Upstream: „cannot load these files yet” (karta). Nasz fork: `GGML_TYPE_COUNT = 43` (`~/llama-master/ggml/include/ggml.h:433`), arch `qwen4exp` jest (`src/llama-arch.cpp:44`), ale typów 143–149 i `prism.hadamard` brak. W ggml-org/llama.cpp nie ma PR z trellisem (wyszukiwanie GitHub: tylko zamknięty port IQK #19726). | grep, API GitHub |
| Najprostsza droga do portu | **halo-box/strix-llama.cpp PR #195** (zmergowany 10-19 jako `ab062040`, kod Laurenta Zuijdwijka): +5098/−3, 67 plików, typy na CPU (ref + AVX2/AVX-512), Vulkan i **HIP** (dequant, get_rows, mmvq, batched przez mmb BF16 WMMA). Opiera się na upstreamowym `prism.hadamard` (ggml-org #29600), którego nasza baza (10-15) nie ma. Enkodery w `llama-quantize` to zaślepki: „refuses TQ2_T / TQK / TQP targets”. **Nie da się zrobić Gyro z 27B.** | API GitHub PR #195 |
| Jakość vs nasze UD | Karta (ref **Q8_0**, ctx 2048, 60 chunków, held-out 2026): Gyro-S KLD 0.401, top-1 75.3%; UD-Q2_K_XL 0.334 / 76.6% przy 46.63 GiB; AP-Q4_K_XL 0.107. Nasz 27B na tym samym protokole agentionai (ref **BF16**, held-out): UD-Q4_K_XL 0.0117, UD-Q3_K_XL 0.0421 (`wiki/modele/kwanty-gguf.md:23`). Gyro-S ma więc ~34× wyższe KLD od naszego produkcyjnego 27B i ~10× wyższe od 16-gigowego UD-Q3_K_XL. Różne modele, różna referencja (Q8_0 zaniża KLD Gyro), więc porównanie jest tylko co do rzędu wielkości ([[lekcja-kld-protokoly]]). | karta, KB |
| 27B czy tylko Flash-Next? | **Tylko Flash-Next.** agentionai ma dla 27B wyłącznie `Qwen3.8-27B-AP-GGUF`, `Signal-3.8-27B(-GGUF)` i `Qwen3.8-27B-DFlash2-ROCmFP4-FAST-GGUF`, bez Gyro (API HF `?author=agentionai`). | API HF |
| Karty < 32 GB | Wagi GPU 27.64 GiB plus KV, więc na 24 GB się nie mieszczą. Potrzebny cache ekspertów Straty albo offload. Strata sama przypisuje Gyro-S do progu **32 GB RAM+VRAM** (`README.md:159,169`). Na XTX R21n szacował ~50–75 t/s bez MTP, czyli mniej niż nasze 114.8 t/s na 27B. | Strata README, R21n |
| Mac 16 GB | **Nie.** Brak kerneli Metal: „not on Intel Arc or the Mac” (Strata `README.md:162`); PR #195 wręcz wyłącza trellis w Metalu („Metal does not claim the trellis types”). Do tego 27.64 GiB > 16 GB. | jw. |

## 4. Co się do nas stosuje (ranking)

| # | Pomysł | Skąd | Zysk (szacunek) | Wysiłek | Bezstratne? |
|---|---|---|---|---|---|
| 1 | **Asynchroniczny checkpoint stanu GDN.** Kopia D2D do zapasowego bufora VRAM (~150–170 MiB; przy ~960 GB/s to ~0.35 ms), potem D2H na strumieniu kopiującym, nakładana na kolejne ubatche i następny prompt. Wzorzec: Maya #253 (wątek boczny, snapshot nienaruszony do następnego zapisu). | Maya #253 | Dziś 2 × 94–104 ms = **~200 ms na prompt**. Arytmetyka: 2k: 2235 → ~2045 ms (**−8.5%**); 8k: 7876 → ~7686 (−2.4%); tura agenta po trafieniu w cache z ~500 nowymi tokenami (~0.5 s prefill + 0.2 s) → **−25…−30% TTFT** `[INFERENCE]`. Dekod t/s bez zmian. | 1–2 dni (`llama-context` state get + serwer) | **tak**: same kopie; bramka md5 |
| 2 | **`LLAMA_SPEC_FOLLOW=<plik>`** w llama-server: wymuszona kontynuacja; draft akceptowany tylko przy zgodności z plikiem; licznik rozjazdów z własnym argmaxem. | Maya v1.1.18 #266 | Brak wzrostu t/s, ale ma **mniejszy rozrzut A/B** przy zmianach niebitowych: kwanty (E1), CUDA vs ROCm, różne karty w katalogu Podkręta. Akceptacja MTP przestaje zależeć od przeskoków near-tie. | ~0.5–1 dzień | narzędzie pomiarowe |
| 3 | **Kary (presence/repeat) także w drafcie MTP.** Wiersz t ma historię = kontekst + drafty 1..t, jak w Maya #295. Dziś „draft ich nie stosuje, kosztuje tylko akceptację” (16k:64). | Maya #295, Strata #2940 | Warunkowo: tylko gdy klient wysyła kary (karta Qwen zaleca presence 1.5 przy wyłączonym thinking; GGUF LFM ma repeat 1.05). Sufit = odzyskanie spadku akceptacji; najpierw E3. Przy ~3 tokenach na krok spadek akceptacji o 10 pp daje ~−8% t/s `[INFERENCE]`. | 0.5 dnia po E3 | tak (cel bez zmian, zmienia się tylko propozycja) |
| 4 | **Test bimodalności świeżych startów (kolejki MES).** Jeśli wyjdzie bimodalny: wstępne otwarcie 2 strumieni na wątku głównym przed resztą. | Strata `3f1fa67f`/`b35a9816` | Na R9700 −13% promptu w ~31% startów. U nas nieznane; przy jednym strumieniu prawdopodobnie 0 `[INFERENCE]`. | E2: 10 min | tak |
| 5 | Ostrzeżenie przy starcie, gdy szybka ścieżka jest wyłączona (np. GPU verify / topka-path off z powodu flag, `-ub`, kwantu) | Maya #279 | UX/diagnostyka, 0 t/s | godziny | — |
| 6 | Stopka „t/s” = tokeny wyjścia / czas dekodu; rezerwa VRAM 512 MiB na kartach bez ekranu w kalkulatorze „fit” | Strata 0.2.1 | produkt (uczciwe liczby, +~1 GB na kontekst/ekspertów) | godziny | — |
| 7 | Layer-major prefill dla MoE offload (każdy ekspert czytany raz na prompt) | Maya #295 (`DS4_LAYER_MAJOR`) | Tylko linia MoE offload (R28, Flash-Next na 24 GB). Przy `-ot exps=CPU` każdy ubatch przenosi ekspertów przez PCIe: transfer ∝ liczba ubatchy (32K / 4096 = 8× zamiast 1×). Najpierw tani proxy: większe `-ub` (E4). | duży (scheduler llama.cpp) | tak |
| 8 | Port Gyro (strix-llama.cpp #195 + `prism.hadamard` #29600) | strix-llama.cpp | tylko pozycja katalogu „32 GB” (5090/R9700) dla Flash-Next; na XTX nie | 2–4 dni + utrzymanie | nie dotyczy (osobny model) |

## 5. Czego nie bierzemy i dlaczego

- **Chunki DeepSeek 8192 / 1010 tok/s**: to naprawa ich własnej regresji TP przy 256-wartościowych blokach. llama.cpp robi ubatche od zawsze.
- **Rekurencja KDA na 4 blokach na głowę (#199)**: nasz kernel GDN już rozkłada kolumny na `blockIdx.z` (`gated_delta_net.cu:388`).
- **Volta FP16 cuBLAS, WMMA Volta, NUMA, deferral CPU, pomijanie ekspertów, HC/DSA, Engram Q6_K**: inny sprzęt (sm_70), inna architektura (GLM/DeepSeek MoE) albo stratne.
- **#232 (próg 8 tokenów)**: n=3, jedna tura gorsza o 11%; nasze progi MMVQ/MMQ są strojone osobno (24n, 24r).
- **Zestaw promptowy dla iGPU, tabele hipBLASLt (Strata)**: zmieniają bity, dotyczą GEMM f16 i iGPU; nasz gfx1100 jest na MMQ.
- **Gyro-S na XTX / Macu 16 GB**: nie mieści się w 24 GB, nie ma Metala, KLD ~34× gorsze od naszego 27B Q4. Nie da się zrobić 27B w tym formacie (brak enkodera).

## 6. Eksperymenty GPU ≤ 10 min

- **E1 (pomiar przed nr 1):** gałąź `quickwins` (`7369380bf`), `LLAMA_CKPT_TIMING=1`, replay omp (`qw/e3d.jsonl`, 16f). Mierzymy udział checkpointów w TTFT tur z < 1k nowych tokenów.
  - Kryterium: ≥ 10% TTFT mediany tur, wtedy implementujemy nr 1.
- **E2 (kolejki MES):** 10 świeżych procesów na XTX, osobno bez MTP i z MTP. Kolejność: najpierw sama pętla `llama-bench`, potem to samo przez serwer z MTP:
  ```
  for i in $(seq 10); do ~/llama-opt/bin/llama-bench -m ~/models/Qwen3.8-27B-UD-Q4_K_XL.gguf -p 4096 -n 64 -r 1 -fa 1 -o jsonl; done
  ```
  - Kryterium: dwa skupiska różniące się o > 5%. Wtedy prototyp „otwórz 2 strumienie na starcie”. Jeśli rozrzut < 2%, zamykamy temat.
- **E3 (kary vs akceptacja):** serwer topka z MTP, ten sam zestaw 8 promptów (seed stały, T=0 i T=1) w trzech wariantach: `presence_penalty` 0 / 1.5 i `repeat_penalty` 1.05. Porównujemy `timings.draft_n_accepted / draft_n` oraz t/s.
  - Kryterium: spadek akceptacji ≥ 5 pp przy karach, wtedy nr 3.
- **E4 (tylko jeśli linia MoE offload żyje):** Flash-Next IQ3_S, `-ot exps=CPU`, `llama-bench -p 32768 -n 0` przy `-ub 2048` / `4096` / `8192`.
  - Jeśli prefill rośnie ~proporcjonalnie do `-ub`, to transfer PCIe dominuje i layer-major (nr 7) ma sufit ≈ czas_transferu × (1 − 1/n_ubatch).

## Do bazy wiedzy

Proponowane wiersze `wiki/ZRODLA.md`:

| Źródło | Wersja / commit | Data | Raport | Werdykt | Co sprawdzić następnym razem |
|---|---|---|---|---|---|
| Project Maya (github.com/mw00/project-maya) **3×** | `abc09c7` v1.1.16 → `8d9a9b5` v1.1.17 (+19 commitów, 17 społeczności) → widziany `14bbeb3` v1.1.18 | 10-20 | R32a | Bez nowych kerneli dla nas; „1010 tok/s” to naprawa regresji TP w DS4. Brać: checkpoint snapshotu w tle (#253) i `--spec-follow` (#266, v1.1.18). | `git log v1.1.18..`; gęsty model, pomiar XTX, cokolwiek o GDN/stanie lub spekulacji |
| Strata (github.com/Niko1221/Strata) **7×** | `e88ee39d` → `cbfd5b92` v0.2.1.3 (silnik 0.1.46.1; +964/−57) | 10-20 | R32a | Dla dyskretnego gfx1100 nic; kolejki MES na gfx12 (−13% promptu w ~1/3 startów) jako hipoteza do testu E2; reszta aplikacja, Docker, bench standard-v1. | `git log cbfd5b92..`; tylko HIP/gfx1100, kolejki/strumienie, KV, nowe modele |
| agentionai Gyro GGUF (HF) | `aa0a0c3e` → `05758344` (tylko karta, wagi bez zmian) | 10-20 | R32a | Tylko Flash-Next; enkoder niepubliczny, 27B niemożliwe; zły plik dla 24 GB i Maców. | nowe wagi albo enkoder; Gyro dla 27B |
| halo-box/strix-llama.cpp (fork llama.cpp dla Strix Halo) | `82f1aa96` (PR #195 `ab062040`: typy trellis 143–149, CPU/Vulkan/HIP) | 10-20 | R32a | Najkrótsza droga Gyro do naszego forka (wymaga `prism.hadamard` z ggml-org #29600). Port tylko pod katalog 32 GB. | czy trellis trafia do ggml-org; wydajność HIP mmvq TQK na gfx1100 |

Proponowane notatki:
- dopisek w `wiki/eksperymenty/2026-10-18-hak-mtp-i-checkpointy.md`: „następny kandydat” ma wzorzec z zewnątrz (Maya #253: kopia w tle, nakładana na następny prompt), więc priorytet rośnie.
- `wiki/metody/`: nowa notatka „A/B na wymuszonej kontynuacji (spec-follow)” ze statusem do-zrobienia.
