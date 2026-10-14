# 29 — NVIDIA/cuda-rust

Klon: `--depth 1`, HEAD `bc46b1f` (2026-10-12). Repo usunięte z `/tmp/repos` po analizie.

## 1. Co to jest
Oficjalna platforma NVIDIA „CUDA dla Rusta”: (a) **cuda-oxide** — własny backend rustc, Rust → PTX, model SIMT z pełnym dostępem do warpów, smem, TMA, klastrów; (b) **cutile-rs** — makra proc + JIT Rust → CUDA Tile IR → cubin (zamknięty `tileiras`), model kafelkowy à la cuTile Python/Triton; (c) wspólny runtime hosta: `cuda-bindings`, `cuda-core`, `cuda-async` (strumienie, futures, grafy) (`README.md:8-31`, `:44`). Główna teza: reguły własności Rusta przeniesione przez granicę launchu (bufory mutowalne dzielone na rozłączne partycje → brak wyścigów danych z konstrukcji) (`README.md:28-31`). Sam projekt nazywa się „early-stage research project” (`README.md:33`). Apache-2.0, bardzo aktywne (commity z X 2026, cutile-rs 0.4.0 z 2025-09-25 w `cutile-rs/CHANGELOG.md`). Sprzęt: wyłącznie NVIDIA sm_80+ (Tile IR) / PTX; zero wsparcia AMD (`cutile-rs/README.md:84-96`).

## 2. Kluczowe techniki (z dowodami)
1. **Bezpieczne partycjonowanie buforów jako model wyścigów** — zero kosztu wydajności wg autorów: persistent GEMM B200 z bezpiecznymi indeksami „within 0.3% of the raw-pointer baseline”, 2068.88 TFLOP/s = 96.35% cuBLAS (`cutile-rs/cutile-benchmarks/paper/sec5_exp1_safety_overhead/README.md:4-5,90-98`; pomiary NVIDIA, B200 z zablokowanym zegarem).
2. **Jeden model `DeviceOp` dla sync/async/graf** — `CudaGraph::capture` raz, `update(op)` = memcpy do stałego bufora wejściowego, `launch()` = `cuGraphLaunch` (`cuda-async/src/cuda_graph.rs:94` instantiate, `:113` `cuGraphUpload` od razu po instantiate, `:308` update, `:344` launch). Dokładnie ten sam wzorzec co ggml-cuda (stałe wskaźniki + kopie wejść przed replay).
3. **Pomiary kosztu granicy kernela** (RTX 5090, tiny kernel f16 D=2048, pomiary NVIDIA, `…/sec5_exp2_execution_mode_overhead/launch_overhead_rust/results_part_a.csv`):
   - sync po każdym kernelu: 6.6 µs/kernel (`:2`),
   - łańcuch na strumieniu, 1 sync: 3.36 µs/kernel (`:19`, 1000 op = 3357 µs),
   - **replay grafu: ~0.81 µs/węzeł** (`:37`, 1000 op = 807 µs; `:29` pojedynczy węzeł 4.6 µs = stały koszt replay).
4. **Programmatic Dependent Launch** jako atrybut launchu (`cuda-core/src/api.rs:121-140`, `CU_LAUNCH_ATTRIBUTE_PROGRAMMATIC_STREAM_SERIALIZATION`), w Tile IR od CUDA 13.4 (`cutile-rs/CHANGELOG.md:23-25`); także launch kooperacyjny i klastry (`cuda-core/src/simt/mod.rs:126-404`).
5. **Redukcja kosztu hosta per launch** (bez grafów): cache ostatniej specjalizacji per call-site, walidacja budująca komunikaty tylko przy błędzie, argumenty w inline arenie zamiast alokacji → 3.9 → 1.6 µs/launch (Ryzen 9950X; `cutile-rs/CHANGELOG.md:153-158`).
6. **Reaktor completion (cuda-async)**: „wake only if was empty” (idea z linuxowego `llist`) zamiast `unpark` przy każdej rejestracji: +38–39% przepustowości rejestracji, bo 8 wątków bije w jedną linię cache `Parker`; hot-spin przegrywa z park (`cuda-async/REACTOR_AB_REPORT.md`, sekcje Results/Findings). Sami przyznają, że to 5–9 Mops/s, daleko ponad realne tempo GPU (Findings pkt 3).
7. **ptx-schedule** — narzędzie do szukania wyścigów: analiza PTX, znajduje „schedule sites” (atomiki, bariery, fence, shfl/vote, cp.async, griddepcontrol, back-edge pętli) i wstrzykuje deterministycznie losowany (seed) `nanosleep`, potem kampania seedów z werdyktami Pass/Hang/Crash/Mismatch i potwierdzaniem (`cuda-oxide/crates/ptx-schedule/README.md:1-80`, `src/lib.rs:118,172`).
8. **Kernele LLM (cutile-kernels)** — standard: split-K decode GQA + merge LSE (`cutile-rs/cutile-kernels/src/attention.rs:730-917`), fuzja QK-norm+RoPE+zapis KV dla decode (`src/experimental/fused_transformer.rs:349`), residual+RMSNorm dla grafów decode (`src/experimental/norms.rs:15`), wstępny persistent grouped GEMM dla MoE (`src/experimental/moe.rs:66`).
9. **End-to-end (Grout, Qwen3-4B bf16, RTX 5090, pomiary NVIDIA/HF)**: 170.5 t/s = 0.77 nominalnego roofline'u pasma (1792 GB/s), vLLM z grafami 163.6 t/s (0.74), SGLang 162.5 (0.73) (`…/sec5_exp3_end_to_end_inference/data/sweep_tg_*/aggregate.csv`, wiersze pp=18 tg=36). Duże GEMM-y lecą do cuBLAS (`…/sec5_exp3_end_to_end_inference/README.md:72`).

## 3. Przeniesienie na AMD/HIP/RDNA3
| Technika | Przenośność | Uwagi |
|---|---|---|
| Rust frontend (oxide/cutile) | **nie** | Generuje wyłącznie PTX / Tile IR; Tile IR → cubin przez zamknięty `tileiras`. Brak ścieżki do AMDGCN. Przepisanie kerneli ggml na Rusta nic by nie dało wydajnościowo nawet przy istniejącym backendzie. |
| Bezpieczne partycje | koncepcyjnie | Gwarancja kompilacji, nie optymalizacja. W C++/HIP nie ma odpowiednika; zysk = mniej błędów, nie µs. |
| Wzorzec graf + update wejść | już mamy | ggml-cuda: `cudaGraphInstantiate`/`cudaGraphExecUpdate` (`ggml-cuda.cu:2740,5617`) + nasza łatka 0029 (asynchroniczne wejścia grafu). |
| `cuGraphUpload` po instantiate | tak (`hipGraphUpload` istnieje w HIP) | Nasz fork nie woła upload (grep: brak w `ggml/src/ggml-cuda`). Wpływ tylko na pierwszy replay po instantiate/update — patrz pomysł 1. |
| PDL / griddepcontrol | **nie** | RDNA3/HIP nie ma programowej zależności siatek (prolog kernela N+1 nakładający się na ogon N). Najbliższe odpowiedniki u nas: fuzje, „ostatni blok”/ticket, persistent grid z barierą atomową (0.5 µs/fazę wg `lfm-decode-round2.md:30`). |
| Klastry, kooperacyjny launch | częściowo | hipLaunchCooperativeKernel istnieje; klastrów/DSMEM brak. Bariera grid w HIP i tak lepiej jako własny licznik atomowy (już zmierzone). |
| Host launch caching | nieistotne | Używamy grafów HIP; koszt hosta per launch nie jest na ścieżce krytycznej poza budową/aktualizacją grafu. |
| Reaktor empty→wake | nieistotne dla GPU | Ewentualnie wątki serwera, ale tam nie ma 8 wątków rejestrujących miliony zdarzeń/s. |
| ptx-schedule (wstrzykiwanie opóźnień) | **tak, koncepcja** | Na AMD: makro wstawiające `__builtin_amdgcn_s_sleep(n)` (lub pętlę na `s_memtime`) w punktach synchronizacji (atomiki ticketu, `__syncthreads`, DPP/ds_swizzle przed LDS, bariery persistent) z seedem z `-D`; włączane tylko w buildzie testowym. Narzędzie poprawności, nie wydajności. |
| Kernele LLM | nic nowego | QK-norm+RoPE+set_rows i rms_norm+residual już mamy (`ggml-cuda.cu:5277-5282`, łatki 0017, 0012, 0049); split-K FA decode jest w ggml. |

Kalibracja platformy `[WNIOSEK]`: na RTX 5090 granica węzła w grafie to ~0.81 µs (pkt 2.3), u nas ~2.5 µs (`lfm-decode-round2.md:29`). Przy 416 kernelach/token LFM różnica ~1.7 µs × 416 ≈ 0.7 ms/token to „podatek platformy” HIP/CP, którego nie da się zbić API hosta — tylko mniejszą liczbą węzłów (fuzje / persistent). Z kolei 0.74–0.77 nominalnego pasma end-to-end dla dense bf16 na GDDR7 pokazuje, że nasze ~700/960 GB/s (73%) w MMVQ na skwantowanych wagach jest na poziomie najlepszych silników NVIDIA na GDDR; dalszy zysk z pasma jest trudny.

## 4. Pomysły dla nas
1. **`hipGraphUpload` po `hipGraphInstantiate` i po udanym `hipGraphExecUpdate`** (ggml-cuda.cu ok. `:2757` i `:5617`, makro w `vendors/hip.h`).
   - Zysk `[SZACUNEK]`: 0 w stanie ustalonym; tylko jeśli instancje są często tworzone/aktualizowane (np. przełączanie kształtów MTP draft/verify, adaptacyjna głębokość draftu z łatki 0039). Wtedy może zdjąć jednorazowy koszt przygotowania kernargów z pierwszego replay (`[WNIOSEK]`: zależy od implementacji CLR, nie zweryfikowane).
   - Koszt: ~5 linii. Ryzyko: ~0 (upload jest asynchroniczny na tym samym strumieniu).
   - Pomiar: najpierw licznik wywołań instantiate/ExecUpdate na token (log w `ggml_cuda_graph_update_executable`); jeśli ≈0 po rozgrzaniu — porzucić bez benchmarku. Jeśli >0, rocprofv3 `--hip-trace` czas pierwszego `hipGraphLaunch` po update, przed/po.
2. **Losowe wstrzykiwanie opóźnień do kerneli z tickiem / ostatnim blokiem / barierą grid** (koncepcja ptx-schedule).
   - Co: makro `GGML_RACE_PERTURB(site_id)` → `if (seed-hash(site_id, blockIdx) < p) __builtin_amdgcn_s_sleep(k)` przed/po atomikach i barierach w: norm+router+top-k (łatka 0053), MoE tail (0051), FA q4_0 (0011; był już wyścig — łatka 0018), ewentualnym persistent kernelu z `lfm-decode-round2`. Kampania: `test-backend-ops` dla tych opów w pętli po seedach (build testowy, nie produkcyjny).
   - Zysk: 0 t/s bezpośrednio; pozwala bezpieczniej robić agresywniejsze fuzje „ostatni blok”/persistent, które są naszą główną drogą na koszt uruchomień. Koszt: 0.5–1 dzień. Ryzyko: fałszywe hangi przy zbyt długich sleepach w spinach.
3. Nic więcej wydajnościowego — wszystkie pozostałe techniki repo albo już mamy, albo wymagają sprzętu NVIDIA (PDL, klastry, TMA, Tile IR).

## 5. Krytyka
- Repo nie jest o wydajności kerneli, tylko o ergonomii i bezpieczeństwie programowania CUDA w Ruście. Liczby wydajności to głównie dowód „bezpieczeństwo nic nie kosztuje”, mierzony na B200 (HBM, sm_100) — bez znaczenia dla nas.
- Grout „pokonuje” vLLM/SGLang o 4–5% przy batch=1 dense bf16, ale vLLM był bez prefix cache, porównanie request-level z TTFT; duże GEMM-y to cuBLAS — kernelowo nic nowego.
- Benchmark grafów używa kernela, który nic nie robi (D=2048); 0.81 µs/węzeł to czysty koszt CP NVIDIA, nie porównywalny 1:1 z naszymi 2.5 µs mierzonymi kopią 2048 floatów (u nas też praca „chowa się” w granicy) — ale rząd wielkości różnicy jest wiarygodny.
- Reaktor A/B: sami autorzy przyznają, że skala testu (Mops/s) nie odpowiada realnym obciążeniom GPU.

## 6. Werdykt
**Brak** (na granicy niskiej) — to framework językowy Rust → PTX/Tile IR bez ścieżki do AMD; jedyne przenośne rzeczy to drobny `hipGraphUpload` i koncepcja testów wyścigów przez wstrzykiwane opóźnienia, żadna nie przyspieszy decode w sposób mierzalny.
