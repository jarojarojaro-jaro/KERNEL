# 57b. Strata (@coldniko) i „Qwen3.8-Flash”: od A do Z, stan na 0.2.2

Data: 2026-10-21. Tylko CPU (bez GPU). Klon: `~/qwen-opt/research-src/strata-new` (`blob:none`, `origin/main` = `011c9e60` = tag `v0.2.2`). Raport uzupełnia wcześniejsze: R21g (0.1.44.1–0.1.45), R21n (0.2.0-beta, Gyro-S), R32a §2 (do 0.2.1.3), R35 E4 (kolejki na XTX). Nowe są tu: delta 0.2.1.4 → 0.2.2, rozróżnienie Qwen3.8-Flash / Flash-Next i zestawienie wszystkich pomiarów na XTX i 3090.

## TL;DR

1. **Strata to silnik C++/CUDA/HIP/SYCL/Metal pod jeden model, Qwen3.8-Flash-Next.** Ten model ma 125B parametrów, z czego 6B aktywnych, do tego 51B embeddingu n-gramowego i 4B MTP. Silnik rozkłada go na trzy poziomy pamięci: gorące eksperty i warstwy gęste w VRAM, wszystkie eksperty w RAM (liczone na CPU), tabelę n-gramów na SSD. Dekoduje spekulatywnie przez warstwę MTP modelu, opcjonalnie z prompt lookup. Licencja MIT, autor Niko Veit (@coldniko, GitHub `Niko1221`). Ma 29 639 gwiazdek i jest już w CompWatch (tier A).
2. **„Qwen3.8-Flash” nie jest modelem do pobrania.** To hostowane API Alibaby (od 2026-08-26, kontekst 1M) i, według karty HF, „official version based on Qwen3.8-Flash-Next with more production features”. Lokalnie istnieje tylko **Qwen3.8-Flash-Next**. Nie jest to destylat ani szybki wariant 27B: ma osobną architekturę (MoE 512 ekspertów top-10, GDN + Qwen Sparse Attention, embedding n-gramowy, hyper-connections).
3. **Połączenie z GSQ-RCO:** domyślne pliki Straty to **`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF`** (Q2_0/IQ2_XS/IQ3_XXS/IQ3_S, 6.3 mln pobrań), a „Coder” to GSQ-RCO IQ1_M z 256 z 512 ekspertów. Dlatego bio współtwórcy GSQ-RCO wymienia Stratę `[INFERENCE]`.
4. **Na XTX Flash-Next jest wolniejszy od naszego 27B.** Pomiar społeczności: IQ3_S **62.3 t/s** dekodu (greedy, MTP `--spec 3`, 7900X + 96 GB DDR5, silnik 0.1.38). My mamy prozę E0 78.9 t/s i czat 95–104 t/s. Nasz box ma 62 GB DDR4, czyli mniej RAM i wolniejszy RAM. Werdykt R21n bez zmian: nie przechodzimy.
5. **0.2.2 (silnik 0.1.47) nie przynosi nic do prędkości gfx1100.** Nowości to Gyro na Intel Arc i Macu, kernele trellis +15–30% na NVIDIA, pula CPU per NUMA i role kart Main/Helper/Off. Z nowych rzeczy dla nas liczy się tylko **jedna lekcja**: zawieszenie pierwszego okna weryfikacji, bo graf czekał na flagę, którą host podnosił dopiero po `cudaGraphLaunch` (§6, pkt 1).

## 1. Co to jest

- **Strata** ([Niko1221/Strata](https://github.com/Niko1221/Strata)) to lokalny silnik inferencji plus aplikacja desktopowa, „Terminal” (CLI `strata launch/connect/update/bench`), serwer OpenAI/Anthropic API pod `127.0.0.1:8080` i obrazy Docker. Opis repo: „Qwen3.8-Flash-Next on any consumer hardware: one-click install for Windows / Linux”.
- **Obsługiwane modele:** Qwen3.8-Flash-Next w wielu kwantach (GSQ-RCO, Swift 1.5, Unsloth UD, Gyro, NVFP4×3, OrcaRouter) oraz od 0.1.44.1 osobna ścieżka **Qwen3.6-35B-A3B** (`docs/MODELS.md:242`). **Gęstego Qwen3.8-27B nie obsługuje.**
- **Wersje:** 0.2.0-beta (10-19) → 0.2.1 (10-20, silnik 0.1.46) → 0.2.1.1–0.2.1.4 (poprawki Terminala i Windows) → **0.2.2** (10-21 11:07, silnik 0.1.47).
- **Model docelowy:** [Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) (HF utworzone 2026-08-24, 2.63 mln pobrań).
  - 125B parametrów, 6B aktywnych, plus 51B embeddingu n-gramowego (20M bi/trigramów w warstwie 2) i 4B MTP (1 warstwa, „trained with multi-steps”).
  - 48 warstw: 36 Gated DeltaNet + 12 Qwen Sparse Attention (QSA, wybór mikrobloków).
  - 512 ekspertów, aktywne 10 routowanych + 1 współdzielony.
  - Kontekst 262 144 natywnie, do 1M z YaRN.
  - Licencja Qwen Community License 1.0.
- **Qwen3.8-Flash** ([QwenCloud](https://www.qwencloud.com/models/qwen3.8-flash), [B.AI](https://docs.b.ai/llmservice/models/qwen3-8-flash/)) to model hostowany:
  - multimodalny (tekst, obraz, wideo → tekst), kontekst 1M (wejście 991K, wyjście 131K), wbudowane narzędzia;
  - cena referencyjna B.AI: $0.16 wejście / $0.47 wyjście za 1M tokenów;
  - liczby parametrów nie podano, wag nie ma.

| | Qwen3.8-27B (nasz) | Qwen3.8-Flash-Next | Qwen3.8-Flash |
|---|---|---|---|
| Typ | gęsty, GDN + pełna uwaga, MTP | MoE 125B/6B akt., GDN + QSA, n-gram 51B, MTP 4B | API (produkcyjna wersja Flash-Next) |
| Wagi | tak | tak (Qwen Community 1.0) | **nie** |
| Bajty/token (dekod) | ~27B × bpw | ~3.9 GB przy Gyro-S (R21n §2); więcej przy IQ3_S | — |
| Gdzie lokalnie | llama.cpp / nasza topka | Strata, llama.cpp (`qwen4exp` + `--moe-cache-mib`), agentionai/llama.cpp (Gyro), SGLang/TokenSpeed (serwer) | — |

## 2. Kto / skąd

- **Niko Veit** ([@coldniko](https://x.com/coldniko), GitHub `Niko1221`). Repo powstało 2026-09-24. Licencja MIT („Copyright (c) 2026 Niko1221 and the Strata contributors”).
- Stan 2026-10-21 (API GitHub): **29 639 gwiazdek, 3 144 forki, 503 otwarte issues**, ostatni push 10:46 UTC. 6.10 było 15.6k, więc liczba gwiazdek się podwoiła w ~2 tygodnie.
- Rytm pracy: od 0.2.0-beta do 0.2.2 minęły 2 dni, 337 commitów bez merge'y i +52 967/−2 271 linii. **Silnik** (`src include cmake sycl metal third_party`) to z tego tylko **+5 709/−215 (≈11%)**, reszta to aplikacja, CLI, testy i dokumentacja.
- **Kredyty w README** (`README.md:382`): wagi Qwen, kwanty GSQ-RCO od **ISTA-DASLab**, Swift 1.5 od UkisAI, Gyro od agentionai, UD od Unsloth. Silnik używa części llama.cpp/ggml, a pomysły bierze ze Splash, ninfer i HyperQwen (R-notatki `strata.md:59`).
- **stratat.com** ([strona](https://www.stratat.com/en)) agreguje posty @coldniko („X is the source of truth”) i tabelę sprzętu. Repo nigdzie do niej nie linkuje, więc traktuję ją jako stronę nieoficjalną albo fanowską **[niezweryfikowane]**.
  - Posty z X (2026-10-06): „Strata wins by a tight margin against all other Strix Halo inference engines in its first try release” i „Only loses to @ciruai engine on Hermes benchmarks”. Tabeli źródłowej nie widziałem, więc **[niezweryfikowane]**.
  - Na stratat.com jest też wpis o **Project Maya** (mw00/project-maya, GLM-5.3-Flash 321B), opisanej jako „Strata-derived engine rewrite”. To potwierdza drugie nazwisko z bio (@PeasantSmith), opracowane w R39a.

## 3. Jak działa technicznie

**Hierarchia pamięci** (`docs/HOW_IT_WORKS.md`, R-notatki `strata.md:38-47`):
- **VRAM:**
  - mixery GDN/QSA, gated residual i hyper-connections, routery, ekspert współdzielony, głowica wyjściowa, warstwa MTP i KV (od 64K kontekstu na GPU zostaje tylko gorąca część KV);
  - resztę VRAM wypełnia **adaptacyjny cache ekspertów**: „every extra GB holds ~700 more experts”.
- **RAM:** wszystkie 24 576 ekspertów (48 × 512), przypięte. CPU liczy chybione eksperty na miejscu (AVX2/AVX-512), równolegle z GPU. Na Linuksie od 0.2.0 eksperty idą z page cache bez kopii, z prefetchem.
- **SSD:** tabela n-gramów (PLE) w IQ4_NL ma 28.8 GB; na token czyta się kilka wierszy.
- **Krzywa trafień cache** dla routingu Flash-Next: H(f) = 1 − (1 − f)³, gdzie f to odsetek ekspertów w VRAM (R21n §3).

**Dekod:**
- **MTP** proponuje do 3 tokenów, jedna weryfikacja przechodzi wszystkie 48 warstw, średnio 2.4–3.2 tokena na przebieg, ×1.6–1.8.
- **`--lookup-chain`**: prompt lookup doklejony za draftami MTP (`2312c83b`); drafter to hash trigramów, 4 pozycje na slot (`src/spec/suffix_drafter.cpp`). Na edycjach kodu daje +6–11%.
- **`STRATA_SPEC_PROB=1`** (opt-in): probabilistyczna akceptacja przy samplowaniu (`33356f72`).
- **Kernele CUDA** (`src/kernels/cuda/`, ~45 plików): `native_moe`, `native_mmvq`, `iq_kernels` (i-quanty przepisane z ggml), `qsa_decode/prompt_attn`, `router_top10`, `fused_gdn`, `kv_q4/q8/stream`, `verify_kernels`.
- **HIP** idzie przez warstwę `hip_compat` (CUDA→HIP); osobne drzewa to `sycl/` i `metal/`.

**Prefill:**
- chunki do 8 192 tokenów (32 768 opt-in);
- eksperty strumieniowane po PCIe w czasie, gdy liczy się uwaga bieżącej warstwy;
- na AMD tabele **hipBLASLt** per para (arch, wersja biblioteki); przy niezgodnej wersji silnik spada do zwykłego hipBLAS.

**Formaty:**
- standardowe typy ggml (Q2_0, IQ2_XS, IQ3_XXS, IQ3_S, IQ1_M, UD-Q4_K_XL…);
- Gyro: trellis QTIP + Hadamard, typy 144–149 (R21n §2);
- NVFP4 w trzech wariantach: konwersja GPTQ Straty, checkpoint NVIDII i NVIDIA FP4-QAD (`docs/MODELS.md:197-236`; tylko NVIDIA, ~80 GB RAM).

**Metodologia** (stała od początku, R `wiki/repo/strata.md`):
- zmiana domyślnej ścieżki musi być bitowo identyczna (greedy ids / „identity gate” na kilku kwantach) i wygrać A/B na przeplatanych parach;
- każda zmiana ma wyłącznik `STRATA_*=0`;
- wszystko, co zmienia bity, jest opt-in z podanym KL.

**Delta 0.2.1.4 → 0.2.2 (silnik 0.1.47; 200 commitów od `cbfd5b92`, silnik +4 747/−160):**

| Zmiana | Liczby (ich pomiar) | Dla nas |
|---|---|---|
| Gyro na NVIDIA: codebook trellisa w shared memory, 4 wiersze na warp (8 linii na wiersz) (`5f81c5dc`) | 3060: Gyro-S 53.6→62.8 t/s (+17%), Gyro-M +11%, bitowo identyczne | nie (trellis tylko dla Flash-Next) |
| Gyro na P100 (sm_60): codebook int8 w smem, chunki wierszy (`9f38ee33`…`88278af7`) | 30/36/33 → 38.5/45.6/42.7 t/s (+30%) | nie |
| Gyro na Intel Arc (SYCL) i Macu (Metal) | A750 8 GB: Gyro-S dekod 15.8 t/s z MTP; Mac mini M4 32 GB: 9.1 t/s | nie |
| Pula CPU podzielona per węzeł NUMA (`numa_pool.hpp`) | raport #3201: 54.05 → 59.3 t/s (+9.7%) na 2 socketach; „not tested on a two-socket machine” | nie (1 socket) |
| `--pool-cores`, nazwane wątki, wątki = rdzenie fizyczne w raporcie sprzętu (#3417: 27.9 vs 38.1 t/s) | — | już w R21n §4.2b |
| Role kart Main / Helper / Off | — | produkt (multi-GPU) |
| Samodopasowanie: ctx 32K/16K/8K, mniejszy chunk i rezerwa, gdy model ledwo się nie mieści | A750: Gyro-M startuje (309 slotów) | produkt: reguła „fit” |
| HIP verify: flaga PLE podnoszona **przed** pierwszym `cudaGraphLaunch` okna (`86d10ed8`) | zawieszenie pierwszego okna: 8/41 → 0/46 przebiegów (Strix Halo IQ3_S); dekod 47.89 vs 47.78 | **lekcja (§6.1)** |
| `GPU_MAX_HW_QUEUES` 1–2: bez primingu kolejek (#3480) | niezmierzone | nie (R35 E4: XTX bez bimodalności) |
| Pakiety RX 6000 (gfx1030/1031) | „built, not tested on a real card” | nie |
| Jedna definicja prędkości: tokeny wyjścia (z thinking, tool calls, przyjęte tokeny MTP) / czas dekodu | agent: 632 → realne 50–75; „przez całe żądanie” daje ~połowę (20.6–31.5 vs 47.8–65.9) | metryka zgodna z naszą E0 |
| Pomiar bezczynności GPU (bez zmiany domyślnych) | 1 karta: 5% czasu bezczynności w dekodzie; 2 karty: 47–49% | punkt odniesienia |

## 4. Liczby

Wszystkie poniższe liczby dotyczą Qwen3.8-Flash-Next. Na 27B Strata nie działa.

| Sprzęt | Kwant / tryb | Dekod t/s | Prefill t/s | Źródło |
|---|---|---:|---:|---|
| **RX 7900 XTX**, 7900X, 96 GB DDR5, ROCm 10.2 nightly | GSQ-RCO IQ3_S, MTP `--spec 3`, greedy, 128K | **62.3** | 926 → **1 687** (tabela hipBLASLt gfx1100, ×1.82) | `bench/results/2026-10-04-community-rx7900xtx-hipblaslt-100500` (#745, xyzzing) |
| RX 7900 XTX, ROCm 7.1.1 vs 10.2 | IQ3_S | 62.0 vs 61.0 | 921 vs 1 535 | `2026-10-03-community-rx7900xtx-rocm102-nightly` |
| RX 7900 XTX + 9950X DDR5 | IQ3_S | 82.5 (T=0, powtarzany akapit, 70% akceptacji, **zawyżone**) | 1 810 przy 98K | #2938 (R21n §3) |
| RX 7900 XTX + RX 6800 XT (helper), 1M ctx, łatki | UD-Q4_K_XL | 97 (długie kodowanie), 39 przy pełnym 1M | 1 350 (50K) | `2026-10-07-community-xtx-6800xt-1m-helper` (#1459) |
| RX 7900 XTX | ? | 75.5 | 1 459 | tabela stratat.com/ModelDock; warunki nieujawnione, strona renderowana JS **[niezweryfikowane]** |
| RTX 3090 Ti, 2× Xeon E5-2699 v3 | IQ3_S, 262K | 90–99 | 1 239–1 304 (~5K) | `2026-10-03-community-z840-rtx3090ti` (#674) |
| RTX 3090 | Coder IQ1_M, 198K | 99 (było 85) | — | `docs/DETAILS.md:95` |
| RTX 3090 | Q2_0 | ~128 (krótki czat) | ~355 | `DETAILS.md:459`, **estymata**, nie pomiar |
| RTX 3090 | ? | 86.5 | 2 094 | stratat.com/ModelDock **[niezweryfikowane]** |
| RTX 5070 12 GB, 7600, 64 GB | Q2_0 / IQ3_S (silnik 0.1.26–0.1.36) | 94 / 53 | 2 650 / 1 620 (32K) | `docs/MODELS.md:35-60` |
| RX 9070 XT 16 GB, 3900X, 47 GB | Q2_0 | 60 | 1 160 | `docs/MODELS.md:62-68` |
| R9700 | Qwen3.6-35B-A3B | 83.2 → 117.8 (llama.cpp 82) | — | R21g |
| RTX 3060 12 GB | Gyro-S (0.2.2) | 62.8 | — | release 0.2.2 |

- **Jakość Flash-Next vs 27B** (karta HF, BF16, scraping tabeli HTML):

  | Benchmark | Flash-Next | 27B | Różnica |
  |---|---:|---:|---:|
  | SWE-bench Pro | 62.5 | 61.7 | +0.8 |
  | DeepSWE 1.1 | 58.7 | 42.2 | +16.5 |
  | SWE-bench Multilingual | 81.0 | 73.8 | +7.2 |
  | NL2Repo | 48.1 | 42.3 | +5.8 |
  | JobBench | 55.7 | 33.4 | +22.3 |
  | Toolathlon | 73.5 | 67.1 | +6.4 |
  | GPQA-D | 91.7 | 89.2 | +2.5 |
  | HLE | 35.9 | 30.8 | +5.1 |
  | LiveCodeBench v6 | 91.9 | 90.3 | +1.6 |
  | IFBench | 81.3 | 79.5 | +1.8 |

  Lokalnie użytkownik dostaje 2–3-bitowe eksperty: KLD od 0.27 (Gyro-S) i więcej, wobec 0.0117–0.0153 dla naszego 27B UD-Q4_K_XL (R21n, R32a §3). Przewaga przy tych kwantach nie jest zmierzona.
- **Nasz punkt odniesienia** (XTX, 27B UD-Q4_K_XL, topka): proza E0 **78.93 t/s** [75.69, 82.21] (REKORDY), czat ~95–104 t/s.

## 5. Licencja / dostępność

- **Kod:** MIT, publiczny, z instalatorami: Windows (CUDA 12/13, HIP gfx12, HIP rdna3), Linux AppImage (cuda12/13, rx9070, **rx7900**, strixhalo, rx6000), Mac (podpisany) i Docker `ghcr.io/niko1221/strata:<ver>-rocm-gfx110x`.
  - Zastrzeżenie: obraz gfx110x i pakiety RX 7000 są „built but not run on a card” przez opiekunów (`docs/AMD_HIP.md:114-118`). XTX uruchamiała tylko społeczność.
- **Wagi:**
  - Qwen3.8-Flash-Next: Qwen Community License 1.0;
  - GSQ-RCO GGUF (ISTA-DASLab): HF publiczne, 6.32 mln pobrań, utworzone 2026-09-07;
  - NVFP4-QAD: NVIDIA Open Model Agreement + licencja Qwen; Strata nie redystrybuuje, konwertuje lokalnie.
- **Qwen3.8-Flash:** tylko API, wag nie ma.

## 6. Co z tego dla nas

Ranking według stosunku zysku do wysiłku.

1. **Audyt kolejności „flaga hosta vs uruchomienie grafu” w PM4 replay i weryfikacji MTP.** Zysk: stabilność, czyli brak rzadkich zawieszeń, 0 t/s różnicy. Wysiłek S.
   - Mechanizm z `86d10ed8`: kernel w grafie czekał na flagę w pamięci, którą host podnosił dopiero po powrocie `cudaGraphLaunch`. Na HIP launch bywa synchroniczny aż do startu pracy, więc w ~1 na 5 przebiegów był deadlock.
   - Do sprawdzenia: czy u nas jakikolwiek spin-wait na GPU (PM4 `WAIT_REG_MEM` / flaga host-mapped) zależy od zapisu hosta, który następuje *po* submit/replay. Reguła: flagę podnosić przed pierwszym submitem albo czekać tylko na zapisy z GPU.
   - **[INFERENCE]**: nie wiem, czy nasz replay ma taki wzorzec. To wymaga przeglądu kodu, nie GPU.
2. **3090 (wynajem): Strata jako punkt odniesienia konkurencji, tylko warunkowo.** Wysiłek M. Zysk: wiedza produktowa, nie t/s.
   - Warunek: host ≥64 GB RAM i ≥60 GB wolnego dysku na IQ3_S.
   - Jeden przebieg `strata bench run` (standard-v1) obok naszego 27B na tej samej karcie. Liczby społeczności dla 3090 Ti to 90–99 t/s na IQ3_S.
   - Bez tego warunku pomijamy: 1 h wynajmu lepiej wydać na nasz A/B DFlash2/MTP.
3. **Zmiana modelu na Flash-Next na XTX: werdykt R21n bez zmian, nie teraz.** Nasze 27B jest szybsze (78.9 vs ~62 t/s), a dekod Flash-Next przy 62 GB DDR4 wyszedłby jeszcze niższy `[INFERENCE]`.
   - Jeśli wrócimy do tematu: test T1 z R21n (IQ3_S w forku z `--moe-cache-mib`, kill < 50 t/s albo pass rate < 27B).
   - Dla Orca (Qwen3.5-27B fine-tune + DFlash2): **nie dotyczy**. Strata nie obsługuje gęstych modeli Qwen3.5/3.8.
4. **Metryka prędkości.** Ich definicja (tokeny wyjścia z thinking / czas dekodu) zgadza się z naszą E0 (REKORDY). Do produktu (UI Podkręta) przenieść zasadę: nie dzielić przez całe żądanie, bo wychodzi ~½ (R32a już to odnotował). Wysiłek S, zysk: wiarygodność liczb.
5. **Nie dotyczy:**
   - tabele hipBLASLt: nasze kwanty prefillują przez MMQ (R21g #3058, R32a);
   - priming kolejek HIP: na XTX rozrzut 0.22%, bez bimodalności (R35 E4);
   - kernele trellis/Gyro: enkoder zamknięty, a Gyro z 27B nie istnieje (R32a §3);
   - NUMA: jeden socket;
   - scorer QSA: 27B nie ma QSA;
   - zestaw promptów iGPU 780M i role kart: pojedyncza karta.

## 6a. Audyt: wzorzec Straty `86d10ed8` w naszej topce (przegląd kodu, CPU)

Zakres: `~/wt/topka-int` @ `cf927413b`, czyli `ggml/src/ggml-cuda/hip-pm4.cu` (taśma PM4, `LAZY_EXEC`, guard, hostgap), ścieżka `LLAMA_GPU_VERIFY` (`src/llama-context.cpp`), `LLAMA_SERVER_YIELD_FAST` (`tools/server/server-queue.cpp`, `server-context.cpp`), stos wejść `GGML_HIP_INPUT_BATCH` i zdarzenia strumieni (`ggml-cuda.cu`), `allreduce.cu`. Szukałem miejsc, w których GPU czeka (WAIT_REG_MEM, czekanie na sygnał, kernel kręcący się w pętli) na pamięć, którą host zapisuje dopiero po submit/doorbell.

**Werdykt: wzorca nie ma.** Taśma PM4 nie zawiera żadnego pakietu czekającego na pamięć. Jej słownik to `SET_SH_REG`, `DISPATCH_DIRECT`, `EVENT_WRITE` CS_PARTIAL_FLUSH, `ACQUIRE_MEM`, `COPY_DATA` (znacznik czasu) i `INDIRECT_BUFFER` (`hip-pm4.cu:714-745`); `WAIT_REG_MEM` w ogóle w niej nie występuje. Cała synchronizacja odbywa się na hoście: przed taśmą `cudaStreamSynchronize`, a po niej host czeka na sygnał HSA zapisywany przez GPU. Kod nie ma też ani jednego `hipStreamWaitValue`. Jedyna pętla wirująca na GPU jest w `allreduce.cu`, a to ścieżka wyłącznie dla wielu GPU.

| # | Miejsce | Kto czeka / na co | Kto zapisuje i kiedy względem submitu | Werdykt |
|---|---|---|---|---|
| 1 | `hip-pm4.cu:1099-1103`: bit BARRIER pakietu AQL (PM4_IB) | CP czeka na zakończenie poprzednich pakietów **własnej** kolejki HSA | stan GPU; poprzednie taśmy są już zakończone, bo host czekał na nie w pkt 4 | OK |
| 2 | `hip-pm4.cu:734, 926, 974`: `EVENT_WRITE` CS_PARTIAL_FLUSH między dispatchami | CP czeka, aż skończą się wcześniejsze dispatche | stan GPU | OK |
| 3 | `hip-pm4.cu:736-741`: `ACQUIRE_MEM` (L0/K$/GL1; system) | operacje na cache, bez porównywania wartości | — | OK |
| 4 | `hip-pm4.cu:1106`: `hsa_signal_wait_scacquire(d.signal < 1)` | **host** czeka na GPU (kierunek odwrotny), z limitem 10 s i potem `GGML_ABORT` | CP dekrementuje sygnał po taśmie | OK. Czeka w trybie aktywnym (ACTIVE), czyli pali CPU, ale to nie błąd |
| 5 | Zapisy hosta przed taśmą: `cudaStreamSynchronize` (1069), naprawa kernargów synchronicznym `cudaMemcpy` (1075), `memset(prog)` (1079), `signal = 1` (1085), treść pakietu i sygnał (1096-1098), potem nagłówek `__atomic_store_n(..., RELEASE)` (1102) → doorbell `screlease` (1103) | — | **wszystkie przed doorbellem**; nagłówek z release publikuje pakiet na końcu | OK, kolejność jest dokładnie odwrotna niż w błędzie Straty |
| 6 | Naprawa IB przez guard (`hip-pm4.cu:1055-1060`) | CP czyta IB z pamięci hosta | host przed doorbellem; pula hosta jest fine-grained (`:580-581`), więc GPU nie trzyma IB w L2 `[INFERENCE]` | OK |
| 7 | `GGML_HIP_PM4_MIN_DISPATCH` (`:275-279`): krótki graf jako asynchroniczny HIP graph, potem taśma | taśma musi poczekać na wcześniejszą pracę na strumieniu HIP | porządkuje to `cudaStreamSynchronize` w pkt 5 | OK |
| 8 | `LAZY_EXEC` / `exec_stale` (`ggml-cuda.cu:5923-5935, 6011-6012`) | instancja HIP graph powstaje dopiero przy fallbacku | host, synchronicznie przed launchem | OK (to sprawa cyklu życia grafu, nie czekania) |
| 9 | `GGML_HIP_INPUT_BATCH` (`ggml-cuda.cu:2591-2655`): podwójny bufor stagingu | host czeka (`cudaEventSynchronize`, `:2643`), zanim nadpisze połówkę; GPU czyta połówkę po `cudaMemcpyAsync` | host pisze do połówki dopiero po zakończeniu jej poprzedniej kopii; flush przed każdym grafem/taśmą (`:5977`) | OK, kolejność zapis-po-odczycie jest zachowana |
| 10 | Fork/join strumieni (`ggml-cuda.cu:5712, 5800`), `event_wait` (`:6047`) | `hipStreamWaitEvent` na zdarzeniach **nagranych przez GPU** | `EventRecord` jest kolejkowany przez ten sam wątek przed czekaniem | OK |
| 11 | `LLAMA_GPU_VERIFY` `gv_fetch` (`llama-context.cpp:1002-1015`) | host: `synchronize()` i potem blokujący `tensor_get` | wiersze logitów żyją do następnego dekodu (`gv_drop`, `:1653, :1902`) | OK |
| 12 | `LLAMA_SERVER_YIELD_FAST` (`server-queue.cpp:185-217, 266-318`; `server-context.cpp:4320`) | tylko wątki hosta (zmienne warunkowe) | cały ggml liczy się na jednym wątku (`server-queue.cpp:296`) | OK, w ogóle bez czekania po stronie GPU |
| 13 | `allreduce.cu:157-176`: kernel kręci się na `arrival_other` w zmapowanej pamięci hosta | GPU czeka na **drugie GPU** (zapis volatile + `__threadfence_system`), a nie na hosta | oba kernele są kolejkowane bez czekania hosta pomiędzy nimi; brak limitu czasu | nie dotyczy pojedynczego XTX; kod z upstreamu. Na 2 GPU zawiesi się, jeśli launch peera nie nastąpi |

**Ryzyko utajone (nie jest błędem przy obecnym użyciu):** `ggml_hip_pm4_launch` (`hip-pm4.cu:1039-1119`) nie bierze `g_mutex` (`:257`; lock jest tylko w build/watch), a jeden `d.signal` służy wszystkim taśmom urządzenia.
- Gdyby dwa wątki (np. dwa konteksty na jednym GPU) uruchamiały taśmy równolegle, wątek B ustawiłby `signal = 1` w trakcie czekania A. Wtedy któryś z nich mógłby uznać, że jego taśma skończyła się, kiedy skończyła się cudza, i czytać wyniki za wcześnie (wyścig, nie zawieszenie).
- Dziś wszystkie obliczenia ggml idą z jednego wątku, więc to nie występuje.
- Poprawka, gdyby kiedyś było trzeba: `std::lock_guard` na `d` w launchu albo sygnał per taśma (`hsa_signal_create` w `ggml_hip_pm4_build`).

**Wniosek:** nasza architektura (taśma zawsze synchroniczna względem hosta, zero oczekiwań GPU na pamięć hosta) nie ma klasy błędów z `86d10ed8`. Lekcja Straty staje się regułą projektową na przyszłość: jeśli kiedyś dodamy asynchroniczne taśmy z `WAIT_REG_MEM` na fladze hosta (np. żeby nałożyć hosta na GPU), flagę trzeba zapisać przed doorbellem, a czekanie musi mieć limit czasu.

## 7. Do bazy wiedzy

- `repo/strata.md`, dopisać: 0.2.2 (`011c9e60`, 10-21, silnik 0.1.47): Gyro na Arc/Mac, trellis NVIDIA +17% (3060) i P100 +30%, pula CPU per NUMA, role kart Main/Helper/Off, pakiety RX 6000 (nieuruchamiane). Silnik to ~11% zmian od 0.2.0-beta. Dla gfx1100 nic do prędkości. 29.6k gwiazdek.
- **Qwen3.8-Flash ≠ Flash-Next:** Flash to hostowane API (1M ctx, $0.16/$0.47), produkcyjna wersja Flash-Next; wag nie ma. Flash-Next to otwarte wagi 125B/6B + 51B n-gram + 4B MTP. Żaden z nich nie jest destylatem 27B.
- **Strata ↔ GSQ-RCO:** domyślne pliki to `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF` (6.3 mln pobrań). „Coder” to GSQ-RCO IQ1_M z 256/512 ekspertów. Swift 1.5 (UkisAI) bazuje na GSQ-RCO.
- **XTX + Flash-Next (społeczność):** IQ3_S 62.3 t/s dekodu (MTP spec 3, greedy, 7900X + 96 GB DDR5). Prefill przy 128K 926 → 1 687 t/s z tabelą hipBLASLt dla właściwej wersji biblioteki. #2938 (82.5 t/s) jest zawyżony.
- **Lekcja (HIP + grafy):** nie czekać w grafie na flagę hosta podnoszoną po `graphLaunch`; na HIP to deadlock w ~20% startów (Strata `86d10ed8`, 8/41 → 0/46).
- **Bezczynność GPU w dekodzie MoE z offloadem:** 1 karta ~5%, 2 karty z podziałem warstw 47–49%; overlap i pipelining dały ±2% przy szumie 2.8% (Strata `bench/results/2026-10-20-0.2.1-idle-gpu/`).
- stratat.com to nieoficjalny agregator (repo do niego nie linkuje), a tabela ModelDock nie ujawnia warunków. Nie cytować jako pomiaru.

## 8. Źródła

- Repo: https://github.com/Niko1221/Strata @ `011c9e60` (v0.2.2): `README.md:382`, `docs/MODELS.md:13-68,115-236,242`, `docs/AMD_HIP.md:75-122,365-395`, `docs/DETAILS.md:95,459`, `docs/HOW_IT_WORKS.md`, `src/spec/suffix_drafter.cpp`, `bench/results/COMMUNITY.md:14,42-45,84-97`; commity `86d10ed8`, `5f81c5dc`, `9f38ee33`, `3f1fa67f`, `b35a9816`, `2312c83b`, `33356f72`.
- Release notes: https://github.com/Niko1221/Strata/releases/tag/v0.2.2, https://github.com/Niko1221/Strata/releases/tag/v0.2.1 (w tym 0.2.1.1–0.2.1.4).
- Raporty społeczności XTX: `bench/results/2026-10-04-community-rx7900xtx-hipblaslt-100500/README.md`, `2026-10-03-community-rx7900xtx-rocm102-nightly/`, `2026-10-07-community-xtx-6800xt-1m-helper/`; issue https://github.com/Niko1221/Strata/issues/2938.
- Karta modelu: https://huggingface.co/Qwen/Qwen3.8-Flash-Next (README, tabela benchmarków); blog https://qwen.ai/blog?id=qwen3.8-flash-next.
- Qwen3.8-Flash (API): https://www.qwencloud.com/models/qwen3.8-flash, https://docs.b.ai/llmservice/models/qwen3-8-flash/.
- GSQ-RCO GGUF: https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF (API HF: createdAt 2026-09-07, downloads 6 316 537).
- Autor: https://x.com/coldniko; agregator postów https://www.stratat.com/en/creator **[nieoficjalny]**; tabela https://www.stratat.com/en/benchmarks (dane ModelDock).
- Nasze: R21g, R21n, R32a §2–3, R35 E4, `wiki/REKORDY.md:126`, `research_notes/Optymalizacja kerneli na AMD/strata.md`.
