# 68a — RDNA3/gfx1100: kernele HIP, ROCm i zegary z ostatnich ~6 tygodni (2026-09-26 … 11-07)

Data: 2026-11-07. Praca tylko na CPU: bez GPU, bez buildów, bez pobierania wag. Jedyny pomiar na karcie to odczyt `sysfs` (zegary DPM), tylko do odczytu. Klony kodu: `~/src/research63/llama.cpp` @ `10d4846` (2026-11-05, upstream), `~/src/research68/hipfire-CHANGELOG-efa8fbb.md` (sam CHANGELOG; klon hipfire miał 633 MB, więc usunięty zgodnie z limitem 200 MB), `~/src/research68/llama-cpp-rdna-boosts` @ `3cb0e6e` (klon peera, tylko czytany).

Punkt odniesienia (produkcja, eco 2200 MHz): czat agenta 120.8 t/s ważone; spec_sweep T=1 118.3 t/s, 26.9 ms/krok; prefill 800–930 t/s przy 4–12k, **465 t/s przy 255k (548 s)**; decode przy 255k 78.7 t/s ([[2026-11-06-ctx-262k-fit]]). W trakcie testów (nie proponuję ponownie): skale Q6_K w MMQ, `kvq` z jednym odczytem KV + strojenie podziałów, cache tokenizacji, parser O(n).

Oznaczenia: **NOWE** = brak w wiki/raportach (grep `wiki/`, `product/research/`); **znane (X)** = jest w notatce/raporcie X; `[INFERENCE]` = mój wniosek lub rachunek, nie pomiar; „producent/autor” = liczba podana przez źródło, niezweryfikowana u nas.

## 1. TL;DR

1. **Dekod (GEMV) nie ma nowej dźwigni na RDNA3.** Najlepszy publiczny kernel weryfikacji dla Qwen3.8-27B na XTX (hipfire, int8×int4 `v_dot4`, B=4) osiąga **69–87% z 960 GB/s** (autor, [hipfire #946](https://github.com/warpfront/hipfire/issues/946)). Nasze MMVQ ma 81–88% ([[sufit-pasma-i-mapa-czasu]]), więc jesteśmy na tym samym poziomie albo wyżej. Sufit GEMV to kilka procent, nie kilkanaście.
2. **Największy NOWY, testowalny zysk leży w prefillu długiego kontekstu, a nie w dekodzie.** Z profilu 24v i modelu liniowego wynika, że FA D=256 to ~53% czasu prefillu 255k, a konwersja KV→f16 ~3% `[INFERENCE]`. Upstream PR [#31746](https://github.com/ggml-org/llama.cpp/pull/31746) (2026-11-05, W7800 = gfx1100) daje dla GQA6 (kształt Qwena) **0.70–0.78× czasu operatora** FA. Nasza wersja ma już część tej zmiany (łatka 0042), ale `nbatch_fa=32` z K2/V2 128 i barierami nigdy nie była mierzona (24f tylko ISA, 24v nie przyjęte). Szacunek: FA −10…−25% → prefill 255k **+5…13%** (548 s → ~485–520 s), przy ≤8k zero.
3. **Drugi NOWY kandydat na prefill: fuzja gate/up + GLU w MMQ ([#29948](https://github.com/ggml-org/llama.cpp/pull/29948), scalone 2026-10-25), dziś bramkowana tylko na NVIDIA** (`ggml-cuda.cu:2224-2225` w `10d4846`: „NVIDIA only: the fused write-back relies on the MMA accumulator layout”). Port na układ akumulatorów WMMA: pp ≤32k **+2…4%** `[INFERENCE]`, prawdopodobnie bitowo. Ryzyko: na RDNA3 wariant MoE w RDNA-FAST stracił 3–16% (63c §2.1).
4. **NOWA obserwacja z naszej karty (sysfs, 2026-11-07, eco 2200): pod obciążeniem FCLK stoi na 2000 MHz (poziom 4 z 0–7), a nie na 2201–2301; MCLK na maksimum 1249.** Nie wiemy, czy to skutek capu sclk, ani czy FCLK ogranicza pasmo. Tani test tylko do odczytu (stock vs eco) rozstrzygnie, czy warto próbować go podnieść.
5. **Kalibracja dla trwającego testu KV-once (XtxKvOnce), bez nowej propozycji.** Weryfikacyjna atencja WMMA w hipfire (4 wiersze × 6 głów, KV q8, jeden przebieg) robi **525–703 GB/s efektywnie** przy 9K–100K, czyli 37/131/310 µs na warstwę ([hipfire CHANGELOG v0.4.4](https://github.com/warpfront/hipfire); `hipfire-CHANGELOG-efa8fbb.md:251`). Dla naszego q4_0 (1152 B/token/warstwę) daje to cel **≤165–220 µs/warstwę przy 100K** `[INFERENCE]`.

## 2. Ustalenia per źródło

### 2.1 llama.cpp: PR-y i issues HIP/RDNA (117 PR od 2026-09-25, przejrzane tytuły i treść istotnych)

Zapytanie: GitHub search `repo:ggml-org/llama.cpp is:pr created:>2026-09-25 (HIP OR ROCm OR RDNA3 OR gfx1100 OR gfx11 OR RDNA)` (117 wyników, odczyt 2026-11-07) + `git log e60eff95f..10d4846 -- ggml/src/ggml-cuda` (623 commity od bazy topki).

| PR / issue | co robi, liczby (autor) | dla nas |
|---|---|---|
| [#31746](https://github.com/ggml-org/llama.cpp/pull/31746) „hip: tune D256 MMA FlashAttention on RDNA3” (draft, 2026-11-05) | Kafle 64 kolumn z `ncols2` 2/4: Q strumieniowane ze smem, `nbatch_fa` 64→32, bariery WMMA, `nbatch_K2/V2`=128, config kluczowany po `ncols2`. W7800 (gfx1100), F16 KV, 2240 tokenów zapytania, KV 4k/32k/131k: czas operatora GQA6 **0.783× (ROCm 7.2.4) / 0.695× (ROCm 10.1)**. Spille `<32,2>`: 558 VGPR → 0. GQA8 bitowo jak master | **częściowo znane**: Q w SRAM = nasza 0042 (`cf397468e`), bariery = 24v (+3.5% kernela, nieprzyjęte), `nbatch_fa=32` = 24f (tylko ISA: scratch 512→192 B, bez pomiaru). **NOWE**: zmierzony pakiet na naszej architekturze i kształcie (pkt 4.1) |
| [#31761](https://github.com/ggml-org/llama.cpp/pull/31761) (draft, 11-05) | Kafel tile D256 2-kolumnowy: `nbatch_K` 64→128, occupancy 8→6; dekod 1 tokenu przy 131k **+13.5%** (Q8_0 27B, F16 KV) | nie dotyczy: dekod/weryfikację robi u nas `kvq`, nie tile |
| [#31751](https://github.com/ggml-org/llama.cpp/pull/31751) (draft, 11-05) | `#pragma unroll 1` w pętli K MMQ dla `J=32` (typy z układem Q8_0): PP17–32 **+36%**, 104 VGPR i 0 spilli zamiast 256/108 B | znikome: nasze Q4_K J=32 nie ma scratchu (`~/opt/isa101/v100/mmq-instance-q4_k.s`: scratch tylko w wariantach `J` 8/24/40/…, nie 32). Dotyczyłoby tylko głowicy MTP IQ4_XS przy turach 17–32 tokenów |
| [#29948](https://github.com/ggml-org/llama.cpp/pull/29948) (scalone 2026-10-25, `c49edf0`) | Fuzja FFN gate/up + GLU w MMQ (przeplecione wiersze po 8, GLU w write-back), CUDA pp Qwen 27B +4.6…7.4% (63c) | **NOWE dla topki** (63c widział go tylko jako zysk Enigmy/CUDA). Bramka NVIDIA-only (`ggml-cuda.cu:2224-2225`), pkt 4.2 |
| [#31234](https://github.com/ggml-org/llama.cpp/pull/31234), [#30792](https://github.com/ggml-org/llama.cpp/pull/30792), [#30803](https://github.com/ggml-org/llama.cpp/pull/30803) | Natywne KV q4_0/q8_0 w kernelu tile/vec, GQA w jednym przejściu: R9700 tg@131k q4_0 **1.24–1.41×** | **znane** (`kvq`, [[fattn-kvq]]) |
| [#30190](https://github.com/ggml-org/llama.cpp/pull/30190) (Vulkan, open) | Tokeny weryfikacji × głowy GQA w jednym kaflu FA (KV raz): gfx1100 W7800, Qwen3.8-27B MTP 4 @32k: krok **74.55 → 70.29 ms (−5.7%)**; FA 0.19–0.65× | **znane** (plan #8, w teście). Kalibracja dla XtxKvOnce |
| [#31669](https://github.com/ggml-org/llama.cpp/pull/31669) GDN replay zamiast rollbacku (WIP) | Pamięć stanu −73…91%; 1 sekwencja ≈ 0% | **znane** ([[gdn-replay]]) |
| [#30139](https://github.com/ggml-org/llama.cpp/pull/30139) stany rekurencyjne czytane w miejscu | 27B: −209 µs/token (5090) | **znane**: topka nie kopiuje stanu GDN („lagged delta-net state has a single cell… no gather”, `src/llama-graph.cpp:3781`) |
| [#31031](https://github.com/ggml-org/llama.cpp/pull/31031) przycięty słownik draftu | 32k wierszy głowicy | **znane** (słownik 64k) |
| [#29720](https://github.com/ggml-org/llama.cpp/pull/29720) rms_norm float4 (scalone 10-16) | CDNA +7–13%, „RDNA more neutral” | znane klasy ([[rmsnorm-dpp]]); bez zysku na RDNA |
| [#29478](https://github.com/ggml-org/llama.cpp/pull/29478) `__vsubss4`→`__vsub4` (scalone 09-26) | MI50 Q6_K tg +12% | **już w topce** (`748d4225b`; `mmq-load-tiles.cuh:990`) |
| [#31625](https://github.com/ggml-org/llama.cpp/pull/31625) fast-math na HIP (open, 11-03) | `-funsafe-math-optimizations` bez reasocjacji i finite-math; brak liczb wydajności | **parkowane** (zmienia numerykę: `approx-func`, `reciprocal-math`) |
| [#31500](https://github.com/ggml-org/llama.cpp/pull/31500), [#31838](https://github.com/ggml-org/llama.cpp/pull/31838), [#31617](https://github.com/ggml-org/llama.cpp/pull/31617) | wbudowane warp-sync, workspace rocBLAS 32 MB (fix crasha `SOLVE_TRI`), ROCm ≥ 6.3 | porządki, bez wpływu na wydajność |
| issue [#30688](https://github.com/ggml-org/llama.cpp/issues/30688) (Vulkan, 10-16) | Przy prawie pełnym VRAM bufor compute celu przeniesiony po re-reserve do GTT → dekod **4×** wolniej, nic w logu | **NOWE jako ryzyko u nas**: przy 262k mamy 1193 MiB zapasu; HIP nie spada po cichu do GTT przy alokacji, ale TTM może ewikować BO `[INFERENCE]`. Tani odczyt `fdinfo` (pkt 4.5) |
| issue [#30638](https://github.com/ggml-org/llama.cpp/issues/30638) (RADV, 10-16) | draft-mtp −10–13% po zmianach upstream; niestabilna akceptacja przy `--cache-reuse` | Vulkan; dla nas tylko lekcja „ms/krok przy tej samej pracy, nie t/s” (mamy) |

### 2.2 hipfire (warpfront) — delta od v0.4.2 (ZRODLA: `1ff5182` v0.4.2)

- **[#947](https://github.com/warpfront/hipfire/issues/947) (2026-10-23)**: łatany build na XTX, Qwen3.8-27B mq4 (14.99 GB), MTP K=3, KV q8: **102 / 97 / 90 t/s przy 9K / 39K / 100K** (v0.4.2.1: 67/59/43). Okno 25.7 → 30.7 ms, czyli nachylenie **~0.05 ms na 1K tokenów** przy KV q8. Autor rozkłada przewagę na: GEMV int8 dla weryfikacji (~10 ms/okno), atencję weryfikacyjną WMMA split-K i skompresowany słownik draftu (+5–10%).
- **[#946](https://github.com/warpfront/hipfire/issues/946) (2026-10-23)**: GEMV `v_dot4_i32_iu8` dla 2–5 wierszy. Pasmo per kształt przy B=4 (autor): GDN qkv+z+β+α **80%**, q+k+v **79%**, gate+up **82%**, o_proj **69%**, down **79%**, lm_head **87%**. Technika: trwała siatka z occupancy, ciągłe zakresy (wiersz, krok K) na warp, pierścień 3× `dwordx4` nontemporal przez granice wierszy, split stały i redukowany w ustalonej kolejności. **Znane co do klasy**: mamy q8_1 + dp4a, multi-col MMVQ 81–88%, reuse q8_1, GLC/DLC ([[mmvq-multikolumnowe]], [[cache-q8-1]]).
- **CHANGELOG v0.4.4 (2026-10-27)**: obie zmiany domyślnie ON dla gfx1100. Atencja weryfikacyjna WMMA: K i Vᵀ dekwantyzowane do płaszczyzn f16 w LDS, 6 głów × wiersze na głowę KV, FA2 z leniwym przeskalowaniem, siatka 4 głowy KV × 24/36 zakresów kluczy. Kernel (4 wiersze, zimne KV): **37.3 / 130.6 / 309.5 µs przy 9K/40K/100K = 525–703 GB/s**. In-model: 101K 43.6 → 68.5 t/s; KLD w paśmie szumu. Maintainer: kod 32K 95.7 → 121.2 t/s (1.27×) (`hipfire-CHANGELOG-efa8fbb.md:246,251`). Skompresowany słownik draftu 65 536 (`:213`) = nasz 64k (**znane**).
- **Wniosek:** hipfire po łatkach jest na XTX blisko nas, ale ma KV q8 (2× więcej bajtów). Po normalizacji nachylenie kontekstu per bajt KV mają ~1.9× lepsze `[INFERENCE: nasz krok przy 255k ≈ 40 ms przy ~3.2 tok/krok, nie mierzone]`. To argument za trwającym KV-once, nie nowa propozycja.

### 2.3 exllamav3 / exllamav3-rdna (SelfRef), [#543](https://github.com/turboderp-org/exllamav3/issues/543) (2026-10-21…25)

- Te same pomysły co wyżej, w innej formie (EXL3, trellis): split-K GEMV z `v_sad_u8` i `v_dot2_f32_f16` (−4.5% rundy), wiązki projekcji ze wspólnym wejściem, atencja dekodu HIP (q_len 1 `v_dot2`, 2–8 WMMA na cache 8-bit; 32k −16%), fuzje aktywacji do transformacji wejścia, residual przeniesiony do następnej normy (bitowo, −0.4…−0.8%).
- turboderp: „graphs are fundamentally broken on ROCm… every graph patch is retained forever” — u nas PM4 zamiast grafów HIP (**znane**, [[pm4-replay]]).
- Dla nas nic nowego: wszystkie klasy mamy (residual w epilogu MMVQ, fuzje GDN, `kvq`).

### 2.4 Strata [#2231](https://github.com/Niko1221/Strata/pull/2231) (2026-10-13, zamknięty)

Bitowe przyspieszenia HIP gfx1100 dla Flash-Next (+11.7% chat / +14.3% agent): DPP w routerze, norma GDN 9.3 → 2.0 µs na warstwę, argmax wieloblokowy 12 → 6 µs, `hipStreamWriteValue32` zamiast host function (15 → 6.7 µs). **Znane** (wiki `repo/strata`). Topka nie używa `hipLaunchHostFunc` w ścieżce kroku (`ggml-cuda.cu:6062-6070` w `#if 0`), a argmax i normy mamy na DPP ([[argmax-dpp]], [[rmsnorm-dpp]]).

### 2.5 AMD: HRX / Lemonade, ROCm 10.1, blogi

- **HRX** ([RFC #27219](https://github.com/ggml-org/llama.cpp/discussions/27219), od 2026-08-17, odpowiedzi do 11-05; [Phoronix 2026-09-02](https://www.phoronix.com/news/Lemonade-11.9-ROCm-HRX); Lemonade [PR #3723](https://github.com/lemonade-sdk/lemonade/pull/3723) hrx-b99, 2026-10-02, „Qwen3.8-27B in there”). Nowy, lekki runtime AMD (libhrx ~2 MiB) z jawnymi command bufferami, niskim kosztem dispatchu („similar levels as… graphics pipelines”) i JIT-em Loom specjalizującym kernele pod kartę w 1–15 ms. Producent podaje **+30–50% prefill i 0–15% dekodu bez MTP** względem lepszego z Vulkan/HIP. Społeczność na gfx1151: tg128 85.1 vs 68.0 (HIP), pp512 +35%, ale pp ≤32 tokenów −16…−28%. Na XTX briansp2020 (rdna-boosts) pisze, że wynik HRX vs HIP z ich kernelami „not what I expected” (2026-10-31). W wiki HRX jest tylko w R01 jako produkt (`01-konkurencja.md:114`). **NOWE jako punkt odniesienia kerneli** (pkt 4.7).
- Ten sam wątek (huppiflupp, 2026-09-19): **kolejność siatki FA dekodu `(kv_block, kv_head)` sprawiała, że każdy wiersz KV (4 głowy) był czytany 4× w odstępie całego przejścia**. Za MALL (powyżej ~8k) dawało to 67 GB/s; zamiana na `(kv_head, kv_block)` przyspieszyła 2.5×. U nas `kvq` ma `blockIdx.z = head_kv` (`fattn-kvq.cu:270`), ale całą siatkę mieści jedna fala (`nsplit = 2·nsm/(ntiles_x·nblocks_z)`, `:632`). Problem prawdopodobnie nie występuje `[INFERENCE]`. Wiersz głowy q4_0 ma jednak 144 B i przecina linie 128 B: bez współdzielenia w L2 odczyt rośnie ×1.78 `[INFERENCE]`. Sprawdza to jeden pomiar liczników (pkt 4.6).
- **ROCm 10.1** ([release notes, 2026-10-05](https://rocm.docs.amd.com/en/latest/about/release-notes.html)): dla gfx1100 bez zmian istotnych dla nas (zgodne z R13). Dwa sygnały regresji: TheRock [#8967](https://github.com/ROCm/TheRock/issues/8967) (10.1 rc2 → stable, dyfuzja gfx1151 do +75% czasu, 2026-10-13) i gufo [#863](https://github.com/gufo-org/gufo/issues/863) (MTP −12.6% między 7.2.3 a 10.1; po analizie to głównie inny tekst greedy, ms/rundę równe, 2026-10-28/29). Lekcja: między toolchainami porównywać ms/krok, nie t/s (**znane**, [[ms-na-krok]]). gufo zauważa też: `hipMalloc` przy kernelach w locie spowalnia `hipLaunchKernel` o ~1.5 µs na sekundy (10.1). U nas PM4 omija `hipLaunchKernel` w kroku.
- **ROCm Optimization Guide 1.0** ([rocm-handbook.amd.com](https://rocm-handbook.amd.com/projects/amd-rocm-optimization-guide/en/latest/)): nowa dokumentacja builtinów (SAD, dot, DPP, permlane, WMMA RDNA3). Nic, czego nie używamy.
- **Blog ROCm**: „Attention Decode on AMD MI450 (Gluon)” dotyczy MI450, nie RDNA3. Nic dla gfx1100.

### 2.6 Społeczność XTX: Reddit, repozytoria pomiarowe, fora

Reddit blokuje odczyt (403/429). Treść znam z fragmentów wyszukiwarki i z repozytoriów, do których posty linkują.

- **r/ROCm „Qwen3.8-27B at ~100 tok/s on a single 7900 XTX (patched hipfire)”** (11-05, `1xdu4mu`) = hipfire #947 (2.2).
- **victoralcazardev/rx7900xtx-local-llm** ([TRIED.md](https://github.com/victoralcazardev/rx7900xtx-local-llm/blob/main/docs/TRIED.md); runtime A/B z [2026-09-26](https://github.com/victoralcazardev/rx7900xtx-local-llm/blob/main/results/20260926-rocm-runtime-ab/README.md)). Źródło jest w R34, ale ten wniosek jest **NOWY dla nas**: kompilator ROCm 10 + **runtime 7.2.4** szybszy od runtime 10.0 (tg −1…−2%, pp **−5%** i większa wariancja na 10.0). Kompilator 7.2.4 przegrywa (tg −7.5% @16K). U nas runtime 10.0 pre4 (`13-rocm-10.1.md:5`); dekod idzie przez PM4, więc zysk dotyczyłby głównie prefillu `[INFERENCE]`. Ten sam plik: `GGML_CUDA_GRAPH_OPT=1` −1.5…−3.9%, LTO ±0.6%, `-ub 1024/2048` bez zysku.
- **nasone32/llama.cpp-RDNA3-7900xtx-opt** ([README](https://raw.githubusercontent.com/nasone32/llama.cpp-RDNA3-7900xtx-opt/main/README.md); repo w Q:v2 10-12, post sprzed ~2 mies.). Delta: flaga kompilatora **`-mllvm --amdgpu-unroll-threshold-local=600`** (NOWE, 0 trafień w wiki), chunked BF16 GDN („near-lossless, not bit-exact”: parkowane), mmvdq dequant-float (RDNA-FAST: −6…24%, znane negatywne).
- **stew675/llama-cpp-rdna-boosts** @ `3cb0e6e` (ENVIRONMENT.md, 2026-11-07): faza SDMA na tym samym boxie daje bimodalne transporty (±16–32%); `HSA_ENABLE_SDMA=0` ją usuwa „but at the slow level”. Mikrobench 2026-08-28: replay grafu HIP na ROCm 10.0 o **+5.3–5.6%** wolniejszy niż na 7.14 (gfx1201). U nas SDMA vs blit dla małych kopii zmierzone jako równe (**znane**, `37-proza-100.md:23`, `24o-luki-hosta.md:57`).
- **szafranski/rx7900xtx-qwen3.8-27b-tuning** ([repo](https://github.com/szafranski/rx7900xtx-qwen3.8-27b-tuning)): 272 W / −75 mV / 2200 MHz, −2.2% przepustowości, bramka „czy undervolt nie zmienił wyjścia”. Undervolt jest poza zakresem. Cap 2200 = nasz eco (**znane**).
- **hcgdw/rx-7900-xtx-llm-benchmark** ([repo](https://github.com/hcgdw/rx-7900-xtx-llm-benchmark)): rocWMMA FA na XTX prefill 713 → 255, dekod 44 → 17 (**znane**: `karty/strix-halo.md:14`, `GGML_HIP_ROCWMMA_FATTN` szkodzi).
- **llamaperf XTX** ([strona](https://llamaperf.com/gpu/rx-7900-xtx)): mediana plain Qwen3.8-27B 4-bit 42.5 t/s (47 raportów, 2026-10-30). Brak trików.
- **X**: `@duycaoxyz` (2112483249121538470): XTX Qwen3.6-35B 133 t/s czat. Nic technicznego.

### 2.7 Wykorzystanie pasma GEMV Q4 na gfx1100: porównanie

| źródło | kernel / warunki | % z 960 GB/s |
|---|---|---|
| **my** (topka, [[sufit-pasma-i-mapa-czasu]], [[mmvq-multikolumnowe]]) | MMVQ multi-col, Qwen, w modelu | **81–88%** (Q5_K 84%) |
| hipfire #946 (autor) | int8 GEMV B=4, kształty 27B, standalone z przerwą launchu | 69–87% (o_proj 69%, lm_head 87%) |
| hipfire przed łatką (#946) | f16 WMMA dla N≤16 (12/16 kolumn pustych) | ~50% |
| hipEngine [ROOFLINE](https://github.com/shisa-ai/hipEngine/blob/main/docs/ROOFLINE.md) (W7900, gfx1100) | „well-written bandwidth-bound kernel” | 75–85% (reguła), llama.cpp Q8 na W7900 ~27–30% całości tokenu |
| amd-hipfire [kampania 07-19](https://github.com/karthik-ramadoss/amd-hipfire/blob/master/docs/specs/2026-07-19-cross-arch-utilization-campaign.md) | A3B MoE, całość tokenu | XTX ~44% (szacunek autora), cel 76–85% |
| Vulkan [#31021](https://github.com/ggml-org/llama.cpp/pull/31021) (RDNA4) | batch 1, MMVQ | „within ~11% of streaming ceiling” |

**Wniosek:** w GEMV jesteśmy na górnej granicy tego, co ktokolwiek publicznie pokazał na RDNA3. Nie szukać tu dalej bez nowego mechanizmu.

### 2.8 arXiv / alphaXiv (okno 6 tygodni)

- [2610.03228](https://arxiv.org/abs/2610.03228) „Reference-Compatible Parallel Execution for Quantized LLM Inference” (2026-10-02, v4 10-22): batchowanie zachowujące numerykę skalarnego wdrożenia (CUDA −4%, Vulkan atencja −32%). **Znane** (nasz tryb bitowy MTP = plain, raport 12).
- [2610.13778](https://arxiv.org/html/2610.13778) ReplaySSM: replay wejść SSM zamiast snapshotów. **Znane** ([[gdn-replay]]).
- [2610.40287](https://arxiv.org/abs/2610.40287) energetyka spekulacji: na gęstych modelach dominuje weryfikacja. Bez działań.
- Brak prac o GEMV/FA specyficznych dla RDNA3 w oknie (wyszukiwanie: „arxiv 2026 AMD RDNA consumer GPU GEMV batch-1 decode”, 2026-11-07).

### 2.9 Nasza karta: zegary pod obciążeniem (pomiar własny, tylko sysfs)

`/sys/class/drm/card0/device/pp_dpm_*`, 2026-11-07 ~23:25 UTC, eco 2200, obciążenie z kolejki GPU (inny job), 80 próbek co 0.25 s; próbki z `gpu_busy_percent > 50`:

- `fclk=2000 MHz` przy `mclk=1249 MHz`: **16 z 28** próbek; reszta to przejścia 601–1600 / mclk 456–772;
- poziomy FCLK: `0:601 1:1000 2:1200 3:1600 4:2000 5:2201 6:2251 7:2301`; **2201–2301 nie pojawiły się ani razu**;
- jedna próbka: sclk 2037 MHz, 259 W, busy 100%.

Nie wiem, czy przy stock FCLK wchodzi na 2301. Brak historycznych logów FCLK (`~/qwen-opt/thermal`, `logs`: 0 trafień). Pkt 4.4.

## 3. Co z tego jest znane (nie proponuję)

GEMV int8 dla weryfikacji (mamy q8_1 + dp4a), skompresowany słownik draftu (64k), natywne KV q4_0 w atencji dekodu (`kvq`), leniwe przeskalowanie softmaksu w `kvq` (`fattn-kvq.cu:38,453`, próg 8), replay GDN, stan GDN bez kopii, residual w epilogu MMVQ, PM4 z chudą granicą (GCR 0x380, [[pm4-replay]]), `GPU_MAX_HW_QUEUES` (bez zysku), SDMA vs blit dla małych kopii (równe), `HIP_FORCE_DEV_KERNARG`, rocWMMA FA (szkodzi), `-mcumode` (gpu-mode Q6), `s_setprio` (23b, odrzucone), host function w kroku (brak).

## 4. Tabela testowalnych pomysłów bezstratnych

Kolumna „zysk” jest liczona na naszym setupie (eco 2200, Q4_K_M, KV q4_0, ub 512). Model czasu prefillu 255k pochodzi z 24v: FA 131 ms na ubatch przy d=32k (stock), liniowo z głębokością; reszta ubatcha ~416 ms; konwersja KV→f16 1.3%. Suma ≈ 475 s stock, co wobec zmierzonych 548 s eco zgadza się z utratą 9–11% prefillu na eco. FA ≈ **53%**, konwersja ≈ **3%** czasu prefillu 255k `[INFERENCE]`.

| # | Pomysł | NOWE / znane | Oczekiwany zysk u nas + dlaczego | Wysiłek | Dokładny test na naszym boxie | Kill | Ryzyko |
|---|---|---|---|---|---|---|---|
| 4.1 | **Pakiet FA prefill D=256 (`<256,256,32,2>`, ncols 64)**: (a) bariery `sched_barrier` z 24v (bitowe, gotowe w `~/wt/prefillfa`); (b) config z #31746: `nbatch_fa` 32, `nbatch_K2/V2` 128, Q ze smem (mamy 0042), config po `ncols2`; (c) opcjonalnie `exp2f` z prescale `log2e` zamiast `expf` (`fattn-mma-f16.cuh:907,1443`) | częściowo znane (24f: ISA `nbatch_fa=32`, scratch 512→192 B; 24v: (a) +3.5% kernela, nieprzyjęte); **NOWE**: zmierzony pakiet #31746 (GQA6 0.70–0.78×) i (c) | FA −10…−25% `[INFERENCE: #31746 mierzył od mastera bez 0042, więc nasz zysk będzie niższy]` → prefill 255k **+5…13%** (548 → ~485–520 s), 32k +1.3…3.4%, ≤8k 0. Dekod 0. Odzyskuje część straty prefillu na eco (−9…−11%) | 1–1.5 d | `test-backend-ops perf -o FLASH_ATTN_EXT` hsk=hsv=256, nh=24, nkv=4, nb=512, kv ∈ {32768, 131072, 262144}, K/V f16 (ścieżka po konwersji), ABBA ×3; potem `llama-bench -fa 1 -ctk q4_0 -ctv q4_0 -ub 512 -p 512 -d 32768,131072 -r 3` (`GGML_HIP_PM4=0`), `long_ctx_bench` TTFT 128k; bramka KLD ([[bramka-kld-kanarki]]), bo (b) zmienia kolejność softmaksu; md5 `/completion` z `n_probs` na prompcie ≥ kilka ubatchy (24v §63) dla samego (a) | kernel < −5% przy kv=131072 albo pp512@d131072 < +2% albo KLD FAIL | numeryka (b),(c) → KLD, nie md5; VGPR przy `nbatch_K2`=128 (w #31746 część SGPR spilli zostaje); przy (c) wyjątki ftz |
| 4.2 | **Fuzja gate/up + GLU w MMQ dla RDNA3 WMMA** (port #29948: przeplecione wiersze po 8, GLU w write-back z akumulatorów WMMA, połowa wierszy zapisu) | **NOWE dla topki** (63c: tylko Enigma/CUDA; RDNA-FAST: wariant MoE −3…16% na RDNA3) | pp ≤32k **+2…4%** `[INFERENCE: znika zapis/odczyt 2×17408×512 f32 na warstwę (~142 MB/ubatch/warstwę, ~9 GB/ubatch ≈ 2% czasu ubatcha) + kernel GLU + jeden odczyt aktywacji]`; 255k +1…2%; CUDA (producent) +4.6…7.4% | 2–3 d | `test-backend-ops -o MUL_MAT` z fuzją (nowe przypadki), `llama-bench -p 512,4096 -ub 512 -r 5` ABBA, rocprofv3 `pp4096` (udział MMQ gate/up przed i po), md5 c4708318/6f14e814/894e56e4 (oczekiwane bitowo: te same akumulatory i ta sama formuła GLU) | pp4096 < +1% albo occupancy MMQ spada (VGPR > 192 dla J=128) | układ akumulatorów WMMA RDNA3 (wiersze r i r+8 nie w tym samym wątku jak na Turing) → przeplot inny niż w #29948; RDNA-FAST −3…16% |
| 4.3 | **Natywne q4_0 K/V w loaderze kafli MMA prefillu** (dekwant do f16 przy kopiowaniu global→LDS, wzór #29846/#31234; bez konwersji całego KV per warstwę per ubatch) | znane dla CUDA (15d, [[fa-kv-kwantyzowane-cuda]]); **NOWE dla prefillu XTX** | prefill 255k **+2…3%** (konwersja ≈ 3% czasu `[INFERENCE]`), 32k +0.6…1.2%; bufor f16 ~**1.07 GB** przy 262144 (4.1 KiB/token × ctx, z [[fa-kv-kwantyzowane-cuda]]) mniej w puli `[INFERENCE: czy pula HIP trzyma go na stałe, nie sprawdzone]` | 2–3 d | jak 4.1 + `test-backend-ops -o FLASH_ATTN_EXT` z KV q4_0, nb 512; szczyt VRAM przy 255k (było 23 367 MiB); md5 (dekwant ten sam co kernel konwersji → oczekiwane bitowo, #29846 deklaruje „bit-identical”) | pp512@d131072 < +1% i VRAM bez zmian | LDS: q4_0 w LDS + f16 płaszczyzny; ewentualne nowe spille |
| 4.4 | **Diagnoza FCLK** pod obciążeniem: stock vs eco (`pp_dpm_fclk`, `pp_dpm_mclk` co 0.25 s w spec_sweep i `llama-bench -p 4096`) | **NOWE** (2.9; 0 trafień „fclk” w logach) | 0% sam w sobie. Jeśli FCLK przy eco stoi na 2000, a przy stock 2301, to część z −1.9% dekodu eco to fabric, a nie sclk `[INFERENCE]`. Wtedy ramię „eco + wymuszony FCLK” może dać dekod +0…2% bez podnoszenia sclk | 0.5 h (odczyt) + 0.5 d (ramię) | odczyt: `while :; do grep '\*' pp_dpm_{sclk,mclk,fclk}; sleep .25; done` w trakcie spec_sweep T=1 (eco, potem stock, ABBA); ramię (root, zgoda jest): `power_dpm_force_performance_level=manual`, `echo "5 6 7" > pp_dpm_fclk`, profil COMPUTE ustawiony jawnie (64 §1.3); spec_sweep ms/krok + W + md5 | FCLK przy stock też 2000, albo ramię < +0.5% ms/krok | `manual` wyłącza automatyczne COMPUTE (64 §1.3), zgłoszenia zawieszeń przy `high`+OD; wyższy FCLK = więcej W (sprzeczne z celem eco, decyzja użytkownika) |
| 4.5 | **Kontrola ewikcji VRAM przy 262k** (mechanizm z #30688): `amd-evicted-vram`, `drm-memory-vram`/`gtt` w `/proc/<pid>/fdinfo/*` llama-server przed i po prefillu 255k | **NOWE** (0 trafień `fdinfo/evicted` w wiki) | 0%, jeśli brak ewikcji; jeśli BO compute/KV trafia do GTT przy 1193 MiB zapasu, dekod przy 255k może być dziś zaniżony `[INFERENCE]` | 10 min | `grep -H 'amd-\|drm-memory' /proc/$(pgrep -f llama-topka/bin/llama-server)/fdinfo/*` przed promptem 255k, po prefillu i po 256 tokenach; porównać z `amdgpu_vram_mm` | `amd-evicted-vram` = 0 i GTT bez wzrostu | brak (tylko odczyt) |
| 4.6 | **Amplifikacja odczytu KV w `kvq`**: liczniki rocprofv3 (`TCC_EA_RDREQ`/`FETCH_SIZE`) vs bajty analityczne (1152 B/token/warstwę q4_0); jeśli > 1.2×, kolejność siatki z `head_kv` najbardziej wewnętrznym albo blok czytający pełny wiersz 576 B | **NOWE** (0 trafień FETCH_SIZE/amplifik.; wzorzec z HRX #27219) | 0…3% dekodu przy ≥128k `[INFERENCE: wiersz głowy 144 B przecina linie 128 B, bez współdzielenia w L2 ×1.78; dziś siatka mieści się w 1 fali, więc pewnie OK]`; wynik ważny dla XtxKvOnce (zmienia liczbę bloków) | 2 h | `rocprofv3 --pmc TCC_EA_RDREQ_sum TCC_EA_RDREQ_32B_sum` na `llama-bench -fa 1 -ctk q4_0 -ctv q4_0 -p 5 -ub 5 -d 131072` (`GGML_HIP_PM4=0`); bajty = 64·RDREQ−32·RDREQ_32B; zmiana siatki nie zmienia obliczeń w bloku → md5 bitowo | amplifikacja ≤ 1.1× | liczniki EA na gfx11 do kalibracji (amd-hipfire P0: najpierw kernel o znanych bajtach) |
| 4.7 | **HRX jako referencja kerneli**: build `hrx-b99` (Lemonade) z Qwen3.8-27B Q4_K_M plain (bez MTP), porównanie tg128 / pp512 / pp4096 i czasów per kernel z topką | **NOWE** (HRX tylko w R01 jako produkt) | 0% bezpośrednio; jeśli HRX bije nas w którymś kernelu (producent: prefill +30–50% vs HIP upstream), mamy wzór do portu; dekod plain jest u nas daleko przed upstream, więc tam raczej kill | 0.5 d + 30 min GPU | `llama-bench -m <Q4_K_M> -fa 1 -p 512,4096 -n 128 -r 3` HRX vs topka (`GGML_HIP_PM4=0` i =1), ta sama karta i eco; potem tracer HRX/rocprofv3 dla najlepszego kernela | HRX ≤ topka w pp4096 i tg128 | build (CPU) dopiero po zwolnieniu kolejki; HRX nie obsługuje KV q4_0 / długiego ctx (#27219: tylko f16 K/V, błędy przy ubatchu po pierwszym) |
| 4.8 | **Flaga `-mllvm --amdgpu-unroll-threshold-local=600`** (nasone32) | **NOWE** (0 trafień) | 0…2% `[INFERENCE]`: pętle z LDS/scratch (FA MMA, MMQ, GDN) mogą się rozwinąć mocniej | 0.5 d | build z flagą, `klab isadiff` (kernele: mmvq, kvq, gdn, mmq Q4_K/Q6_K, FA `<256,256,32,2>`): VGPR, scratch, F_fma/F_add (reasocjacja = 0); jeśli zmiana tylko w zimnych kernelach → kill; inaczej `llama-bench -p 4096` + spec_sweep ABBA + md5 | brak zmian ISA w gorących kernelach albo ABBA < +0.5% | więcej VGPR → niższa occupancy (24v: spille FA z hoistingu) |
| 4.9 | **Runtime ROCm 7.2.4 + kompilator ROCm 10** (victoralcazar: runtime 10.0 −5% pp, −1…−2% tg, większa wariancja) | **NOWE dla nas** (R13 porównywał tylko 10.0 z 10.1) | prefill 0…+5% (dane z innej XTX i innego forka); dekod ~0, bo PM4 omija runtime w kroku `[INFERENCE]` | 0.5 d | `LD_LIBRARY_PATH` na runtime 7.2.4, `llama-bench -p 512,4096 -d 0,16384 -r 3` ABA, potem PM4 soak (S6) | pp4096 < +2% albo jakikolwiek błąd PM4/page fault | **wymaga pobrania** runtime 7.2.4 (zgoda); PM4 zależy od zachowania ROCr/CLR (raport 17) → wysokie ryzyko |

**Kolejność:** 4.5 i 4.4 (odczyty, bez ryzyka; 4.4 przy następnym spec_sweep) → 4.6 (2 h, zasila XtxKvOnce) → 4.1 (najlepszy stosunek zysku do pracy w prefillu) → 4.3 i 4.2 → 4.8 przy najbliższym buildzie → 4.7 i 4.9 tylko przy wolnym czasie albo za zgodą.

## 5. Kalibracja dla testów w toku (bez nowych propozycji)

- **KV-once / `kvq`** (XtxKvOnce): cel z hipfire to ≥525–700 GB/s efektywnie dla atencji weryfikacyjnej. Dla q4_0 to **≤165 µs (700 GB/s) … ≤220 µs (525 GB/s) na warstwę przy 100K** i ≤420–560 µs przy 255k (294 MB/warstwę) `[INFERENCE]`. Vulkan #30190 dał −5.7% kroku przy 32k na gfx1100 (MTP 4, f16 KV). Jeśli nasz KV-once przy 32k da mniej niż ~−3% kroku, coś jest nie tak z kaflem albo podziałem `[INFERENCE]`.
- **Podział `kvq`**: hipfire używa stałej siatki 4 głowy × 24/36 zakresów kluczy (96/144 bloków ≈ 2–3 na WGP), czyli tej samej klasy co nasze „2 bloki na WGP” (`fattn-kvq.cu:625-632`).

## 6. Zaparkowane (stratne) — bez rankingu

| pomysł | źródło | dlaczego odpada | liczby (informacyjnie) |
|---|---|---|---|
| HIP fast-math (`approx-func`, `reciprocal-math`, bez `signed-zeros`) | [#31625](https://github.com/ggml-org/llama.cpp/pull/31625) | zmienia numerykę exp/dzielenia, brak danych wydajności | — |
| chunked BF16 GDN w prefillu | nasone32, rdna-boosts block 02 | „near-lossless, not bit-exact” (autor) | — |
| f16 WMMA / hipBLASLt z tabelą strojenia w prefillu | Strata [#1389](https://github.com/Niko1221/Strata/issues/1389), victoralcazar (Strata v0.2.8) | aktywacje f16 zamiast q8_1 (jak 63-SYNTEZA §4) | prefill MoE +41…71%, dekod przy 120K −16…25% |
| KV oct3 / fwht4 / turbo4 | r/llamacpp `1xlsdrb`, hipfire CHANGELOG, szafranski | inny kwant KV | — |
| podkręcanie pamięci (OD_MCLK) | MegaCapybara (63a §10) | nie stratne numerycznie, ale łamie [[2026-10-20-karta-fabrycznie]] i grozi cichymi błędami pamięci; wymaga osobnej decyzji | 466 → 540 t/s (+20% OC, 5090) |
| undervolt | szafranski | wykluczony w zadaniu | −75 mV, −9.9% W |

## 7. Źródła (z datami)

| źródło | data / wersja | co z niego wzięte |
|---|---|---|
| [llama.cpp #31746](https://github.com/ggml-org/llama.cpp/pull/31746) | 2026-11-05 (draft) | FA D256 MMA RDNA3, GQA6 0.70–0.78× |
| [llama.cpp #31761](https://github.com/ggml-org/llama.cpp/pull/31761), [#31751](https://github.com/ggml-org/llama.cpp/pull/31751) | 2026-11-05 (draft) | tile D256 +13.5% @131k; J=32 spill +36% PP17–32 |
| [llama.cpp #29948](https://github.com/ggml-org/llama.cpp/pull/29948) | scalone 2026-10-25, `c49edf0` | fuzja gate/up+GLU w MMQ, NVIDIA-only (`ggml-cuda.cu:2224-2225` @ `10d4846`) |
| [llama.cpp #31234](https://github.com/ggml-org/llama.cpp/pull/31234), [#30792](https://github.com/ggml-org/llama.cpp/pull/30792), [#30803](https://github.com/ggml-org/llama.cpp/pull/30803) | 2026-10-19…27 | natywne KV kwantyzowane w tile/vec |
| [llama.cpp #30190](https://github.com/ggml-org/llama.cpp/pull/30190) (Vulkan) | 2026-10-08 | KV raz na weryfikację, −5.7% kroku @32k gfx1100 |
| [llama.cpp #31669](https://github.com/ggml-org/llama.cpp/pull/31669), [#30139](https://github.com/ggml-org/llama.cpp/pull/30139), [#31031](https://github.com/ggml-org/llama.cpp/pull/31031), [#29720](https://github.com/ggml-org/llama.cpp/pull/29720), [#29478](https://github.com/ggml-org/llama.cpp/pull/29478), [#31625](https://github.com/ggml-org/llama.cpp/pull/31625) | 2026-09-26…11-04 | znane / parkowane |
| [llama.cpp issue #30688](https://github.com/ggml-org/llama.cpp/issues/30688), [#30638](https://github.com/ggml-org/llama.cpp/issues/30638) | 2026-10-16 | ewikcja do GTT; regresja MTP na RADV |
| [llama.cpp discussion #27219 (HRX)](https://github.com/ggml-org/llama.cpp/discussions/27219) | 2026-08-17 … 11-05 | HRX; kolejność siatki FA (huppiflupp 09-19); liczby gfx1151 |
| [hipfire #946](https://github.com/warpfront/hipfire/issues/946), [#947](https://github.com/warpfront/hipfire/issues/947) | 2026-10-23/24 | GEMV int8 69–87% pasma; 102/97/90 t/s @9K/39K/100K |
| hipfire CHANGELOG v0.4.4/v0.4.5 (`~/src/research68/hipfire-CHANGELOG-efa8fbb.md:213,246,251`) | v0.4.4 2026-10-27; HEAD `efa8fbb` 2026-10-30 | atencja weryfikacyjna WMMA 525–703 GB/s |
| [exllamav3 #543](https://github.com/turboderp-org/exllamav3/issues/543) | 2026-10-21…25 | RDNA3: split-K, fuzje, atencja HIP; grafy ROCm „broken” |
| [Strata #2231](https://github.com/Niko1221/Strata/pull/2231) | 2026-10-13 (zamknięty) | bitowe poprawki gfx1100 (znane) |
| [TheRock #8967](https://github.com/ROCm/TheRock/issues/8967); [gufo #863](https://github.com/gufo-org/gufo/issues/863) | 2026-10-13; 2026-10-28/29 | regresje ROCm 10.1; lekcja ms/krok |
| [ROCm 10.1 release notes](https://rocm.docs.amd.com/en/latest/about/release-notes.html) | 2026-10-05 | brak zmian dla gfx1100 |
| [AMD ROCm Optimization Guide 1.0](https://rocm-handbook.amd.com/projects/amd-rocm-optimization-guide/en/latest/) | 2026 (odczyt 11-07) | builtiny RDNA3 (nic nowego) |
| [Phoronix: Lemonade 11.9 HRX](https://www.phoronix.com/news/Lemonade-11.9-ROCm-HRX); [Lemonade PR #3723](https://github.com/lemonade-sdk/lemonade/pull/3723); [Lemonade backends](https://lemonade-server.ai/docs/dev/backends-reference/) | 2026-09-02; 2026-10-02; odczyt 11-07 | HRX gfx1100/gfx1151, hrx-b99 z Qwen3.8-27B |
| [victoralcazardev TRIED.md](https://github.com/victoralcazardev/rx7900xtx-local-llm/blob/main/docs/TRIED.md), [runtime A/B](https://github.com/victoralcazardev/rx7900xtx-local-llm/blob/main/results/20260926-rocm-runtime-ab/README.md) | 2026-09-26 (A/B), odczyt 11-07 | runtime 7.2.4 > 10.0 |
| [nasone32 README](https://raw.githubusercontent.com/nasone32/llama.cpp-RDNA3-7900xtx-opt/main/README.md) | odczyt 2026-11-07 | flaga `--amdgpu-unroll-threshold-local=600` |
| stew675/llama-cpp-rdna-boosts `ENVIRONMENT.md`, `benchmarks/rocm101-microbench/RESULTS.md` | `3cb0e6e` 2026-11-07; mikrobench 2026-08-28 | faza SDMA; replay grafu 10.0 +5.5% |
| [szafranski tuning](https://github.com/szafranski/rx7900xtx-qwen3.8-27b-tuning), [hcgdw benchmark](https://github.com/hcgdw/rx-7900-xtx-llm-benchmark) | odczyt 2026-11-07 | cap 2200, rocWMMA |
| [hipEngine ROOFLINE](https://github.com/shisa-ai/hipEngine/blob/main/docs/ROOFLINE.md); [amd-hipfire kampania](https://github.com/karthik-ramadoss/amd-hipfire/blob/master/docs/specs/2026-07-19-cross-arch-utilization-campaign.md) | 2026-05-10; 2026-07-19 | % pasma |
| [llamaperf XTX](https://llamaperf.com/gpu/rx-7900-xtx) | 2026-10-30 | mediana plain 42.5 t/s |
| [arXiv 2610.03228](https://arxiv.org/abs/2610.03228), [2610.13778](https://arxiv.org/html/2610.13778), [2610.40287](https://arxiv.org/abs/2610.40287) | 2026-10-02…29 | znane klasy |
| Reddit r/ROCm `1xdu4mu`, r/LocalLLaMA `1waif2b`, r/LocalLLM `1vzd0b3`, r/llamacpp `1xlsdrb` | 2026-09…11 (tylko fragmenty wyszukiwarki; 403/429) | odsyłacze do hipfire, nasone32 |
| Pomiar własny: `pp_dpm_{sclk,mclk,fclk}` | 2026-11-07, eco 2200 | FCLK 2000 MHz pod obciążeniem |
| Nasze pliki | — | `fattn-kvq.cu:38,270,453,625-635`, `fattn-mma-f16.cuh:69-218,907,1443`, `src/llama-graph.cpp:3781`, `~/opt/isa101/v100/mmq-instance-q4_k.s`, `24v`, `24f`, `63c`, [[2026-11-06-ctx-262k-fit]], [[2026-11-06-eco-sweep-sclk]] |
