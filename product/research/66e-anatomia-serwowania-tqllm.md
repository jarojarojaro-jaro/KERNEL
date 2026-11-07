# 66e: anatomia silnika serwującego (vLLM vs SGLang) na tle llama-server oraz tqLLM 1.4.4

Data: 2026-11-07. Autor: podagent R66e_ServingAnatomy. Praca tylko na CPU: bez GPU, bez pobierania modeli, serwer :8080 nietknięty. Klon kodu: `~/src/research66/tqllm` (`--depth 1`). Jedyny pomiar to mikrobench CPU budowy maski KQ (§3.3, `66e-skrypty/maskbench.cpp`).
Oznaczenia: `[INFERENCE]` = wniosek bez pomiaru; „deklaracja producenta” = liczba ze strony lub CHANGELOG-u, której nie powtórzyliśmy.

## 1. TL;DR

1. **Artykuł Kumara (część 1 z 10)** opisuje, gdzie vLLM 0.32 i SGLang 0.5.22 tną 5 warstw (L1 frontend … L5 klaster) na procesy oraz ile kosztuje to IPC na krok. **llama-server ma wszystko w jednym procesie**: L1 w wątkach HTTP, a L2+L3+L4 w jednym wątku `server_context`. Kosztu IPC na krok więc nie ma, a nasza luka hosta jest już zmierzona: **GPU stoi 410 µs/krok (~1.5% z 27.3 ms)** przy krótkim kontekście ([37 §2](37-proza-100.md)). Tanie cięcia zostały już wzięte (24o, 37).
2. **NOWE dla nas:** (a) nikt nie zmierzył luki hosta przy 94k/199k. Budowa maski KQ na CPU rośnie z `n_kv`: mój mikrobench CPU daje **0.25 ms na graf weryfikacji (5 wierszy) przy 199k** wobec 1 µs przy 2k. To jedyny kandydat na koszt hosta zależny od długości. (b) Parser czatu O(n²) w wątku HTTP (0.07 → 0.52 ms/token, [39c](39c-deepseek-v41-deployment.md)): tqLLM ma gotowy wzorzec O(n) z wyrocznią testową.
3. **tqLLM 1.4.4** (`9a9e7e5`, 2026-11-07, Apache-2.0, 51★) to silnik C++ dla rodziny Qwen3.5/3.8 i kilku MoE (CUDA sm_86–121 i Metal). Nie ma ROCm, Intela ani Vulkana (Android to pusty folder). „TurboQuant” to **stratne** kwanty wag (TQ3/TQ4/TQ3_4S) i KV (tq3, turbo2–4, tcq2/3), więc ląduje w sekcji 6. Spekulacja jest u nich bezstratna (greedy token w token).
4. Liczby z tqllm.com w większości już znamy (273.1 t/s na 3090; „1.63× Strata” = 77.1 vs 47.2 t/s z 1.2.x). Nowe w 1.3–1.4.4: `--exact on` jako domyślny, bitowo dokładna atencja na Metalu (reguła T(x)), ANE w prefillu (stratne), GB10 i `MemAvailable`, CUDA graphs przegrywające z bezpośrednimi launchami na sm_120 w ich silniku, eksmisja „MRU-other” w cache ekspertów, rejestr flag env.
5. **Top 3 testy:** T1 ślad luk hosta przy 94k/199k (20 min GPU, kod już jest); T2 parsowanie czatu raz na krok i O(n) (CPU + 10 min GPU); T3 maska KQ poza ścieżką krytyczną, tylko jeśli T1 ją pokaże (+0.5…1.5% przy 199k `[INFERENCE]`).

## 2. Co to jest

### 2.1 „Anatomy of an LLM Serving Engine” (Aditya Kumar)

- Typ: wpis na blogu, część 1 z 10-częściowej serii. Opublikowany 2026-10-28, zaktualizowany 2026-11-01. Przypięty do vLLM 0.32.0 (`5df63a7`) i SGLang 0.5.22 (`baa9bef`). Licencja CC BY 4.0. Autor deklaruje pomoc AI przy pisaniu.
- Sprzęt: brak. Autor pisze wprost: „I haven't run the script on a GPU, so there are no measurements here”. Jedyna liczba wydajności pochodzi z cudzego źródła: profil vLLM v0.6.0 dla Llama 3 8B na 1×H100, czyli HTTP API server 33%, scheduling 29%, GPU 38% czasu. Sprawdziłem to u źródła (blog vLLM 2024-09-05). Ten profil dotyczy architektury sprzed rozdzielenia procesów.
- Treść, fakty z kodu:
  - **vLLM:** przy TP=1 są 2 procesy (API server + EngineCore z workerem w środku, executor `uni`), przy TP=2 są 4 procesy. Hop API→EngineCore idzie przez ZMQ + msgpack z 2 wątkami I/O, które zwalniają GIL. Hop EngineCore→workery to `MessageQueue` w pamięci współdzielonej (`shm_broadcast.py`), który przesyła `SchedulerOutput` **co krok**. Jest jedna księga KV (`BlockPool`) w EngineCore.
  - **SGLang:** 3 procesy przy TP=1 i 4 przy TP=2. Scheduler, KV i executor siedzą w jednym procesie na GPU. Rank 0 rozsyła **tylko nowe żądania** (`broadcast_pyobj` po gloo), a każdy rank planuje deterministycznie sam. Detokenizer działa w osobnym procesie. `event_loop_overlap` przetwarza wynik kroku N−1 na CPU, gdy GPU liczy krok N.
  - **Pułapka stop-stringów w vLLM:** stop-string wykrywa dopiero `OutputProcessor` w API serverze, więc EngineCore może puścić jeszcze jeden krok, zanim przyjdzie abort.
  - **Metoda pomiaru bez łatek:** różnice `_sum`/`_count` histogramów Prometheus między dwoma scrape'ami przy jednym żądaniu w locie dzielą czas klienta na pracę rdzenia, frontend+IPC i HTTP+detokenizację (`split_latency.py`).
  - **Rust:** vLLM przepisuje L1 na Rust za tą samą granicą ZMQ. SGLang (`SGLANG_RUST_SERVER=1`) wkłada L1 do procesu schedulera rank 0, a gateway gRPC tokenizuje w L5.
- **Część 2 serii** („A Request's Life in vLLM V1”, 2026-11-02) dokłada jedyne twarde liczby. Jeden pythonowy API server ma sufit ~37 000 strumieniowanych tokenów/s, czyli **27 µs CPU na token**. Frontend w Ruście potrzebuje **~12 µs/token**. Oba zmierzono z mock-engine vLLM (instant prefill, losowe tokeny, 4 rdzenie P).

### 2.2 tqLLM (tqllm.com, github.com/turbo-tan/tqllm)

- **Co to jest:** produkt i silnik open source, nie sam format kwantyzacji. Jeden autor plus „zespół agentów AI” (strona główna, sekcja „How it is built”). Repo istnieje od 2026-10-02. Wersja 1.4.4 z 2026-11-07, commit `9a9e7e5`. Wcześniejsze publiczne wersje: 1.4.2 i 1.4.1 (2026-11-05), 1.2.3 (2026-10-22), 1.0.0 (2026-10-14). Kandydatów 1.3.0, 1.4.0 i 1.4.3 nie opublikowano (CHANGELOG.md:8, 72).
- **Sprzęt:**
  - CUDA: RTX 30/40/50, GB10/DGX Spark. Jeden obraz Docker x86-64 + arm64, Linux i WSL2.
  - Apple Silicon: natywny build z MLX 0.32.4, instalacja przez `brew install turbo-tan/tap/tqllm` (CHANGELOG.md:20).
  - **Brak ROCm, Intela i Vulkana.** `src/backends/android/README.md` to tylko opis przyszłego backendu Vulkan/OpenCL/CPU z gałęzi `feat/android-*`.
- **Modele:** Qwen3.5/3.8 dense (hybryda atencja + GDN), `qwen35moe` (MiniCPM-V 4.7 35B-A3B, Qwen3.6-35B-A3B), Qwen3.8-Flash-Next 125B-A6B. Eksperymentalnie MiniMax-M3.1-Flash i GLM-5.3-Flash (tylko GB10).
- **Technika:**
  - Spekulacja bezstratna dla greedy: DFlash2 (drzewo/łańcuch), MTP, DSpark. Plain i każda weryfikacja liczą atencję tą samą arytmetyką (`docs/ARCHITECTURE.md:44-46`).
  - TurboQuant to rotacja wag (WHT) plus mały codebook (`docs/reference/formats.md:9`). Formaty TQ3/TQ4/TQ3_4S są stratne.
  - Skompresowane KV (stratne).
  - TqCache: najstarsze KV w RAM hosta, dokładnie, przez CUDA VMM.
  - Eksperci MoE w RAM według profilu routingu, cache ekspertów w VRAM.
  - Własny serwer HTTP z API OpenAI, Responses i Anthropic Messages.

**Liczby (deklaracje producenta, tqllm.com/performance, CHANGELOG):**

| liczba | sprzęt | warunki | uwaga |
|---|---|---|---|
| 273.1 / 199.5 t/s (reasoning-v1 / code-v1) | RTX 3090, 350 W | LocalMaxxing, 32K, thinking on, **T=0**, 320 tokenów, mediana 5; TQ3_4S-v2 + DFlash2 Q4_K_M, 7 draftów, drzewo, KV BF16 | znane (15c, 32f): ~6.15 tok/krok, workload niskiej entropii |
| 155.2 / 149.9 / 131.0 t/s (plain 55.5 / 54.5 / 50.6) | 3090 | WikiText „summarise” 2K/8K/32K, greedy, 400 tok., KV tq3 (stratne), mediana 3 | znane; plain ≈ nasz parytet per bajt (15c) |
| 202.8 / 157.1 / 144.4 / 106.6 t/s | 3090 | 32K/128K/192K/256K, prompt z kodem C++, greedy, ≤512 tok., **KV T4KV (4-bit)**, łańcuch; akceptacja 273/420 … 271/469 | jedyna seria „długi kontekst + kod”; nieporównywalne z naszym 199k = 74.5 (inny prompt, ~13.9 vs ~17.6 GB wag/krok) |
| 104.9 / 75.2 / 49.6 / 7.7 t/s | 3090 | 32K / 256K / 512K / 1M, WikiText wypełniony w ~90%, 256 tok., od 256K KV tcq3/tcq2 (stratne), za 256K YaRN | ta sama karta, inny prompt: 256K = 75.2, a nie 106.6. Rozrzut ×1.4 z samego workloadu |
| Flash-Next 77.1 vs Strata 47.2 t/s po 128K („1.63×”) | 3090 | ten sam GGUF IQ3_S (GSQ-RCO), greedy, reasoning off, eksperci w RAM | **znane z 60c**; porównanie ze Stratą 0.2.2 (stara) |
| MiniCPM-V 35B-A3B IQ3_S 202.4–203.1 vs llama.cpp 135.7–136.8 t/s | 3090 | 3 prompty, greedy, 512 tok., wszystko w VRAM; llama.cpp `60f0237`, KV q8_0 | znane (15c T4, +49%, „wiarygodne”) |
| MoE: wspólny ekspert w launchu routowanych: IQ3_S 207.8 → 220.1, Q5_K_M (2000 MiB ekspertów w RAM) 176.5 → 187.1 t/s | 3090 | MiniCPM-V 4.7 35B-A3B, wyjście identyczne | **nowe** dla nas (CHANGELOG.md:292-293, wpis 1.2.0; nie było w 60c) |
| Mac M5 Pro 48 GB: 8K 51.9 … 256K 27.5 t/s, exact | M5 Pro | mlx-community 4-bit, DFlash2, `--exact on` | **nowe**; vs TensorFold 1.2.1 / Splash 1.4.0 |
| GB10: `--np 8` 104.5 → 135.1 t/s (weryfikacja batchowa ≤ 24 kolumny) | DGX Spark | 27B, 8 × 131 072 | nowe (1.4.4) |
| 5090 Flash-Next: czat 128 → 154 t/s bez CUDA graphs | RTX 5090 + serwerowy CPU | bezpośrednie launche per warstwa | nowe (1.4.1) |

## 3. Technika w szczegółach

### 3.1 Pięć warstw Kumara a nasz stos

| warstwa | vLLM 0.32 (TP=1) | SGLang 0.5.22 | **llama-server (topka-q63 `c0576e3e8`)** | **Enigma (upstream llama.cpp + Bun)** | tqserve 1.4.4 |
|---|---|---|---|---|---|
| L1: HTTP, szablon, tokenizacja, detok., JSON | proces API server (asyncio), ZMQ+msgpack do rdzenia | proces główny + osobny proces detokenizera | **wątki HTTP** (cpp-httplib): parsowanie JSON, szablon, tokenizacja, `to_json`, parser czatu (`README-dev.md:90-97`; tokenizacja `server-context.cpp:5121`; parser `server-task.cpp:162-173`) | **dodatkowy proces**: proxy Bun `/v1/*` → llama-server, strumień przepuszczany (`app/engine/src/server/api.ts:104-124`), dalej jak obok, ale bez łatek L1 topki | wątki połączeń: szablon, tokenizacja, `StreamWriter` (detok. + JSON) (`tools/serve/scheduler.hpp:37-107`) |
| L2: scheduler | EngineCore (`AsyncScheduler`) | proces schedulera per GPU | **jeden wątek `server_context`** (`README-dev.md:88`), `update_slots()` (`server-context.cpp:3385`) | j.w. (upstream) | jeden wątek silnika `Scheduler::run` (`scheduler.hpp:160-275`) |
| L3: KV | `BlockPool` w EngineCore | `RadixCache` per rank | ten sam wątek: komórki KV, `--cache-ram`, checkpointy | j.w. | `KvStore` (flat/paged/tiered) |
| L4: executor | w EngineCore (TP=1) / workery + shm (TP≥2) | ten sam proces | ten sam wątek: `llama_decode` → graf HIP / taśma PM4 | graf CUDA/Vulkan/Metal | CUDA graphs per krok |
| L5: klaster | llm-d (zdarzenia KV po ZMQ PUB) | Model Gateway | brak (1 użytkownik) | brak | brak |

Wnioski:
- **IPC na krok = 0.** Między L1 a L2 jest `server_queue` w procesie (mutex + condvar), a wyniki idą przez `queue_results.send(unique_ptr)` (`server-context.cpp:2351`) bez serializacji. Odpowiednik hopu ZMQ+msgpack z vLLM kosztuje u nas kilka µs. Hopu przez pamięć współdzieloną nie ma.
- **Stop-stringi są tańsze niż w vLLM.** `process_token` sprawdza je w pętli głównej w tym samym kroku (`server-context.cpp:2100-2128`, `find_stopping_strings` :625), więc nie ma dodatkowego kroku jak w `async_llm.py` vLLM. tqserve robi to jak vLLM, czyli w wątku połączenia (`StreamWriter`, `session.hpp:978`) `[INFERENCE: nie sprawdziłem, czy stop kończy generowanie przed kolejnym krokiem]`.
- **Detokenizacja (`common_token_to_piece`) jest w pętli głównej**, kilka µs na token. Pełny parser czatu (PEG, tool calls, reasoning) działa w wątku HTTP, czyli jak `OutputProcessor` w vLLM i DetokenizerManager w SGLang: poza ścieżką krytyczną GPU, ale **O(n²)** (§3.2).
- **Enigma ma jeden hop więcej** (proces Bun, jak API server vLLM), ale przepuszcza strumień bez parsowania. Koszt per chunk jest pomijalny `[INFERENCE]`. Większy koszt L1 Enigmy wynika z tego, że upstream llama.cpp nie ma łatek L1 topki (tabela 3.2, wiersze tokenizacji i szablonu).

### 3.2 Gdzie idzie nasz narzut hosta: rejestr znanych pomiarów

| element | koszt (zmierzony) | kiedy | źródło | stan |
|---|---|---|---|---|
| HTTP + szablon jinja | 9–11 ms → ~1 ms (natywny ChatML: parse 108.6 → 8.8 ms) | na turę (TTFT) | [45](45-opoznienia.md), wiki `produkt/opoznienia-ttft.md:13` | w produkcji (`LLAMA_CHAT_NATIVE=1`) |
| tokenizacja | 7.3k: 15 → ~3 ms; w13: 1492 → 329 ms; szablon + tokenizacja 25.5 ms @14k, 137.3 ms @91k; cache przyrostowy −0.5…2.5 ms | na turę | [42](42-safe-io.md), [24i](24i-sciezka-agenta.md) | `LLAMA_TOKENIZE_PAR=8` w produkcji, `TOK_CACHE` opcja |
| parser czatu (PEG) w wątku HTTP | **O(n²)**: 0.07 → 0.52 ms/token przy 1k → 12.8k tok.; 3.5 s CPU na 12.8k-tokenowe wywołanie | na token, poza pętlą GPU | [39c §2.1](39c-deepseek-v41-deployment.md) | nic; „opóźnienie strumienia dopiero od ~750 KB” `[INFERENCE 39c]` |
| próbkowanie + accept | 645 → 140 µs/krok; post_decode 963 → 375 µs | na krok | wiki `latki/latki-hostowe.md:18` | w produkcji (K3) |
| handshake `yield_to_queue` | ~100 µs/krok → 3.8 µs (`YIELD_FAST=2`) | na krok | [24o](24o-luki-hosta.md) | w produkcji (`server-queue.cpp:164-190`) |
| re-capture grafu przy przekroczeniu `n_kv` co 256 tok. | instantiate/ExecUpdate 2.9 ms średnio, 13.5 ms max; ~19.5 ms/zdarzenie | co 256 tokenów | [24o](24o-luki-hosta.md) | `GGML_HIP_PM4_LAZY_EXEC=1` w produkcji |
| **GPU bezczynne między taśmami (mediana)** | **410 µs/krok**: przed weryfikacją 168 µs (sync 28, CP 24), przed draftem 321 µs (sync 107 = czekanie na async catch-up), host ~62 µs na decode × 3, `llama_synchronize` 21× po 0.12 µs | na krok, ctx krótki | [37 §2](37-proza-100.md) | tanie cięcia (blit, sync-query) dały 0; następne: catch-up w taśmie draftu, −60…100 µs `[INFERENCE 37]` |
| granice dispatchy w kroku | 946 dispatchy/krok (weryfikacja 824); górna granica bez granic przed MMVQ+normą −2.17 ms (−8.8%) | na krok (GPU, nie host) | [54](54-mniej-granic.md), [37 §3-4](37-proza-100.md) | fuzje zaimplementowane, część niezmierzona |
| efekt produkcyjny trzech przełączników host-gap | czat 113.0 → 114.6 (+1.4%), mvs 420.2 → 433.0 (+3.0%) | – | `PODSUMOWANIE-NOC-2026-10-20.md:47-48` | w produkcji |
| wolny host (Westmere, PCIe gen2, 4070 Ti) | luka GPU ~2.1 ms/krok (6.6%); `YIELD_FAST=2` +1.0% | – | [31-4070ti:178](31-4070ti.md) | lekcja dla Enigmy: słaby CPU = większa luka |
| 5060 Ti (sm_120) | luki hosta 1.9 ms/krok łącznie | – | [31-5060ti:117](31-5060ti.md) | niezmierzone A/B |
| **maska KQ przy długim kontekście** | **niezmierzone na GPU**; CPU: §3.3 | na graf, rośnie z `n_kv` | ten raport | **nowe** |

**Bilans przy krótkim kontekście:** z 27.3 ms/krok host blokuje GPU przez ~0.41 ms (~1.5%). Pełny overlap w stylu SGLang `event_loop_overlap` / vLLM „async output processing” (plan #11 w [63-SYNTEZA](63-SYNTEZA.md), 63e E1) ma więc sufit **~+1.5%** na czacie (63e szacował +1…2% dla Qwena). To potwierdza dotychczasowy ranking: overlap jest tani w teorii, mały w zysku.

### 3.3 Nowe: koszt hosta zależny od `n_kv` (maska KQ)

- Topka buduje maskę KQ na CPU dla każdego grafu, który ma atencję (weryfikacja celu, catch-up MTP, draft MTP). Szybka ścieżka dla jednej sekwencji (`LLAMA_KV_MASK_FAST`, domyślnie on) wygląda tak (`src/llama-kv-cache.cpp:1843-1895`, `:1932-1972`):
  - przejście po `n_kv` pozycjach komórek;
  - `memcpy` wiersza na pozostałe tokeny ubatcha;
  - nowy `std::vector` staging przy każdym wywołaniu (`input_data`, `:1549-1555`, zerowany przez `resize`);
  - upload przez `ggml_backend_sched_set_tensor_async` (`src/llama-graph.cpp:80-86`).
  - Maska nie ma dopełnienia do 64 wierszy: `ne[1] = n_tokens` (`src/llama-graph.cpp:1089`).
- **Mikrobench CPU** (`66e-skrypty/maskbench.cpp`, Ryzen 7 5700X, `-O2 -march=native`, 200 powtórzeń, najlepszy / średni czas). To model szybkiej ścieżki bez uploadu, a nie pomiar serwera.

| `n_kv` | 1 wiersz (draft) | 5 wierszy (weryfikacja MTP n=4) |
|---|---|---|
| 2 048 | 0.7 / 0.8 µs | 1.0 / 1.1 µs |
| 32 768 | 11.1 / 11.3 µs | 16.9 / 18.2 µs |
| 98 304 | 33.6 / 34.2 µs | 54.3 / 62.4 µs |
| 199 936 | 69.1 / 70.1 µs | **234.7 / 256.7 µs** |
| 262 144 | 91.4 / 92.1 µs | 257.7 / 327.2 µs |

- `[INFERENCE]` Szacunek przy 199k na krok: weryfikacja ~0.25 ms, dwa grafy MTP po ~0.07 ms i H2D ~2.4 MB przy ~20–25 GB/s (pinned 1–100 KB mierzone w 37: 22–25 µs) ≈ 0.1 ms. Razem **~0.5 ms na krok ~45 ms ≈ 1.1%**. Na ścieżce krytycznej jest tylko ta część, która nie nakłada się na pracę GPU, a tego nie wiemy.
- Wniosek: maska **nie tłumaczy** ~13 ms „niezwiązanych z pasmem” między 1.7k a 199k ([63d E7](63d-atencja-spec-kwant.md)). Wcześniejsza hipoteza F5 („1–3 ms przy 94k”) jest najpewniej nieaktualna po `LLAMA_KV_MASK_FAST`. Zmierzone 54–62 µs przy 98k to ~20× mniej `[INFERENCE: F5 mógł mierzyć ścieżkę generyczną]`. Mimo to warto to potwierdzić śladem na GPU (T1), bo ślad zmierzy też inne koszty zależne od `n_kv`, których ten mikrobench nie modeluje (`set_input_k_idxs`, kopie stanu, sync).

### 3.4 Nowe: wzorzec strumienia O(n) w tqLLM

- `StreamWriter::update` (`tools/serve/session.hpp:982-995`) dokleja bajty każdego tokenu raz. Ponownie ogląda tylko niestabilny ogon (niepełny UTF-8, możliwy prefiks stop-stringu albo markera narzędzia, końcowe białe znaki). Koszt strumienia to O(n).
- Stary algorytm „przelicz cały prefiks na każdy token” (O(n) na token, czyli O(n²) na odpowiedź) został jako **wyrocznia testowa** `update_reference` (`:996-1007`). Delty obu wersji muszą być identyczne.
- U nas wątek HTTP robi pełny `common_chat_parse` na całym wygenerowanym tekście dla każdego wyniku częściowego (`server-task.cpp:167-173`), a pętla wysyła po jednym wyniku częściowym na każdy przyjęty token (`server-context.cpp:2142`). Przy MTP (2–4 tok/krok) daje to 2–4 pełne parsowania na krok.
- Skala dla porównania: vLLM python ~27 µs CPU/token, Rust ~12 µs/token (Kumar, część 2). U nas po 12.8k tokenach to 520 µs/token (39c).
- Ryzyko jest pośrednie: [lekcja-obciazenie-cpu](../../wiki/lekcje/lekcja-obciazenie-cpu.md) pokazuje, że każdy konkurent o CPU przesuwa t/s dekodu o rząd naszych zysków (0.4–1 ms luki hosta na krok).

### 3.5 tqLLM: co nowego w kodzie i działaniu od 1.2.3 (`c2163c2`) do 1.4.4 (`9a9e7e5`)

1. **`--exact on` jako domyślny** (`docs/reference/options.md:57-74`):
   - aktywacje i KV w FP16/BF16, bez GEMM int8/FP8 i bez ekspertów liczonych na CPU, więc „greedy output is the same from build to build”;
   - prefill 27B liczy teraz GEMM FP16 zamiast int8 na RTX 30 i FP8 na RTX 40/50 i GB10 (CHANGELOG.md:153-155);
   - przybliżenie zamówione jawnie daje jedną linię `WARN` i notkę w `/health`.
   - Odpowiednik naszej reguły „tylko bezstratne”, ale jako przełącznik w produkcie.
2. **Metal: bitowo dokładna atencja dla drzewa i łańcucha** (`src/backends/metal/attention_exact.hpp:1-30`):
   - klucze poniżej `T(x) = 64·⌊(x−15)/64⌋` idą w kaflach 64 na jednostce macierzowej, w kawałkach zależnych tylko od T (1024 klucze do 32K, potem podwajanie, maks. 32 kawałki);
   - ostatnie 16–79 kluczy liczy pętla per wiersz w kolejności AR;
   - wiersz bloku na głębokości d ≤ 15 ma to samo T co jego krok AR, więc **część „bulk” jest wspólna dla wszystkich wierszy weryfikacji**, a wynik zgadza się bit w bit z plain.
   - Dla nas to wzór, jak zrobić „jeden odczyt KV na weryfikację” (plan #8 w 63) **i** zachować `LLAMA_SPEC_BITEXACT`. `[INFERENCE: przeniesienie na `kvq` HIP niesprawdzone]`
3. **GB10 / pamięć zunifikowana** (CHANGELOG.md:37-38, 165, 345-348):
   - `cudaMemGetInfo` liczy page cache jako zajęty („6.7 GB free with 55.8 GB available”);
   - silnik używa `MemAvailable` i w efekcie mieści kontekst 262K, który wcześniej był odrzucany;
   - KV na hoście jest wyłączone na pamięci zunifikowanej, a CUDA graphs zostają (+5–6% dekodu).
4. **CUDA graphs vs bezpośrednie launche** (CHANGELOG.md:158-161):
   - Flash-Next na RTX 5090 (sm_120, PCIe) bez grafów: czat 128 → 154 t/s, 64K 118 → 134;
   - na 3090 grafy są lepsze (−3% bez nich).
   - Uwaga: to ich grafy per warstwa, współdzielone przez warstwy jednego rodzaju (CHANGELOG 1.2.0), a nie cały krok jak w llama.cpp.
5. **Eksmisja w cache ekspertów** (CHANGELOG.md:174-177):
   - warstwy idą w stałym cyklu, więc LRU zawsze wyrzucał bank warstwy potrzebnej za chwilę;
   - polityka „najświeższy inny bank” podniosła trafienia z 0.5% do 77% (3090, 128K: 5 → 27.7 t/s).
   - Ogólna lekcja dla każdego cache'u o dostępie cyklicznym.
6. **TqCache** (`src/kv/kv_store.hpp:1-60`):
   - polityki `flat`, `paged` i `tiered` (najstarsza strona idzie do RAM hosta);
   - tryb VMM: jeden zarezerwowany zakres adresów, część zmapowana na VRAM, część na pinned RAM, kernel czyta oba przez jeden wskaźnik;
   - tryb `staged`: okno najnowszych pozycji w VRAM, starsze granule kopiowane z hosta do dwóch buforów staging (parzystość warstw) przed atencją danej warstwy.
   - 5060 Ti przy 200K: 113 t/s z całym KV w VRAM vs 70 z TqCache. Przy 224K/248K: 42/32 t/s zamiast odmowy (`docs/guides/long-context.md`). Wynik dokładny.
7. **Rejestr flag** (`config/flags.yaml`): 55 zmiennych env, a wycofane nazwy zatrzymują narzędzie i podają zamiennik (`tools/gen_flags.py --check`, ctest `flags_registry`). Dla porównania topka-q63 czyta **283** różnych `getenv("LLAMA_*|GGML_*")` (zliczenie w `src`, `common`, `tools`, `ggml/src`).
8. **Serwer** (`tools/serve/scheduler.hpp`):
   - wątek silnika publikuje tylko identyfikatory tokenów (`publish`, wersja++), a wątek połączenia robi tekst i JSON. Jeśli nie nadąża, naturalnie łączy kroki (widzi tylko ostatnią wersję);
   - żądanie, któremu w prefillu zabraknie pamięci przy innych dekodujących, wraca do kolejki, zamiast dostać 500 (CHANGELOG.md:18-19, `scheduler.hpp:224-231`);
   - przy `--np 1` bez schedulera `decode_stream` woła `on_tokens` (detokenizacja + wysyłka do socketu) **synchronicznie między krokami** (`session.hpp:1224-1229`). To antywzorzec z artykułu, możliwy tylko dzięki O(n).
9. **ANE w prefillu na Macu** (`src/backends/metal/ane_ffn.hpp`, `qwen35.cpp:583-633`, flaga `TQLLM_MLX_ANE_FFN`):
   - ostatnie C kanałów pośrednich FFN liczy Neural Engine przez Core ML, równolegle z GPU (wavefront dwóch połówek);
   - według ich własnego rejestru „quality changes”, więc sekcja 6.
10. **Kontrakt formatów i pluginy** (CHANGELOG.md:97-102):
    - dekwantyzacja na GPU każdego formatu GGUF porównana z referencją CPU, a matvec z iloczynem w podwójnej precyzji: 14/19 przechodzi, IQ2_XXS, IQ2_XS, IQ2_S, IQ3_XXS i IQ1_S mają znane luki;
    - plugin, który deklaruje „exact”, jest przy ładowaniu porównywany bit w bit z kernelem wbudowanym.

## 4. Macierz relewancji

| pomysł | AMD gfx1100 topka | Enigma NVIDIA CUDA (upstream) | Apple Metal | Intel | Strix Halo (gfx1151, zunifikowana) |
|---|---|---|---|---|---|
| 5 warstw / IPC per krok | 0 (jeden proces) | proxy Bun = 1 hop, pomijalny `[INFERENCE]` | j.w. | j.w. | j.w. |
| luka hosta przy długim ctx (maska) | **T1/T3**: do zmierzenia, ~1% przy 199k `[INFERENCE]` | ta sama ścieżka w upstream (bez `KV_MASK_FAST`, wolniej) `[INFERENCE]` | j.w. | j.w. | j.w.; wolniejszy CPU w laptopie zwiększa koszt |
| parser czatu O(n²) / koalescencja per krok | **T2** (CPU-contention, długie wyjścia agenta) | ten sam kod upstream | ten sam | ten sam | ten sam; mniej rdzeni P → większe ryzyko |
| overlap kroku (SGLang / vLLM async output) | plan #11, sufit ~1.5% przy krótkim ctx | CUDA graphs + słabszy CPU → większy sufit (4070 Ti: 6.6% luki) | ? | ? | ? |
| bitowo dokładna atencja T(x) + wspólny bulk | wzór dla plan #8 (`kvq`) z bitexact | n/d (Enigma upstream) | **bezpośrednio**: tqLLM ma to na Metalu | n/d | jak gfx1100 |
| `MemAvailable` vs free z backendu | n/d (VRAM dyskretna) | GB10: `--fit` upstream może zaniżać `[INFERENCE]` | Apple: `recommendedMaxWorkingSetSize` (już w Enigmie) | iGPU Intel: podobny problem `[INFERENCE]` | **tak**: planer Enigmy liczy z RAM statycznie (`catalog/index.ts:77-87`), a upstream `--fit` czyta free z backendu `[INFERENCE]` |
| CUDA graphs off na sm_120 | n/d | tanie ramię w optymalizatorze (5090) | n/d | n/d | n/d |
| MRU-other dla cache cyklicznego | n/d dziś (brak cache ekspertów) | MoE offload: lekcja | – | – | MoE na 96–128 GB: lekcja |
| TqCache (KV w RAM, dokładne) | niepotrzebne (262k się mieści) | 12–16 GB: alternatywa dla cięcia ctx („drabina degradacji”, plan #17) | – | – | n/d (pamięć wspólna) |
| rejestr flag z twardym błędem | topka 283 zmienne → T7 | Enigma przekazuje env: ochrona przed literówką | – | – | – |

## 5. Testowalne pomysły (tylko bezstratne)

| # | pomysł | bezstratny? | oczekiwany zysk i dlaczego | wysiłek | jak testować na naszej maszynie | ryzyko |
|---|---|---|---|---|---|---|
| **T1** | **Ślad luk hosta przy długim kontekście**: `LLAMA_HOSTGAP_TRACE=1` przy 1.7k / 94k / 199k, mediany per para taśm i `graph→inputs` per decode | tak (pomiar) | 0% sam w sobie. Rozstrzyga, czy host rośnie z `n_kv`: jeśli GPU idle > ~1 ms/krok przy 199k (vs 410 µs przy krótkim), T3 i overlap (#11) wchodzą do planu; jeśli płasko, host znika z listy długiego ctx i zostaje GPU (plan #3) | 0 kodu (ślad jest w topka-q63: `ggml/src/ggml-hostgap.cpp`, `src/llama-context.cpp`, `tools/server/server-context.cpp`); ~20 min GPU | kolejka GPU, osobny port: `python3 ~/qwen-opt/long_ctx_bench.py --label hg-lc --bin ~/llama-topka/bin/llama-server --depths 1700,94000,199000 --env LLAMA_HOSTGAP_TRACE=1 -- <args run-topka.sh>`; potem `python3 ~/qwen-opt/hostgap/hg_parse.py <server.log> --min-steps 30 --range i:i+1` per głębokość. Kryterium: wzrost idle/krok między 1.7k a 199k | niskie; ślad sam dodaje µs (porównywać mediany, nie t/s) |
| **T2** | **Parser czatu raz na krok + O(n)**: (a) jeden wynik częściowy na krok MTP (wszystkie przyjęte tokeny w jednej delcie) zamiast jednego na token; (b) przyrostowy parser z wyrocznią jak tqLLM `update_reference` | tak (te same tokeny; zmienia się tylko podział strumienia na delty; tekst końcowy i tool calls identyczne – test różnicowy) | CPU wątku HTTP −50…−75% od razu (a), O(n²) → O(n) (b); dekod 0…+1% przy długich wyjściach `[INFERENCE]` (pośrednio, CPU-contention). Pierwszy krok = pomiar: A/B `stream:true` vs `stream:false`, T=0, wyjście 12k tok., ms/krok na ostatnich 2k tokenach | (a) 0.5 d, (b) 2–3 d (parser PEG w `common/`) | najpierw pomiar (10 min GPU): `serve_bench.py`/`curl` na osobnym porcie, ta sama wiadomość z `max_tokens 12288`, seedy 1–2, ABBA stream on/off; metryka ms/krok z `timings` + `ps -o %cpu` wątku HTTP; potem md5 tekstu i diff tool calli na 48 promptach `spec_sweep` + agent_bench | (a) klienci liczący delty jako tokeny (UI liczników) – tqLLM świadomie zostawił 1 delta/token; (b) błąd w niestabilnym ogonie → wyrocznia w teście |
| **T3** | **Maska KQ poza ścieżką krytyczną** (warunkowo po T1): zbudować maskę weryfikacji, gdy GPU liczy draft (pozycje i `n_kv` znane wcześniej, treść tokenów nie jest potrzebna), albo generować ją na GPU z `p_lo` i tablicy pozycji; dodatkowo stały bufor staging zamiast `std::vector` per wywołanie | tak (te same wartości maski; md5 c4708318/6f14e814) | przy 199k ~0.3–0.5 ms/krok → **+0.5…1.5%**; przy 94k ~+0.3%; krótki ctx 0 `[INFERENCE, mikrobench §3.3]` | 1–2 d | `long_ctx_bench.py` ABBA 94k/199k + bramka md5 `p100_md5.sh`; kill jeśli T1 pokaże `graph→inputs` < 0.2 ms przy 199k | niskie (dane wejściowe), średnie przy wersji GPU (nowy kernel) |
| T4 | **Overlap kroku** (plan #11 / 63e E1, odpowiednik SGLang `event_loop_overlap`) | tak (z konstrukcji) | sufit przy krótkim ctx ~1.5% (410 µs z 27.3 ms); większy na słabych CPU (4070 Ti: 6.6% luki) – wartość głównie dla **Enigmy** | średni-wysoki | jak w 63; priorytet ustalić po T1 | jak w 63 |
| T5 | **Enigma: rezydua frontu (L1) na upstream** – odpowiednik `split_latency.py`: czas klienta − (`prompt_ms`+`predicted_ms` z `timings`), przez proxy Bun i bezpośrednio, prompty 1k/32k/91k × wyjście 1/512/8k | tak (pomiar) | wiedza; spodziewane: 91k turę upstream obciąża szablon + tokenizacja rzędu 0.1 s (nasz pomiar przed łatkami: 137 ms, 24i) i parser O(n²) przy długim wyjściu; decyzja o łatkach L1 (`TOKENIZE_PAR`, `CHAT_NATIVE`, `TOK_CACHE`) w buildach Enigmy | 0.5 d (skrypt) + 15 min GPU | `bun` skrypt w `app/engine/tools/`, XTX na osobnym porcie (build Enigmy ROCm/Vulkan); bez :8080 | niskie; łatki dla Enigmy = decyzja produktowa (Enigma dziś na czystym upstream) |
| T6 | **Enigma: ramię `GGML_CUDA_DISABLE_GRAPHS=1`** w optymalizatorze tylko dla sm_120 | tak | 0 ± 2% `[INFERENCE]`; tqLLM zyskał +20% bez grafów na 5090, ale w swoim silniku; u nas grafy +1.8…4.3% na 3060/5060 Ti (09-chmura) | 0.5 h + 10 min $ (5090) | `llama-bench -fa 1 -n 128` ±env, ABBA; potem spec ramię w optymalizatorze | niskie; najpewniej kill |
| T7 | **Rejestr flag topki** (wzór `config/flags.yaml`): lista 283 zmiennych, typy user/debug/retired, twardy błąd na wycofaną nazwę, `run-topka.sh` sprawdzany przy starcie | tak (0 t/s) | chroni przed cichą literówką w env (np. przełącznik host-gap nieaktywny = −1.4% bez sygnału) | 0.5–1 d CPU | ctest/skrypt grep `getenv` vs rejestr; start serwera z błędną nazwą → exit | niskie |
| T8 | **Atencja „bulk wspólny + ogon AR” (reguła T(x))** jako wariant planu #8 (`kvq` jeden odczyt KV) z bitexact względem plain | tak (bit w bit z plain z konstrukcji, jak tqLLM Metal) | ten sam zysk co #8 (+5…15% przy 94–199k wg 63) plus zachowanie `LLAMA_SPEC_BITEXACT` bez osobnej ścieżki | wysoki (3–5 d, część #8) | `test-backend-ops` + md5 plain vs MTP w trybie BITEXACT, `long_ctx_bench.py` ABBA | średnie (ogon 16–79 kluczy per wiersz w pętli – koszt przy W=5 do zmierzenia) |
| T9 | **Enigma na GB10/Strix Halo: wolna pamięć z `MemAvailable`, nie z backendu** – sprawdzić, czy upstream `--fit`/`-fit on` przy pamięci zunifikowanej odrzuca kontekst, który się mieści | tak | UX: większy kontekst zamiast odmowy (tqLLM GB10: 262K odrzucone → mieści się) | 0.5 d CPU (kod upstream `llama_params_fit`) + test na Strix Halo/GB10 ($) | odczyt kodu, potem jeden start z `-fit on` przy zapełnionym page cache | niskie |

Kolejność: T1 (rozstrzyga T3/T4), równolegle T2-pomiar i T7 (CPU). T5 dla Enigmy w bloku z planem #2 (uczciwy bench, G5 zegar klienta).

## 6. Zaparkowane (stratne) – nie rekomendujemy

| pozycja | dlaczego odpada | liczby (informacyjnie) |
|---|---|---|
| Kwanty wag TurboQuant TQ3/TQ4/TQ3_4S (rotacja WHT + codebook) | inny kwant wag | 27B: TQ_XS 11.85 GB, TQ_S 12.55, TQ_M 13.14, TQ_L 14.72 GB (CHANGELOG 1.0.0); KLD TQ_S 0.055, TQ_XS 0.079 vs BF16 (wiki `repo/tqllm.md`) |
| KV tq3, turbo2/3/4, tcq2/tcq3 (trellis), T4KV | inna numeryka KV | 3090 256K: 106.6 t/s (T4KV) / 75.2 (tcq3, inny prompt) |
| `--exact off` (prefill int8/FP8, eksperci CPU, int8 KV na Macu od 32K) | przybliżenia; KL 0.003–0.010 na Macu | – |
| QSA rzadka atencja na Macu (`--qsa-from 49152`) | zmienia tekst (sami piszą) | 128K 38.9 → 49.6 t/s |
| ANE FFN w prefillu (`TQLLM_MLX_ANE_FFN`) | „quality changes” w ich rejestrze flag | brak liczb publicznych |
| Flash-Next `TQFN_TAIL_SKIP` | „approximate tail skip, opt-in” | – |
| Prompt cache tqLLM przy `--np > 1` | „a reused prompt is not byte-identical” (sami ostrzegają przy `--exact on`) | GB10 8 sesji: 4.5 → 11.9 t/s |
| Flash-Next `slots=auto` | „the slot count can change greedy output (known issue)” | – |

## 7. Co jest NOWE, a co już znane

- **Znane** (nie powtarzać):
  - rekordy tqLLM 273.1 / 199.5, WikiText 131–155, MoE MiniCPM +49%, `--moe-host-mb`, DFlash2, `tq_split_point`, Flash-Next 77.1 vs 47.2 (15b, 15c, 32f, 60c, wiki `repo/tqllm.md`);
  - τ = 0.9 dla draftu (60c T3, DO-PRZETESTOWANIA);
  - bramka `--np N` = `--np 1` (60c);
  - pełna mapa luk hosta przy krótkim kontekście (24o, 37);
  - O(n²) parsera (39c);
  - overlap kroku jako plan #11.
- **Nowe:**
  1. mapowanie 5 warstw Kumara na llama-server i Enigmę (§3.1), w tym stop-stringi w pętli głównej (brak dodatkowego kroku) i proxy Bun jako dodatkowy hop L1;
  2. mikrobench maski KQ: koszt hosta rośnie liniowo z `n_kv` (0.25 ms/graf weryfikacji przy 199k), hipoteza F5 „1–3 ms przy 94k” najpewniej nieaktualna;
  3. brak pomiaru luki hosta przy długim kontekście → T1;
  4. tqLLM O(n) `StreamWriter` z wyrocznią i publikacja samych ID tokenów z wątku silnika;
  5. tqLLM 1.3–1.4.4: `--exact on`, atencja T(x) na Metalu, GB10 `MemAvailable`, graphs vs direct na sm_120, eksmisja MRU-other, rejestr flag, ANE (stratne), wyniki Mac M5 Pro i 3090 do 1M;
  6. sufit frontu vLLM 27 µs/token (Python) i 12 µs/token (Rust) jako punkt odniesienia dla naszych 70–520 µs/token parsera.

## 8. Źródła

- Kumar, „Anatomy of an LLM Serving Engine” (część 1), 2026-10-28 / 11-01: https://hiraditya.github.io/posts/anatomy-of-an-llm-serving-engine/ (vLLM `5df63a7203cdb9328d824a27b682e77c7b9928be`, SGLang `baa9befa381511cd4d56f83980951e5a45fffc6d`; skrypt https://github.com/hiraditya/hiraditya.github.io/blob/main/assets/code/split_latency.py).
- Kumar, „A Request's Life in vLLM V1” (część 2), 2026-11-02: https://hiraditya.github.io/posts/a-requests-life-in-vllm-v1/ (27 µs vs ~12 µs CPU/token, mock-engine).
- vLLM blog, „vLLM v0.6.0: 2.7x Throughput Improvement…”, 2024-09-05 (>12 mies.): https://vllm.ai/blog/2024-09-05-perf-update (33% / 29% / 38%, async output processing).
- tqLLM: https://tqllm.com/ , https://tqllm.com/performance.html (odczyt 2026-11-07); repo https://github.com/turbo-tan/tqllm @ `9a9e7e5e27bd053aa8753147ec2d43b430da3c1d` (v1.4.4, 2026-11-07; klon `~/src/research66/tqllm`); GitHub API: 51★, 6 forków, utworzone 2026-10-02, Apache-2.0. Pliki: `CHANGELOG.md`, `docs/ARCHITECTURE.md:44-54`, `docs/reference/options.md:57-79`, `docs/reference/formats.md:9`, `docs/CREDITS.md:12-23`, `docs/guides/long-context.md`, `config/flags.yaml`, `tools/serve/scheduler.hpp:1-292`, `tools/serve/session.hpp:971-1007,1191-1234`, `tools/tqserve.cpp:519-568`, `src/kv/kv_store.hpp:1-60`, `src/backends/metal/attention_exact.hpp:1-30`, `src/backends/metal/ane_ffn.hpp`, `src/backends/metal/qwen35.cpp:583-633`, `src/backends/android/README.md`.
- Nasz kod: topka-q63 `c0576e3e8ba0bb994676bd02894dd2a23609ccd9` (`~/wt/topka-q63`): `tools/server/README-dev.md:86-119`, `server-context.cpp:625,2100-2142,2311-2352,3385,4407-4410,5071-5126`, `server-task.cpp:162-173`, `server-task.h:14-22`, `server-queue.cpp:164-190,266-314`, `src/llama-kv-cache.cpp:1549-1562,1843-1972`, `src/llama-graph.cpp:80-86,1089`. Enigma: `app/engine/src/server/api.ts:104-124`, `catalog/index.ts:77-102`.
- Nasze raporty: [24o](24o-luki-hosta.md), [37](37-proza-100.md), [39c](39c-deepseek-v41-deployment.md), [42](42-safe-io.md), [45](45-opoznienia.md), [54](54-mniej-granic.md), [24i](24i-sciezka-agenta.md), [31-4070ti](31-4070ti.md), [31-5060ti](31-5060ti.md), [63-SYNTEZA](63-SYNTEZA.md), [63d](63d-atencja-spec-kwant.md), [15b](15b-spekulacja-frontier.md), [15c](15c-nowe-silniki.md), [60c](60c-quant-and-3090-engines.md); `../PODSUMOWANIE-NOC-2026-10-20.md:45-48`; wiki `latki/latki-hostowe.md:18`, `lekcje/lekcja-obciazenie-cpu.md:14`, `repo/tqllm.md`.
- Mikrobench: `66e-skrypty/maskbench.cpp` (CPU, Ryzen 7 5700X, 2026-11-07).
