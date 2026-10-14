# 27 — flashinfer-bench-starter-kit + FlashInfer-Bench (format FlashInfer-Trace)

Repo: https://github.com/flashinfer-ai/flashinfer-bench-starter-kit (commit `75ccd05`, 2026-04-25) oraz projekt-matka
https://github.com/flashinfer-ai/flashinfer-bench (commit `15618a6`, 2026-09-25). Przeczytałem też zbiory danych na HF:
`flashinfer-ai/mlsys26-contest` (definicje + workloady konkursu) i `flashinfer-ai/flashinfer-trace` (definicje `gdn_mtp_*`)
oraz blog https://flashinfer.ai/2025/10/21/flashinfer-bench.html. Samej biblioteki FlashInfer nie omawiam (raport 07).
Ścieżki bez prefiksu odnoszą się do `flashinfer-bench/`, a `kit/` do starter kitu.

## 1. Co to jest

Starter kit to tylko szablon zgłoszenia do konkursu MLSys 2026 „AI Kernel Generation” (tory: fused MoE FP8, DSA sparse
attention, GDN decode/prefill). Zawiera puste `kernel.cu`/`kernel.py`, `config.toml`, skrypty `pack_solution.py`,
`run_local.py`, `run_modal.py` i dokumenty `EVALUATION.md`/`FAQ.md` (`kit/README.md:27-36`, `kit/solution/cuda/kernel.cu`).
Konkurs zamknięto 24.04.2026 (`kit/EVALUATION.md:165`), a repo stoi od tego czasu i nie ma pliku licencji.
Wartość leży w FlashInfer-Bench (Apache-2.0, aktywny, ostatni commit we wrześniu 2026). To schemat JSON **Definition → Workload →
Solution → Trace**, narzędzia do zbierania workloadów z prawdziwego serwowania (SGLang + zrzuty API FlashInfer),
benchmark (CUPTI, zimny L2) oraz `apply()`, które podmienia kernel w silniku na najlepszy z bazy. Działa wyłącznie na
NVIDIA (B200 sm_100a w konkursie, `kit/EVALUATION.md:10`; timing przez `flashinfer.testing`, `flashinfer_bench/bench/timing.py:13`).

## 2. Kluczowe techniki (z dowodami)

| # | Technika | Dowód |
|---|---|---|
| T1 | **Definition**: nazwa koduje stałe osie (`{op_type}_{props}_{constants}`), osie `const`/`var`, tensory wejść i wyjść, `constraints` i **referencja w czystym PyTorch** (funkcja `run`) jako jedyna specyfikacja semantyki, także dla agenta | `docs/flashinfer-trace/definition.mdx:9-31,167-173` |
| T2 | **Workload** = wartości osi `var` plus źródło każdego wejścia: `random`, `scalar` albo `safetensors` (ścieżka i klucz). Jedna linia JSONL na workload | `docs/flashinfer-trace/workload.mdx:19-45` |
| T3 | **Trace** = definicja + workload + rozwiązanie + ewaluacja (status z 6 klas, max abs/rel error, latencja, środowisko). Workload „goły” to trace bez rozwiązania, więc baza wyników i zbiór zadań mają jeden format | `docs/flashinfer-trace/trace.mdx:20-74` |
| T4 | **Zbieranie z prawdziwego ruchu**: SGLang z prawdziwymi promptami (ShareGPT) i zrzut „Level 10” na granicy API FlashInfer (`FLASHINFER_DUMP_*`). Bez zmian w SGLang/FlashInfer | `scripts/collect_workloads.py:3-4,389-454,668-677`, `.claude/skills/collect-workloads/SKILL.md:9-11` |
| T5 | **Polityka zapisu**: tensory int (indptr, indeksy) idą do safetensors, float jako `random` („activation values don't affect kernel performance”), skalary jako wartości | `scripts/sanitize_dumps.py:8-11,460-494` |
| T6 | **Dedup i różnorodność**: maks. 2 workloady na ten sam zestaw osi, maks. 20 na definicję. Wybór zachłanny farthest-point po znormalizowanych osiach z gwarancją jednego reprezentanta na batch size. Dla atencji klucz to średnie `kv_len`/`q_len` liczone z indptr | `scripts/sanitize_dumps.py:644-648,712-781`, `flashinfer_bench/tracing/presets.py:165-198,228-266` |
| T7 | **Kontrolowany batch przy zbieraniu**: statyczne batche 8/32/64/128 × 4 rundy przez offline Engine, bo serwer z continuous batching nie daje wiarygodnie dekodowania z B>1 | `scripts/collect_workloads.py:484-499,697-702` |
| T8 | **Pomiar**: mediana czasu GPU z CUPTI, `cold_l2_cache=True`, `use_cuda_graph=False`, blokada per urządzenie. Domyślnie 10 rozgrzewek, 50 iteracji, 3 próby, każda z nowymi wejściami losowymi | `bench/timing.py:71-82`, `bench/config.py:35-45`, `bench/evaluators/default.py:59-74` |
| T9 | **Poprawność**: element jest zły tylko wtedy, gdy przekracza **i** atol, **i** rtol. Do tego `required_matched_ratio` (MoE 0.9–0.95), osobny ewaluator dla low-bit i test TVD dla samplingu | `bench/utils.py:96-123`, `bench/eval_config.yaml:4-10`, `bench/evaluators/lowbit.py:20-27`, `kit/FAQ.md:112-114` |
| T10 | **Wynik**: średnia arytmetyczna speedupów per workload względem bazy FlashInfer. Jeden błędny workload zeruje kernel. `win@p`/fast_p jako krzywa | `kit/EVALUATION.md:104-114`, `examples/win_at_p.py:4-9` |
| T11 | **`apply()` / ApplyTable**: dla każdego klucza (osie workloadu) wybiera rozwiązanie o najwyższym speedupie z traces, w granicach max_atol/rtol, z fallbackiem na oryginał. To tablica dispatchu zbudowana z pomiarów | `flashinfer_bench/apply/table.py:188-225,380`, `apply/config.py:16-22`, blog („Day-Zero Integration”) |
| T12 | **Narzędzia dla agentów**: pack/extract rozwiązania, sanitizer, NCU jako funkcje z JSON-schema; skille Claude do onboardingu modelu (discover → extract definitions → collect workloads → PR) | `kit/README.md:163-223`, `.claude/skills/*/SKILL.md` |

Dane konkursu i HF (moje odczyty plików):
- `gdn_decode_qk4_v8_d128_k_last`: 54 workloady, B ∈ {1,4,8,16,32,48,64}, B=1 tylko 10 razy. **Wszystkie** tensory
  (q, k, v, state, a, b, A_log, dt_bias) są z prawdziwego przebiegu w safetensors, wbrew domyślnej polityce T5.
  Opis: „Captured from Qwen3 Next linear attention layers (TP=4)”.
- MoE `moe_fp8_block_scale_ds_routing_topk8_ng8_kg4_e32_h7168_i2048`: 19 workloadów, seq_len od 1 do 14107.
  `routing_logits` i `routing_bias` są prawdziwe, a wagi i aktywacje losowe. Prawdziwy rozkład ekspertów zostaje,
  wartości wag nie mają znaczenia.
- `gdn_mtp_qk{4,8,16}_v{8,16,32}_d128_k_last` (flashinfer-trace): GDN dla weryfikacji spekulacji (T>1, pula stanów +
  `initial_state_indices`, opcjonalny `intermediate_states_buffer` dla rollbacku). Workloady qk8_v16: 50, wszystkie
  `seq_len=4`, B od 1 do 48.

## 3. Przeniesienie na AMD/HIP/RDNA3

| Element | Przenośność | Jak u nas / dlaczego nie |
|---|---|---|
| Schemat JSON (T1–T3) | **tak, jako idea** | Schemat jest niezależny od sprzętu, ale nie ma typów blokowych (`dtype` tylko fp32…int8/bool, `definition.mdx:126-138`), czyli brak Q4_K/Q5_K/Q6_K/IQ4_XS/q8_1/q4_0. U nas wejścia identyfikujemy typem ggml + `ne/nb` + `op_params`, a wagi **nazwą tensora w GGUF** (odpowiednik `safetensors`+`tensor_key` bez zrzutu). Pythonowego stacku FIB nie przejmujemy: builder torch/tvm-ffi, CUPTI i `torch.cuda` nie obsłużą kerneli ggml w grafie HIP. |
| Zrzut na granicy API (T4) | **tak** | Odpowiednik to `ggml_backend_sched_eval_callback` (`ggml-backend.cpp:1931-1960`, użyty w `common/debug.cpp:143-181`). Haczyk: jeśli callback „chce” węzeł, scheduler tnie graf w tym miejscu i synchronizuje (`:1939-1954`). To łamie fuzje ggml-cuda (`ggml_cuda_can_fuse` patrzy na kolejne węzły) i grafy HIP. Sygnatury wykonanych **grup fuzji** trzeba więc logować w `ggml_cuda_graph_evaluate_and_capture` (`ggml-cuda.cu:5398`), raz na klucz grafu. Dane zrzucać osobnym przebiegiem, w którym callback wybiera tylko węzły-granice segmentów. |
| Polityka random/real (T5) | **częściowo** | Dla MMVQ/FA wartości aktywacji faktycznie nie zmieniają czasu. Zmieniają go za to: `ids` MUL_MAT_ID (które wagi ekspertów czytamy, trafienia w MALL), top-k/argmax, długości KV i clamp q8_1 (S1, poprawność). Te muszą być prawdziwe, co konkurs sam przyznał, zrzucając `routing_logits` i stan GDN. |
| Dedup/farthest-point (T6) | **tak** | Klucz: (sygnatura grupy fuzji, typy, `ne`, liczba kolumn, kubełek głębokości KV). Wagą workloadu jest **liczba wywołań na krok**, której FIB nie ma (patrz krytyka). |
| Pomiar CUPTI, zimny L2, bez grafu (T8) | **nie wprost** | Na RDNA3 odpowiednikiem L2 jest 96 MB MALL. Zimny cache warto skopiować, i tak robi `mmvq-bench`. Ale `use_cuda_graph=False` plus czas samego kernela pomija granicę ~2.53 µs (`lfm-decode-round2.md:21-35`), czyli główne wąskie gardło LFM (416 kerneli/token). Dla nas jednostką pomiaru musi być **segment w grafie HIP**, nie pojedynczy op. |
| Tolerancje (T9) | **tak, jako uzupełnienie** | U nas domyślna bramka to bitowa równość z upstream/`GGML_HIP_*=0`. atol∧rtol + matched ratio tylko dla zmian niebitowych (FA q8_0 na WMMA, stan GDN fp16), obok KLD. |
| ApplyTable (T11) | **tak, w C++** | Generowany z pomiarów nagłówek dispatchu: (typ, nrows, ncols) → (rows/block, waves_per_eu, ścieżka). Dziś te progi są ręczne (K1, K4). |
| Definicje MoE/DSA | **nie** | FP8 block-scale + routing DeepSeek (grupy, bias) nie pasuje do LFM (64/4, Q5_K). RDNA3 nie ma FP8. |
| Definicje GDN decode/MTP | **semantyka tak** | Ta sama reguła delta i gating (`docs/op-types/gdn.mdx:7-16,85-89`). Nasz Qwen ma 48 głów V × 128² (`11-vllm-xpu-kernels.md:75`), czyli byłby to `gdn_mtp_qk16_v48_d128`. Ich MTP zapisuje stany pośrednie per token, czyli dokładnie to, co S4 (lag+replay) usunął (`NOTES.md:290-293`). |

## 4. Pomysły dla nas

Wszystko poza P4 i P5 to infrastruktura. Bezpośredni zysk t/s wynosi 0, a korzyść to tańsze i trafniejsze iteracje
agentów piszących kernele. Nie powtarzam: bramki bitowej, `logit_hash`, zatruwania buforów, dokładnych wejść
całkowitych, diffu histogramu kerneli (04), archiwum/TRAPS i LOO (21), czyszczenia MALL w mikrobenchu (04-P8).

**P1. `GGML_HIP_TRACE`: katalog workloadów z prawdziwego dekodowania (Qwen MTP n=4/5 i LFM n=1).**
- Co: w `ggml-cuda.cu` w `ggml_cuda_graph_evaluate_and_capture` (`:5398`), przy budowie/aktualizacji grafu (nie przy
  każdym odtworzeniu), dopisywać do JSONL rekord na każde **uruchomienie kernela**:
  - sygnaturę grupy fuzji (np. `RMS_NORM+MUL→q8_1`, `MUL_MAT_ID+…moe_down_reduce`), nazwę wybranego kernela i szablonu (typ, ncols);
  - typy i `ne/nb` źródeł, `op_params`, nazwy tensorów (`blk.N.ffn_gate_exps`);
  - liczbę wywołań na krok po deduplikacji.
- Workload ma postać jak w FIB: osie `var` = liczba kolumn, głębokość KV, liczba użytych ekspertów, a wagi są
  referencją do GGUF po nazwie.
- Druga, opcjonalna faza (bez grafów HIP, `eval_callback` tylko na granicach segmentów) zrzuca prawdziwe dane małych
  wejść: aktywacje q8_1 (5×5120 B), `ids`, `a/b` GDN, długość KV.
- Zysk `[SZACUNEK]`: 0 t/s. Daje jedną tabelę „co naprawdę biegnie w kroku i ile razy”. Agent dostaje definicję +
  workloady z wagami, zamiast zgadywać kształty z llama-bench (różne `ne` w MTP i llama-bench to znana pułapka, 04-P1).
- Koszt: 1–1.5 dnia. Ryzyko: logowanie w ścieżce przechwytywania grafu. Przełącznik domyślnie wyłączony, bez wpływu na wynik bitowy.
- Pomiar: suma `wywołania × czas_rocprof` per sygnatura musi dać czas GPU kroku z `trace_breakdown.py` z dokładnością ±2%.

**P2. Replay segmentów w grafie HIP z prawdziwymi wagami (zamiennik mikrobenchu i weryfikator decyzji).**
- Co: narzędzie C++ na infrastrukturze `test-backend-ops` (budowanie grafu ggml), które czyta JSONL z P1. Dla danego
  workloadu buduje **łańcuch węzłów segmentu**, np. warstwę LFM: rms_norm(q8) → in_proj+conv → out_proj(+res) →
  norm+router+topk → gate+up → quantize → down+reduce. Wagi ładuje z GGUF (mmap, prawdziwe `blk.N`) i **rotuje po
  wszystkich warstwach** danego typu, więc MALL jest „zimny” jak w modelu. Mierzy wall-time odtworzenia grafu HIP
  (zdarzenia wokół `hipGraphLaunch`) oraz czasy kerneli z rocprofv3.
- Uzasadnienie: dziś mikrobench myli się co do Q6_K i GLC|DLC, więc decyzje zapadają na rocprofv3 w pełnym modelu
  (`NOTES.md:247-248`). Do tego `test-backend-ops -perf` powtarza **ten sam** tensor wag w jednym grafie
  (`test-backend-ops.cpp:1650-1661`), więc małe wagi siedzą w MALL. FIB rozwiązuje to `cold_l2_cache`, ale gubi granice.
  Segment w grafie trzyma oba efekty.
- Zysk `[SZACUNEK]`: pętla agenta zamiast pełnego `spec_sweep` (2 rundy A/B na serwerze) dostaje sygnał w sekundach, a
  pełny pomiar zostaje do werdyktu (jak H2 w 21). Kandydaci na pierwsze użycie: niezrobione fuzje LFM z
  `lfm-decode-round2.md:103-112` (down+reduce z normą następnej warstwy, gate+up piszące q8_1, ~0.1 ms/token każda).
- Koszt: 2–3 dni. Ryzyko: replay segmentu nie odda wpływu sąsiednich warstw na MALL. Walidacja: replay musi
  odtworzyć znane wyniki z NOTES, w tym zysk K1 GLC|DLC i Q6_K, którego mikrobench nie widział. Jeśli nie odtworzy, narzędzie odpada.
- Pomiar: korelacja Δ(replay) z Δ(ms/krok serwera) na 5–6 historycznych łatkach (np. 0049–0054 dla LFM, K1/K2 dla Qwena).

**P3. Wynik ważony wywołaniami zamiast średniej speedupów.**
- Co: w raporcie replayu i w briefie agenta liczyć `Σ_i count_i · t_i` (przewidywane ms/krok) oraz resztę
  `ms/krok_serwer − Σ`. Reszta to budżet granic, hosta i przerw. FIB liczy średnią arytmetyczną speedupów per
  workload (`kit/EVALUATION.md:106`), więc 2× na kernelu wołanym raz na krok liczy się tak samo jak 2× na kernelu
  wołanym 106 razy.
- Do każdej definicji dopisać **prędkość światła** z osi (bajty wag + KV + aktywacji / 960 GB/s) i pokazywać % roofline obok czasu.
- Zysk: 0 t/s. Lepszy ranking celów. Koszt: 2 h na wierzchu P1/P2.

**P4. Analiza offline: unikalni eksperci przy weryfikacji k tokenów w LFM (decyzja o spekulacji dla MoE).**
- Co: z P1 (faza danych) zrzucić prawdziwe `ids` top-4 dla 38 warstw MoE na promptach PL/EN/kod (wzorem konkursu,
  który zrzucał prawdziwe `routing_logits`). Potem, **bez GPU**, policzyć średnią liczbę unikalnych ekspertów U(k)
  w oknach k kolejnych tokenów.
- Górne ograniczenie przy routingu losowym: U = 64·(1−(60/64)^k) daje 7.75 / 11.3 / 17.7 dla k = 2 / 3 / 5.
- Przy 1.04 GB wag ekspertów i ~0.76 GB reszty na token (`NOTES.md:338`) odczyt na krok weryfikacji to ×1.54 / ×2.05 /
  ×2.98 bajtów pojedynczego tokenu `[SZACUNEK, routing jednostajny]`. Prawdziwa lokalność routingu da mniej.
- Zysk: decyzja, czy n-gram/self-spec dla LFM (`NOTES.md:341`, otwarte) ma sens przy realnym U(k) i stałym koszcie
  ~416 granic na krok, który się amortyzuje.
- Koszt: 0.5 dnia (skrypt Python na zrzutach). Ryzyko: brak, analiza offline. Pomiar: U(k) per typ promptu i per
  warstwa, prognoza ms/krok (bajty/700 GB/s + granice) vs akceptacja n-gramu z `spec_sweep`.

**P5. Analiza offline numeryki stanu GDN w 16 bitach na prawdziwych danych.**
- Co: zrzucić z P1 sekwencję q, k, v, a, b dla kilku warstw GDN Qwena (np. 4 z 48; ~40 KB na warstwę i token przy
  założonych 16 głowach q/k i 48 głowach v w fp32 `[SZACUNEK]`, 2000 tokenów ≈ 320 MB) i stan startowy. W numpy na CPU przeliczyć rekurencję w fp32 vs stan fp16/bf16 (z i bez
  stochastic rounding) i zmierzyć błąd wyjścia i stanu w funkcji długości. Tak robi konkurs: prawdziwy stan i bramki w
  workloadach GDN, bo `randn` dla `a/b` daje nierealne decay.
- Zysk: rozstrzyga przed pisaniem kernela, czy pomysł „stan GDN w 16 bitach” (07, 11-P1: −151 MB/krok odczytu+zapisu) ma
  sens numerycznie. `[SZACUNEK]` przy ~640 GB/s to ~0.2 ms/krok, jeśli numeryka przejdzie.
- Koszt: 0.5–1 dnia. Ryzyko: brak dla GPU. Wynik niebitowy, więc ostateczna bramka to i tak KLD na modelu.

**P6. Definicje dla agentów kernelowych (format FIB, nasz zakres).**
- Co: `research/defs/<nazwa>.json` dla ~8 gorących rodzin: mmvq wielokolumnowe (typ × kształt × ncols 1..16), GDN lag,
  FA kvq q4_0 i planowany q8_0 (GQA 6×n tokenów / 4×1 dla LFM), norm_router_topk, moe_down_reduce,
  in_proj_conv, rms_norm_mul_rope.
- Każda definicja: osie const/var z prawdziwych modeli, referencja = upstream ggml (`GGML_HIP_*=0`) albo backend CPU
  (zamiast PyTorch), bramka (bitowa / KLD), workloady z P1 z wagami wywołań, roofline z P3.
- Brief agenta wskazuje plik definicji, nie NOTES (zgodne z 21-P2 „attention budget”).
- Koszt: 1 dzień. Zysk: pośredni, mniej źle dobranych kształtów i trybów w pracy agentów.

**Outside the box: tabela dispatchu z pomiarów (à la ApplyTable, T11).**
- Po P2 przemiatać per (typ, nrows, ncols) warianty, które już są w kodzie (rows/block, `waves_per_eu`, MMVQ vs WMMA
  small-N od 7/9 kolumn, para MMVQ), i generować z wyników nagłówek `mmvq-dispatch.inc`. Progi K1/K4 przestają być
  ręczne, a po każdej zmianie kernela tabela przelicza się automatycznie.
- Zysk `[SZACUNEK]` 0–2% na weryfikacji, głównie na typach i kształtach, których nikt ręcznie nie stroił (UD ma
  mieszane typy na małych k/v, `NOTES.md:268`). Koszt: 1 dzień po P2.

## 5. Krytyka

- **Metryka ślepa na koszt uruchomień.** CUPTI mierzy sam kernel, bez grafu (`timing.py:74-81`). Definicje są per op,
  więc fuzja wielu opów w ogóle nie ma gdzie zaistnieć. Dla LFM (416 granic × ~2.5 µs ≈ 1 ms z 4.1 ms) taki benchmark
  nagradzałby szybsze pojedyncze kernele i był obojętny na to, co u nas dało najwięcej (0049–0054).
- **„Float nie wpływa na wydajność” to uproszczenie** (`sanitize_dumps.py:461`). Prawdziwe dla GEMM/atencji, fałszywe
  dla routingu MoE, top-k, samplingu i numeryki rekurencji. Konkurs po cichu to obszedł, zrzucając `routing_logits` i
  cały stan GDN. Domyślny generator robi `randn` dla wszystkiego, a int jako `randint(-1024,1024)` (`bench/utils.py:28-50`).
  Indeks wygenerowany w ten sposób jest nieprawidłowy, jeśli workload go nie zrzuci.
- **GDN MTP nie sprawdza zapisu stanu.** Referencja zwraca `final_state = initial_state.clone()` (linia 101 referencji
  `gdn_mtp_qk16_v32_d128_k_last`), a workloady nie podają `intermediate_states_buffer`. Część krytyczna dla rollbacku
  spekulacji (stany pośrednie) nie przechodzi żadnej walidacji. Rozwiązanie, które źle zapisuje stany, przejdzie test.
- **Niespójne definicje GDN**: dokument opisuje `use_qk_l2norm` (`docs/op-types/gdn.mdx:75`), a definicja konkursowa
  go nie ma i referencja nie normalizuje q/k. FAQ przyznaje, że qk4_v8 na HF to „earlier version” inna niż na stronie
  konkursu (`kit/FAQ.md:230-232`).
- **Luźne tolerancje MoE**: atol=1, rtol=0.3, a 10% elementów może być dowolnie złe (`kit/EVALUATION.md:51`,
  `kit/FAQ.md:114`). Przy bramce bitowej dla naszych fuzji to nie do przyjęcia.
- **Średnia arytmetyczna speedupów** i `speedup_factor` względem pętli PyTorch (`trace.mdx:55` sam przyznaje, że to
  bywa „very large”) nie są miarą wpływu na end-to-end.
- **Inny reżim niż nasz**: serwerowe B 1–128, TP 2–8, FP8. B=1 to tylko 10/54 workloadów GDN decode, a weryfikacja MTP
  jest tylko dla `seq_len=4`. Nasz przypadek (1 sekwencja, 5 kolumn, kwanty blokowe) jest na marginesie zbioru.
- Starter kit nie zawiera żadnej techniki kernelowej (szablony z `TODO`), nie ma licencji i jest martwy od końca konkursu.

## 6. Werdykt

**Średnia (metodologia, zero kerneli).** Do wzięcia jest wzorzec „prawdziwe workloady per kernel z ruchu + definicja z
referencją + dedup”, w wersji dostosowanej do nas: zapis na granicy grup fuzji ggml-cuda, wagi po nazwie z GGUF,
pomiar segmentu w grafie HIP i wynik ważony wywołaniami (P1–P3, P6). Do tego dwie tanie analizy offline na
prawdziwych danych (P4 eksperci LFM, P5 stan GDN 16-bit). Ich metryka kernel-only nie widzi kosztu uruchomień, który
jest naszym głównym wąskim gardłem w LFM.
