# 15c. Nowe silniki i produkty konkurencji: teardown (stan na 2026-10-16)

Zakres: Magnitude, tqLLM, Actual Computer (silnik „e”) i delta TensorFold v1.0.11 → v1.0.12. Dla każdego: audyt deklaracji, mechanizm na poziomie kodu oraz co skopiować albo czemu przeciwdziałać. Na końcu aktualizacja obrazu konkurencji z `research/01-konkurencja.md`.

Metoda i ograniczenia:
- Kod czytany z klonów blobless w `/tmp/r15c/` (magnitude `1f54d5b7`, tqllm `23af3c9`, TensorFold `v1.0.12` = `833bbfcb`). Paczki Actual pobrane i rozłożone tylko statycznie, **nic nie uruchamiane**. Rozmiary plików i nagłówki GGUF pochodzą z HF API i odczytów HTTP range.
- **Bez lokalnego GPU i bez wydatków w chmurze.** Wszystkie „nasze” liczby pochodzą z pomiarów z 2026-10-15/16 (`wiki/index.md`, `BENCHMARKI-NVIDIA-2026-10-16.md`).
- Oznaczenia: `[NIEZWERYFIKOWANE]` = nie sprawdziłem u źródła pierwotnego; `[WNIOSEK]` = mój rachunek albo wnioskowanie.
- Notatki robocze z pełnymi tabelami (dla tqLLM, Actual i TensorFold) leżą w `/tmp/r15c/notes-{tqllm,actual,tensorfold}.md`. Ten raport je streszcza i scala, poprawiając jeden błąd (§5.2).

Pasma do rooflinów: RTX 3090 936 GB/s, RTX 5060 Ti 448 GB/s, RX 7900 XTX 960 GB/s, DGX Spark (GB10) 273 GB/s, Mac M4 Pro 273 GB/s, DGX Station (GB300) 7.1 TB/s.

---

## 1. TL;DR

1. **Magnitude to bezpośredni konkurent naszego planu, ale nie w tym, co nas wyróżnia.**
   - Ma własny silnik w Ruście z językiem kerneli „Seismic” i backendami Metal, CUDA, Vulkan i CPU. **Nie ma HIP/ROCm**: AMD działa tylko przez Vulkan, z niekwalifikowanymi ścieżkami i błędami na Strix Halo i iGPU. Od v0.2.0 (PR #130, 2026-09-27) to już nie fork llama.cpp.
   - Autotune istnieje naprawdę: 60 s przy pierwszym załadowaniu, małe dyskretne przestrzenie (KSPLIT, LANES, ROWS, ROTATE, WEIGHTS_AHEAD, INT8).
   - Hasło „nie zmienia wyjścia” jest **fałszywe w sensie bitowym**. Kandydat przechodzi, gdy jego błąd mieści się w α = 8 krokach zaokrąglenia bf16 względem domyślnego kernela. Do tego domyślny KV to K8V4, a jakości w benchmarkach nie mierzą.
   - „2.19× vs Ollama” zmierzono na zadaniu **kopiowania** fragmentu Moby-Dick przy 64k kontekstu, na domyślnej Ollamie.
   - Wcześniejsze porównanie z llama.cpp dawało na CUDA tylko **+19% decode** (Qwen3.6-35B-A3B, DGX Spark). Usunęli je z README 2026-10-13.
2. **tqLLM** to własny silnik CUDA tylko dla Qwen3.5/3.8, wyłącznie NVIDIA.
   - 273.1 t/s na 3090 jest formalnie zweryfikowane w LocalMaxxing, ale przy T=0, 320 tokenach thinking i średnio 6.15 zaakceptowanych tokenach na krok. Zmierzył to **prywatny build** `8c12e1a`.
   - W plain decode per bajt mają **parytet z nami** (77% pasma wobec naszych 71–78%).
   - Przewaga składa się z trzech rzeczy: mniej bajtów (TQ3_4S, KLD nieopublikowany), drafter DFlash2 z blokiem 8 i drzewem, temperatura 0.
   - Ich „exact” znaczy tyle, że spec daje to samo co ich plain w jednej konfiguracji. Naprawili to dopiero 10-13, po zgłoszeniu wyniku.
3. **Actual „e”** to host w asemblerze AArch64 plus 86 cubinów sm_103a, czyli **tylko DGX Station**. 455 / 8,046 t/s zgadza się z rooflinem, ale pochodzi z ich własnego `e bench`, bez warunków. Na sprzęcie konsumenckim Actual uruchamia vendored llama.cpp („aci-cpp”) albo silnik „malibu” w Ruście.
   - Lekcje:
     - relay na AWS Nitro Enclave z TLS pinowanym do atestacji;
     - device-code login (u nich bez ekranu potwierdzenia, co jest anty-wzorcem);
     - MTP bitowo równe spec-off;
     - spec-copy wpięty w MTP.
4. **TensorFold 1.0.12:**
   - LFM2.5 wszedł tylko na Metal: M5 Ultra 261.5 plain, czyli 30% pasma. Nasz XTX daje 293.7 na cięższym Q5_K_M (54%).
   - Nowości: okna weryfikacji bitowo równe ścieżce 1-wierszowej („twins”), Recall (trwały n-gram wyceniany wobec MTP) oraz podział ekspertów na 2 Sparki.
   - HIP to preview i nadal jest słaby (2×W7800 TP2 39 t/s plain wobec naszego 1×XTX 43.2).
5. **Co zmienia się w planie:**
   - „Strojenie kerneli na komputerze użytkownika” **przestało być unikalne** (Magnitude). „Spec nie zmienia odpowiedzi” robią już tqLLM, Actual i TF.
   - Unikalne zostaje: natywny AMD (HIP/PM4); pełne pokrycie modeli llama.cpp; **mierzone przed → po na maszynie użytkownika wobec tuned upstream**; bramka md5/KLD opublikowana razem z wynikiem.
   - Trzy najtańsze działania o największym zwrocie:
     1. (a) wpisy do LocalMaxxing (XTX nie ma dziś żadnego verified runu Qwen3.8-27B) plus raportowanie dwóch klas obciążenia (kopia i nie-kopia);
     2. (b) spec-copy / n-gram z wyceną kosztu okna;
     3. (c) batch-invariant verify, żeby greedy ze spekulacją == plain.

---

## 2. Audyt deklaracji

Kolumny: deklaracja, sprzęt, model i kwant, obciążenie (batch, kontekst), baseline, wyjście i jakość, komenda reprodukcji, roofline, werdykt.

### 2.1 Magnitude

| # | Deklaracja (źródło) | HW | Model / kwant | Obciążenie | Baseline | Wyjście / jakość | Repro | Roofline / Amdahl `[WNIOSEK]` | Werdykt |
|---|---|---|---|---|---|---|---|---|---|
| M1 | „1.32× prefill, 2.19× decode vs Ollama (MLX)” ([benchmarks](https://magnitude.dev/benchmarks)) | Mac mini M4 Pro 48 GB | 11 modeli ~4-bit: Magnitude GGUF UD-Q4_K_XL, Ollama MLX NVFP4 | **prose-repeat**: model ma dosłownie powtórzyć fragment Moby-Dick (`evaluation/fixtures/.../prose.py:10`); ~64k kontekstu, 256 tokenów, greedy, thinking off, b=1; mediana z 2, część Ollamy to pojedyncze żądania z wcześniejszego runu | Ollama v0.35.1 (2026-09-29) z domyślnymi ustawieniami. Według samych autorów drafter Ollamy „drafted very few tokens” dla Gemma E4B/26B/31B | „outputs differ… Answer quality isn't scored” | tak (`magnitude-bench run --mode prose-repeat …`) | 27B: 34.3 t/s przy (17.56 + 2.06 GB drafter)/273 GB/s ⇒ **≥2.4 tok/rundę**. Gemma 31B: Ollama 8.6 t/s to 0.5 pełnego odczytu wag na token, czyli bardzo słaby baseline | **wiarygodne tylko dla specjalnego obciążenia** (kopia + słaby baseline) |
| M2 | „1.34× prefill, 2.17× decode vs Ollama (llama.cpp)” (jw.) | DGX Spark GB10 | jw.; Ollama GGUF Q4_K_M | jw. | Ollama v0.35.1, domyślne ustawienia, drafter z tagu (MTP) | jw.; Nemotron 3.5: **0.76×** | tak | Qwen3.8-27B: 66.7 t/s przy 19.6 GB/rundę ⇒ **≥4.8 tok/rundę** (plus KV 64k ≈ +1.6 GB/rundę dla K8V4 ⇒ ≥5.2). Qwen3.5-4B: 296 t/s przy (2.99 + 0.69) GB ⇒ ≥4.0. Bez kopiowania takich akceptacji DFlash nie daje | **wiarygodne tylko dla specjalnego obciążenia** |
| M3 | (wycofane) „Up to 2× faster than llama.cpp: 92% decode na Metal, 19% na CUDA” (commit `658cb1ec`, 2026-09-30; zastąpione w `00268e25`, 2026-10-13) | M4 Pro; DGX Spark | Qwen3.6-35B-A3B 4-bit | 64k, **bez spekulacji** | llama.cpp (wersja i flagi nieznane) | — | dane w `scripts/benchmark-chart.py@658cb1ec` | Spark: 49 → 58 t/s decode, 2033 → 2507 prefill. 58 t/s × ~1.9 GB aktywnych ≈ 110 GB/s = 40% pasma | **wiarygodne**. To najuczciwsza liczba: **+19% decode nad llama.cpp na CUDA**. Metal +92% przy bazie 30 t/s `[NIEZWERYFIKOWANE]` |
| M4 | „Spends up to a minute on your chip… keeps the fastest combination that **doesn't change the model's output**” (README, FAQ) | wszystkie | — | — | domyślny kernel natywny | `STANDARD_ALPHA = 8.0` (`engine/executor/src/native/tuning/precision.rs:22`); dopuszczenie przy `sqrt(error_power/step_power) ≤ α` (`seismic/runtime/src/native/admission.rs:7-12`, `comparison.rs:16-19`); parametry `code arithmetic` (KSPLIT, LANES, OPERAND, INT8) zmieniają bity (`cuda_dense.seismic:1-58`) | budżet `STANDARD_TUNING_BUDGET = 60 s` (`tuning/mod.rs:331`) | — | strojenie: **prawda**. „Nie zmienia wyjścia”: **fałsz** (błąd ograniczony, nie zero; jakości modelu w publikacji nie ma) |
| M5 | „Each model ships with the fastest speculative decoding drafter” | — | DFlash2 Q8 dla Qwen3.8-27B to **kopia z z-lab** (karta HF `magnitudedev/Qwen3.8-27B-DFlash2-GGUF`); DSpark dla LFM 2.6B/8B; MTP dla Gemma; **brak draftera dla LFM2.5-24B-A2B** (`catalog/models.json`) | — | — | metoda jest stała w katalogu i użytkownik jej nie zmieni (#157) | — | — | **częściowo**: kuracja i hosting drafterów, bez pomiaru per maszyna |
| M6 | „Quantized KV halves memory per agent” | — | domyślny `KvCodec::AffineK8V4` (`engine/src/options.rs:121`); opcja `RotatedK4V4` | — | bf16 | 6 bitów średnio, czyli ~0.4× pamięci bf16 plus skale. KLD nieopublikowany | — | — | **prawda**; jakość niezmierzona publicznie |
| M7 | „Any Apple Silicon, NVIDIA, or AMD GPU” | AMD | Vulkan 1.3 z własnymi shaderami; RDNA natywnie wave32; GCN w trybie 64 jako 2 logiczne subgrupy (`inference/docs/compatibility.md:128,150`) | — | — | „Pending conformance… validated offline but not yet run” (GCN, NVK) | — | — | **nominalnie**. Na RDNA3 brak publicznych liczb. Błędy: #151 (iGPU nie przechodzi walidacji numerycznej), #154 (iGPU wybrany zamiast dGPU), #157 (DFlash2 na RADV nie kompilował się, naprawione w 0.2.5) |
| M8 | „Memory that flexes”, „sessions share prefix caches” | — | prefix cache z resume state (`design/inference/engine/prefix-cache.md`) | — | — | — | — | — | **wiarygodne** (tego nie mierzyłem) |
| M9 | Brak offloadu MoE do RAM | 3060 12 GB | Qwen3.6-35B-A3B | — | llama.cpp `--n-cpu-moe` | — | issue #194 (2026-10-16) | — | **luka**: modele 35B-A3B mają „DoesNotFit” na 12 GB |

Kontekst firmy: YC, 2 osoby według [Tracxn](https://platform.tracxn.com/a/d/company/62a6455dac10fd5d961a5c5e/magnitude) `[NIEZWERYFIKOWANE]`. Repo założone 2026-06-12 jako „AI coding agent platform” (`AGENTS.md:3`). 6,944★ (gh api, 2026-10-16). Assety wydania `cli@0.2.9` mają 3,460 pobrań w 1 dobę. 1,378 commitów (Anders Lie 608, trg 595).

### 2.2 tqLLM (szczegóły: `/tmp/r15c/notes-tqllm.md`)

| # | Deklaracja | HW | Model / kwant | Obciążenie | Baseline | Wyjście / jakość | Repro | Roofline | Werdykt |
|---|---|---|---|---|---|---|---|---|---|
| T1 | 273.1 t/s reasoning-v1, 199.5 code-v1, „submitted, approved” | 3090 | Qwen3.8-27B-TQ3_4S-v2 (14.50 GB) + DFlash2, KV BF16 | kanoniczne prompty LocalMaxxing, **T=0, 320 tokenów**, thinking on, mediana z 5, 32K | — | „bit-identical” w zgłoszeniu z 10-03, ale exactness naprawiono dopiero 10-13 (`946b683` → `7d7382b`) | **prywatny commit `8c12e1a`**, nie ma go w repo | 13.88 GB/krok, 22.5 ms/krok (616 GB/s = 66%), **6.15 / 4.56 tok/krok** | **wiarygodne tylko dla specjalnego obciążenia** (T=0; początek thinking parafrazuje prompt). Na streszczeniach WikiText 131–155 t/s |
| T2 | 175.9 / 109 t/s na 5060 Ti („not submitted”) | 5060 Ti | TQ_XS 11.85 GB / TQ_S 12.55 GB | LM, T=0 | — | — | brak | ≥4.5 tok/krok | **selektywne raportowanie**: na tablicy są ich zgłoszone **niższe** 156.2 / 100.5 (TQ_S, 10-10) |
| T3 | plain 55.5 t/s | 3090 | TQ3_4S-v2, 12.97 GB/token z head4 | WikiText, greedy, 400 tokenów | — | — | `bench/relbench.py` | 720 GB/s = **77%** | **wiarygodne**. Ta sama sprawność per bajt co nasza |
| T4 | „37% szybciej niż llama.cpp na 35B MoE” | 3090 | MiniCPM-V 4.7 35B-A3B IQ3_S (202.8 vs 136.4) i Q5_K_M (170.3 vs 124) | 3 prompty, greedy, 512 tokenów | llama.cpp `60f0237`, `-ncmoe 2` | — | brak skryptu | IQ3_S: 35% vs 24% roofline | IQ3_S: **wiarygodne** (+49%). Q5: porównuje różne polityki placementu |
| T5 | DGX Spark 132.5 vs 97.6 z drafterem | GB10 | MiniCPM IQ3_S + DSpark | 2 prompty kodowe + 1 proza | llama.cpp + DSpark | — | brak | — | wiarygodne, ale **na prozie drafter spowalnia** (86.5 vs 96.8 bez draftera) |
| T6 | 200K prompt przy 113 t/s na 5060 Ti | 5060 Ti | TQ_XS + DFlash2, KV tq3 | treść promptu nieujawniona | — | — | brak | ≥3.55 tok/krok, przy realnym BW ~5.2 | **tylko dla specjalnego obciążenia** (kopiowanie z kontekstu) |
| T7 | Flash-Next 125B ~16% szybciej niż Strata 0.1.44 (106.84 vs 92.21) | 3090 | GSQ IQ3_S | 5 czatów | Strata z innym draftem | — | build dev | — | **nieweryfikowalne** |
| T8 | „Agenci sami się ulepszają” (Agora, QwenGyre, Alpha/Omega) | — | — | — | — | — | brak artefaktów | tempo commitów pasuje do agentów (test FAIL → fix w 13 min) | **nieweryfikowalne** (deklaracja procesowa) |
| T9 | „Exact greedy z drafterem i bez” | — | — | — | własny plain | od `7d7382b` w obrębie jednej konfiguracji; zmienia się z `-ub`, `--gemm-rows` i między GPU (`matvec_rules.hpp:40-41`); głowa LM to „not a certified argmax” (`README.md:428-438`) | `test-dflash-exact` ręcznie, poza CI | — | **częściowo prawda** |

### 2.3 Actual Computer / „e” (szczegóły: `/tmp/r15c/notes-actual.md`)

| # | Deklaracja | HW | Model | Obciążenie | Baseline | Jakość | Repro | Roofline | Werdykt |
|---|---|---|---|---|---|---|---|---|---|
| A1 | 455 t/s w 1 strumieniu ([case study 2026-10-15](https://actual.inc/company/blog/case-study-dgx-station-and-nemotron-3-5-super-vl)) | DGX Station GB300 (7.1 TB/s; „8 TB/s” dotyczy pełnego B300) | Nemotron 3.5 Super VL, FP8 W8A8, MTP | „preliminary”, własny `e bench`; prompt, T i kontekst nieopublikowane | brak | „output bitwise spec off” (e.strings) | nie | 12.23 B aktywnych ⇒ 12.6 GB/token FP8 ⇒ sufit AR ~452 t/s przy 80% BW; MTP k=3 wymaga ≥2.25 tok/krok | **wiarygodne**, niezależnie **nieweryfikowalne** |
| A2 | >8,000 t/s przy 128 strumieniach (8,046), 10,474 przy 256 | jw. | jw. | jw. | brak | — | nie | sufit AR przy C128 ~4,469 ⇒ wymaga MTP ≥1.9 tok/krok/strumień | **wiarygodne tylko z MTP**; niezależnie catid: Qwen3.8-27B SGLang 6,349 t/s przy C128 |
| A3 | „Users see 2x effective throughput vs leading inference options” | ? | ? | ? | bez nazwy | ? | nie | — | **nieweryfikowalne / marketing** |
| A4 | 100M tokenów/dzień za darmo przez relay | relay | — | 100M/dzień = 1,157 t/s non-stop | — | — | — | nasz 3090 LFM 263.9 t/s ≈ 22.8M/dzień | **wiarygodne jako polityka** |
| A5 | „Zero setup, tuned for your hardware” | — | `e` ma w rejestrze sprzętu tylko „NVIDIA GB300”; reszta to malibu albo aci-cpp (vendored llama.cpp) | — | — | — | — | — | **prawda tylko na GB300**; gdzie indziej to dobór silnika i fit pamięci |
| A6 | „Our confidential relay can't see… Nobody can” | AWS Nitro | — | — | — | — | atestację sprawdziłem ręcznie: SPKI certyfikatu TLS `api.actual.inc` == `public_key` w dokumencie atestacji | — | **częściowo**: TEE jest prawdziwe, ale kod enklawy zamknięty, PCR0 podpisuje samo Actual, web chat idzie przez „web proxy”, a klienci OpenAI SDK nie weryfikują atestacji. Telemetria OTLP domyślnie ON |

### 2.4 TensorFold v1.0.12 (szczegóły: `/tmp/r15c/notes-tensorfold.md`)

| # | Deklaracja | HW | Model | Obciążenie | Baseline | Jakość | Roofline | Werdykt |
|---|---|---|---|---|---|---|---|---|
| F1 | LFM2.5-24B-A2B: 261.5 t/s plain, 299.5 code z n-gramem (#822, #873) | M5 Ultra (~1.2 TB/s) | MLX 4-bit (1.388 GB aktywnych/token) | 256 tokenów, 1 strumień | mlx-lm 178.8 / 181.2 | token_sha stałe, drafted == plain | 363 GB/s = **30%** | **wiarygodne** (jeden autor, jedna maszyna) |
| F2 | n-gram na LFM bitowo dokładny, +10.6% (M4 Pro) i +14.5% (M5) na kodzie, 0% na czacie | M4 Pro, M5 Ultra | jw. | 1 prompt kodu | `--no-drafts` | bitowo | 51 zaoszczędzonych forwardów z ~256 przy koszcie okna 1.24–1.68× | **wiarygodne tylko na kodzie/kopii** |
| F3 | Super VL na 2×GB10: plain 18.8 → 20.2, MTP 38.2 → 46.8 (recipe:86-91) | 2× GB10, NCCL (RoCE) | NVFP4 + FP8 | 8 promptów, 256 tokenów | TP=1 | TP=2 == TP=1 tokenowo | ~9.8 GB/token, 67% BW na 1 GB10; narzut ~160 µs na warstwę MoE `[WNIOSEK]` | **wiarygodne**; skalowanie słabe |
| F4 | `--precision checkpoint`: prefill 1.81×, KL 0.0077 | GB10; RTX PRO 6000 | W4A4/W8A8 | 3 prompty | `--precision full` | inne tokeny, KL zmierzony | prefill compute-bound, FP4 MMA | **wiarygodne** |
| F5 | Recall: powtórzone żądania 2.4× (27B), 3.0× (Nemotron); świeży tekst ±0.3% | M3 Ultra, GB10 | — | powtórki po restarcie | Recall off | weryfikacja targetem | — | **tylko dla specjalnego obciążenia** (powtórki) |
| F6 | HIP 27B: 2×W7800 TP2 39.0 t/s, 4×V620 TP4 40.3 (vLLM-rdna 44.4), 1×V620 z MTP 42 (#655, #626) | gfx1100, gfx1030 | MLX 4-bit | 256 tokenów | vLLM-rdna (inny kwant) | graph == eager | 2×864 GB/s przy 39 t/s = 34% | **wiarygodne i słabe** (nasz 1×XTX: 43.2 plain, 109 z MTP) |

---

## 3. Mechanizmy na poziomie kodu

### 3.1 Magnitude: Seismic, autotune i „precision admission”

**Architektura.** Monorepo Bun/TypeScript (aplikacja desktop, CLI, demon ACN, integracje agentów) plus workspace Rust `inference/` (README):
- `engine/`: rodziny modeli `qwen35`, `lfm2`, `gemma4`, `nemotron_h`, `dflash`, `muse_glimmer`, scheduler, serwer;
- `seismic/`: język, kompilator, runtime, backendy;
- `service/`: HTTP, katalog, assessment.

Historia silnika: `old-inference/` (stary silnik na llama.cpp, „libggml-metal.so” w #82), potem `inference-v2/` i `-v3/` (Python/TileLang, 09.2026), `inference-v4/`, a od #130 (merge `c91b55c7`, 2026-09-27) obecny `inference/`. **Silnik produkcyjny ma 3 tygodnie.**

**Kernele.** 316 deklaracji `native` w 8,628 liniach `.seismic` (`engine/kernels/kernels/*.seismic`) plus implementacje: 81 `.cu`, 85 Metal, 77 Vulkan GLSL.
- Każdy kernel ma „portable body” w Seismic, który jest wyrocznią semantyczną. Natywne implementacje są kandydatami.
- CUDA kompiluje u użytkownika NVRTC 12.9 do CUBIN dokładnie pod jego arch (`docs/compatibility.md`, floor sm_80). Turing i starsze idą przez Vulkan.
- Wagi GGUF są **przepakowywane przy ładowaniu** do własnych układów, np. `iq4g32@mma16` (#175: „failed to qualify repack_weight… E=gguf_iq4_nl, U=iq4g32@mma16”).
- Decode GEMV na CUDA to **MMA bf16/f16 z aktywacją zaokrągloną do A (bf16)** przy dokładnych kodach wag, do 16 wierszy (`cuda_dense.seismic:4-9`). To inna droga niż nasz MMVQ int8 dp4a na q8_1. Kandydat INT8 (aktywacje q8_1 jak w llama.cpp, s8 MMA) jest strojony tylko dla 17–64 wierszy.

**Autotune (`inference/docs/tuning.md`).**
- Przestrzeń: dyskretne parametry per launch. Policzone w deklaracjach:

  | parametr | liczba deklaracji |
  |---|---|
  | KSPLIT | 34 |
  | ROWS | 34 |
  | LANES | 28 |
  | OPERAND | 14 |
  | TILE_M / TILE_N | 14 / 14 |
  | ROTATE | 13 |
  | BATCH_ROWS | 12 |
  | INT8 | 9 |
  | TPW | 7 |
  | WEIGHTS_AHEAD | 6 |
  | STAGERS | 6 |
  | PACK_TOKENS | 6 |

  To dokładnie marketingowe „ile wątków współpracuje” (LANES/KSPLIT), „jak duży kawałek” (ROWS/TILE) i „jak daleko prefetch” (WEIGHTS_AHEAD). Zwykle 2–4 wartości na parametr, np. `KSPLIT in [4, 2, 8]`, `ROTATE in [2, 1, 4]` (`cuda_dense.seismic:28-58`).
- **Dwie klasy parametrów.** `code` nie zmienia arytmetyki (np. ROTATE: „every value gives the same bits”, `cuda_dense.seismic:15-18`). `code arithmetic` zmienia kolejność sum albo precyzję (KSPLIT, LANES, OPERAND, INT8).
- Cel: ważona średnia `time / time_at_defaults` po czterech punktach obciążenia: prefill 4k i 64k, decode przy 4k i 64k historii, z launchami draftera i verify w każdej szerokości, którą load przygotowuje (`tuning.md`, „Performance workload”). Stroją więc **pod realny graf spekulacji**, nie pod pojedynczy kernel.
- Budżet: jeden zegar 60 s (`tuning.md:65`; `STANDARD_TUNING_BUDGET`, `executor/src/native/tuning/mod.rs:331`). Wysiłek dzielony według udziału kernela w czasie (`(effort + price)/(share × opportunity)`). Kompilacja nachodzi na pomiar. Wynik zapisywany per tożsamość (model, kernel, artefakt, urządzenie, toolchain), a kolejne ładowania nie stroją ponownie.
- **Bramka numeryczna:**
  - Kandydat jest uruchamiany na tych samych wejściach co domyślny, z wyzerowanymi wyjściami, żeby wyłapać brakujące zapisy.
  - Dopuszczenie wymaga: liczby całkowite, pakowane i nienapisane wiersze bit w bit; wartości niefinite te same bity; dla floatów `sqrt(Σ(c−d)² / Σ(w²/12)) ≤ α`, gdzie w to szerokość komórki zaokrąglenia typu aktywacji (`comparison.rs:6-19`, `admission.rs:7-12`).
  - α = 8 „set to admit every technique with a measured effect on speed (the packed weight forms measure 3.1 to 6.7)” (`precision.rs:18-22`, `docs/precision.md:4-6`).
  - `[WNIOSEK]` Dla bf16 to RMS ok. 2.3 ulp, czyli ~1–2% względnie na wyjściu każdego kernela. Rząd wielkości jak błąd kwantyzacji aktywacji q8_1 w llama.cpp, więc jakościowo pewnie nie gorzej niż llama.cpp, ale **na pewno nie bitowo**.
  - Tryb `NumericalRequirement::BitExact` istnieje w runtime (`admission.rs:21-23`), ale profil serwujący go nie używa.
- **Ewaluacja jakości** jest zaprojektowana porządnie (`design/inference/evaluation.md`): niezależne referencje f32 per rodzina; KL z teacher forcingiem (mean, p99, max, top-1); przeplatanie A/B; werdykt względem szumu. W publicznym benchmarku jakości jednak nie ma.

**Spekulacja (`design/inference/engine/speculative-generation.md:301-379`).**
- Polityka adaptacyjna.
- Koszty launchy draftera i verify są mierzone per klasa wierszy, kontekst i liczba współdzielących requestów: „Nothing is forecast… A launch not yet measured costs at least what a smaller one measured”.
- Akceptacja trzymana per głębokość (EMA, monotoniczna).
- Runda wybiera budżet z największą liczbą tokenów na sekundę.
- Mechanizm „look”: okresowe rundy szersze niż optymalna, żeby wykryć tekst, który stał się przewidywalny.
- Gwarancje projektowe (`inference/docs/kernels/drafting-and-verification.md:14`): prefill nie płaci za drafter; verify kosztuje tyle co jeden krok decode; draft kosztuje tylko odczyty draftera.

**Skąd prędkość** `[WNIOSEK]`:
- (1) Na Macu i Sparku przewagę daje głównie DFlash/DFlash2 z adaptacyjną szerokością wobec słabego MTP Ollamy, na zadaniu kopiowania.
- (2) Na CUDA bez spekulacji jest **+19% decode** (M3), czyli mniej niż nasz zysk kerneli nad upstreamem na MoE (3090 LFM 180.2 → 263.9, +46%; inny model i inny GPU).
- (3) Koszt: brak bitowej zgodności (α = 8, K8V4, aktywacje bf16) i 26 modeli w katalogu zamiast „dowolny GGUF”.

### 3.2 tqLLM

Własny silnik C++/CUDA (~57 tys. linii, `src/qwen35.cpp` 4,643 linie), tylko sm_86/89/120/121, tylko Qwen3.5/3.8 dense i `qwen35moe`.

- **TQ3_4S:**
  - blok 32 wag = 4 skale E3M5 plus 3-bitowe kody codebooka N(0,1);
  - wagi zapisane w bazie WHT32, a aktywacje obracane raz, w fuzji z RMSNorm, SwiGLU i gate (`kernels/quant.cu:22-42, 432-448`);
  - dekod przez PRMT do fp16 i mma m16n8k16 (`quant.cu:480-588`).
- **Exactness:**
  - tokeny verify leżą w wymiarze N MMA, więc kolumna nie zależy od liczby kolumn;
  - plain decode to `verify(n=1)` (`tools/serve/session.hpp:703-705`);
  - attention dzielona na dwie części w punkcie zależnym tylko od qpos: `tq_split_point(q) = q≥15 ? (q−15)/32·32 : 0` (`kernels/common.cuh:66-72`); merge w stałej kolejności.
- **DFlash2:**
  - jeden niekauzalny przebieg z blokiem 8;
  - lattice rank 256 z top-16 kandydatami na pozycję;
  - drzewo best-first z 8 węzłów;
  - drafter konwertowany przy ładowaniu do TQ3;
  - głowa draftera czyta 65K wierszy draft vocab (`qwen35.cpp:2933-3106`, `dflash.cu:141-255`).
- **MoE `--moe-host-mb`:** najrzadziej trafiani eksperci według profilu routingu idą do pinned RAM, per ekspert, nie per warstwa (`qwen35.cpp:955-1012`). llama.cpp `-ot` / `-ncmoe` tego nie umie, bo działa na całych tensorach `*_exps`.
- **TqCache:** najstarszy KV w RAM przez CUDA VMM plus staging per warstwa (`src/kv_store.hpp:1-53`).
- **Prefill na Ampere:** int8 IMMA przez cuBLASLt na wagach requantyzowanych per wiersz (`kernels/int8_gemm.cuh:1-6`). pp 2,258 t/s przy 2K na 3090, u nas pp512 1,378–1,410.

### 3.3 Actual „e”, malibu, aci-cpp

- **`e`:**
  - 14.9 MB, ELF aarch64 z debug_info; host to ~70 plików `host/a64/*.S` (serwer HTTP, JSON, SSE i gramatyki też w asemblerze);
  - 86 cubinów CUDA 13.2 `-arch sm_103a`; linkuje tylko `libcuda` i `libc`;
  - model jako blob „MSPC” interpretowany przez walker (`walk.S`) z CUDA graphs per krok i PDL;
  - kernele: `nm_route`, `nm_moe_*`, `nm_ssd_*` (Mamba2), `gdn_*` (Qwen3.8), `gemm_dec_q8f*`, `spec_accept`, `mtp_*`, plus `pl_*` (Pearl PoUW mining, opt-in, tylko x86).
- **Precyzja:** `--q8 f` to „vLLM's FP8 W8A8 recipe”, KV bf16.
- **Spec:**
  - `--spec-k 3` (zakres [0,4]), „output bitwise spec off”;
  - `--spec-copy`: wiersz, którego ostatnie 8 tokenów wystąpiło wcześniej, dostaje drafty skopiowane z kontekstu zamiast drafty MTP (przy ≤32 wierszach decode);
  - asercja „the draft path is not batch-invariant”, czyli batch-invariance jest wymaganiem.
- **Scheduler:** `--max-step-ms 50` (chunk prefillu cięty pod budżet kroku), `--max-seqs 128`, nagłówek `X-E-Queue-Wait-Estimate-Ms`, paged KV przez `cuMemCreate`.
- **Wybór silnika w demonie:** `auto`. Wybiera malibu, gdy architektura GGUF jest wspierana; `e`, gdy `e probe` akceptuje model i sprzęt; w pozostałych przypadkach aci-cpp (vendored llama.cpp, ~2,862 symboli `ggml_` w 691–812 MB binarce). Publiczny fork `actual-computer/llama.cpp` ma 0 własnych commitów.
- **Relay:**
  - demon łączy się wychodząco WSS do `api.actual.inc`, więc NAT nie przeszkadza;
  - preflight `GET /api/attestation?nonce=` zwraca dokument Nitro; demon weryfikuje łańcuch do przypiętego roota AWS, nonce i PCR0 z trust-manifestu (JWS EdDSA, `kid rt-1`, wersja 53, gen-44 live 2026-10-15), potem pinuje SPKI TLS;
  - LAN cluster: mDNS plus `Noise_XX_25519_ChaChaPoly_SHA256`;
  - routing **między replikami**, nie sharding jednego modelu.
- **Device auth:** RFC 8628 na własnych ścieżkach `/api/device-auth/{code,token,register,refresh}`, klucz urządzenia i podpisane nagłówki `x-aci-*`. Strona `/device` **autoryzuje oczekujący kod bez kliknięcia** (`useEffect → mutate({action:"authorize"})`) `[WNIOSEK: ryzyko z RFC 8628 §5.4]`.
- **Instalatory:** `curl|bash` i `irm|iex` bez sumy kontrolnej i bez podpisu („unsigned legacy download path”, `install.ps1:6`). Uruchamiają pobraną binarkę przed instalacją (`install.sh:391`) i dopisują PATH do `.profile`, `.zshrc` i `.bashrc`. Aktualizacje w aplikacji są podpisane (cosign).

### 3.4 TensorFold 1.0.12: tylko nowe techniki

1. **Twins:** GEMV na 1, 2–7 i 8–32 wiersze z tą samą kolejnością fma co kafle prompt (`zig/kernels/metal/core/tile_qmv.metal`, `zig/src/core/tile_qmm.zig:122-175`). Przy ładowaniu `twinExact` porównuje bity ścieżek na danym GPU, a przy niezgodności rodzina wraca do 1 wiersza (`tile_qmm.zig:252-290`, `c411e554`). Grupowanie picków po ekspercie od 16 wierszy (#868).
2. **Dokładny dekod 4-bit „half pair” (0x6400)** zamiast pre-scalingu x·2^-4s. Pre-scaling gubi subnormale: x = 2^-126 daje 0x0080 → 0x0000 (`e9bf19d9`). Przy okazji jest szybszy: okno 16 wierszy 61.9 → 47.0 ms.
3. **Recall** (`core/lanes/recall*.zig`, `b2f5b0c8`):
   - klucze 8-tokenowe, dopasowanie ≥16;
   - pasma długości 16/32/64 z EMA 0.95;
   - kopia wchodzi tylko wtedy, gdy bije oczekiwany zysk głowicy MTP;
   - rekord jest trwały na dysku.
4. **TP przez hosty z podziałem samych ekspertów:** rank 0 liczy całość, rank 1 połowę szerokości każdego eksperta; sumy w kolejności udziałów, więc TP=2 == TP=1 bitowo (`cuda_worker.zig:1,44-66`, `98f369a2`).
5. **`--precision checkpoint`:** NVFP4 W4A4 i FP8 W8A8 na MMA sm_120a/121a, wiersze niezależne od sąsiadów (`ck_lane.cu`, `5e8b0a9a`).
6. **HIP:** usunięto chunked prefill GDN na rzecz rekurencji fp32 token po tokenie (`recurrence/gated_delta.hip`). Wybrali exactness kosztem prefillu, co jest przeciwieństwem naszej drogi.

---

## 4. Magnitude kontra nasz PLAN.md

### 4.1 Pokrycie

| Element PLAN.md | Magnitude | Ocena |
|---|---|---|
| §0.1 „zmierzony baseline na komputerze użytkownika” | tuning trace mierzy kernele wobec domyślnych; „przed → po” wobec Ollamy czy llama.cpp w UI: brak dowodów `[NIEZWERYFIKOWANE]` | **luka u nich** |
| §0.1 „optymalizacja poza flagami (kernele, scheduler, spekulacja)” | tak: własne kernele, strojenie 60 s, adaptacyjna szerokość draftu | **pokrywa, i to tańszym UX niż nasza „noc”** |
| §0.1 „weryfikacja te same odpowiedzi (md5/KLD)” | α = 8 per kernel, KV K8V4; KL tylko wewnętrznie, publicznie „quality isn't scored” | **luka u nich**; nasza obietnica jest mocniejsza, o ile ją opublikujemy |
| §0.1 „raport przed → po” | strona benchmarków vs Ollama (kopia, 64k) | częściowo, marketingowo |
| §0.1 „AMD jako pełnoprawna platforma” | tylko Vulkan, niekwalifikowany, błędy iGPU i Strix Halo (#151, #154, #157) | **duża luka u nich** |
| §2 L1 konfiguracja (spekulacja, backend, fit) | tak, automatycznie; drafter z katalogu | pokrywa |
| §2 L2 strojenie lokalne (warianty kerneli) | tak, w 60 s, zamiast nocy | **pokrywa, szybciej** |
| §2 L3 przepisy z labu (per arch × rodzina) | „We write optimized kernels for the most popular open-weight families” (FAQ): 26 modeli w katalogu | pokrywa dla wąskiego katalogu |
| §3.3 integracje agentów, API OpenAI/Anthropic | Pi, OpenCode, Hermes, OpenClaw, Codex, Claude Code, Oh My Pi, Cline, jednym kliknięciem | **wyprzedzają nas** |
| §4.1 silnik = cienka nakładka na llama.cpp | własny silnik, rozbudowywany od nowa (v1–v4 w 4 miesiące) | **tu jest nasza przewaga**: dowolny GGUF, tagi semver upstreamu |
| §4.2 detekcja sprzętu | Seismic topology, pomiar pamięci per proces; liczne błędy dual-GPU i iGPU (#128, #141, #154) | porównywalnie, oni z bugami |
| §4.3 MoE offload | **brak** (#194) | nasza przewaga na 12–16 GB |
| §7 podpis i dystrybucja | desktop Mac/Win/Linux, auto-update, serwer jako usługa | wyprzedzają nas |
| §8 biznes | Apache-2.0, darmowy, YC | jak większość; konkurencja o tych samych ludzi |

### 4.2 Co musimy zrobić inaczej

1. **Baseline:** dwa „przed” zgodnie z PLAN §2 i 01 §3.2 pkt 3, czyli domyślna Ollama oraz **tuned llama.cpp (A1)**. Ich +19% nad llama.cpp na CUDA jest mniejsze niż nasze +23% (3090 Qwen A1 → nasz) i +46% (LFM). To publicznie najmocniejszy argument, ale tylko wtedy, gdy zmierzymy ich silnik na tych samych kartach.
2. **Obciążenie:** zawsze dwie klasy: „nowe pisanie” (nasz spec_sweep, 6 promptów PL/EN, T=1) i „kopiowanie / edycje” (prose-repeat albo copy). Inaczej Magnitude i tqLLM wygrywają samym doborem promptu.
3. **Jakość jako liczba na ekranie wyniku:** greedy md5 względem naszego plain (i względem upstreamu tam, gdzie łatki są bitowe) oraz KLD dla reszty. Ich α = 8 i K8V4 to luka, którą opisujemy faktami, nie przymiotnikami.
4. **AMD natywnie:** HIP/ROCm z PM4 na Linuksie, a na Windows Vulkan i HIP według pomiaru. Magnitude na RDNA3 nie ma ani jednej liczby.
5. **Szerokość:** każdy GGUF z llama.cpp, MoE offload, multi-GPU (ich #141: druga karta ignorowana).
6. **Gdzie odpuszczamy wyścig:** Mac (Metal) i integracje agentów. Tam są dalej, więc kopiujemy wzorzec „1 klik dla agenta” (PLAN §3.3 ekran 6).
7. **Nasze L2 „noc” może być za wolne jako UX:** Magnitude stroi w 60 s przy pobraniu modelu. Naszą „szybką kalibrację 1–5 min” (PLAN §4.3) trzeba utrzymać poniżej ~1 min dla wariantów bitowych, a noc zostawić na przepisy i spekulację na tekstach użytkownika.

---

## 5. Transfer na nasz stos i ranking

### 5.1 Budżet czasu, który atakujemy

- Qwen3.8-27B, XTX: 27.74 ms/krok przy ok. 3.0 tok/krok (109 t/s).
- Qwen3.8-27B, 3090: 38.4 ms/krok, 3.31 tok/krok. Bajty na krok `[WNIOSEK]`: target 17.56 GB plus 4 × (warstwa MTP IQ4_XS ~0.22 GB + głowa draftu 65K × 5120 × 4.25 bit ≈ 0.18 GB) ≈ **19.2 GB**. Floor przy 936 GB/s to 20.5 ms, czyli ok. 53% pasma.
- tqLLM: 13.9 GB i 22.5 ms/krok (66%).
- Nasza nadwyżka ponad floor (~18 ms) to verify 5 wierszy, 4 sekwencyjne przebiegi MTP i granice kerneli (3090: 795 kerneli/token, przerwy 2.55 ms).
- LFM2.5, XTX: 3.41 ms/token, czyli narzut ponad roofline 1.55 ms (TF: 2.7–3.5 ms na Macach).

### 5.2 Korekta notatki o tqLLM

Notatka robocza proponowała jako #1 „4-bit głowa draftu + 65K draft vocab dla MTP”. **To już mamy:** `--spec-draft-vocab-n 65536 --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs` (`research/09-chmura-3090.md:28`), co dało ×1.12 na 3090. Pozycja odpada z rankingu. Zostaje tylko wariant „verify-head 4-bit + int8 rescore”, który nie jest exact, więc go odrzucamy.

### 5.3 Ranking

Ranking według (oczekiwany zysk na naszym wąskim gardle × pewność) / wysiłek:

| # | Pomysł (źródło) | Co atakuje | Maks. zysk na naszych profilach `[WNIOSEK]` | Co zmienić | Wysiłek (os.-dni) | Ryzyko | Platformy |
|---|---|---|---|---|---|---|---|
| 1 | **LocalMaxxing i dwie klasy obciążenia w raporcie** (tqLLM, Magnitude) | wiarygodność zewnętrzna | 0% prędkości. Na XTX nie ma żadnego verified runu Qwen3.8-27B (`/api/agent-context`, wyszukiwanie 10-16) | `lmx speed-test run --canonical-prompt reasoning-v1/code-v1`; spec_sweep z klasą „copy” | 0.5–1 | niskie | wszystkie |
| 2 | **Spec-copy / n-gram wpięty w MTP, wyceniany kosztem okna** (Actual `--spec-copy`, TF Recall, TF n-gram LFM, Magnitude adaptive) | tok/krok na kodzie, edycjach i turach agenta | Qwen: tury kopiujące +30–100% (Recall 2.4×), proza 0. LFM: kod −0.3…0.45 ms/token eff. (+10–15%). Czat 0, jeśli jest guard | upstream ma `ngram-*` i `--lookup-cache-dynamic` (`common/arg.cpp:1625, 4259-4380`). Brakuje: tabeli kosztu k = 1..8 na prawdziwym tekście, reguły `E[tok]/cost(k) > plain`, łączenia z MTP | 2–5 | regres czatu bez guardu; kalibracja na powtórkach zaniża koszt MoE o 7–10% (TF `0e081cfe`) | host: wszystkie |
| 3 | **Adaptacyjna szerokość draftu z mierzonymi kosztami launchy i akceptacją per głębokość** (Magnitude `speculative-generation.md:301-379`) | dobór n dla MTP i DFlash2 | wyjaśnia nasze DFlash2 n=15 < MTP (89.7 vs 104.8). Zysk 0–5% na mieszance, więcej na zmiennym tekście. U nas T2 (wycena głębokości) wyszło równo albo gorzej, więc pewność średnia | `speculative.cpp`: tabela kosztów per klasa wierszy, EMA per głębokość, „looks” | 3–5 | niskie | host |
| 4 | **Batch-invariant verify ⇒ greedy ze spekulacją == plain** (tqLLM, Actual, TF twins) | 0 ms. Produkt: bramka md5 działa przy włączonym spec, a hasło „te same odpowiedzi” obejmuje spec | 0% prędkości, możliwy koszt −2…5% plain | MMVQ multi-kolumnowy (0001/0002) z kolejnością 1-kolumnowego; split FA zależny tylko od pozycji; plain przez verify(1) | 5–10 | średnie (wydajność) | HIP, CUDA; Vulkan osobno |
| 5 | **Int8 IMMA prefill na Ampere** (tqLLM `int8_gemm.cuh`) | prefill i TTFT (nasz słaby punkt) | pp 2,258 vs nasze 1,378–1,410 przy 2K: do +60%. Część różnicy to mniejsze wagi `[WNIOSEK]` | najpierw profil MMQ sm_86 (czy int8 mma chodzi na pełnej przepustowości), potem ścieżka requant per wiersz → IMMA dla dużych batchy | 2–4 | jakość: requant per wiersz jest stratny, KLD-gate | tylko CUDA sm_86/89 |
| 6 | **Per-expert placement MoE w RAM z profilu routingu** (tqLLM) | modele większe niż VRAM na 12–16 GB | tylko gdy model się nie mieści: tqLLM 170.3 vs 124 (+37%); Magnitude tego nie ma (#194) | rozbić `*_exps` na hot i cold, remap id w MUL_MAT_ID | 5–8 | profil zależny od tekstu | CUDA, HIP |
| 7 | **TQ3_4S jako kwant** (tqLLM, fork llama.cpp-tq3 z portem HIP) | bajty na krok | 17.6 → ~13.9 GB: floor na XTX 18.3 → 14.5 ms, czyli **−3.8 ms/krok (~−14%)** | port typu 46 do naszego MMVQ/MMQ | 3–6 (CUDA, HIP) | **jakość nieznana**: TQ_S KLD 0.055, TQ_XS 0.079 vs BF16 (HF YTan2000), czyli kilka razy gorzej niż UD-Q4_K_XL; TQ3_4S-v2 bez KLD | CUDA, HIP; Vulkan/Metal 5–10 |
| 8 | **DFlash2 blok 8 + drzewo 8 dla hybrydy GDN** (tqLLM) | tok/krok | T=0 LM reasoning: mal 6.15 vs nasze ~3.3; przy T=1 i PL nieznane | tree verify GDN (dwa sloty stanu, replay); lattice | 10–20 | wysokie: przy T=1 i dla PL może przegrać z MTP | HIP, CUDA |
| 9 | **Lokalne strojenie tylko parametrów bitowo neutralnych przy pierwszym starcie, ≤60 s** (Magnitude: klasy `code` / `code arithmetic`) | 0–5% kerneli na nieznanych kartach | według raportu 02 wynik zależy od (arch, kształt), nie od egzemplarza, więc mały | podział parametrów w `kt-table-<arch>.inc` na „bit-neutral” (lokalnie bez bramki) i „arithmetic” (tylko z labu z KLD) | 2–4 | niskie | HIP, CUDA |
| 10 | **Metryka „α kroków zaokrąglenia vs domyślny”** w `test-backend-ops` dla niebitowych łatek (Magnitude `comparison.rs`) | higiena bramek | 0% | `sqrt(Σ(c−d)²/Σ(w²/12))` vs kernel bazowy, obok FP64-ref i mutacji (TF #608) | 1–2 | brak | wszystkie |
| 11 | `llms.txt` / runbook instalacji dla agentów (Actual) | dystrybucja | — | strona i plik | 0.5–1 | — | — |
| 12 | Scheduler z budżetem czasu kroku i wyceną kolejki (Actual `--max-step-ms`, `X-E-Queue-Wait-Estimate-Ms`) | persona 3 (wielu użytkowników) | p99 ITL | dynamiczny chunk prefillu w llama-server | 3–5 | — | host |
| 13 | Device-code login **z ekranem potwierdzenia** plus relay E2E (Actual, ale bez ich błędów) | persona 3, zdalny dostęp | — | backend, UI; relay: Noise/WireGuard albo TEE | 3–5 (login), 15–25 (relay) | operacyjne i prawne | — |

Czego nie kopiujemy:
- ręcznego asemblera hosta (`e`);
- Pearl miningu i tokenów Bittensor;
- `curl|bash` bez sum kontrolnych;
- auto-autoryzacji urządzeń;
- α = 8 jako domyślnej polityki;
- rekurencji GDN token po tokenie w prefillu (TF HIP);
- „half pair” 0x6400: nasze MMVQ to int8 dp4a.

---

## 6. Projekty eksperymentów

Żaden nie wymaga lokalnego GPU. GPU = chmura, **do zatwierdzenia**. Ceny Vast z PLAN §1: 3090 ~$0.23/h, 5060 Ti podobnie.

**X1. Magnitude vs nasz fork na tych samych kartach (zewnętrzna walidacja M1–M3).**
- Hipoteza: na 3090 i 5060 Ti (oba w ich floorze sm_80+) nasz fork bije Magnitude na spec_sweep T=1 (nie-kopia). Magnitude wygrywa na prose-repeat (kopia).
- Prototyp:
  - ich harness: `magnitude-bench run --mode prose-repeat --model qwen3.8-27b:gguf:q4 --context 64k --engine magnitude --passes 2 --fresh-tuning` i `--engine llama.cpp --llama-binary <nasz llama-server>`;
  - nasz spec_sweep przez ich serwer OpenAI;
  - LFM2.5-24B-A2B (u nich bez draftera) jako czyste porównanie kerneli.
- Pomiar: ABBA, t/s, tokeny na rundę, czas tuningu z ich trace'u. Dla Qwena greedy md5 nasz plain vs nasz MTP oraz KLD ich wyjścia wobec referencji BF16 (`llama-perplexity --kl-divergence`).
- Koszt: ~3 h × 2 karty ≈ **$1.5–2**.
- Kill: jeśli Magnitude na nie-kopii jest ≥ nasz fork −5% na obu kartach, nasza przewaga kerneli na NVIDIA nie istnieje, a PLAN §2 L3 dla NVIDIA trzeba przepisać.

**X2. LocalMaxxing: verified runy forka.**
- Hipoteza: XTX MTP n=4 przy T=0 na reasoning-v1 daje ≥130 t/s i mal ≥3.8, czyli pierwsze miejsce verified na XTX (dziś 0 verified).
- Prototyp: `lmx speed-test run --canonical-prompt reasoning-v1|code-v1` na naszym serwerze.
- Pomiar: t/s, mal, status verified.
- Koszt: $0 na XTX, ale **wymaga zgody na lokalne GPU** (~15 min); 3090 w chmurze ~$0.3.
- Kill: <90 t/s na 3090. Wtedy priorytet przechodzi na drafter (#8), a publikację wstrzymujemy.

**X3. Tabela kosztów okna i n-gram na LFM (#2).** Za TF E1/E2.
- Hipoteza: na XTX `cost(k)/cost(1)` ≤ 1.35/1.9/3.2 dla k = 2/4/8, a n-gram z guardem daje kod +8–15% i czat ≥ −1%.
- Prototyp: `llama-bench -p 1,2,4,8,16 -n 0 -ub 16` jako górna granica (losowe tokeny), potem forward k tokenów z prawdziwego tekstu. Upstream `--spec-type ngram-mod` bez zmian, potem guard.
- Pomiar: spec_sweep 6 × 3, T=1.
- Koszt: 1–2 dni pracy plus ~1 h GPU (XTX za zgodą albo 3090 $0.3).
- Kill: cost(2) > 1.5 i cost(4) > 2.3 albo kod < +5%.

**X4. Exactness MTP == plain (#4).**
- Hipoteza: rozjazd md5 bierze się z ≤2 opów (MMVQ multi-col, FA split-K).
- Prototyp: greedy md5 plain vs MTP na 6 promptach; bisekcja pierwszego tensora, który się różni (dump przez eval-callback).
- Pomiar: indeks pierwszego różnego tokenu, op.
- Koszt: 1–2 dni, GPU < 1 h.
- Kill: rozjazd w >2 niezależnych opach. Wtedy koszt to >10 os.-dni i odkładamy.

**X5. KLD TQ3_4S-v2 i TQ_S vs UD-Q4_K_XL (#7), $0 GPU niemożliwe, więc chmura.**
- Hipoteza: TQ3_4S ma KLD ≤ 1.5× UD-Q4_K_XL przy −18% bajtów.
- Prototyp: `llama-perplexity --kl-divergence-base` z BF16; TQ przez fork llama.cpp-tq3 (CUDA).
- Koszt: ~3 h na 3090 ≈ $0.7.
- Kill: KLD > 1.5× UD-Q4_K_XL, wtedy nie portujemy.

**X6. Referencyjna akceptacja DFlash2 blok 8 + drzewo (#8) na naszych promptach.**
- Hipoteza: tqLLM przy T=1 na PL ma mal ≥ 3.5, czyli więcej niż nasze MTP 3.3.
- Prototyp: obraz Docker `ghcr.io/turbo-tan/tqllm:1.0.0` na 3090, nasze 6 promptów przy T=0 i T=1.
- Koszt: ~2 h ≈ $0.5.
- Kill: mal przy T=1 na PL < 3.5. Wtedy nie budujemy tree-DFlash2.

**X7 ($0 CPU, offline). Ekonomia verify MoE.**
- Hipoteza: dla LFM2.5 (64 eksperty, top-4) unia ekspertów przy k = 2/4/8 to 1.94/3.6/6.5× `[WNIOSEK z 64·(1−(60/64)^k)/4]`. Przy losowym routingu koszt okna MoE rośnie więc prawie liniowo, a n-gram opłaca się tylko przy wysokiej akceptacji.
- Prototyp: rachunek plus histogram picków z dumpów routera (jeśli mamy logi), bez GPU.
- Kill: nie dotyczy (to analiza, która ustawia próg dla X3).

---

## 7. Dowody zewnętrzne

| Temat | Co jest | Czego brak |
|---|---|---|
| Magnitude | issues z liczbami użytkowników: tylko #82 (stary silnik na llama.cpp, 6× wolniej, naprawione); harness otwarty; 6.9k★ | **brak niezależnych benchmarków nowego silnika**, brak wpisów LocalMaxxing `[NIEZWERYFIKOWANE: przeszukałem tablicę 3090 i issues]`, brak liczb RDNA3 |
| tqLLM | LocalMaxxing: verified runy `cmuspkbsg008erx01bvmv1y6l` (273.1) i `cmusplwgl008hrx01ba1um6d1` (199.5), engine „TQLLM (tanllm) 8c12e1a” (sprawdziłem przez API 10-16); 5060 Ti `cmv2vel9u00jnmr011nbtgqet` (156.2). Kontekst 3090: EXL3 242.1 / 169.6, llama.cpp MTP 82.7 | 0 niezależnych reprodukcji; 15★, 0 issue; repo „recipes” zwraca 404 |
| Actual | [catid/dgx_station_benchmarks](https://github.com/catid/dgx_station_benchmarks): Qwen3.8-27B SGLang MTP 6,349 t/s C128, DFlash2 265.8 C1, llama.cpp ~240 C128; specyfikacja Station: [NVIDIA](https://www.nvidia.com/en-us/products/workstations/dgx-station.md), [STH](https://www.servethehome.com/nvidia-dgx-station-systems-available-at-last-gb300-gb200-workstations-for-your-desktop/) | nikt poza Actual nie publikuje Nemotron 3.5 Super na Station |
| TensorFold | receipts kontrybutorów (BlivionIaG `lfm2-receipts`), kontrole vLLM w #655/#804, Liquid AI: [LFM2.5-24B 184 t/s na M5 Max](https://www.liquid.ai/blog/lfm2-5-24b-a2b) | ashhart: „single runs… not alternated”; brak wpisów TF w LocalMaxxing dla 3090 / Qwen3.8-27B |

Co potwierdziłoby albo obaliło deklaracje:
- **Magnitude:** nasze X1, czyli ich harness na 3090/5060 Ti plus nasz spec_sweep. Także wpis do LocalMaxxing z ich silnikiem i ich odpowiedź w issue o porównaniu z llama.cpp.
- **tqLLM:** publikacja commitu `8c12e1a` i powtórzenie rekordu z publicznego obrazu; KLD dla TQ3_4S-v2.
- **Actual:** wyniki `e` od niezależnego posiadacza Station, np. catid, z promptami i T.
- **TF:** przeplatane powtórki ashharta, LFM na CUDA.

---

## 8. Aktualizacja obrazu konkurencji (`research/01-konkurencja.md`)

### 8.1 Nowe wiersze do tabeli „Nowe projekty nastawione na prędkość” (01 §2.1)

| Produkt | Dla kogo | Sprzęt | Co jest automatyczne | Poziom | Prędkość / przed → po | Licencja, trakcja |
|---|---|---|---|---|---|---|
| **Magnitude** ([repo](https://github.com/magnitudedev/magnitude), [site](https://magnitude.dev)) | użytkownicy agentów kodujących, Mac i NVIDIA | Metal (Apple M*), CUDA sm_80+, Vulkan 1.3 (AMD, Intel, Turing), CPU; Mac/Win/Linux | rekomendacja modelu; kernele strojone ≤60 s przy pobraniu (α = 8, nie bitowo); drafter z katalogu (DFlash/DFlash2/DSpark/MTP) z adaptacyjną szerokością; KV K8V4; prefix cache; 1 klik do 8 agentów; tryb serwera | **K** (pierwszy konsumencki K) | 2.19× / 2.17× decode vs domyślna Ollama na kopii przy 64k; vs llama.cpp bez spec +19% decode (Spark) | Apache-2.0, **6.9k★ w 4 miesiące**, YC, ~2 osoby |
| **tqLLM** ([repo](https://github.com/turbo-tan/tqllm), [site](https://tqllm.com)) | 1 użytkownik, 1 GPU NVIDIA | tylko CUDA sm_86/89/120/121 (Docker, Linux/WSL2) | dobór kerneli per CC plus timing wariantów bit-identycznych (próg 2%); fit pamięci | **F/K** (lekki) | 3090 Qwen3.8-27B: plain 55.5 (TQ3), DFlash2 273.1 na LocalMaxxing przy T=0 | Apache-2.0, 15★; rekord z prywatnego buildu |
| **Actual Computer** ([site](https://actual.inc)) | zespoły i firmy („department AI factory”), agenci | `e` tylko GB300; malibu (Rust, NVIDIA i Apple) i aci-cpp (llama.cpp) dla reszty | wybór silnika (`e probe` → malibu → llama.cpp), fit, relay, klastry LAN | **R/M** konsumencko; **K** tylko na GB300 | Station: 455 C1 / 8,046 C128 (własny bench) | zamknięty; free do 100M tok/dzień; ~3 osoby |

### 8.2 Zmiany w istniejących wierszach i tezach

- **01 §2.4, wiersz „Kernele, graf, JIT: u konsumenta LLM nikt”** jest nieaktualny. Magnitude stroi kernele na urządzeniu (60 s), a tqLLM wybiera warianty bit-identyczne przy ładowaniu. Nowa teza: **nikt nie łączy strojenia z bitową bramką ani z publikowanym KLD**. Magnitude ma bramkę błędu względem domyślnego kernela (α = 8), nie względem modelu.
- **01 §2.4, „Weryfikacja poprawności po strojeniu”:** dopisać Magnitude (bramka α per kernel, wewnętrzne KL) i tqLLM (spec == plain w jednej konfiguracji).
- **01 §2.1, TensorFold:** LFM2.5 na Metal (261.5 t/s M5 Ultra), HIP jako preview ze źródeł, Recall, TP przez hosty. Na NVIDIA i AMD nadal nie konkuruje z nami na LFM ani na 27B.
- **01 §2.8, zagrożenia:** nowy wiersz.
  - Zagrożenie: „Magnitude jako »LM Studio z własnymi kernelami« dla agentów”.
  - Dowód: 6.9k★, 1 klik do 8 agentów, desktop 3 OS.
  - Prawdopodobieństwo: **już jest**. Wpływ: **wysoki na Mac i NVIDIA, niski na AMD**.
  - Odpowiedź: AMD natywnie, uczciwy baseline i jakość na ekranie wyniku, dowolny GGUF i MoE offload, LocalMaxxing.
- **01 §3.1, tabela „kto jest blisko”:** Magnitude ma 2 i 3, oraz 5 w wersji marketingowej. Brakuje mu 1 (pomiar przed → po na maszynie użytkownika), 4 (md5/KLD) i 6 (AMD natywnie).
- **PLAN §0.1, teza „Żaden nie robi naraz…”:** w mocy, ale trzeba ją zawęzić. „Optymalizacja poza flagami” nie jest już wyróżnikiem. Wyróżnikiem jest kombinacja **weryfikacji (md5/KLD) + przed → po wobec tuned upstream + AMD natywnie**.
- **PLAN §2, L2 „noc”:** dodać „szybki lokalny tuning bitowo neutralnych parametrów ≤60 s” jako część kalibracji. Konkurencja ustawiła oczekiwanie „przy pobraniu, nie w nocy”.

---

## 9. Źródła

**Magnitude** (klon `/tmp/r15c/magnitude`, HEAD `1f54d5b7`, 2026-10-15):
- strony: https://magnitude.dev, https://magnitude.dev/benchmarks;
- kod i dokumenty w `inference/`:
  - `README.md`; `docs/tuning.md:65`; `docs/precision.md:4-6`;
  - `docs/compatibility.md:128,150`; `docs/kernels/drafting-and-verification.md:14`;
  - `engine/executor/src/native/tuning/precision.rs:18-22`; `engine/executor/src/native/tuning/mod.rs:331`;
  - `seismic/runtime/src/native/admission.rs:1-32`; `seismic/runtime/src/native/comparison.rs:1-20`;
  - `engine/src/options.rs:121,426`; `engine/kernels/kernels/cuda_dense.seismic:1-58`; `engine/kernels/kernels/dense_rows.seismic:1-60`;
  - `catalog/models.json`; `evaluation/fixtures/src/magnitude_fixtures/prose.py:1-16`;
- dokumenty projektowe: `design/inference/kernel-formation.md`, `design/inference/seismic-numerical-precision.md`, `design/inference/evaluation.md`, `design/inference/engine/speculative-generation.md:200-379`, `design/inference/engine/prefix-cache.md`;
- commity `658cb1ec`, `00268e25`, `c3d4254a` (#181); PR #130 (merge `c91b55c7`);
- issues: https://github.com/magnitudedev/magnitude/issues/82, /141, /151, /154, /157, /162, /175, /194;
- HF: https://huggingface.co/magnitudedev/Qwen3.8-27B-DFlash2-GGUF (kopia z z-lab, 2.06 GB), API `models?author=magnitudedev`.

**tqLLM:** https://github.com/turbo-tan/tqllm (HEAD `23af3c9`), https://tqllm.com, https://tqllm.com/performance.html. Pliki: `src/qwen35.cpp`, `kernels/quant.cu:22-42,480-593,2852-2924`, `kernels/common.cuh:66-72`, `kernels/int8_gemm.cuh:1-6`, `kernels/formats/matvec_rules.hpp:1-52`, `README.md:428-438`. Commity `36bd7fa`, `946b683`, `7fb94d7`, `7d7382b`, `baa4df8`. LocalMaxxing: https://www.localmaxxing.com/api/agent-context, `/api/speed-tests?hfId=Qwen/Qwen3.8-27B&gpuName=RTX%203090`. HF: https://huggingface.co/YTan2000/Qwen3.8-27B-TQ, https://huggingface.co/YTan2000/Qwen3.8-27B-TQ3_4S.

**Actual:** https://actual.inc, https://actual.inc/llms.txt, https://actual.inc/company/blog/case-study-dgx-station-and-nemotron-3-5-super-vl, https://actual.inc/install, https://dl.actual.inc/install.ps1 (build `09f197a`), https://actual.inc/.well-known/relay-trust.json, https://github.com/actual-computer. Config modelu: https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16. SN95: https://taodaily.io/everything-worth-knowing-about-actual-computer-sn95. Pearl: https://pearlresearch.ai/Pearl_Whitepaper.pdf.

**TensorFold:** https://github.com/ashhart/TensorFold/releases/tag/v1.0.12 (`833bbfcb`); PR-y /pull/821, /822, /823, /867, /868, /871, /873 (LFM), /655, /626 (HIP), /804 (GLM), /796, /833; commity `e9bf19d9`, `c411e554`, `b2f5b0c8`, `98f369a2`, `5e8b0a9a`; `docs/recipes/nemotron-3.5-super-vl.md:86-91`, `docs/recall.md`.

**Nasze:** `~/KERNEL/wiki/index.md`, `~/KERNEL/product/BENCHMARKI-NVIDIA-2026-10-16.md`, `~/KERNEL/product/research/09-chmura-3090.md:28,49,160`, `~/KERNEL/qwen-opt/research/tensorfold/update-v1.0.11.md`, `~/KERNEL/product/research/01-konkurencja.md`, `~/KERNEL/product/PLAN.md`.

---

## 10. Do bazy wiedzy

Proponowane wpisy; podagent nie edytuje wiki. Nazwy plików są unikalne w vaulcie, foldery istnieją.

| Folder | Tytuł (plik) | Streszczenie w 1 linii | Kluczowe liczby (źródło) |
|---|---|---|---|
| `research/` | Raport 15c: nowe silniki (`raport-15c-nowe-silniki.md`) | teardown Magnitude, tqLLM, Actual i TF 1.0.12: kto naprawdę jest szybszy i dlaczego | ten raport; status `do-sprawdzenia` dla liczb konkurencji |
| `repo/` | Magnitude: silnik Seismic z autotunem 60 s (`magnitude.md`) | własny silnik Rust z kernelami Metal/CUDA/Vulkan, strojenie przy pobraniu z bramką α = 8 (nie bitową); AMD tylko przez Vulkan | α = 8 (`precision.rs:22`); budżet 60 s (`tuning/mod.rs:331`); KV K8V4 domyślnie (`options.rs:121`); vs llama.cpp +19% decode Spark (`658cb1ec`); vs Ollama 2.17–2.19× na prose-repeat 64k (magnitude.dev/benchmarks); 6,944★ (2026-10-16) |
| `repo/` | tqLLM: silnik CUDA dla Qwen3.8 z TQ3 i DFlash2 (`tqllm.md`) | rekord LocalMaxxing 3090 przy T=0 z prywatnego buildu; per bajt plain jak my | 273.1 / 199.5 t/s, mal 6.15 / 4.56, 22.5 ms/krok, 13.9 GB/krok (LocalMaxxing `cmuspkbsg008erx01bvmv1y6l`); plain 55.5 t/s = 77% BW; TQ_S KLD 0.055 (HF YTan2000) |
| `ludzie-firmy/` | Actual Computer (`actual-computer.md`) | relay na AWS Nitro i silnik „e” tylko pod GB300; konsumencko llama.cpp i malibu | 455 C1 / 8,046 C128 t/s (blog 2026-10-15, własny bench); sufit AR 452 / 4,469 przy 7.1 TB/s (rachunek); free 100M tok/dzień |
| `repo/` (aktualizacja) | TensorFold (`tensorfold.md`) | v1.0.12: LFM2.5 tylko Metal, twins, Recall, TP ekspertów, HIP preview | M5 Ultra LFM 261.5 plain (30% BW) vs nasz XTX 293.7 (54%); 2×W7800 27B 39.0 t/s (#655); Super VL 2×GB10 MTP 38.2 → 46.8 (recipe:86-91) |
| `research/` (aktualizacja) | Raport 01: konkurencja (`raport-01-konkurencja.md`) | strojenie kerneli u konsumenta już istnieje (Magnitude); wyróżnik = weryfikacja + baseline vs tuned upstream + AMD | §8 tego raportu |
| `produkt/` (aktualizacja) | Ryzyka produktu (`produkt-ryzyka.md`) i Werdykt (`werdykt.md`) | nowe ryzyko: Magnitude na Mac i NVIDIA z integracjami agentów; zawężenie tezy „nikt nie robi naraz” | 6.9k★ w 4 mies.; brak HIP, brak bitowej bramki, brak MoE offload (#194) |
| `metody/` (aktualizacja) | Zgodność bitowa / md5 (`zgodnosc-bitowa-md5.md`) | (1) metryka „α kroków zaokrąglenia vs kernel domyślny” jako uzupełnienie FP64-ref; (2) świadek subnormalny dla dekodu 4-bit (TF) | `sqrt(Σ(c−d)²/Σ(w²/12))` (Magnitude `comparison.rs:16-19`); x = 2^-126: 0x0080 → 0x0000 (TF `e9bf19d9`) |
| `metody/` (aktualizacja) | Pomiar ABBA (`pomiar-abba.md`) | zawsze dwie klasy obciążenia (nowe pisanie i kopia) oraz T=0 i T=1 osobno; benchmarki konkurencji wygrywają doborem promptu | Magnitude prose-repeat; tqLLM T=0 na 320 tokenach; tqLLM 131–155 t/s na WikiText wobec 273 na LocalMaxxing |
| `kernele/` (aktualizacja) | Fuzje weryfikacji (`fuzje-weryfikacji.md`) | batch-invariant verify: punkt podziału attention zależny tylko od qpos, kolumny MMA niezależne, plain = verify(1) | `tq_split_point` (tqllm `kernels/common.cuh:66-72`); naprawione 10-13 (`7d7382b`); Actual: „output bitwise spec off” |
| `kernele/` (aktualizacja) | Fuzje LFM MoE (`fuzje-lfm-moe.md`) | koszt okna weryfikacji LFM według TF i unia ekspertów | cost(k)/cost(1) = 1.24 / 1.68 / 2.81 / 5.05 dla k = 2/4/8/16 (M5 Ultra, #868); unia 64·(1−(60/64)^k) (rachunek) |
| `eksperymenty/` (nowy, gdy ruszy) | X1: Magnitude vs nasz fork na 3090/5060 Ti (`2026-10-xx-magnitude-vs-fork.md`) | plan: ich harness i nasz spec_sweep, kopia i nie-kopia | koszt ~$1.5–2; kill: Magnitude ≥ fork −5% na nie-kopii |
| `lekcje/` (nowa) | Benchmark na kopiowaniu zawyża spekulację (`lekcja-benchmark-kopia.md`) | zadania „powtórz tekst” dają 4–6 tok/krok i nie mówią nic o nowym pisaniu | Magnitude Spark 27B ≥4.8 tok/rundę (roofline); tqLLM 350–365 t/s na copy vs 131–155 na streszczeniach |
| `ludzie-firmy/` (aktualizacja) | Ollama (`ollama.md`) | baza porównania Magnitude to Ollama v0.35.1 z domyślnymi ustawieniami; jej MTP na Macu przy 64k prawie nie draftuje | Gemma 4 31B Mac 8.6 t/s (magnitude.dev/benchmarks) |
