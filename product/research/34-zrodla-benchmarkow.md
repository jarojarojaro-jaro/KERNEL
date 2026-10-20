# 34 — Źródła benchmarków lokalnej inferencji: przegląd podobnych do LocalMaxxing

Data: 2026-10-20. Autor: agent Res34Sources z trzema zwiadowcami (SrcHwDb, SrcEngineMac, SrcQuantPick). Tylko CPU, bez kont, nic nie publikowaliśmy.

**Zakres.** Badam tylko to, czego jeszcze nie mamy, w stosunku do `wiki/ZRODLA.md`. Tam są już: LocalMaxxing (R32d), LocalScore, InferenceX/AgentX (R21f), llmfit, apxml, gguf-parser-go, panel sprzętu HF, Artificial Analysis i LMArena. Do tego dochodzą wątki llama.cpp #10879/#15021/#21043 (tylko wiersze Llama‑2‑7B, `research_notes/.../local_llm_practice.md`) oraz kyuz0 i llm-tracker (Strix Halo).

**Konwencje.**
- `[INFERENCE]` oznacza wniosek własny, którego nie zmierzyliśmy.
- „plain” to dekodowanie bez spekulacji.
- „MTP n” to spekulacja głowicą MTP z `--spec-draft-n-max n`.
- „pokrycie” dotyczy naszych kart (XTX, 3090, 5060 Ti, 4060 Ti, 3060, 5090), Maców i naszych modeli (Qwen3.8‑27B, LFM2.5‑24B‑A2B).

**Surowe pliki** leżą poza repo, w `/tmp/res34/`:
- `lsp.json`: zbiór llm-speed 2026-10-17.3, 522 wiersze;
- `ta.csv`: Token Atlas, 32 942 wiersze;
- `llmcheck.json`, `llb.json`, `club.md`.

## TL;DR

1. **Od czasu R04 wyrosła cała półka „LocalMaxxingów”.** Trzy z nich mają realną wartość:
   - **llm-speed.com**: podpisane runy, otwarty zbiór CC BY 4.0, CSV/JSON i API;
   - **llm-bench.io**: autor ma XTX; 15 runów Qwen3.8‑27B na XTX, mediana 73.3 t/s;
   - **llamabench.ai** (Xpress AI): „verified” oznacza niezależną reprodukcję w ich serwerowni, plus bramka poprawności wielu tur.

   Najlepszym źródłem dla naszych kart NVIDIA jest **club-3090** (Apache-2.0, każdy wiersz ma n, CV, limit mocy i PCIe). Najszerszym agregatorem jest **Token Atlas**: 32,9 tys. wierszy, każdy z URL-em źródła.
2. **Publiczne liczby dla XTX + Qwen3.8‑27B leżą znacznie poniżej naszych.**
   - Plain: społeczność 35–48 t/s, my 43.2 (tg128).
   - MTP: najwyżej **92.4 t/s** (PR #29679, Vulkan, Windows, MTP n=5). Typowo 62–77.
   - Nasz spec_sweep (T=1) daje 109.0 t/s, a decode przy T=0 na prompcie 1.7k daje 130.2.
   - Jesteśmy ~1.2–1.8× przed najlepszym publicznym wynikiem. Zastrzeżenie: inne prompty, T i kwanty (§2.1).
3. **Na tej samej karcie wynik zależy od klasy promptu prawie 2×.** XTX z MTP n=5: proza 39–47, kod 68–70, wywołania narzędzi 73.4 t/s (lcz.me). To potwierdza naszą zasadę zakresu per zadanie zamiast jednej liczby (§2.2).
4. **Pułapka MTP dla produktu.** Gdy ~2 GB VRAM zajmuje pulpit, llama.cpp wyrzuca warstwę 0 na CPU. Fuzja Gated DeltaNet przestaje wtedy działać, a MTP daje **−40%** zamiast +35…52% (HF Qwen3.8‑27B #49). Picker musi liczyć VRAM pulpitu (§2.3).
5. **Konkurenci pickera** (§3):
   - **canirunthisllm.com** ma najlepszy wzór i uczciwie modeluje hybrydy, ale nie zna MTP i myli się na krawędzi 12–16 GB;
   - **LLM Configurator** jest polski (ma interfejs PL i moduł AI Act/RODO);
   - **Local Model Dojo** to płatna aplikacja Windows z pickerem i „8 tweakami”, czyli najbliższy produktowy odpowiednik Podkrętu.

   Żaden z nich nie mierzy na urządzeniu z MTP i nie dostraja kerneli.

Źródła z API/feedem (15 pozycji) przekazałem `agent://CompWatch`. Ten dopisał do `tools/compwatch/config.json` repozytoria club-3090, victoralcazardev i vijay-14. Feedy JSON (llm-speed, llmcheck, kyuz0) czekają na decyzję Main (zob. „Do bazy wiedzy”).

## 1. Ranking źródeł

Kolumna „jakość” to ocena metody od 1 do 5. „Werdykt” to przydatność dla nas od 1 do 5. Wiersze są posortowane według werdyktu.

| # | źródło | co | pochodzenie | jakość metody | pokrycie dla nas | API / licencja | werdykt |
|---|---|---|---|---|---|---|---|
| 1 | **club-3090** [BENCHMARKS.md](https://github.com/noonghunna/club-3090/blob/master/BENCHMARKS.md) (noonghunna + społeczność, 2.4k★) | Tabele konfiguracji Qwen3.6/3.8‑27B: MTP, DFlash2, vLLM, ik_llama, llama.cpp; 1×/2×3090, 4090, 5090 | zgłoszenia + operator; każdy wiersz ma n, CV, limit W, PCIe, datę | **4**: A/B tylko w jednej sesji; bez T=0/klasy promptu w nagłówku, ale dwie klasy (narracja/kod) | 3090 ★★★, 4090, 5090; XTX/Mac brak | surowy markdown (raw.githubusercontent) + API commitów; **Apache-2.0** | **5** |
| 2 | **llm-speed.com** ([dane](https://llm-speed.com/data), [metoda](https://llm-speed.com/methodology); CLI `meadow-kun/llm-speed`) | Podpisane (Ed25519/JWS) runy z 5 obciążeń: chat-short 128→256, chat-long 4096→1024, agent-trace ~16k, concurrent, long-context | zgłoszenia z CLI; „no retry-and-keep-best”, flaga 3σ zamiast kasowania | **4**: stałe bajty promptu, digest wag, wersja backendu; podpis to proweniencja, nie weryfikacja sprzętu; brak T i MTP w polach | 3090, 4090, 5090, M1 Pro/M3 Pro/M3 Ultra/M4 Max; Qwen3.8‑27B (3090/4090/5090), LFM2.5 (4090/5090/A4000); **zero AMD** | `/data/open-dataset.json` → wersjonowany CSV/JSON; `api.llm-speed.com/v1/results` (50 najnowszych); RSS `/feed.xml`; HF dataset + Zenodo DOI; **CC BY 4.0** | **5** |
| 3 | **llm-bench.io** ([metoda](https://llm-bench.io/benchmark-methodology)) | 4 scenariusze (agent, kod Breakout, RP, research), tok/s + TTFT + jakość oceniana LLM-em (GPT‑5.4 mini) | zgłoszenia z klienta (podpis urządzenia); błędne runy oznaczane ręcznie | **2**: domyślne próbkowanie modelu, bez seeda, 1 przebieg na scenariusz, myślenie liczone jako wyjście, brak kontroli wiarygodności | **XTX ★★★** (autor ma XTX): 15 runów Qwen3.8‑27B, mediana 73.3, maks. 77.0 t/s; 97 stron sprzętu | `/api/benchmarks` zwraca JSON, ale **robots: Disallow /api/**. Dozwolone `sitemap.xml` (456 modeli, 97 kart) i strony runów (JSON w HTML). Licencja: brak | **4** |
| 4 | **Token Atlas** ([tokatlas.github.io](https://tokatlas.github.io/)) | Agregator 32 942 wierszy (444 nazwy sprzętu, 709 modeli), każdy z URL-em i cytatem źródła | **zebrane** przez autonomicznego agenta z wątków llama.cpp, issue/PR, LLMCheck, oMLX, Hardware Corner | **3**: proweniencja wzorowa, ale są duplikaty. Kolumna `ctx` to okno, nie głębokość. **Miesza zagregowane `-npl 8`** (5090 „299 t/s”) z batch 1 | XTX 25 wierszy Qwen3.8‑27B, 3090 21, 5090 29, 5060 Ti 13; 4060 Ti/3060 0; LFM2.5: 0 | `data/records.csv` (17 MB), `records.json`, `sources.json`; licencja własna brak (upstream mieszane) | **4** |
| 5 | **Wątek HF Qwen3.8‑27B #49** + repo [PascalAI2024/qwen38-27b-quant-bench](https://github.com/PascalAI2024/qwen38-27b-quant-bench) (x0me, 2026-08-15) | KLD/top‑1 kwantów **naszego modelu** + MTP/n-gram na 4080 SUPER | pomiar użytkownika (z pomocą AI, ujawnione) | **3**: wikitext c512, 100 chunków, ref. Q8_0; spec: n=7 promptów, restart serwera | Qwen3.8‑27B ★★★ (16 GB) | CSV w repo, **MIT** | **4** |
| 6 | **localbench** (oobabooga, [Substack](https://localbench.substack.com), [metoda](https://localbench.substack.com/p/gguf-benchmark-methodology)) | KLD + top‑1 kwantów GGUF, 250k tokenów w 6 kategoriach do ~30k ctx, z szablonem czatu | operator | **5**: ref. BF16, unia top‑40 logprobów, łatany llama.cpp | Qwen3.5/3.6‑27B, Gemma 4; **brak Qwen3.8, LFM2.5** | RSS `/feed`; tabele jako obrazy; autor prosi o niepublikowanie wykresów | **4** |
| 7 | **canirunthisllm.com** ([metoda](https://canirunthisllm.com/methodology/)) | Picker: dopasowanie + tok/s z wzoru kalibrowanego na wątkach llama.cpp, XiongjieDai i LocalScore; crowd jako mediana ≥3 | wzór + zgłoszenia (parsowany output) | **4**: MoE z aktywnych, SWA/MLA, KV hybryd OK; R² 0.98 Apple / 0.90 GPU | wszystkie nasze karty i Maki (estymaty) | brak API; sitemap | **4** (konkurent, §3) |
| 8 | **Repozytoria XTX jednego autora**: [victoralcazardev/rx7900xtx-local-llm](https://github.com/victoralcazardev/rx7900xtx-local-llm) (2026-10-18), [vijay-14/qwen3-8-rocm-bench](https://github.com/vijay-14/qwen3-8-rocm-bench) (08-30), post [lcz.me #1164](https://lcz.me/topic/1164) | Konfiguracje Qwen3.8‑27B na 1×XTX (ROCm/Vulkan, MTP, 262k ctx, limit 272 W) | autor sam mierzy | **4**: każdą liczbę da się odtworzyć; lcz rozdziela klasy promptów | **XTX ★★★** | repo: MIT / CC BY 4.0 (docs); vijay: JSON w `results/published/`, Apache-2.0 | **4** |
| 9 | **asiai** ([leaderboard](https://asiai.dev/leaderboard/), [panel agentowy](https://asiai.dev/research/comparison-panel/2026-05-apple-silicon-agentic-inference-panel)) | Mac: CLI + panel operatora; TTFT serwer vs klient, moc z IOReport | operator + społeczność | **4**: rozgrzewka, 3 przebiegi, mediana, T=0, kontrola termiki | Maki; Qwen3.6 hybrydy | `api.asiai.dev/api/v1/leaderboard` → **403**; kod Apache-2.0 | **4** |
| 10 | **local-ai-bench.org** | 3×3090, nagłówek = **najwolniejsze 60 s** z 10‑minutowej sesji agentowej + sondy PCIe/VRAM | operator, 281 rekordów (2026-10-12) | **4**: metryka „podłogi” realna, ale większość wyników to pojedyncze runy | 3090; Qwen3.8‑27B | feed nie testowany | **3** |
| 11 | **llamabench.ai** ([metoda](https://llamabench.ai/methodology), [API](https://llamabench.ai/api); Xpress AI, @wmeddie) | Runner opakowuje `llama-bench`/`llama-server`; SHA‑256 GGUF; osobny eval v2 (SVG, Breakout, narzędzia, RP) | zgłoszenia; **verified = reprodukcja** przez ich GPU | **4**: przypięty build i hash wag, test poprawności greedy 1/2/3 tur. Ale ctx 512 w większości runów | 238 runów; 3090 24, 5090 21, 3060 8, 4060 Ti 16G 4; **XTX 0**; LFM2.5 na 4090 339 t/s (UD‑Q3_K_XL, KV q4_0) | **brak API odczytu** (`GET /api/results` zwraca tylko liczbę); afiliacja Amazon | **3** |
| 12 | **llama.cpp: wątki wyników** [#4167 Apple](https://github.com/ggml-org/llama.cpp/discussions/4167), [#15013 CUDA](https://github.com/ggml-org/llama.cpp/discussions/15013), [#10879 Vulkan](https://github.com/ggml-org/llama.cpp/discussions/10879), [#15021 ROCm](https://github.com/ggml-org/llama.cpp/discussions/15021) (tylko delta) | Llama‑2‑7B Q4_0 pp512/tg128 z llama-bench | zgłoszenia; opiekun wybiera wiersze | **3**: przypięty commit, ale podsumowania mieszają commity (M2 Ultra tg 94.27 → 125.21 przy tym samym sprzęcie) | XTX, 3090, 5090, 5060 Ti, 3060, M1–M6; 4060 Ti tylko 8 GB | tylko HTML | **3** |
| 13 | **oMLX community** ([omlx.ai/benchmarks](https://omlx.ai/benchmarks/performance)) | Mac MLX: PP/TG przy 1k/4k/64k, batch 1/2/4, pełny JSON ustawień, termika | zgłoszenia z aplikacji (546k wyników) | **3–4**: bogate metadane, ale T=1 i MTP domyślnie włączone; własne kwanty „oQ4e” | Maki ★★★; LFM2.5, Qwen3.8 | brak JSON (429); robots z zastrzeżeniami treści | **3** |
| 14 | **llamaperf.com** ([o stronie](https://llamaperf.com/about)) | Raporty z r/LocalLLaMA wyciągnięte LLM-em + zgłoszenia; mediany per GPU tylko z runów plain | **zebrane** (tylko pierwszy post wątku) | **3**: audyt „plain > pasmo ⇒ odrzut”, zakresy nie są uśredniane; ale to opinie, nie pomiary | XTX 39 raportów (mediana plain Qwen3.8‑27B **47.9**, n=5), 3090, 5060 Ti, 3060, Maki | `/api` zabronione w robots, brak feedu; reklamy | **3** |
| 15 | **OpenBenchmarking pts/llama-cpp** ([mirror](https://mail.openbenchmarking.org/test/pts/llama-cpp); główna domena 403) | Phoronix Test Suite: pp512–2048, tg128, ≥3 przebiegi | zgłoszenia + Phoronix | **4** (powtarzalne), ale tylko pusty kontekst i Q8_0 | XTX, 5090, 5060 Ti (po 3 wyniki) | eksport `&export=csv` działa; licencja brak | **3** |
| 16 | **llmcheck.net** ([dane](https://llmcheck.net/data/v1/benchmarks.json)) | Zbiór Apple Silicon: 383 wiersze, **74% to estymaty** z wzoru | zebrane + wzór | **2** (uczciwie oznaczone) | Maki; LFM2.5 (M5 Max 184 z karty Liquid, M5 32G 74.2) | JSON/CSV, **CC BY 4.0** | **3** |
| 17 | **PCPrice.Watch** ([GPU guide](https://www.pcprice.watch/gpu-buying-guide)) | Ceny **sprzedanych** kart z eBay, 7 rynków (w tym PL), mediana 90/7 dni, odświeżane co 8 h | zebrane | **4** (sprzedaż, nie oferty) | 3090, XTX, 5090; brak strony 5060 Ti 16G | brak API | **3** |
| 18 | **HF API** (`/api/models?author=unsloth&sort=createdAt`, `&expand[]=gguf`) | Nowe wydania GGUF z metadanymi (architektura, parametry, ctx, rozmiar) | API | – | wszystkie modele | JSON; HF ToS | **3** |
| 19 | **NikoCloud R9700 notes** ([spekulacja](https://github.com/NikoCloud/r9700-local-inference-notes/blob/main/docs/04-speculative-decoding.md)) | DFlash2 vs MTP na RDNA4 | operator | **4** | R9700 (pokrewny gfx12) | markdown | **3** |
| 20 | **local-llm-benchmarks.dev** (kyuz0, następca gridu toolboxes) | Krzywe głębokości 0–64k (prefiks +2048), T=0, odchylenie std | operator | **5** | tylko Strix Halo i R9700 | `data/results.json` (4.4 MB); licencja brak | **3** |
| 21 | **Puget Labs** ([R9700 dual](https://www.pugetsystems.com/labs/articles/amd-radeon-ai-pro-r9700-dual-gpu-ai-inference-performance/)) | GenAI-Perf 500/200 tok, moc z sysfs; uczciwe korekty (tokenizer zawyżał 1.9×) | operator | **4** | nie nasze karty | brak; all rights reserved | **2** |
| 22 | **Unsloth GGUF benchmarks** / **Quesma** ([blog](https://quesma.com/blog/qwen-quantization-quality/)) | KLD/PPL kwantów (producent) / KLD + sędzia pairwise + TB 2.1 | operator | 3 / 4 | Qwen3.5/3.6 | markdown / brak | **2** |
| 23 | **LLM Configurator** ([llmconfigurator.com](https://llmconfigurator.com/en), Jakub Rusinowski) | Picker + baza GPU + „efficiency leaderboard” + AI Act/RODO; **interfejs PL** | wzór dopasowany do 14 runów llama-bench + kuratorowane wiersze | **2** (101 ze 102 wierszy efektywności to estymaty z TGP) | XTX/3090/5060 Ti/5090, Qwen3.8, LFM2.5, **Bielik** (zakresy z modelu) | `measured-benchmarks.json`, **CC BY 4.0** | **2** (konkurent PL, §3) |
| 24 | **Anubis OSS** ([leaderboard](https://devpadapp.com/leaderboard.html)) | Mac: tok/s + J/token (IOReport), przedziały ufności 95% | zgłoszenia z aplikacji | **2–3**: metadane niewalidowane (M5 Pro z pasmem 100 GB/s, zabawkowy model 10M na szczycie) | Maki; LFM2‑24B (nie 2.5) | JSON `anubis/api/leaderboard.php`; GPL kodu, dane bez licencji | **2** |
| 25 | **RigPrice** | Ceny ofert eBay (USD) + „co uruchomi” | zebrane (oferty) | 3 | wszystkie poza 5090 | brak | **2** |
| 26 | **BAEM1N/llm-bench** ([repo](https://github.com/BAEM1N/llm-bench)) | 4 platformy × 5 silników, Qwen3.5, 5 100 pomiarów: zimny prefill, nonce, restart, 5× mediana | operator | **4** | 2×3090, M5 Max, Spark, Strix Halo | CSV w repo; licencja brak | **2** (Qwen3.5, kwiecień 2026) |
| 27 | **Hardware Corner GPU ranking** ([ranking](https://www.hardware-corner.net/gpu-ranking-local-llm)) | llama-bench Q4_K_XL, 16k–131k ctx, laboratorium | operator | 4 | tylko NVIDIA; nieaktualne (2025-12) | brak | **2** |
| – | Słabe lub martwe (1 linia każde) | Spec-Bench (Vicuna, 2025-04); ML.ENERGY (tylko H100/B200, dataset za tokenem); HF LLM-Perf (2025-07); MLPerf Client i UL Procyon (bez publicznej bazy); XiongjieDai (2024); aidatatools (tylko Ollama, wysyłka domyślnie włączona); Silicon Score (kopie z Reddita); mlx-chronos (0 wyników); john-rocky (≤9B); Intel low-bit (lm_eval, nie GGUF); Thireus (tylko wielkie MoE); gguf-bench.com (2×3060, zadania); localmodeldojo / forsakenai (aplikacja, SPA); canirun.ai, whatmodelscanirun, gpu_poor, OllamaLab (wzory); bestvaluegpu (429), GPU PRIX (bez sklepów PL), geizhals (403), ceneo (captcha), gpupricehistory (503); llm-stats (Cloudflare, API z kluczem), LLM Explorer (zły certyfikat TLS), Epoch, The Open Weights, HF daily papers | – | – | – | – | **1** |

**Adwersaryjnie, co łączy te bazy:**
- Żadna nie zapisuje T, klasy promptu i statystyk draftu naraz. llm-speed ma stałe prompty, ale nie zapisuje MTP. llm-bench.io zostawia domyślne próbkowanie i liczy myślenie jako wyjście. llamaperf i Token Atlas tylko zbierają z innych źródeł.
- **Token Atlas** pokazuje zagregowany `llama-batched-bench -npl 8` (5090 „299 t/s”, PR #29768) w tej samej kolumnie `tps` co batch 1. Bez filtra po `notes` taki wiersz zawyża wynik ~4×.
- **Podpis** (llm-speed, llm-bench.io, llamabench) potwierdza tylko pochodzenie, nie prawdziwość liczby. Jedynym źródłem z niezależną reprodukcją jest **llamabench.ai**: GPU w serwerowni Xpress AI. Odpowiednikiem u LocalMaxxing jest tylko kontrola sufitu pasma (R32d §3).

## 2. Czego nauczyliśmy się dziś

### 2.1 XTX + Qwen3.8‑27B: gdzie jest społeczność

| źródło | silnik / kwant | spec | t/s | warunki |
|---|---|---|---|---|
| [llamaperf XTX](https://llamaperf.com/gpu/rx-7900-xtx) | „4-bit”, mieszane | plain | **47.9** (mediana, n=5) | zebrane z Reddita |
| [lcz.me #1164](https://lcz.me/topic/1164) | llama.cpp b10448 **Vulkan** RADV, unsloth Q4_K_M 17.1 GB, KV q8_0 | plain / MTP n=5 | 38.9 / 73.4 (narzędzia), 68–70 (kod), 39–47 (proza ZH) | `--reasoning off`, 128k ctx, NUMA przypięte |
| [victoralcazardev](https://github.com/victoralcazardev/rx7900xtx-local-llm) | ROCm b11454 + PR #29509 `hip-kvmix`, GSQ‑RCO IQ3_S 12.1 GB, KV q8_0/q5_1 | plain / MTP n=3 + ngram-map | 37.2 / 68.9 (pusty ctx); 19.3–25.9 przy 240k | 272 W |
| [vijay-14](https://github.com/vijay-14/qwen3-8-rocm-bench) | ROCm 10, UD‑Q4_K_M | MTP N=2 | 35.1 → 45.0 (kontrolowane), 36.3 → 62.6 (upstream) | ramiona dały różny tekst |
| [llm-bench.io](https://llm-bench.io/benchmarks/cmtf5lp1v000701nx8alaqccv) | llama.cpp „b182‑c1d0e7a”, Q4_K_XL | nieujawniona `[INFERENCE: MTP, bo 77 > sufit plain 57]` | 77.0 maks., **73.3 mediana z 15** | myślenie wł., domyślne T, 4 scenariusze |
| [llama.cpp PR #29679](https://github.com/ggml-org/llama.cpp/pull/29679) (przez Token Atlas) | Vulkan, sterownik AMD 26.8.1 Windows, Q4_K_S, KV q4_0 | MTP n=2 / **n=5** | 78.9–81.5 / **92.4** | 64k ctx, średnia z 4 runów |
| [issue #27734](https://github.com/ggml-org/llama.cpp/issues/27734) | Vulkan Windows, UD‑Q4_K_XL | plain | 40.8 przy ctx 98k; **8.9** przy 131k; 40.3 przy 131k z `GGML_VK_SUBALLOCATION_BLOCK_SIZE=4294967296` | czas ściany, prompt 31 tokenów |
| **my** (`REKORDY.md:18-36`) | ROCm, fork, UD‑Q4_K_XL, KV q4_0 | plain / MTP n=4 + słownik | **43.2** tg128 / **109.0** spec_sweep (T=1) / 130.2 (T=0, 1.7k) | 6 promptów PL/EN × 3 seedy |

**Wnioski.**
- Przy MTP jesteśmy 1.2× przed najlepszym publicznym wynikiem (92.4, Vulkan Windows) i ~1.5× przed medianą llm-bench.io. Zastrzeżenie: ich prompty i T są inne, a 92.4 to Q4_K_S, czyli o ~7% mniej bajtów `[INFERENCE]`.
- **Plain nie jest naszą przewagą.** Mediana społeczności 47.9 jest wyższa niż nasze 43.2. Po przeliczeniu na bajty wag różnica znika: przy Q4_K_S/Q4_K_M ~15.6–16.0 GB zamiast 16.8 GB nasze 43.2 odpowiada ~45–46.5 t/s `[INFERENCE]`. Przy pięciu raportach i mieszanych kwantach to szum, nie przegrana.
- Przy okazji: **PR #29679** (polityka 4 wierszy MMVQ na Vulkan dla RDNA3 przy 8 kolumnach, czyli przy batchu weryfikacji) dotyka tego samego problemu co nasz R24n (MMVQ przy N=5). Warto przeczytać, jakie progi kolumn tam wybrano.

### 2.2 Klasa promptu przesuwa wynik ~2× na tej samej karcie
- lcz.me: ta sama maszyna i parametry, a decode z MTP wynosi 39 t/s dla prozy i 73 t/s dla wywołań narzędzi. Autor wprost pisze, że liczby z forów dla XTX (44–90 t/s) różnią się dlatego, że nikt nie podaje promptu.
- U nas rozrzut per prompt to en-chat 87.8 wobec pl-kod 125.3 (1.43×, `REKORDY.md:23`).
- **Wniosek dla Podkrętu:** pokazywać zakres per zadanie (czat/kod/agent), nie jedną liczbę. Przy porównaniach z bazami podawać klasę promptu.

### 2.3 MTP na desktopie potrafi spowolnić o 40% (pułapka VRAM)
- [HF Qwen3.8‑27B #49](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF/discussions/49), na 4080 SUPER 16 GB, n=7 promptów:
  - `draft-mtp` daje +35% (proza) i +52% (przepisywanie kodu), osiągając 41.42 / 46.87 t/s;
  - n-gram jest w granicach szumu;
  - przy ~2 GB VRAM zajętych przez przeglądarkę ten sam config daje **−40%**: warstwa 0 trafia na CPU, a ścieżka fuzji Gated DeltaNet się rozpada.
- U victoralcazara karta XTX jest jednocześnie kartą ekranu. Gdy brakuje VRAM, KWin pada („Not enough memory for command submission!”).
- **Dla pickera:** budżet VRAM musi odejmować zajętość pulpitu mierzoną na żywo. Po starcie trzeba sprawdzić, czy wszystkie warstwy są na GPU, i w razie czego wyłączyć MTP albo zmniejszyć ctx `[INFERENCE: nasza estymata R04 §3.2 ma margines 1 GiB; to za mało dla 16 GB z MTP]`.

### 2.4 Spekulacja dwustopniowa (n-gram + MTP) potwierdzona zewnętrznie
- club-3090, 1×3090, ik_llama, Qwen3.6‑27B MTP‑IQ4_KS:
  - MTP: 59.67 / 72.40 t/s (narracja / kod);
  - **two-stage** (ngram `n_max`=4 + MTP `n_max`=3): **59.4 / 97.8** t/s, czyli kod +35%, narracja bez zmian (2026-05-24);
  - na 4090: 82.5 / 120.9.
- To ten sam mechanizm co nasz ogon lookupu (code-edit XTX 400.9 t/s, `REKORDY.md:28`). Nie ma tu nic nowego, ale jest niezależne potwierdzenie kierunku i dobry wiersz porównawczy dla 3090.

### 2.5 Backend Vulkan vs HIP na RDNA3: dane są sprzeczne, trzeba mierzyć u użytkownika
- **#10879 vs #15021**, ten sam XTX i commit, Llama‑2‑7B: Vulkan tg 190.9 wobec HIP 163.8. HIP ma za to +13% pp.
- **victoralcazar**, Linux RADV, Qwen3.8 IQ3_S: HIP 40.1 wobec Vulkan **11.3**. Vulkan zbija zegar pamięci do 456–772 MHz, a HIP prowadzi o 63% nawet przy przypiętym zegarze ([engines.md](https://github.com/victoralcazardev/rx7900xtx-local-llm/blob/main/docs/measurements/engines.md)).
- **lcz.me**, RADV 25.2.8: Vulkan plain 38.9, czyli ok.
- **OpenBenchmarking, R9700**, gpt-oss-20b Q8_0: Vulkan 175.9 wobec HIP 140.4 tg.
- Binarka zbudowana z Vulkan i HIP naraz **po cichu wyłącza MTP** ([#23199](https://github.com/ggml-org/llama.cpp/issues/23199)).
- **Dla nas:** wybór backendu w Podkręcie musi wynikać z krótkiego pomiaru na maszynie, nie z tabeli. Dystrybuujemy binarki jednego backendu.

### 2.6 Wykorzystanie pasma przez upstream (llm-speed, CC BY 4.0)

Qwen3.8‑27B Q4_K_M plain, chat-short, llama.cpp:

| karta | t/s | wykorzystanie pasma |
|---|---|---|
| 3090 | 37.6 | **0.69** |
| 4090 | 43.1 | 0.73 |
| 5090 | 75.2 | 0.72 |

- Wykorzystanie liczone jako t/s × 17.1 GB / pasmo producenta.
- U nas XTX: 43.2 × 16.8 / 960 = **0.76**.
- Stąd sufit plain na 3090 ≈ 0.76 × 936 / 17.1 ≈ 41.6 t/s `[INFERENCE]`. To zgadza się z verified 41.3 upstream na LocalMaxxing (R32d).
- Ten sam zbiór na 4090 z `mtp-on`: chat-short **84.5**, chat-long 73.1, agent-trace 77.6. To pierwszy publiczny i podpisany ślad agentowy z MTP dla naszego modelu.

### 2.7 Hybrydy a cache prefiksu
- asiai: dla Qwen3.6 (DeltaNet) llama.cpp nie użyje ponownie prefiksu z cache między różnymi wiadomościami użytkownika (`llama_memory_can_shift=false`). TTFT testu prefiksu: **5965 ms** w ścieżce GGUF LM Studio wobec 131 ms w Rapid-MLX. MTP na M5 Max z 35B‑A3B dało +38% decode.
- U nas `LLAMA_SERVER_CACHE_SHARE_MIN` skraca start sesji agenta z 8019 do **1612 ms** (`REKORDY.md:41`).
- To realny wyróżnik produktu. Warto go pokazać w porównaniu z LM Studio na tym samym scenariuszu.

### 2.8 Jakość kwantów
- **Qwen3.8‑27B, 12 GB** (HF #49):
  - unsloth UD‑IQ2_XXS 8.39 GiB: KLD 0.146, top‑1 82.98%;
  - bartowski IQ2_XXS 8.75 GiB: KLD 0.301, top‑1 76.53%;
  - czyli **dla 3060 tylko UD‑IQ2_XXS**. Nasz Saluki IQ2-mix (7.89 GB) trzeba porównać na tym samym protokole;
  - KV Qwen3.8 to 64 KB/token (16 z 64 warstw ma atencję), co zgadza się z naszym wzorem.
- **localbench**, Qwen3.6‑27B:
  - nawet UD‑Q8_K_XL ma KL **0.373 na długich dokumentach** wobec 0.001 na kodzie;
  - KLD liczone na krótkim wiki zaniża szkody przy długim kontekście;
  - **dla naszej bramki KLD** (`qwen-opt/tools/kld_canary`): dodać chunk długiego dokumentu `[INFERENCE: ich skala jest korpusowa, nie przenosi się 1:1]`.
- **Quesma**:
  - sędzia pairwise nie odróżnił BF16 od żadnego kwantu 4‑bit;
  - UD‑Q4_K_XL ma KLD 0.013, a UD‑IQ2_XXS przegrał ~19/20 pojedynków;
  - to potwierdza decyzję „zostajemy przy UD‑Q4_K_XL” (`ZRODLA.md:147`).
- **Thireus** (README): niższe `-b`/`-ub` podnosi PPL, więc PPL różnych uploaderów są nieporównywalne. Podobnie na Qwen3.8: PPL 6.75 (Q8_0, 100 chunków, PascalAI) wobec 6.954 (BF16, 580 chunków, ubergarm) `[INFERENCE: różnica też z referencji, nie tylko z liczby chunków]`.

### 2.9 Mac
- [#4167](https://github.com/ggml-org/llama.cpp/discussions/4167): M5 MacBook Air 16 GB ma `recommendedMaxWorkingSetSize` **12.7 GB** (F16 7B się nie ładuje). To zgadza się z R30 (M1 Pro 16 GB = 10.67 GiB).
- Na M5 pp512 skoczyło z 987 do 3220 między commitami (tensor API). Apple podaje dla M5 vs M4 TTFT 3.3–4.1×, ale decode tylko +19–27%. **Wyników pp na Macu nie wolno porównywać między commitami.**
- LFM2.5‑24B‑A2B MLX 4‑bit na M4 24 GB: TG 59.9 / 57.4 / **29.9** t/s przy 1k / 4k / 64k, batch 4 = 189 t/s ([oMLX](https://omlx.ai/benchmarks/performance/scui8boi)). Na Macu 16 GB nie ma wiersza dla LFM2.5 `[INFERENCE: ~13–14 GB wag 4‑bit nie zmieści się w 12.7 GB z KV]`.

### 2.10 Ceny kart do katalogu (2026-10-20)

[PCPrice.Watch](https://www.pcprice.watch/gpu-buying-guide), sprzedane na eBay, 7 rynków UE:

| karta | mediana 90 dni | mediana 7 dni | n |
|---|---|---|---|
| 3090 | €1 224 | €1 314 | 237 |
| 7900 XTX | €872 | €1 021 (+16% w 30 dni) | 294 |
| 5090 | €2 229 | – | 25 |

- Do katalogu bierzemy medianę 7‑dniową, bo 90‑dniowa nie nadąża za rosnącym rynkiem.
- 5060 Ti 16G i 4060 Ti 16G są tylko z ofert, nie sprzedaży:
  - RigPrice: $755 / $700 (n=7);
  - GPU PRIX: 4060 Ti 16G mediana 3 mies. €629.
- Ceneo i geizhals są dla botów zamknięte (captcha / 403). **PL-owego źródła cen z API nie ma.**

### 2.11 Bramka poprawności z llamabench
- Runner powtarza stałe prompty przy T=0 w 1, 2 i 3 turach. Bełkot (także pojawiający się dopiero w 2.–3. turze, typowy błąd KV) unieważnia wynik.
- Złapali tak Qwen3.5‑4B Q4_K_XL, który przy 15–23 t/s „ładnie” generował śmieci.
- **Pomysł:** dodać do `quick_quality.py` sprawdzenie wielu tur. Nasz tryb bitowy sprawdza zgodność z referencją, ale nie test 3. tury z cache.

## 3. Konkurenci naszego pickera

| picker | wejście | skąd tok/s | MoE / hybrydy | MTP | AMD / Mac | błędy zauważone | vs Podkręt |
|---|---|---|---|---|---|---|---|
| **canirunthisllm.com** | GPU/Mac, ctx, kwant (realne rozmiary GGUF) | `1/(aktywne_wagi/(BW·eff)+KV/(BW·eff)+narzut)`, kalibrowane na wątkach llama.cpp; crowd: mediana ≥3 parsowanych runów, korekta per urządzenie co tydzień | **tak**: aktywne parametry, SWA/MLA; KV Qwen3.8 0.3 GB przy 4k jest poprawne | nie | tak / tak | XTX Q4_K_M: 36–54 t/s, górna granica = 100% pasma; prefill XTX > 4090; 3060: „nie” (pomija UD‑IQ2_XXS 8.39 GiB); 5060 Ti: „tylko Q2_K”; bez IQ; linki afiliacyjne do chmury | najlepszy z wzorów; przegrywa na 12–16 GB i bez MTP (±35–52% albo −40%) |
| **llmfit** (znany, R04) | wykrycie lokalne | BW/rozmiar × 0.55 + mediany LocalMaxxing | aktywne | nie | tak | −22…+75% u nas (R04) | j.w. |
| **LLM Configurator** (PL) | GPU/Mac, workload, budżet | model dopasowany do 14 runów llama-bench | ? | nie | tak / tak | 101/102 wierszy efektywności to estymaty z TGP | **jedyny polski**; ma Bielika, RODO i AI Act; nie mierzy |
| **Local Model Dojo** (Average Joes Construction LLC) | skan CPU/GPU/VRAM/backendów | **pomiar** 5 promptów (szybkość, JSON, kod, rozumowanie, długi tekst) | ? | nie | tylko Windows | płatny $9.99/mies.; przykłady na stronie to tagi Ollamy (`deepseek-coder:6.7b`, `qwen3-coder:30b`) `[INFERENCE: backend Ollama]` | **najbliższy produkt**: picker + „8 tweaków” (plan zasilania, Defender) + ranking opt-in. Nie widać kerneli, MTP ani specyfiki AMD |
| **llamabench.ai** „Find your next local model” | sprzęt, RAM, min. tok/s, zastosowanie | tylko zmierzone runy + Intelligence Index (hostowany) | – | tak (`draft-mtp`, `ngram-mod` w konfiguracji) | XTX 0; AMD tylko 7900 XT, 9060 XT, 8060S, 890M | ctx 512 w większości runów | baza, nie estymator; mało AMD |
| **llm-speed** `/tools/vram-fit` | model + kwant + GPU/Mac | zmierzone runy | – | nie | brak AMD | – | j.w. |
| **llmcheck.net** | Mac | `1/(GB/(BW·0.7828)+1.46 ms)`; MoE z aktywnych +4.97 ms | aktywne | wykluczone | tylko Mac | 74% wierszy to estymaty | gotowy wzór bazowy dla Maca |
| **canirun.ai** (midudev) | GPU | `BW/VRAM×0.70` z **pełnym** rozmiarem | **nie** (LFM liczony jak dense) | nie | tak | Qwen3.8‑27B Q4 = 14.3 GB (realnie 17.4) | słaby |
| **whatmodelscanirun** (MIT) | GPU | `BW/(wagi+1 GB)`, kalibracja ±5% na 9070 XT dla 2–8.5 GB | KV bez hybryd (~4× za dużo dla Qwen3.8) | nie | tak | – | dane `models.json`/`gpus.json` na MIT do wzięcia |
| **RigPrice** | budżet | ~28.4 t/s Qwen3.8 na 3090 + ceny ofert | ? | nie | – | – | pomysł: łączy cenę z dopasowaniem |
| **gpu_poor**, **OllamaLab**, **llamaperf calculator** | GPU | wzór (llamaperf oznacza measured/estimated) | nie / nie / ? | nie | – | nieaktualne | – |

**Jak wypadamy.**
- Wszyscy poza Local Model Dojo przewidują wynik z pasma z karty katalogowej. Najlepszy (canirunthisllm) ma przedział ±20% i nie zna MTP ani backendu. Na krawędzi 12–16 GB, czyli w naszym głównym segmencie, jego werdykty są błędne (3060: „nie”, 5060 Ti: „tylko Q2”).
- Nasza przewaga, w kolejności: pomiar na urządzeniu z **MTP i klasą zadania**, realny wolny VRAM (pułapka −40%), wybór backendu pomiarem (§2.5) oraz własne kernele.
- Do skopiowania:
  - z canirunthisllm: crowd jako „mediana ≥3 parsowanych runów + cotygodniowa korekta η per urządzenie”;
  - z llmfit: etykiety `measured / estimated`;
  - z llamabench: hash GGUF i powtórka wielu tur.
- Local Model Dojo pokazuje, że ludzie płacą za „picker + tweaki systemowe” nawet bez optymalizacji kerneli (to wniosek o cenie, R06 §2.5.1).

## 4. Rekomendacje (bez GPU, kolejność wg zysku/kosztu)

1. **Monitoring.** Dzienny diff dwóch źródeł na CC BY 4.0, z atrybucją, bez republikacji wierszy:
   - llm-speed: `open-dataset.json` → nowa wersja → filtr Qwen3.8 / LFM2.5 / nasze karty;
   - llmcheck: `data/v1/benchmarks.json`, tylko `sourced` i `community`.

   Do tego, raz w tygodniu, mapa strony llm-bench.io (nowe runy XTX) i Token Atlas `records.csv` (filtr `notes` bez `-npl`). Decyzja: Main/CompWatch.
2. **Picker.** Odejmować zmierzone zajęcie VRAM pulpitu i po załadowaniu sprawdzać, czy warstwa 0 jest na GPU (§2.3). Pokazywać zakres per klasa zadania (§2.2).
3. **KLD.** Dodać do bramki chunk długiego dokumentu (§2.8). Dla 3060 porównać Saluki IQ2-mix z UD‑IQ2_XXS na protokole z HF #49.
4. **Przeczytać PR #29679** (progi MMVQ przy 8 kolumnach na RDNA3, Vulkan) pod R24n.
5. **Ceny w katalogu** z PCPrice.Watch (mediana 7 dni, sprzedane), z datą. PL-owego API brak.

## Do bazy wiedzy

**Proponowane wiersze `wiki/ZRODLA.md`** dla sekcji „Benchmarki i rankingi”. Format: źródło | wersja | raport | werdykt | liczby | następnym razem.

| źródło | wersja | raport, notatka | werdykt | liczby | następnym razem |
|---|---|---|---|---|---|
| llm-speed.com (meadow-kun/llm-speed; CC BY 4.0) | zbiór 2026-10-17.3, 522 wyniki / 277 runów; CLI 0.0.5 | [R34](../product/research/34-zrodla-benchmarkow.md) | Podpisane runy, stałe prompty, otwarte dane; zero AMD, brak pola MTP. | Qwen3.8‑27B Q4_K_M plain: 3090 37.6, 4090 43.1, 5090 75.2; 4090 MTP 84.5 / agent-trace 77.6 | nowa wersja `open-dataset.json`; czy pojawi się AMD/XTX |
| llm-bench.io | metodologia v1.2 (2026-09), sitemap 571 URL | R34 | Autor ma XTX; jakość oceniana LLM-em; domyślne T; `/api` zabronione w robots. | XTX Qwen3.8‑27B: 15 runów, mediana 73.3, maks. 77.0 | nowe runy XTX przez sitemap |
| llamabench.ai (Xpress AI) | 238 runów / 41 systemów (2026-10-20) | R34 | „Verified” = reprodukcja w ich serwerowni; bramka bełkotu przy wielu turach; brak API odczytu. | LFM2.5 4090 339 t/s (Q3_K_XL, ctx 512); Qwen3.8‑27B 5090 155 (Q6_K, ngram-mod); XTX 0 | runy XTX/LFM2.5 |
| Token Atlas (tokatlas.github.io) | 2026-10-18, 32 942 wierszy | R34 | Największy agregator z URL-em źródła; uwaga: `-npl 8` w kolumnie tps, `ctx` = okno. | XTX Qwen3.8 MTP n=5 92.4 (PR #29679, Vulkan Windows) | filtr Qwen3.8/LFM2.5 × nasze karty |
| club-3090 BENCHMARKS.md (noonghunna; Apache-2.0) | wiersze do 2026-09-14 | R34 | Najlepsza tabela 3090: n, CV, W, PCIe. | ik_llama two-stage ngram+MTP: kod 97.8 vs MTP 72.4 (+35%), 4090 120.9 | wiersze Qwen3.8‑27B 1×3090 |
| llamaperf.com | 2026-10-20 | R34 | Raporty z Reddita wyciągnięte LLM-em; mediany tylko z plain. | XTX Qwen3.8‑27B plain mediana 47.9 (n=5) | mediana XTX plain/MTP |
| llama.cpp wątki #4167/#15013 (delta R34; #10879/#15021 już w `local_llm_practice.md`) | do 2026-10-16 | R34 | Wiersze nieaktualne per commit; tylko Llama‑2‑7B. | M5 Air 16 GB limit roboczy 12.7 GB; 5060 Ti tg 93.5; 3060 76.9; 3090 161.9–177.8 | wiersze 4060 Ti 16G |
| localbench (oobabooga) | ostatni wpis 2026-04-26 | R34 | Najlepsza metoda KLD (6 kategorii, do 30k); brak Qwen3.8. | Qwen3.6‑27B UD‑Q8_K_XL: KL kod 0.001 / długie dokumenty 0.373 | wpis o Qwen3.8 (RSS) |
| HF unsloth/Qwen3.8‑27B‑GGUF #49 + PascalAI2024/qwen38-27b-quant-bench (MIT) | 2026-08-15 | R34 | KLD naszego modelu; MTP −40% przy zajętym VRAM pulpitu. | UD‑IQ2_XXS KLD 0.146 / top‑1 82.98% vs bartowski 0.301 / 76.53%; MTP +35/+52% | – |
| XTX: victoralcazardev/rx7900xtx-local-llm, vijay-14/qwen3-8-rocm-bench, lcz.me #1164 | 2026-10-18 / 08-30 / ~09 | R34 | Jedyne publiczne XTX + Qwen3.8 + MTP; poniżej naszych. | 68.9 (IQ3_S MTP n=3), 62.6 (N=2), 73.4 (Vulkan n=5, narzędzia); proza 39–47 | nowe commity (CompWatch) |
| asiai (asiai.dev) | panel 2026-05 | R34 | Najlepsza metodologia na Macu; API 403. | GGUF hybryda: brak reużycia prefiksu, TTFT 5965 vs 131 ms MLX | – |
| oMLX community, llmcheck.net (CC BY 4.0), Anubis, Silicon Score | 2026-10-17…20 | R34 | Mac: oMLX ma krzywe ctx; llmcheck w 74% to estymaty. | LFM2.5 M4 24 GB MLX: 59.9/57.4/29.9 t/s przy 1k/4k/64k | wiersz Mac 16 GB dla LFM2.5 |
| local-ai-bench.org, local-llm-benchmarks.dev (kyuz0), OpenBenchmarking (mirror), Puget, BAEM1N/llm-bench, Hardware Corner | 2026-04…10 | R34 | Dobre metody, słabe pokrycie naszych kart. | 3090 EXL3 MTP podłoga agentowa 111; R9700 Vulkan 175.9 vs HIP 140.4 (gpt-oss) | – |
| Słabe lub martwe: Spec-Bench, ML.ENERGY, HF LLM-Perf, MLPerf Client, Procyon, XiongjieDai, aidatatools, Intel low-bit, Thireus, mlx-chronos, llm-stats, LLM Explorer, Epoch | 2026-10-20 | R34 | Nieaktualne, nie nasz sprzęt albo zamknięte. | – | nie wracać |

**Do sekcji „Aplikacje, firmy i chmury”:**

| źródło | raport, notatka | werdykt | następnym razem |
|---|---|---|---|
| Pickery: canirunthisllm.com, LLM Configurator (PL, CC BY 4.0 JSON), canirun.ai, whatmodelscanirun (MIT), RigPrice, gpu_poor, OllamaLab | R34 §3 | Wszystkie liczą z pasma, nikt nie zna MTP; canirunthisllm najlepszy, ale błędny na 12–16 GB. | czy canirunthisllm doda MTP / pomiar |
| Local Model Dojo (localmodeldojo.com) | R34 §3 | Płatna aplikacja Windows ($9.99/mies.): picker + pomiar + 8 tweaków systemowych; najbliższy produkt. | cennik, czy dodadzą AMD/kernele |
| Ceny GPU: PCPrice.Watch (sprzedane, UE w tym PL), RigPrice, bestvaluegpu, GPU PRIX; ceneo / geizhals zamknięte | R34 §2.10 | Do katalogu PCPrice.Watch, mediana 7 dni; brak API i źródła PL. | ceny XTX (trend +16%/30 dni) |

## Źródła

- **Bazy:**
  - https://llm-speed.com/ , /data , /methodology , /folklore , /data/open-dataset.json , https://api.llm-speed.com/v1/results , /feed.xml
  - https://llamabench.ai/ , /methodology , /api , /models/qwen3-8-27b
  - https://llm-bench.io/benchmarks/cmtf5lp1v000701nx8alaqccv , /benchmark-methodology , /impressum , /robots.txt , /sitemap.xml
  - https://llamaperf.com/about , /gpu/rx-7900-xtx , /report/1248
  - https://tokatlas.github.io/data/records.csv
  - https://localmodeldojo.com/ , https://www.hardware-corner.net/gpu-ranking-local-llm
- **XTX:**
  - https://github.com/victoralcazardev/rx7900xtx-local-llm
  - https://github.com/vijay-14/qwen3-8-rocm-bench
  - https://lcz.me/topic/1164
  - https://github.com/ggml-org/llama.cpp/pull/29679
  - https://github.com/ggml-org/llama.cpp/issues/27734
  - https://github.com/ggml-org/llama.cpp/issues/23199
- **Wątki llama.cpp:** https://github.com/ggml-org/llama.cpp/discussions/4167 , /15013 , /10879 , /15021
- **NVIDIA i spekulacja:**
  - https://raw.githubusercontent.com/noonghunna/club-3090/master/BENCHMARKS.md (wiersze 135–142)
  - https://local-ai-bench.org/
  - https://github.com/NikoCloud/r9700-local-inference-notes
  - https://huggingface.co/z-lab/Qwen3.8-27B-DFlash2
  - https://github.com/hemingkx/Spec-Bench/blob/main/Leaderboard.md
- **Kwanty:**
  - https://huggingface.co/unsloth/Qwen3.8-27B-GGUF/discussions/49
  - https://github.com/PascalAI2024/qwen38-27b-quant-bench
  - https://localbench.substack.com/p/qwen-3-6-27b-gguf-quality-benchmark
  - https://unsloth.ai/docs/models/qwen3.5/gguf-benchmarks.md
  - https://quesma.com/blog/qwen-quantization-quality/
  - https://huggingface.co/ubergarm/Qwen3.8-27B-GGUF
  - https://github.com/Thireus/GGUF-Tool-Suite
- **Mac:**
  - https://asiai.dev/research/comparison-panel/2026-05-apple-silicon-agentic-inference-panel
  - https://omlx.ai/benchmarks/performance/scui8boi
  - https://llmcheck.net/data/v1/benchmarks.json
  - https://devpadapp.com/anubis/api/leaderboard.php
  - https://machinelearning.apple.com/research/exploring-llms-mlx-m5
- **Pickery i ceny:**
  - https://canirunthisllm.com/methodology/
  - https://canirun.ai/why
  - https://github.com/BenD10/whatmodels
  - https://llmconfigurator.com/measured-benchmarks.json
  - https://www.pcprice.watch/gpu-buying-guide
  - https://rigprice.com
  - https://gpuprix.com/eu/gpus/geforce-rtx-4060-ti-16gb
- **Inne:**
  - https://mail.openbenchmarking.org/test/pts/llama-cpp
  - https://www.pugetsystems.com/labs/articles/amd-radeon-ai-pro-r9700-dual-gpu-ai-inference-performance/
  - https://github.com/BAEM1N/llm-bench
  - https://local-llm-benchmarks.dev/data/results.json
  - https://huggingface.co/api/models?author=unsloth&sort=createdAt&direction=-1
- **Nasze pliki:** `wiki/REKORDY.md:18-41,74,110`, `wiki/ZRODLA.md:108-117,147`, `product/research/32d-localmaxxing.md`, `product/research/04-wykrywanie-sprzetu-i-dobor-modeli.md:280-291`, `research_notes/Optymalizacja kerneli na AMD/local_llm_practice.md:80-85,283-301`
- **Zwiadowcy (transkrypty):** `agent://Res34Sources.SrcHwDb`, `agent://Res34Sources.SrcEngineMac`, `agent://Res34Sources.SrcQuantPick`
