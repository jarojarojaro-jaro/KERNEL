# 15a — Trwałe kernele / megakernele dla decode (vLLM MonoKernel i prior art) a nasz stos

Data: 2026-10-16. Bez lokalnego GPU i bez chmury: wszystko z kodu źródłowego, nagłówków GGUF, nagłówków ROCm i naszych zapisanych profili.
Oznaczenia: `[NIEZWERYFIKOWANE]` = nie sprawdzone u źródła lub pomiarem; `[SZACUNEK]` = rachunek z naszych liczb; `[WNIOSEK]` = wniosek z kodu bez pomiaru.
Skrypty tego raportu: `15a-lfm-budget.py` (budżet tokenu LFM z taśmy PM4), `15a-gguf-active-bytes.py` + `15a-ggufls.py` (bajty aktywne na token z nagłówka GGUF, bez numpy).

## TL;DR

1. **vLLM MonoKernel (RFC #60904)** to jeden trwały kernel na warstwę dekodera (GLM-5.2: cała warstwa w jednym launchu; DeepSeek-V4.1: dwa launche, K1 i K2). Wewnątrz nie ma **żadnej bariery siatki**. Siatka to dokładnie 256 CTA × 512 wątków (1 CTA na CU MI355X). Etap to lista zadań: zadanie `t` biegnie na CTA `(base+t) % 256`. Zależności idą przez **„tagged pairs”** `(wartość, tag epoki)` zapisywane jednym 8/16-bajtowym store’em. Konsument polluje sam payload, aż zgodzi się tag, więc hand-off kosztuje jeden obieg pamięci (bez flagi i bez fence). **Wagi niezależne od wejścia ładuje przed czekaniem.** Część pracy liczy redundantnie, żeby ominąć hand-off (każde z 256 CTA MoE samo liczy RMSNorm, kwant FP8 i top-8 z 256 wyników routera). W pętlach czekania jest bounded poll ze słowem błędu i fail-stop.
2. **Nagłówek 13.70 → 5.92 ms (GLM-5.2, 8× MI350X, batch 1)** jest wiarygodny, ale dotyczy innego reżimu niż nasz. Roofline: na GPU przypada ~5.8–9.2 GB/token, czyli 0.72–1.15 ms przy 8 TB/s. Baza vLLM wykorzystuje więc **5–8% pasma HBM**, a MonoKernel **12–24%**. To reżim TP8 ograniczony latencją (2459 launchy, 2 all-reduce na warstwę), nie pasmem. Względem mocniejszej bazy (ATOM) zysk GLM to TPOT 6.897 → 5.380 ms (−22%), nie 2.3×.
3. **arXiv 2605.07182 nie dotyczy tego tematu.** To „Star Elastic” (NVIDIA): zagnieżdżone podmodele Nemotron Nano v3 30B/23B/12B z jednego post-trainingu i osobny podmodel dla fazy „thinking” i „answering”. Dla nas nie ma tu nic o kernelach (krótko w §5).
4. **Stary szacunek „trwały kernel MoE po PM4 ≈ 1.4%” był poprawny tylko dla samych granic** (2×38×0.6 µs). Pominął to, co megakernele faktycznie zyskują: prefetch wag ponad granicą operacji (rampa i pierwszy bajt), nakładanie małych, latencyjnych operacji na strumień wag i redundantne liczenie zamiast hand-offów. Nowy budżet LFM na XTX z naszej taśmy PM4:
   - aktywne wagi z GGUF 1.777 GB/token, podłoga 1.85 ms przy 960 GB/s;
   - dziś 3.40 ms/token, czyli **54% pasma** (upstream 46%);
   - pula „DRAM prawie bezczynny” = 0.70 ms narzutu matvec ponad strumień 900 GB/s + 0.53 ms małych kerneli = **1.23 ms (36% czasu)**;
   - z tego granice PM4 to tylko 0.14–0.26 ms.
5. **Odpowiedzi:**
   - **XTX:** trwały kernel z barierami między fazami **nie pobije PM4**. Zmierzona bariera trwałego gridu 0.48–0.77 µs = granica PM4 0.46–0.86 µs; to wynik rundy 4 i on się nie zmienia. Pobić PM4 może tylko kernel *dataflow* z prefetchem wag: `[SZACUNEK]` +12…+28% dla LFM (odzysk 30–60% puli). Tańszy krok pośredni to **„PM4-PDL”**: taśma PM4 bez pakietów granicy między parą producent→konsument, a konsument ładuje wagi i czeka na flagę/ticket. `[SZACUNEK]` +5…+15% LFM przy ~1/4 kosztu i bitowo z definicji (te same kernele).
   - **Ampere (sm_86/89):** nie ma PDL, a granica grafu CUDA kosztuje ~1–2 µs `[NIEZWERYFIKOWANE dla 3090]`. Pula granic LFM na 3090 to 357 × (0.8–1.3) µs ≈ 0.29–0.46 ms, więcej niż na XTX z PM4, a LFM też jest na 54% pasma. Trwały kernel ma tu relatywnie *więcej* do wzięcia niż na XTX, ale to osobny port CUDA.
   - **Blackwell (sm_120):** PDL już jest w llama.cpp (+5–13% tg upstream). Megakernel dołożyłby tylko drobnoziarniste zależności i nakładanie małych operacji. 5060 Ti z LFM Q4_K_M jest już ~70% pasma `[SZACUNEK]`, więc zysk byłby mały.
   - **Model:** zyskuje **LFM2.5** (hidden 2048, kernele 0.7–17 MB, stały narzut 2.2–6.3 µs na wywołanie przy 0.8–19 µs strumienia). Qwen3.8-27B już ma 76–77% pasma w plain decode, więc `[SZACUNEK]` najwyżej +3–6%.
6. **Ranking (zysk × pewność / koszt):**
   1. mikrobench PM4-PDL, potem PM4-PDL w taśmie LFM;
   2. prefetch wag do MALL (96 MB Infinity Cache) dispatchem bez bariery w trakcie małych kerneli;
   3. przyjęcie z RFC procesu bezpieczeństwa: bounded wait + słowo błędu, stres 10⁵ replayów bit w bit;
   4. trwały blok MoE LFM jako dataflow;
   5. pełny megakernel warstwy LFM (25–35 osobodni na backend; ryzyko: co-residency na konsumenckim GPU z wyświetlaczem).
7. **Sprzętowa odpowiedź AMD na „bańki” omija RDNA3.** `hipLaunchAttributeExtDynDataPrefetch` (prefetch do L2 przed startem kernela) jest w HIP 7.15 u nas, ale ROCr zwraca 0 regionów dla wszystkiego poniżej gfx12.5 (`amd_gpu_agent.cpp:2734-2740`). PDL w ROCm nadal istnieje tylko jako enum.

## 1. Audyt tez

Roofline: MI350X/MI355X HBM 8 TB/s; RX 7900 XTX 960 GB/s; RTX 3090 936 GB/s; H100 3.35 TB/s; A100 1.6 TB/s (wg MPK).

| # | Teza (dokładnie) | Sprzęt | Model + kwant | Obciążenie / batch / ctx | Baza (strojona?) | Identyczne wyjście / jakość | Komenda / logi | Roofline / Amdahl | Werdykt |
|---|---|---|---|---|---|---|---|---|---|
| 1 | „Time per token, batch 1 / 8: 13.70 / 17.33 ms → 5.92 / 11.44 ms (2.31× / 1.51×)”, launche 2459 → 210 (RFC #60904) | 8× MI350X, TP8 | GLM-5.2-MXFP4: eksperci MXFP4, atencja BF16 (domyślnie) | decode, ~3k ctx; `perf_ab.py`: 256 tok, greedy, ignore_eos, oba ramiona HIP graph FULL_DECODE_ONLY | „vLLM as shipped”, domyślne (BF16 atencja, ~31 kerneli/warstwę). Nie strojona: ATOM jest szybszy (#4) | nie bitowo; GSM8K 1240 vs 1228/1234/1235, McNemar p=0.22–0.63; sanity: 90% promptów zgodne na 8 tokenach | harness `tools/mono_check/perf_ab.py` był w commicie `85f7d86209` i został usunięty z PR („Keep the MonoKernel GPU harness out of the PR”); surowych logów brak; „layer times profiler-corrected, from one run” | `[SZACUNEK]` bajty/GPU ≈ 9.2 GB (BF16 atencja) → podłoga 1.15 ms. Baza = 8.4% pasma, Mono = 19.5%. Usunięte 2249 launchy × ~2.5 µs ≈ 5.6 ms z 7.78 ms zysku; resztę tłumaczą all-reduce w kernelu | **wiarygodne**; dotyczy reżimu TP8 ograniczonego latencją, nie pasmem |
| 2 | „batch 1, FP8 attention opt-in: 4.80 ms (2.85×)” | jw. | + atencja FP8 (dodatkowa kwantyzacja) | jw. | jw. | inna numeryka (opt-in, osobna bramka jakości) | brak | podłoga FP8 ≈ 0.72 ms → 15% pasma | wiarygodne; **nie porównywać** z bazą BF16 jako czysty zysk kernela |
| 3 | Warstwa MoE b4/b8 FP8: 178.8/189.6 → 69.1/100.6 µs | jw. | jw. | 57 z 75 warstw | jw. | jw. | jw. | podłoga warstwy 8.7–14 µs, więc Mono ≈ 13–20% pasma | wiarygodne (reżim latencji) |
| 4 | ATOM #2435: GLM MTP4 C1 TPOT 6.897 → 5.380 ms (−22%), C2 −26% | MI355X, TP4 | GLM-5.2-MXFP4, natywny scaled-FP4 MFMA | Agentic, MTP4 | ATOM main (mocniejsza baza) | GSM8K 0.9606 vs 0.9674 (−0.68 pp, inna numeryka FP4) | brak logów w PR | — | **wiarygodne**; to realistyczna skala zysku względem dobrej bazy |
| 5 | FlyDSL #1204: warstwa GLM-5 S=4 78.4 µs vs 205.8–213.7 µs „ATOM latest” | 8× MI355X TP8, pozycja 3000 | GLM-5 | HIP-graph replay | ATOM | testy golden (cosinus) | brak | ~70 MB/warstwę/GPU przy 8 TB/s ≈ 9 µs → 11% pasma | wiarygodne (latencja) |
| 6 | FlyDSL #1214 (gfx1250): 37.3–37.7 µs/warstwę przy S=1, jedno GPU | 1× gfx1250 (256 CU) | GLM-5 shard TP8 | replay 16 warstw, bounded waits | pierwsza rewizja PR | golden, równość zbioru indeksów | brak | pasmo gfx1250 niepubliczne `[NIEZWERYFIKOWANE]` | nieweryfikowalne (pasmo); ważne dla ryzyk: zawieszenie wymagające restartu hosta, 200× wolniej przy współlokatorze |
| 7 | DSv4.1 #60397 (scalone 2026-10-10): kernel 1.10–2.18× na 96 punktach; AgentX p90 interaktywność TP2 c1 318 → 429 (1.35×) | 2/4× MI355X | DeepSeek-V4.1-Flash, MXFP4 + MXFP8 | AgentX 3600 s/punkt, DSpark | ta sama maszyna z mono=0 (TP2); dla TP4 bieg InferenceX z innej maszyny | GSM8K 0.9742 → 0.9750; GPQA −0.2±0.6; AIME25 −1.0±0.7 | opis testów w PR; numery z AITER przed przeniesieniem | — | wiarygodne; scalone upstream |
| 8 | Hazy „No Bubbles”: Llama-1B BF16 <1 ms/forward na H100, 78% pasma, 2.5× vLLM, 1.5× SGLang; B200 <680 µs | H100, B200 | Llama-3.2-1B BF16 | batch 1, prompt 32, 128 tok | vLLM/SGLang 2025 (≤50% pasma) | brak danych o jakości | kod open source | 2.48 GB / 3.35 TB/s = 0.74 ms → 78% się zgadza | **wiarygodne** |
| 9 | MPK (OSDI ’26): do 1.7×; Qwen3-8B A100 14.5 → 12.5 ms (podłoga ~10 ms) | A100/H100/B200 | Qwen3-8B BF16 i inne | batch 1–n | vLLM/SGLang | — | kod open source | 16 GB / 1.6 TB/s = 10 ms → 80% | **wiarygodne**, recenzowane |
| 10 | TileRT: GLM-5.3 469 tok/s/użytkownika, #1 AgentX | 8× MI355X | GLM-5.3 FP8 | AgentX, MTP | GB300 FP4 (inny system) | — | binarne `.so`, zamknięty kod | `[SZACUNEK]` ~1.2 ms/forward podłogi, więc 469 tok/s wymaga ≥0.56 tok/forward; z MTP spełnione | wiarygodne tylko z MTP; kernel nieweryfikowalny |
| 11 | Lucebox: Qwen3.5-0.8B BF16 413 vs 267 t/s llama.cpp (1.55×) | RTX 3090 | Qwen3.5-0.8B BF16 | batch 1 | llama.cpp | — | repo (`22-lucebox.md:41-47`) | `[SZACUNEK]` ~1.6 GB/token → podłoga 1.71 ms; 413 t/s ≈ 71% pasma, llama.cpp ≈ 46% | **wiarygodne**; jedyny dowód na konsumenckiej karcie |
| 12 | llama.cpp PDL #22522 (scalone 2026-05-20): tg +5–13% (RTX PRO 6000: gpt-oss 20B 332 → 376), DGX Spark +4–5% | Blackwell | różne | llama-bench tg | master | bez zmian numeryki | tabele w PR | — | wiarygodne |
| 13 | Nasz: „trwały kernel MoE po PM4 ≈ 1.4%” (`NOTES.md:379`, `lfm-decode-round4.md:169`) | XTX | LFM2.5 Q5_K_M | tg | taśma PM4 | — | — | liczy tylko 2×38 granic × 0.6 µs | **niepełne**; poprawione w §4 |

## 2. Mechanizm: jak działa MonoKernel (kod)

Źródła:
- kod: gałąź PR #60889 (head `0ab9c66567`), ścieżki `vllm/models/deepseek_v32/amd/mono/kernel/`;
- PR #60397 (scalony): `vllm/models/deepseek_v41/amd/mono/`;
- rodowód: FlyDSL PR #1204 → ATOM PR #2435 → vLLM; projekt pochodzi z TileRT (lineage w opisie FlyDSL #1204).

### 2.1 Siatka i harmonogram
- `grid = 256 CTAs x 512 threads (one CTA per MI355X CU)` (`kernel/glm/kernel.py:20-21`; `kernel/layout.py`: `BLOCKS = 256`, `THREADS = 512`). Zwykły launch, **nie cooperative** (`kernel.py:2447`: `.launch(grid=(G,), block=(THREADS,), stream=stream)`).
- Co-residency zapewnia odmowa: przy mniej niż 256 CU (GPU partycjonowany, CPX) ścieżka się nie włącza. Komentarz w kodzie mówi wprost: „every CTA of a launch stays resident: a partitioned GPU deadlocks” (`deepseek_v41/amd/mono_decode.py:148-151`).
- „Every stage is a list of tasks; task t of a stage runs on CTA (stage_base + t) % 256 and every CTA walks the stages in order. **There is no grid-wide barrier**: dependencies only point to earlier stages and all CTAs are co-resident, so every spin wait makes progress” (`kernel.py:36-39`).
- Bazy etapów są rozłożone tak, żeby zadania następnego etapu trafiały na CTA zwolnione przez poprzedni („split before uk, so every split tile lands on a CTA freed by qkv_a”, `kernel.py:275-290`).
- Etapy GLM (jeden launch): input RMSNorm → q_a/kv_a → q_a norm → q_b+RoPE → zapis KV/PE → indeks K/Q/W → scoring indeksera → radix top-2048 → absorbed q (W_UK) → sparse MLA split softmax → merge → W_UV → W_o → TP peer reduce + residual → post-attn norm → router (sigmoid) + kwant FP8 → top-8 → 1 shared + 8 routed up/gate/SiLU → kwant FP8 → down + ważenie → TP peer reduce + residual (`kernel.py:25-34`). Łącznie 14 etapów z pollowaniem (`glm/layout.py`, `POLL_STAGES`).

### 2.2 Synchronizacja: tagged pairs zamiast flag i barier
- Producent zapisuje `(value, tag)` jednym store’em 8/16 B z `sc1` (device) albo `sc0 sc1` (system, peer GPU) (`kernel.py:435-445`).
- `tag = step*launches_per_step + layer + 1`. `step` to licznik na urządzeniu podbijany raz na krok dekodowania, więc działa w grafie bez czyszczenia skrzynek (`kernel.py:360-364`).
- Konsument (`poll`, `kernel.py:460-543`) ładuje cały batch par (do `POLL_MAX = 12`) i ponawia go, dopóki którykolwiek tag nie pasuje. Tak „a batch costs one round trip after its last producer lands”. Asm `s_nop 0` w pętli blokuje hoisting ładowań.
- `pre_poll`: fala 0 czeka na jedną małą parę od każdego producenta, zanim CTA załaduje duży payload, „so waiting CTAs do not flood memory” (`kernel.py:545-551`). To bezpośrednia odpowiedź na nasz zmierzony problem: tysiące czekających głodziły producentów, 8–11 µs/fazę (`lfm-decode-round2.md:33-36`).
- **Bounded waits**: `poll_limit` ponowień, po wygaśnięciu słowo `poll_err[stage]`, flaga `poll_xrank` na ranku 0 i wczesne wyjście reszty kroku. Host robi fail-stop (`kernel.py:497-538`). Kernel kończy się wtedy ze złymi wartościami, ale GPU nie wisi.
- Porównanie z Hazy: „store payload → fence → atomicAdd licznika” i „spin na liczniku → load payload” to 2 obiegi na hand-off. Na B200 dało to 250 z 600 µs forwardu („storing activations, awaiting consistency, and loading them”). Tagged pair skraca hand-off do 1 obiegu.
- DSv4.1 używa tego samego mailboxa (`common/sync.py`, spin z `s_sleep(1)`) oraz **liczników zadań MoE** („the MoE's ug queue and down counts”, `layer.py:47`), czyli dynamicznej kolejki zadań.
- Lekcja z PR #60397: „Before the per-width scratch, layer 3 diverged at replay 13 on every run”. Wspólna pamięć scratch dla różnych szerokości kroku dawała wyścig. Każda szerokość dostała własny scratch; stres to 100K replayów porównywanych bit w bit.

### 2.3 MoE w jednym launchu (GLM, S=1)
- 256 zadań up/gate. Zadanie `u` liczy 8 wierszy pośrednich slotu `u // 32`: 8 routed slotów × 32 zadania; zadania `u < 32` liczą też shared expert (`kernel.py:2076-2087`).
- **Redundancja zamiast hand-offu.** Każde z 256 CTA samo liczy RMSNorm stanu po atencji i kwantyzację FP8 per 128, w kolejności elementów routera, więc bitowo identycznie. Fala 0 liczy też top-8 z 256 opublikowanych wyników routera (`kernel.py:2117-2144`). Znika etap „norma → kwant → top-k → rozgłoszenie”.
- **Prefetch przed czekaniem.** Wagi shared expert nie zależą od routingu, więc są ładowane przed pollem („the later zero-weight MMAs of the other tasks are cheaper than a branch”, `kernel.py:2117-2119`). Wag *routed* expertów nie da się pobrać przed top-k; to jedyny nieukrywalny bąbel MoE.
- down: ważenie wagą trasy w kolumnie próbki (`kernel.py:2311-2314`), potem `peer_reduce` (push BF16 partiali do wszystkich peerów jako tagged pairs i suma w kolejności ranków, więc wszystkie ranki są bit-identyczne, `kernel.py:888-938`).

### 2.4 Atencja i wagi skwantyzowane
- Sparse MLA: 32/64 kluczy × 8 głów na CTA, split softmax, potem merge; indekser top-2048 to 3-przebiegowy radix (11/11/10 bit) w jednym CTA na ścieżce krytycznej (`kernel.py:1326-1870`). Na gfx1250 pierwszy przebieg 3.3 → 2.0 µs (FlyDSL #1214).
- GEMV na rdzeniach macierzowych także przy S=1: `mfma_f32_16x16x32_bf16`, próbki jako wymiar N. Nieaktywne kolumny powielają ostatnią (`n_sel`), co przy ograniczeniu pasmem jest darmowe.
- MXFP4 czytane w miejscu, w layoucie AITER (16,16) shuffle, poszerzane **dokładnie** do BF16 (`v_cvt_scalef32_pk_bf16_fp4`, `ops.py: mxfp4_to_bf16x8`). FP8 block-128 jest pakowane na hoście w kafle 1 KB. Partial każdego 64-k chunku jest skalowany w f32, czyli „exact block-scaled FP8 on bf16 activations” (`kernel.py:47-55`).
- Na gfx1250 natywne WMMA FP8 (`16x16x128_fp8_fp8`) obcina sumę do ~2.6e-5 względnie, więc eksperci idą ścieżką BF16 (FlyDSL #1214). **Dokładność wygrywa z „natywnym” formatem.**

### 2.5 Dlaczego najpierw ROCm i czego brakuje na CUDA
- RFC: „The standard starts ROCm-only, where all known MonoKernels live… CUDA joins with a CUDA co-author” (`body.md:9`). Wszystkie implementacje (GLM, DSv4.1, MiniMax-M3, Kimi-K3) piszą zespoły AMD we FlyDSL/ATOM/AITER.
- Powód techniczny `[WNIOSEK]`: na ROCm baza jest droższa. Granica w grafie HIP to u nas 2.75 µs (gfx1100). Rachunek GLM daje ≥3.4 µs na usunięty launch, gdyby cały zysk pochodził z launchy. ROCm nie ma PDL: w ROCm 10.0 jest tylko `hipGraphDependencyTypeProgrammatic` (`hip_runtime_api.h:2109-2116`) bez triggera w `libamdhip64.so` (`07-flashinfer.md:68`). Na CUDA granica grafu to 0.8 µs (B200, MPK) – 1.3 µs (H100, Hazy), a PDL na sm_90+ działa.
- Na CUDA *są* megakernele, tylko nie w vLLM: TileRT (B200, zamknięte `.so`), MPK, Hazy, Lucebox (3090), DeepGEMM Mega MoE.
- Brakujące klocki w vLLM-CUDA: odpowiednik prymitywów FlyDSL (mailboxy, bounded waits, peer-push all-reduce; na CUDA NVSHMEM/symmetric memory) i autor. Co-residency na CUDA: `cudaLaunchCooperativeKernel` daje gwarancję; czy da się go przechwycić w grafie, `[NIEZWERYFIKOWANE]`.
- W HIP 7.15 (nasz `/opt/rocm`) jest `hipLaunchAttributeCooperative`, „Valid for graph nodes, launches” (`hip_runtime_api.h:1719`), a `libamdhip64.so` loguje „[hipGraph] Current capture node ModuleLaunchCooperativeKernel”.
- Status: RFC otwarty. Scalony jest tylko #60397 (DSv4.1); GLM #60889 jest otwarty z pustym opisem. Maintainerzy są sceptyczni: benchislett „I don't particularly like the Monokernel interface”; tlrmchlsmth chce zgodności layoutów KV/wag i kerneli JIT zamiast binariów.

### 2.6 Prior art w skrócie
- **Hazy Megakernels** (`HazyResearch/Megakernels`):
  - interpreter instrukcji per SM z harmonogramem z Pythona;
  - SMEM stronicowany (13 × 16 KiB na H100), żeby następna instrukcja zaczęła ładować wagi, zanim poprzednia skończy;
  - liczniki w pamięci globalnej z `atomicAdd` po `tma::store_async_wait()` (`demos/low-latency-llama/matvec_adds.cu:129-132, 174`);
  - spin z `__nanosleep`; w `include/config.cuh:48` `GMEM_SPIN_LOOP_SLEEP_NANOS` jest zadeklarowany jako `bool` (= 1 ns), drobny błąd;
  - podział MLP na 4 chunki z osobnymi licznikami: down czeka tylko na swój chunk, czego PDL nie potrafi;
  - budżet B200: 250/600 µs na hand-offy aktywacji, 200 na liczenie, 30 na czekanie na wagi.
- **MPK / Mirage** (arXiv 2512.22219, OSDI ’26):
  - kompilator robi z grafu „tGraph” na poziomie SM;
  - runtime w kernelu: workery i schedulery na zarezerwowanych SM (4 SM, 16 warpów schedulera), kolejki w pamięci urządzenia na `atomicAdd`, launch hybrydowy JIT/AOT;
  - pipelining między zadaniami: 1.2–1.3× na ostatnim linear;
  - na B200 launch 3.8 µs eager i 0.8 µs w grafach, czyli 0.2 ms/token dla 293 kerneli (Qwen3-8B);
  - MoE: balanser hybrydowy plus gather w ładowaniu GEMM.
- **ThunderKittens/HipKittens**: biblioteki kafelków, na których Hazy zbudował megakernel. HipKittens (arXiv 2511.08083) celuje w CDNA, nie RDNA. Megakernela na AMD nie mają.
- **FlashInfer** (nasz `repos/07-flashinfer.md:61`): „monomoe”, trwały grid, handoffy przez dane, reset przez parytet. Przenośne co do logiki.
- **TensorFold** (M5): megakernel z barierą siatki przegrał, 4.6–18 µs/fazę wobec 4.01 µs relaunchu (`tensorfold/README.md:70, 257`).
- **Lucebox** (3090): 82 bloki × 512, `AtomicGridSync`, ~5 barier na warstwę, RMSNorm redundantnie w każdym bloku (`22-lucebox.md:41-47`).
- **llama.cpp/ggml**:
  - PR o trwałym kernelu ani megakernelu: brak (szukane w GitHub: „megakernel”, „persistent kernel”);
  - PDL #22522 scalone;
  - #30004: regresja ADD/GELU na B200 od commita PDL;
  - #28863 (gfx1100, tensor split) stwierdza brak megakernela na AMD.

## 3. Nasz budżet tokenu (ponowny rachunek)

### 3.1 LFM2.5-24B-A2B Q5_K_M na RX 7900 XTX
Bajty aktywne z nagłówka GGUF (`15a-gguf-active-bytes.py`): eksperci 4/64 1016.3 MB, shortconv 346.5, głowica (tied `token_embd` Q6_K) 215.0, gęste FFN 105.9, atencja 72.7, router F32 19.8. **Razem 1.777 GB/token.** Podłoga: 1.85 ms przy 960 GB/s, 1.95 ms przy 900 GB/s (realny streaming, `lfm-decode-round4.md` §1b: 789–925 GB/s).

Taśma PM4, tryb szybki (`~/wt/lfm4-prof/c2_tr_1.txt`; na dispatch: koniec poprzedniego → koniec tego, z granicą). Liczy `15a-lfm-budget.py`:

| składnik | µs/token | uwagi |
|---|---|---|
| wall (spec_sweep) | 3404 | 293.7 t/s |
| host (sync 16.7 + submit→done 24 + reszta) | ~220 | megakernel tego nie rusza |
| taśma GPU | 3184 | 305 dispatchy |
| └ matvec (181 dispatchy, 1.758 GB) | 2650 | 663 GB/s z granicami |
| &nbsp;&nbsp;└ czysty strumień przy 900 GB/s | 1953 | |
| &nbsp;&nbsp;└ narzut ponad strumień | **698** | gate+up 38×6.3, in_proj+conv 29×4.8, down 37×3.5, out_proj/attn-q 39×2.2, małe attn 20×2.4 µs |
| └ nie-matvec (124 dispatchy) | **534** | norm_router_topk 198, rms_norm 126, FA 83, attn_prep 63, combine_fwht 34, reszta 30 |
| **pula „DRAM prawie bezczynny”** | **1231 (36% wall)** | to atakuje megakernel |
| └ z tego granice PM4 | 140–260 | 305 × 0.46–0.86 µs |

Efektywne pasmo: 1.777 GB / 3.404 ms = 522 GB/s = **54% z 960** (upstream na 3090 46%, §3.3). Literatura: kernel-per-op przy batch 1 na małych modelach daje ≤50% (Hazy), megakernele 71–80% (Hazy 78%, MPK 80%, Lucebox ~71%).

Scenariusze (`15a-lfm-budget.py`, `[SZACUNEK]`):

| scenariusz | oszczędność | ms/token | t/s | Δ |
|---|---|---|---|---|
| S0: stary szacunek (2×38 granic MoE × 0.6 µs) | 46 µs | 3.358 | 298 | +1% |
| S1: PM4-PDL, granica 0.6 → 0.25 µs, rampa matvec ukryta ≤1 µs | 287 µs | 3.117 | 321 | +9% |
| S1': jw., rampa ukryta ≤2 µs | 449 µs | 2.955 | 338 | +15% |
| S2: megakernel dataflow, odzysk 30% puli | 369 µs | 3.035 | 330 | +12% |
| S2: odzysk 45% puli | 554 µs | 2.850 | 351 | +19% |
| S2: odzysk 60% puli | 739 µs | 2.665 | 375 | +28% |
| fizyczna podłoga ≈ strumień 1953 + bąbel router→ekspert 38×6.5 + 240 hand-offów × 0.6 + host 220 | — | 2.564 | 390 | +33% |

Kontrola spójności: 72% pasma (Lucebox) dałoby 2.57 ms taśmy + 0.22 host = 2.79 ms (+22%), a 78% (Hazy) 2.59 ms (+31%). Mieści się w S2.

### 3.2 Qwen3.8-27B UD-Q4_K_XL na XTX
- Aktywne 16.83 GB/token (17.55 GB pliku − 0.715 GB `token_embd`, który idzie przez get_rows).
- Plain tg128 43.2 t/s = 23.15 ms, czyli 727 GB/s = **76%**. Pula ≤ 23.15 − 16.83/0.9 = 4.45 ms (19%), z tego granice PM4 ~0.5 ms (807–919 dispatchy).
- MTP: 27.74 ms/krok, weryfikacja 5 kolumn (bliżej obliczeń) + łańcuch GDN.
- `[SZACUNEK]` megakernel +3–6%, PM4-PDL +1–3%. Nie warto jako pierwsze.

### 3.3 RTX 3090 (`09-chmura-3090.md` §5–6)
- LFM tg128 (profil Ampere) 284.5 t/s = 3.515 ms; podłoga 1.898 ms przy 936 GB/s, czyli **54%** (upstream A0 241.2 t/s = 46%). 357 kerneli/token.
- Granica grafu CUDA na sm_86 niezmierzona; z literatury 0.8 (B200) – 1.3 µs (H100), więc 0.29–0.46 ms (8–13%) `[NIEZWERYFIKOWANE]`. nsys (1.85 ms przerw) jest zawyżony przez profiler.
- sm_86/89 nie mają PDL (#22522: „CC >= 90; does not include Ada”). Jedyne narzędzia to fuzje albo trwały kernel.
- Qwen tg128 43.0 = 23.26 ms vs podłoga 17.98 ms → 77%.

### 3.4 RTX 5060 Ti (sm_120)
- LFM Q4_K_M 207.86 t/s (serwer) = 4.81 ms; bajty Q4_K_M ~1.5 GB `[SZACUNEK]`, więc podłoga ~3.35 ms przy 448 GB/s → ~70%.
- PDL już działa (nasze łatki 0053/0057 mają `ggml_cuda_pdl_sync`). Pula mniejsza; megakernel `[SZACUNEK]` +5–10%.

## 4. Odpowiedzi na pytania i analiza transferu

### 4.1 Czy trwały kernel warstwy pobije PM4 na XTX?
- **Z barierami między fazami: nie.** Zmierzona bariera trwałego gridu to 0.48–0.58 µs (16–96 bloków) i 0.72–0.77 µs (192), a granica PM4 0.46–0.86 µs (`lfm-decode-round2.md:30-31`, `lfm-decode-round4.md:24-44`). Fazy z tysiącami czekających to 8–11 µs/fazę. Wniosek rundy 4 („~1.4%”) jest dla tej klasy projektów słuszny.
- **Jako dataflow (MonoKernel/Hazy): tak, `[SZACUNEK]` +12…+28%.** Zysk nie pochodzi z granicy, tylko z trzech rzeczy:
  - (a) wagi następnej operacji ładowane przed czekaniem: rampa, pierwszy bajt i ogon nachodzą na siebie;
  - (b) małe operacje (norma, router/top-k, FA przy krótkim kontekście, attn_prep, combine) biegną na wolnych CTA, a reszta strumieniuje wagi;
  - (c) redundantne liczenie zamiast hand-offów.
- Wymaga to przepisania matvec Q5_K/Q6_K/Q8_0 na pętle zadań w siatce ≤ CU, z naszą kolejnością redukcji, jeśli ma być bitowo.
- **Co nieusuwalne dla LFM:** wagi ekspertów zależą od top-k (38 × ~5–6.5 µs ≈ 0.2–0.25 ms/token). LFM nie ma shared expert do prefetchu.
- **Krok pośredni, który bierze dużą część (a) bez przepisywania kerneli: „PM4-PDL”.**
  - Taśma PM4 pozwala pominąć pakiety granicy (`CS_PARTIAL_FLUSH` + `ACQUIRE_MEM`) między dwoma dispatchami: zmierzone 0.24–0.35 µs, wynik błędny bez flag (`lfm-decode-round4.md:44`).
  - Konsument (MMVQ n=1) najpierw ładuje swój wycinek wag do VGPR, potem czeka na flagę `gen`. Flagę ustawia z release ostatni blok producenta: tickety „ostatni blok” już mamy w 0051/0053/0054/0056/0057.
  - To dokładnie P1 z `repos/13-cutile-python.md:40-53`. Wtedy był zablokowany, bo `hipExtAnyOrderLaunch` jest ignorowany w grafach. **PM4 usuwa tę blokadę.**
  - Kluczowe założenie do mikrobenchmarku: dispatcher wydaje grupy robocze kolejnych dispatchy jednej kolejki po kolei, więc konsument nie zablokuje slotów producenta. Bez tego jest zakleszczenie `[NIEZWERYFIKOWANE]`.

### 4.2 Czy pobije grafy CUDA + PDL?
- **Ampere/Ada:** brak PDL, granica ~1 µs+ `[NIEZWERYFIKOWANE]`, LFM na 54% pasma. Trwały kernel jest jedyną drogą do (a) i (b). Potencjał jak na XTX albo większy, ale to osobna implementacja CUDA: cooperative launch albo dynamiczna kolejka zadań (bez wymogu co-residency, §4.4).
- **Blackwell:** PDL daje (a) dla par sąsiadów (+5–13% upstream). Megakernel dokłada (b), (c) i drobne zależności (Hazy: PDL „very coarse”). Przy 448 GB/s karta jest bliżej pasma, więc `[SZACUNEK]` +5–10%.

### 4.3 Który model
LFM2.5: stały narzut 2.2–6.3 µs na wywołanie przy strumieniu 0.8–19 µs i pula 36%. Qwen ma pulę 19% i dominującą weryfikację MTP. Kandydat do sprawdzenia: LFM2.5-2.6B (gęsty, Q4_0 1.59 GB, w `~/models/lfm/`), z jeszcze mniejszymi macierzami `[NIEZWERYFIKOWANE]`.

### 4.4 Co musi się zmienić w ggml/forku, ryzyka, platformy

| pomysł | zmiany | osobodni | bitowo? | ryzyka | platformy |
|---|---|---|---|---|---|
| A. PM4-PDL (pary matvec) | `hip-pm4.cu`: tryb „overlap” dla oznaczonych par (bez boundary packets) + słowo `gen` w taśmie; prolog MMVQ n=1: wagi → VGPR → spin `s_sleep 1` z limitem + słowo błędu; producent: release flagi w istniejącym tickecie | 6–9 | **tak** (te same obliczenia) | zakleszczenie, jeśli wydawanie WG nie jest w kolejności; presja VGPR (prefetch 22 dword/lane przy K=2048, `13-cutile-python.md:44`); tryb „slow-mode 3072 bloków” | tylko HIP z PM4 (RDNA3; Windows/PAL nie) |
| B. Prefetch do MALL w trakcie małych kerneli | dispatch „touch” (bez granicy) wag in_proj/out_proj następnej warstwy (~11.5 MB) równolegle z norm_router/FA/attn_prep; obecne ładowania GLC\|DLC wag mogą omijać MALL, do sprawdzenia | 2–4 | **tak** | rywalizacja o pasmo z bieżącym kernelem; polityka alokacji MALL dla compute `[NIEZWERYFIKOWANE]` | HIP/RDNA3 (MALL 96 MB); na NVIDIA tylko Ada 72 MB L2 / 5060 Ti 32 MB, 3090 ma 6 MB |
| C. Trwały blok MoE LFM (dataflow) | nowy kernel: norm+router+top-k → gate+up → down+reduce, siatka 96×512, dynamiczna kolejka zadań (atomowy indeks zadania, jak DSv4.1 i nasz `chain_cost.hip`), tagged pairs | 10–12 (HIP) + 8 (CUDA) | możliwe (kolejność redukcji jak w MMVQ/0051) | spin/głód (pre_poll), VGPR, kod jednej fali z zimnego I$ (już raz zaszkodził: 13 → 56 µs, NOTES runda 3) | HIP, CUDA; Vulkan/Metal nie (brak gwarancji postępu WG) |
| D. Pełny megakernel warstwy LFM | wszystkie etapy (shortconv, GQA FA q8_0, set_rows, MoE) jako zadania; LDS/VGPR arena; harmonogram per szerokość | 25–35 na backend | trudne, ale możliwe | jak C plus koszt utrzymania przy zmianach grafu llama.cpp; co-residency na GPU z wyświetlaczem (gfx1250: 200× wolniej przy współlokatorze, raz zawieszenie wymagające restartu) | HIP, CUDA |
| E. Proces z RFC | bounded poll + słowo błędu we wszystkich naszych spinach/ticketach, epoki zamiast czyszczenia, stres 10⁵ replayów bit w bit, scratch per szerokość grafu | 1–2 | n/d | — | wszystkie |

Bezpieczny projekt na konsumenckie GPU `[WNIOSEK]`: zamiast „zadanie t na CTA (base+t)%G” (wymaga co-residency, a vLLM odmawia przy <256 CU) warto użyć **dynamicznego indeksu zadania z atomika w porządku topologicznym**. CTA czeka tylko na zadania pobrane wcześniej przez już działające CTA, więc nie ma zakleszczenia, nawet gdy kompozytor zajmuje część CU. Kosztem jest jeden atomik na zadanie (u nas ~0.5 µs przy małej siatce).

Spójność na RDNA3 `[NIEZWERYFIKOWANE]`: L0 i GL1 nie są koherentne, więc polling musi iść z `glc dlc` (do L2), a release producenta wymaga `s_waitcnt vscnt(0)` + `buffer_gl*_inv` po stronie konsumenta. Jak w modelu pamięci AMDGPU dla gfx10/11. Atomowość 8-bajtowego store’a (tagged pair) na gfx11 trzeba sprawdzić.

### 4.5 Ranking

| # | pomysł | oczekiwany zysk (LFM XTX) | pewność | koszt | (zysk×pewność)/koszt |
|---|---|---|---|---|---|
| 1 | A. PM4-PDL (po mikrobenchu X1) | +5…+15% (środek 9%) | 0.4 | 7.5 pd | **0.48** |
| 2 | B. Prefetch MALL | 0…+6% (3%) | 0.25 | 3 pd | 0.25 |
| 3 | E. Proces bezpieczeństwa | 0 t/s, mniejsze ryzyko zawieszeń | — | 1.5 pd | (zalecane niezależnie) |
| 4 | D. Pełny megakernel LFM | +12…+28% (20%) | 0.2 | 30 pd | 0.13 |
| 5 | C. Trwały blok MoE (ponad A) | +2…+5% (3.5%) | 0.3 | 11 pd | 0.10 |
| 6 | Qwen: A/D | +1…+6% | 0.3 | 7.5–30 pd | ≤0.08 |

## 5. arXiv 2605.07182 — inny temat (krótko)
**„Star Elastic: Many-in-One Reasoning LLMs with Efficient Budget Control”** (Taghibakhshi i in., NVIDIA, 2026-05-08):
- jeden post-training dodaje do rodzica zagnieżdżone podmodele: osie SSM, kanały embeddingu, MoE, FFN; router trenowany end-to-end, curriculum KD;
- Nemotron Nano v3 30B/3.6A daje 23B/2.8A i 12B/2.0A przy 160B tokenów;
- „elastic budget control”: mniejszy podmodel dla fazy thinking, większy dla odpowiedzi; do 16% wyższa dokładność albo 1.9× niższa latencja (vLLM, BF16, batch 16–40);
- throughput H100: 12B 2.4× vs 30B przy maks. batchu 224 vs 36;
- RTX Pro 6000: 12B NVFP4 7426 tok/s vs 30B BF16 2178 tok/s (agregat, ISL 8192 / OSL 16384).

Dla nas:
- nie ma kerneli. Zagnieżdżony podmodel *tego samego* modelu mógłby być drafterem self-spec ze wspólnym KV, ale Nemotron Elastic nie jest naszym modelem;
- trening to temat `10-post-training.md`;
- liczby to throughput przy dużym batchu, nie batch 1;
- niska istotność.

## 6. Eksperymenty (falsyfikowalne)

**X1 — mikrobench PM4-PDL** (XTX; $0; wymaga zgody na lokalne GPU)
- Hipoteza: para zależnych matvec (2048×2048 Q5_K, 1024 bloki → to samo) w taśmie PM4 bez pakietów granicy, gdzie B ładuje wagi do VGPR i czeka na flagę `gen` z ticketu A, skraca (koniec A → koniec B) o ≥1.0 µs wobec taśmy z granicą (dziś 5.44 µs/wywołanie). Przy 10⁵ replayach: 0 złych wyników i 0 wygaśnięć bounded spin.
- Prototyp: rozszerzyć `~/wt/lfm4-prof/pm4.cpp` i `chain_cost.hip`. Warianty siatek 1024/1536/2560/3072/6144 (B > pojemność GPU = test zakleszczenia).
- Pomiar: (T(1000) − T(200))/800, mediana z 25, sprawdzenie łańcucha.
- **Kill:** oszczędność <0.5 µs/parę albo jakiekolwiek wygaśnięcie lub zawieszenie.

**X2 — PM4-PDL w taśmie LFM** (XTX; $0; zgoda)
- Hipoteza: taśma 3184 → ≤3100 µs (−3%) przy włączeniu dla out_proj, in_proj+conv, down i attn q/k/v/o.
- Pomiar: `ab.sh` llama-bench tg128 -r 5, 3 rundy ABBA; `GGML_HIP_PM4_DEBUG=3` + `trace.py` per klasa; hash logitów `a7ce25b73f887fed` (d0) i `b47452b9380b665b` (d3000) bez zmian; greedy md5 `894e56e4…`; soak `pm4_soak.py` 4 min.
- **Kill:** <2% taśmy albo jakakolwiek zmiana hashu.

**X3 — prefetch MALL** (XTX; $0; zgoda)
- Hipoteza: dispatch „touch” bez granicy, wpięty przed `norm_router_topk`, ściąga ~11.5 MB wag następnej warstwy do MALL, a następne in_proj+conv i out_proj skracają się łącznie o ≥2 µs/warstwę.
- Pomiar: jak X2, plus czasy norm_router w trace.
- **Kill:** <1% taśmy albo spowolnienie małych kerneli większe niż zysk.

**X4 — budżet CPU** (zrobione, $0): §3.1, `15a-lfm-budget.py`. Rozszerzenie: ścieżka krytyczna warstwy (6 etapów × latencja + hand-off) wobec strumienia, z czasami etapów z trace. Rozstrzyga, czy S2 ogranicza latencja, czy pasmo.

**X5 — granica grafu CUDA na Ampere** (Vast RTX 3090, ~$0.20/h × 1.5 h ≈ $0.30–0.45 + transfer; **wymaga zgody**)
- Port `boundary.cpp` na CUDA: łańcuch N kerneli (pusty / copy2k / matvec Q5_K 2048²) w grafie; trwały łańcuch cooperative z flagami per kafel. Dodatkowo LFM `nsys` bez `--cuda-graph-trace=node` i llama-bench.
- **Kill dla megakernela na NVIDIA:** granica ≤0.8 µs i pula (wall − strumień) <20%.

**X6 — wartość „early start” na NVIDIA** (Vast/RunPod 5060 Ti, ~$0.3; zgoda): `GGML_CUDA_PDL=0` vs `1` (przełącznik istnieje, #30004) na LFM i Qwen, llama-bench tg128 ABBA. To górna miara tego, co da X2 po stronie AMD (przy innym koszcie granicy).

## 7. Dowody zewnętrzne

| teza | co potwierdza | co obala lub osłabia | stan |
|---|---|---|---|
| GLM 13.70 → 5.92 ms | spójne z FlyDSL #1204 (2.6× na warstwę vs ATOM) i TileRT #1 na AgentX | ATOM #2435: −22% TPOT względem lepszej bazy, więc 2.3× wynika w dużej części ze słabej bazy vLLM | brak niezależnej reprodukcji i surowych logów; harness usunięty z PR |
| DSv4.1 mono | scalone (#60397); porównanie z biegiem InferenceX 37510490434 | — | upstream |
| megakernel na konsumenckich kartach | Lucebox 3090 1.55× (0.8B BF16), MPK A100 +16% (8B) | TensorFold M5: bariera siatki przegrywa; nasz pomiar faz z czekającymi 8–11 µs | brak megakernela na RDNA3 w publicznym kodzie (#28863) |
| PDL na NVIDIA | llama.cpp #22522: +5–13% tg, scalone | #30004: regresja ADD/GELU na B200 od commita PDL | upstream |
| sprzętowy prefetch przed kernelem na AMD | `hipLaunchAttributeExtDynDataPrefetch` w HIP 7.15 | ROCr: 0 regionów poniżej gfx12.5 (`amd_gpu_agent.cpp:2734-2740`) | **nie dla gfx1100** |

Nie znalazłem żadnego benchmarku maintainerów vLLM dla MonoKernel ani wpisów LocalMaxxing z megakernelem na consumer GPU.

## 8. Źródła
- RFC: https://github.com/vllm-project/vllm/issues/60904 (body, 8 komentarzy: maeehart, benchislett, Fangzhou-Ai, jiacao-amd, tlrmchlsmth ×2, simondanielsson)
- GLM-5.2 MonoKernel: https://github.com/vllm-project/vllm/pull/60889, head `0ab9c66567`:
  - `vllm/models/deepseek_v32/amd/mono/kernel/glm/kernel.py:18-60` (projekt), `:360-364` (epoka), `:435-445` (put), `:460-543` (poll, bounded), `:545-551` (pre_poll), `:2076-2171` (MoE S=1), `:2447` (launch);
  - `kernel/layout.py` (BLOCKS/THREADS/POLL_MAX), `kernel/glm/layout.py` (POLL_STAGES, stage_tasks), `kernel/config.py` (geometria GLM-5);
  - harness: `tools/mono_check/perf_ab.py` w commicie `85f7d86209`.
- DSv4.1: https://github.com/vllm-project/vllm/pull/60397 (scalone 2026-10-10, `f6b54daade`): `mono_decode.py:148-151`, `mono/common/sync.py`, `mono/layer.py:47, 392`
- gfx942: https://github.com/vllm-project/vllm/pull/60731; DSv4-Pro: https://github.com/vllm-project/vllm/pull/61482; abstrakcje: https://github.com/vllm-project/vllm/pull/61311; MiniMax-M3: https://github.com/vllm-project/vllm/pull/59705; Kimi-K3: https://github.com/vllm-project/vllm/pull/60683, /61435, /60793, /61498
- FlyDSL: https://github.com/ROCm/FlyDSL/pull/1204 (GLM-5/Kimi, wyniki), https://github.com/ROCm/FlyDSL/pull/1214 (gfx1250, ryzyka). ATOM: https://github.com/ROCm/ATOM/pull/2435
- TileRT: https://github.com/tile-ai/TileRT (README, v0.1.6, binarne backendy). InferenceX `8ac98344`: `benchmarks/multi_node/amd_utils/server_tilert.sh`
- GLM-5.2 config: https://huggingface.co/zai-org/GLM-5.2/resolve/main/config.json, https://huggingface.co/amd/GLM-5.2-MXFP4/resolve/main/config.json
- Hazy: https://hazyresearch.stanford.edu/blog/2025-05-27-no-bubbles; https://github.com/HazyResearch/Megakernels (`demos/low-latency-llama/matvec_adds.cu:129-132,174`, `include/config.cuh:42-48`)
- MPK: https://arxiv.org/abs/2512.22219 (v2; §5.2, §6.1, §6.4, §6.6), https://github.com/mirage-project/mirage
- HipKittens: https://arxiv.org/abs/2511.08083
- Star Elastic: https://arxiv.org/abs/2605.07182
- llama.cpp: https://github.com/ggml-org/llama.cpp/pull/22522, /issues/30004, /issues/28863
- ROCm: `/opt/rocm/include/hip/hip_runtime_api.h:1660-1745` (DynDataPrefetch, Cooperative), `:2109-2116` (Programmatic enum); https://github.com/ROCm/rocm-systems/blob/develop/projects/rocr-runtime/runtime/hsa-runtime/core/runtime/amd_gpu_agent.cpp (L2734-2740), `projects/clr/rocclr/device/rocm/rocdevice.cpp:1160-1170`
- Nasze:
  - `qwen-opt/NOTES.md:379`;
  - `qwen-opt/research/lfm-decode-round2.md:24-41`, `lfm-decode-round4.md:12-51, 96, 165-170`;
  - `~/wt/lfm4-prof/c2_tr_1.txt`;
  - `qwen-opt/research/repos/07-flashinfer.md:61,68`, `13-cutile-python.md:40-53`, `16-mkernel.md:53`, `18-tensara.md:96`, `22-lucebox.md:41-47,110-121`;
  - `product/research/09-chmura-3090.md` §3–6.

## Do bazy wiedzy

| folder | tytuł (plik) | streszczenie 1 linia | kluczowe liczby (źródło) |
|---|---|---|---|
| research | Raport 15a: megakernele dla decode (`raport-15a-monokernel.md`) | Trwały kernel dataflow może dać LFM +12–28%, ale bariery między fazami nie dają nic ponad PM4; najpierw PM4-PDL | pula 1.23 ms = 36% z 3.40 ms; 54% pasma; S1 +9–15%, S2 +12–28% (15a §3.1) |
| repo | vLLM MonoKernel (`vllm-monokernel.md`) | RFC #60904: jedna trwała siatka 256×512 na warstwę, tagged pairs, prefetch wag przed czekaniem, bounded waits; tylko ROCm | GLM-5.2 13.70 → 5.92 ms, 2459 → 210 launchy (RFC); ATOM −22% TPOT (#2435); baza 8%, mono 19% pasma HBM (15a §1) |
| repo | Hazy Megakernels / MPK (`megakernele-prior-art.md`) | Interpreter instrukcji z SMEM stronicowanym (Hazy) i kompilator tGraph (MPK); 71–80% pasma przy batch 1 | Hazy H100 78%, B200 250/600 µs na hand-offy; MPK A100 14.5 → 12.5 ms; B200 0.8 µs/launch w grafie (15a §2.6) |
| eksperymenty | Budżet tokenu LFM pod megakernel (`2026-10-16-budzet-lfm-megakernel.md`) | Bajty z GGUF + taśma PM4: strumień 1.95 ms, narzut matvec 0.70 ms, małe kernele 0.53 ms, host 0.22 ms | 1.777 GB/token (GGUF); 663 GB/s matvec z granicami; `15a-lfm-budget.py` |
| lekcje | Trwały kernel: zysk to prefetch, nie granica (`lekcja-megakernel-prefetch-nie-granica.md`) | Szacunek 1.4% liczył tylko granice; megakernele wygrywają nakładaniem rampy wag i małych operacji, a bariera siatki = granica PM4 | bariera 0.48–0.77 µs vs PM4 0.46–0.86 µs (round2/round4); status do-sprawdzenia do X1/X2 |
| rocm | HIP DynDataPrefetch (`hip-dyn-data-prefetch.md`) | `hipLaunchAttributeExtDynDataPrefetch` (prefetch L2 przed kernelem) w HIP 7.15, ale ROCr daje 0 regionów poniżej gfx12.5 | `amd_gpu_agent.cpp:2734-2740`; `hip_runtime_api.h:1660-1712` |
| kernele | aktualizacja `pm4-replay.md` | Dopisać pomysł PM4-PDL (pominięcie boundary packets + flaga `gen` + prefetch wag) jako następny krok | overlap bez granicy 0.24–0.35 µs (round4 §1a); szac. +5–15% LFM |
| kernele | aktualizacja `fuzje-lfm-moe.md` | Trwały blok MoE ponownie oceniony: +2–5% ponad PM4-PDL; bąbel router→ekspert ~0.2–0.25 ms/token nieusuwalny | 38 × 5–6.5 µs (15a §4.1) |
| nvidia | aktualizacja `sm-86-89-120.md` | Ampere/Ada bez PDL: granica grafu CUDA niezmierzona (lit. 0.8–1.3 µs), LFM 3090 też na 54% pasma, więc megakernel ma tam więcej do wzięcia niż na XTX z PM4 | 284.5 t/s vs podłoga 1.898 ms (09-chmura-3090 §5); X5 ≈ $0.30–0.45 |
| research | Star Elastic (`star-elastic-2605-07182.md`) | NVIDIA, zagnieżdżone podmodele Nemotron Nano v3 i podmodel per faza rozumowania; nie o kernelach, niska istotność | 30B → 23B/12B, 160B tokenów, 1.9× niższa latencja, 12B NVFP4 7426 tok/s (arXiv 2605.07182) |
