# 21b — Zasoby „GPU perf engineering” (wafer-ai) + Blackwell Tuning Guide: techniki dla decode/prefill na XTX i konsumenckich NVIDIA

Data: 2026-10-19. Autor: podagent ResGpuPerf. Tylko CPU i źródła: bez GPU i bez chmury, niczego nie budowałem.
Kod sprawdzany w drzewie `~/wt/topka` (build `topka`, commit `eb7509cb9` = `amd-opt` + lookup tail + cache share).
Oznaczenia: `[SZACUNEK]` = moje wyliczenie; `[INFERENCE]` = wniosek bez pomiaru; `[NIEZWERYFIKOWANE]` = teza źródła, której nie sprawdziliśmy.

## 0. Najważniejsze

1. **Lista wafer-ai to dobry spis lektur, ale nie przepis na nasz problem.** 5 z 6 działów dotyczy serwerów z dużym batchem, Hoppera/B200 i rozproszenia: NVLink, DeepEP, EPLB, disaggregation, k8s. Dział AMD to wyłącznie CDNA/Instinct (MI350, CDNA4 ISA). Nie ma tam ani jednego źródła o RDNA3, o batch=1 na kartach konsumenckich ani o skwantyzowanym GEMV (GGUF/K-quants).
2. **Blackwell Tuning Guide (v13.4) to krótki dokument o B200/GB200: HBM3, L2 126 MB, NVLink 5.** Dla sm_120 (RTX 50) podaje tylko limity: 48 warpów/SM, 128 KB shared/SM, 99 KB na blok, 32 bloki/SM. Opis z listy wafer („Tensor memory, Blackwell execution features”) **nie zgadza się z treścią**: o tensor memory w przewodniku nie ma nic. Najważniejsza rzecz dla nas jest tam, gdzie przewodnik milczy:
   - na sm_120 **nie ma** tcgen05/TMEM, wgmma, 2-CTA ani TMA multicast;
   - CUTLASS na GeForce wymusza klaster 1×1×1 („no multicast feature”);
   - FA3/FA4, DeepGEMM i kernele ThunderKittens-H100 **nie przenoszą się** na RTX 5090/5060 Ti.
3. **Większość technik z listy, które mają sens przy batch 1, już mamy albo zmierzyliśmy negatywnie.** Dotyczy to: dataflow megakernel (15a), PM4-PDL i prefetchu MALL na XTX (16a: kill), MoE gate+up i sufitu wzorca (16g), jednego przejścia po KV dla grupy GQA (kvq, 16c), batch-invariance ze stałym rozmiarem splitu (12), Stream-K w MMQ/FA (upstream), cache policy GLC|DLC wag w weryfikacji (mmvq.cu:345-347) oraz WMMA dla weryfikacji 9–16 kolumn (0037).
4. **Nowe, tanie i bezstratne (bitowo z konstrukcji) pozycje dotyczą NVIDIA:**
   - **(a) PDL w gorącym kernelu MMVQ jest użyty tylko w połowie.** Gęsty `mul_mat_vec_q` woła `ggml_cuda_pdl_sync()` *przed* jakimkolwiek odczytem wag (`mmvq.cu:1530`) i nigdy nie woła triggera (`ggml_cuda_pdl_lc` tylko w `mul_mat_vec_q_moe`, `mmvq.cu:1980`). Wg dokumentacji CUDA następny kernel startuje dopiero, gdy wszystkie bloki zakończą pracę albo wywołają trigger. PDL ukrywa więc dziś tylko launch i prolog, a nie rampę strumienia wag. Poprawka: trigger na starcie + prefetch L2 pierwszych linii wag *przed* `cudaGridDependencySynchronize` dla matvec bez `ids`. `[SZACUNEK]` LFM +1–4.5% na 5060 Ti, +3–11% na 5090.
   - **(b) L2 persisting window** (`accessPolicyWindow`) dla wag czytanych w każdym tokenie (głowa LFM 215 MB, atencja/conv): +1–2% LFM na 4090/5090/5060 Ti `[SZACUNEK]`. Na XTX odpowiednika nie ma (MALL nie jest sterowalny z HIP, 18 §3.5).
   - **(c) Prefetch L2 w pętli MMVQ jest dziś włączony tylko na DGX Spark.** Upstream na GB10 przy 5 kolumnach zmierzył +2.9% (Q4_K), +3.9% (Q5_K) i +6.2% (Q6_K). Teza, że „na kartach z wyższym pasmem to nie pomaga”, nie ma danych w podlinkowanym komentarzu. To kandydat do weryfikacji MTP (4–5 kolumn) na 3090/5060 Ti.
5. **RTX 5090 to karta, na której narzut kerneli waży najwięcej.** Nikt u nas jej nie mierzył. Projekcja LFM Q4_K_M (§4.1): 435–570 t/s, czyli tylko 37–48% pasma 1.792 TB/s, bo stały narzut ~1.5 ms/token z 5060 Ti nie maleje razem z czasem strumienia. Tam PDL/prefetch (a) i ewentualny trwały blok MoE mają największą dźwignię.
6. **XTX: najważniejsza „technika z listy” to ta, której nie mamy po wyłączeniu PM4, czyli tani launch.** Raport 17 zaleca `GGML_HIP_PM4=0` (koszt: LFM −12%, Qwen MTP −4.7%). Zmierzona podłoga pakietu AQL to 2.08 µs nawet bez fence’ów (lfm-decode-round4.md:37,47-50), więc żadne sztuczki AQL/HIP graph tego nie odzyskają. Jeśli PM4 nie da się zabezpieczyć (Pm4Fix), jedyną bezstratną drogą do tych 12% jest kernel trwały: bariera siatki 0.48–0.77 µs wobec 2.75 µs granicy grafu HIP. To odwraca wniosek 15a, który zakładał działające PM4. Decyzja zależy od wyniku Pm4Fix.
7. **FP4/FP8 nie przyspieszą naszego decode** (bajty wag te same: NVFP4 4.5 bpw ≈ Q4_K 4.5 bpw). W prefillu na sm_120 dają +65–81% (09), ale tylko na plikach NVFP4, które dziś są słabe jakościowo (KLD Qwen 0.0865 vs 0.0265, `wiki/nvidia/nvfp4.md:20-21`). XTX nie ma FP8/FP4 w ogóle.
8. **Pięć eksperymentów (§6):**
   - E1 — PDL trigger + prefetch przed czekaniem (lokalna 5060 Ti, $0);
   - E2 — pierwsza kampania 4090/5090 z rozkładem przerw (~$1.5);
   - E3 — L2 persisting window dla LFM;
   - E4 — prefetch L2 w pętli MMVQ dla 2–8 kolumn;
   - E5 — koszt granicy grafu CUDA na Ampere/Ada (X5 z 15a; bramka dla trwałego kernela na NVIDIA) razem z prototypem bariery trwałej siatki na XTX bez PM4.

---

## 1. Co jest w źródłach i co z tego wynika (audyt)

### 1.1 wafer-ai/gpu-perf-engineering-resources
Repo: https://github.com/wafer-ai/gpu-perf-engineering-resources (README 363 linii, 4235 gwiazdek, sekcja Frontier „verified 2026-10-17”). Polityka źródeł („paper, spec, repo, implementer report… Performance claims need the hardware, workload, precision, baseline”) jest zbieżna z naszą fabryką (16h).

Dział po dziale, z oceną przydatności dla nas:

| dział | co zawiera | przydatność dla batch 1 / XTX / RTX | uwagi krytyczne |
|---|---|---|---|
| Start here | scaling-book, kipply arithmetic, roofline, PMPP, Etalon | **wysoka** (model mentalny bajty/token) | — |
| 1. Fundamentals | CUDA PG, Best Practices, Hopper/Blackwell TG, PTX, cuobjdump | średnia | brak RDNA ISA i modelu pamięci AMDGPU |
| 2. Kernel optimization | transpose, reduction, decoupled look-back, online softmax, batch-invariance, Volkov, Stream-K, DeepGEMM, siboehm, Gordić, TMA, tcgen05 | **wysoka** dla nauki; techniki: online softmax, split, Stream-K, batch-invariance już mamy | DeepGEMM/TMA/tcgen05 = Hopper/B200, nie sm_120 |
| Tensor cores / low precision | OFP8, MX, TE, tcgen05 | niska (decode bandwidth-bound) | MX/NVFP4 ważne dla jakości kwantów (15e) |
| Attention | FA1–4, FlashInfer | średnia: FA2 (podział pracy), FlashInfer (load balancing, graph-safe) | FA3/FA4 wymagają wgmma/tcgen05, na sm_120 nie ma |
| 3. Triton / CUTLASS / CK / AITER / HipKittens | — | niska | AITER i HipKittens celują w CDNA; Compute Profiler (roofline) tylko Instinct (`wiki/rocm/rocprof.md:20`) |
| Profiling | Nsight Systems/Compute, Sanitizer, CUTLASS methodology, rocprof-compute | średnia | metodologia CUTLASS (zegary, rozgrzewka) zgodna z naszym ABBA |
| 4. Engines | Orca, vLLM, Sarathi, SGLang, KV (GQA, MLA, KIVI, Jenga), kwanty, spekulacja, XGrammar | średnia: Jenga (KV dla hybryd), EAGLE-3 (18 #8), Sarathi (18 #4) | throughput przy dużym batchu |
| 5. Distributed | NCCL, DeepEP, EPLB, DistServe, Mooncake, Dynamo, llm-d | ~0 (jedno GPU) | — |
| 6. Hardware | Blackwell brief/TG, CUTLASS Blackwell, HIP hardware impl., CDNA4 | średnia | „HIP hardware implementation” opisuje CDNA (MFMA, AGPR, DME); o RDNA tylko banki LDS (64 dla RDNA2/3/4) |
| Frontier | KernelBench(-Verified), FlashInfer-Bench, SOL-ExecBench, KernelGuard | **wysoka dla fabryki**: „physics-floor check” przeciw reward hackingowi | nasz błąd „1075 GB/s = 112% peaku” (`wiki/metody/wyniki-negatywne.md:17`) złapałby taki check |

Twierdzenia z listy, które sprawdziłem:
- **Stream-K**: „peak speedup up to 14× and 6.7×” (https://arxiv.org/abs/2301.03598). To szczyt na patologicznych kształtach w zbiorze 32 824 geometrii, więc nie jest typowy; uczciwa liczba to „wyższa i stabilniejsza średnia”. U nas Stream-K już jest w MMQ (`mmq.cuh:173,346`) i w FA (`fattn-common.cuh:1155-1196`, upstream).
- **NVFP4 blog** (https://developer.nvidia.com/blog/introducing-nvfp4-for-efficient-and-accurate-low-precision-inference/): dwupoziomowe skale, E4M3 na 16 wartości i FP32 na tensor, 4.5 bita/wartość. Pomiar dokładności jest dla DeepSeek-R1 (FP8 → NVFP4, ≤1 pp), czyli modelu 671B. Na modelach 24–27B nasze KLD jest ~3× gorsze od UD-Q3_K_XL. Ważne potwierdzenie raportu 15e: ggml nie ma tej skali FP32 na tensor (99.8–100% skal subnormalnych), a NVIDIA pisze wprost, że bez niej zakres E4M3 nie wystarcza.
- **Lista podaje „HIP hardware implementation” jako źródło AMD.** Dokument mówi „4 SIMD × 16 ALU, wave64, MFMA, AGPR” (CDNA), a RDNA3 ma 2× SIMD32 na CU, wave32 i WMMA bez osobnych tensor core’ów (`wiki/rocm/rdna3-gfx1100.md:13-17`). Dla naszego zespołu to źródło myli.

### 1.2 Blackwell Tuning Guide (https://docs.nvidia.com/cuda/blackwell-tuning-guide/, wersja 13.4)
Treść dotycząca sm_120:
- maks. 48 warpów/SM (cc 10.0: 64), 64K rejestrów/SM, 255 rej./wątek, 32 bloki/SM;
- shared 128 KB/SM, maks. 99 KB/blok (cc 10.0: 228/227 KB);
- klastry „supported by Blackwell GPUs”, portable 8 (16 tylko B200 opt-in), DSMEM równolegle z L2;
- L2 persistence „similar to Ampere” (odsyła do CUDA PG 4.13);
- carveout L1/shared przez `cudaFuncAttributePreferredSharedMemoryCarveout`.

Wszystko inne (HBM3, GB200 126 MB L2, NVLink 5) dotyczy datacenter.

**Krytyka:** przewodnik nie mówi, czego sm_120 **nie ma**. Uzupełnienie z innych źródeł:
- CUTLASS (https://docs.nvidia.com/cutlass/latest/media/docs/cpp/blackwell_functionality.html#blackwell-sm120-gemms): „On Geforce series graphics card, there is no multicast feature therefore the cluster shape is fixed to 1x1x1”, tylko layout TN, warp-level `mma` z FP4/FP6/FP8 i TMA warp-specialized.
- Notatki praktyka (RTX 5090, https://github.com/fengwang/ncu-report-skill-rtx-5090/blob/main/blackwell-cuda-programming.md): brak tcgen05/TMEM/wgmma/2-CTA, klastry do 8, `persistingL2CacheMaxSize` = 60 MB `[NIEZWERYFIKOWANE u nas]`.
  - **Błąd w tym źródle:** twierdzi, że FP4 `mma.sync` na sm_120 jest „library-only”. Nasz fork używa wprost `mma.sync.aligned.kind::mxf4nvf4.block_scale.scale_vec::4X.m16n8k64` (`ggml/src/ggml-cuda/mma.cuh:1276-1286`), a raport 09 zmierzył natywne FP4 w prefillu. Działa przy `sm_120a`.

### 1.3 Karty: liczby do rachunków

| karta | pasmo GB/s | L2 | SM/CU | PDL | TMA | klastry/DSMEM | FP8 / FP4 tensor | źródło |
|---|---|---|---|---|---|---|---|---|
| RX 7900 XTX (gfx1100) | 960 | 6 MB L2 + 96 MB MALL | 96 CU | brak (enum tylko, 15a §2.5) | brak | brak | brak / brak | `wiki/rocm/rdna3-gfx1100.md:13-17` |
| RTX 3090 (sm_86) | 936 | 6 MB | 82 | brak (cc < 9.0) | brak (cp.async) | brak | brak / brak | Blackwell RTX whitepaper tab. 1 (https://images.nvidia.com/aem-dam/Solutions/geforce/blackwell/nvidia-rtx-blackwell-gpu-architecture.pdf) |
| RTX 4090 (sm_89) | 1008 | 72 MB | 128 | **brak** (Ada, #22522 „CC >= 90”) | brak | brak | FP8 tak / brak | j.w. |
| RTX 5060 Ti (sm_120) | 448 | 32 MB | 36 | tak | tak | tak, bez multicast | tak / tak (`sm_120a`) | https://en.wikipedia.org/wiki/GeForce_RTX_50_series (tabela specyfikacji); `wiki/karty/rtx-5060-ti.md:12` |
| RTX 5090 (sm_120) | 1792 | 96 MB (persist ≤ 60 MB) | 170 | tak | tak | tak, bez multicast | tak / tak | whitepaper tab. 1; fengwang (60 MB) |

**Little’s law** (bajty w locie = pasmo × latencja; założona latencja DRAM ~600 ns `[ZAŁOŻENIE]`): XTX 576 KB → 6.0 KB/CU; 3090 562 KB → 6.8 KB/SM; 4090 605 KB → 4.7 KB/SM; 5060 Ti 269 KB → 7.5 KB/SM; 5090 1075 KB → 6.3 KB/SM `[SZACUNEK]`. Wszystkie karty potrzebują po ~5–8 KB w locie na SM/CU, czyli ~10–16 ładowań 16 B na falę/warp w locie. To samo wyszło w ATT na XTX: gate+up spędza 85% czasu w `s_waitcnt vmcnt` (16g §1). TMA nie jest do tego potrzebne: imp na 5090 pisze „TMA for paged KV — cp.async already at near-peak”, a nasz kvq-cuda doszedł do ~92% z 448 GB/s na cp.async (16c TL;DR 4).

---

## 2. Mapa technik: (a) XTX/HIP, (b) NVIDIA Ampere/Ada/Blackwell

„Mamy?”:
- **tak** = w produkcji albo w gałęzi z pomiarem;
- **neg** = zmierzone negatywnie;
- **nie** = nie robione.

Zysk dotyczy naszych obciążeń: Qwen MTP / LFM plain / agent kodujący.

### 2.1 Memory-bound matvec / skwantyzowany GEMV

| technika | (a) XTX | (b) NVIDIA | oczekiwany zysk | wysiłek |
|---|---|---|---|---|
| koalescencja, szerokie ładowania 16 B, buffer loads | **tak** (`MMVQ_BUFFER_LOADS`, `mmvq.cu:197-231`) | tak (upstream) | — | — |
| wiersze/fale na blok, strojenie per arch | **tak** (`mmvq-n1-wiersze`; sm_86 N1_ROWS=2 +7–8.5%, sm_120 −2.7%, `wiki/nvidia/sm-86-89-120.md:22`) | tak (profil karty) | — | — |
| wielokolumnowy GEMV dla weryfikacji (wagi czytane raz na N tokenów) | **tak** (2–8 MMVQ multi, 9–16 WMMA iu8 0037) | tak (MMVQ ≤ 8, potem MMQ) | — | — |
| cache policy wag (strumień poza L0/GL1) | **tak**: GLC\|DLC, verify mmvq 22.95 → 22.08 ms (`mmvq.cu:345-347`); głowa Q6_K traci ~0.14 ms | nie: `ld.global.L1::no_allocate`/`evict_first` | XTX: cpol 0 dla samej głowy Q6_K ≈ +0.5% Qwen MTP `[SZACUNEK]`; NVIDIA nieznany | 0.5 dnia |
| prefetch wag do rejestrów w pętli | **tak** w GU_BLOCK (16g) | upstream: `prefetch.global.L2` tylko na DGX Spark (`mmvq.cu:30-34,1703-1721`) | NVIDIA 2–8 kol.: 0…+3% weryfikacji `[SZACUNEK]` z danych GB10 | 0.5 dnia (E4) |
| sufit wzorca, repack wag przy ładowaniu | audyt zrobiony dla LFM (16g); repack Qwena = 18 #13 | nie | Qwen +10% przy p=0.3 (18) | 8 dni |
| nontemporal loads | **neg** (12.9 → 14.4 µs, `wyniki-negatywne.md:16`) | — | — | — |
| tensor core’y w GEMV S=1 (MonoKernel: MFMA z próbkami jako N) | dla N=1 bez sensu (VALU 7.5%, 16g) | jw. | 0 | — |

### 2.2 Atencja przy dekodowaniu

| technika | (a) | (b) | zysk | wysiłek |
|---|---|---|---|---|
| flash-decoding (split KV + combine), online softmax | **tak** (kvq HIP) | **tak** (upstream vec/MMA + `flash_attn_combine_results`; kvq-cuda) | — | — |
| jedno przejście po KV dla całej grupy GQA | **tak** (kvq; 94k 43.0 → 70.9 t/s) | **tak** w gałęzi `kvq-cuda`: 3090 Qwen tg64@64k +36.8%, MTP@64k +27.6% (16c), wyjątek n=1 D256 q4_0 po KLD | — | — |
| jedno przejście dla wszystkich kafli N×G (weryfikacja) | nie (18 #5) | nie | MTP @94–113k +8% (18) | 5 dni |
| stały rozmiar splitu (batch-invariance) | **tak** w `batch-invariant` (12) | nie | determinizm, nie szybkość | — |
| combine w klastrze przez DSMEM (bez osobnego kernela) | n/d | nie; tylko sm_90+/sm_120 | Qwen ≤0.4%, LFM 5090 ~1–1.5% `[SZACUNEK]` (10–16 warstw × 2–3 µs) | 2–3 dni, niski priorytet |
| L2 persistence dla KV | n/d (MALL niesterowalny) | nie | LFM @8–32k na 5090 ≤ 2.8% bajtów `[SZACUNEK]`; imp: „measurable above 4K ctx” **bez liczby** (wątpliwe) | w E3 |
| FP8 w atencji | brak FP8 | Ada/Blackwell: imp FP8 prefill +3.3% pp4096 (stratne) | ~0 w decode (compute idle) | nie robić |

### 2.3 MoE (LFM2.5-24B-A2B, jedno GPU)

| technika | (a) | (b) | zysk | wysiłek |
|---|---|---|---|---|
| fuzja gate+up+SwiGLU + kopia q8_1 | **tak** (GU_BLOCK, +0.33% LFM / +1.39% Uncensored) | tak (profil, `GATE_UP_Q8` off na sm_86/120) | — | — |
| down + ważenie + residual w jednym kernelu | **tak** (`mul_mat_vec_q_moe_down_reduce`, `mmvq.cu:3260`) | tak | — | — |
| trwały blok MoE (dataflow, tagged pairs) | nie; 15a C: +2–5% ponad PM4-PDL; bez PM4 patrz §4.4 | nie; 3090/4090 bez PDL → największy potencjał (15a §4.2) | zależny od E5 | 10–12 dni HIP + 8 CUDA |
| expert-aware weryfikacja / drafty (koszt u(N)) | model w 18 §3.4 | jw. | dotyczy 18 #2 | — |
| DeepEP / EPLB / GShard / MegaScale | n/d (jedno GPU) | n/d | 0 | — |

### 2.4 Narzut launchu, graphs, PDL, megakernele

| technika | (a) | (b) | zysk | wysiłek |
|---|---|---|---|---|
| graphs | HIP graph 2.75 µs/granicę (round4:30) | CUDA graphs upstream (`ggml-cuda.cu:5917`) | — | — |
| replay PM4 (granica 0.46–0.86 µs) | **tak, ale zalecane wył.** (17: 8 resetów w produkcji) | n/d | PM4 off = LFM −12%, Qwen −4.7% (17:24) | Pm4Fix (inny agent) |
| fuzje (mniej kerneli) | **tak** (weryfikacja 2156 → ~830, `hip-graph-narzut.md:16`) | tak (te same łatki) | — | — |
| PDL | brak w ROCm | **częściowo**: `ggml_cuda_pdl_sync/lc` w wielu kernelach, ale gęste MMVQ bez triggera i bez pracy przed sync (`mmvq.cu:1530`) | 5060 Ti LFM +1–4.5%, 5090 +3–11% `[SZACUNEK]`, §4.2 | 1–2 dni (E1) |
| PM4-PDL / tickety / flagi | **neg** (16a X1/X2) | n/d | — | — |
| tagged pairs (wartość+epoka jednym store’em) | nie testowane jako hand-off matvec (16a testował licznik/flagę/relay/CP) | nie | tylko jako część trwałego bloku (15a C) | — |
| megakernel warstwy | 15a D: 25–35 dni, odrzucony | Lucebox 3090: 1.55× na 0.8B BF16 (15a #11) | LFM 3090 54% pasma → potencjał | gated by E5 |
| trwała siatka z barierami | 15a: nie bije PM4; **bije HIP graph** (0.48–0.77 vs 2.75 µs) | nie mierzone | XTX bez PM4: odzysk do ~0.45 ms/token LFM `[SZACUNEK]` §4.4 | E5 |

### 2.5 TMA, klastry, L2 residency, FP4/FP8 (funkcje Hopper+/Blackwell)

| technika | (a) | (b) | zysk | wysiłek |
|---|---|---|---|---|
| TMA (`cp.async.bulk`) | brak (DME tylko CDNA3/4) | sm_120 tak; 3090/4090 nie | decode ~0 (cp.async już blisko peaku: imp; 16c 92%) | — |
| klastry / DSMEM | brak | sm_120 tak (CUTLASS: GEMM 1×1×1, bez multicast) | combine/ticket bez osobnego kernela: ≤1.5% | niski priorytet |
| L2 persisting window | brak API dla MALL (18 §3.5) | Ampere+ (`cudaStreamAttributeAccessPolicyWindow`, także węzły grafu) | 3090 (6 MB) 0; LFM 4090/5090/5060 Ti +1–2% | 0.5–1 dnia (E3) |
| FP8/FP4 decode | brak | bajty jak w K-quantach | 0 | — |
| FP4 prefill (W4A4 NVFP4 MMQ) | brak | **jest upstream** na `sm_120a` (+65–81%, 09) | tylko z plikami NVFP4; jakość słaba (15e) | — |
| FP8 KV | brak | Ada/Blackwell | ≈ q8_0 w bajtach, inna numeryka | nie robić |

---

## 3. Rachunki dla nowych pozycji

### 3.1 Projekcja RTX 5090 (dlaczego narzut liczy się tam najbardziej)
- LFM Q4_K_M na 5060 Ti: 4.81 ms/token (207.86 t/s), podłoga ~3.35 ms przy 448 GB/s, czyli ~1.5 GB/token (15a §3.4). Narzut 1.46 ms.
- Na 5090 podłoga to 1.5 / 1.792 = 0.84 ms.
  - Jeśli narzut jest stały (latencja, launch, rampa): 0.84 + 1.46 = 2.30 ms → **435 t/s (37% pasma)**.
  - Jeśli połowa narzutu skaluje się z pasmem: 0.84 + 0.73 + 0.73 × 448/1792 = 1.75 ms → **571 t/s (48%)**. `[SZACUNEK]`
- Qwen UD-Q4_K_XL plain: podłoga 16.48 / 1.792 = 9.20 ms. Narzut z 3090 to 23.26 − 17.98 = 5.28 ms (15a §3.3).
  - Stały narzut: 14.5 ms → 69 t/s.
  - Połowa skaluje się z pasmem: 9.2 + 2.64 + 2.64 × 936/1792 = 13.2 ms → 76 t/s.
- Wniosek: na 5090 narzut to 40–63% czasu tokenu LFM, a na 5060 Ti 30%. Każda technika przeciw bańkom między kernelami (PDL, prefetch przed czekaniem, trwały blok MoE) jest na 5090 warta ~2× więcej niż na kartach, które mierzyliśmy. Bez pomiaru (E2) to tylko hipoteza.

### 3.2 PDL: trigger i praca przed `cudaGridDependencySynchronize`
Mechanika wg CUDA PG 4.5 (https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/programmatic-dependent-launch.html):
- „The CUDA driver can launch the secondary kernel when all primary thread blocks have launched and executed `cudaTriggerProgrammaticLaunchCompletion`. If the primary kernel doesn’t execute the trigger, it implicitly occurs after all thread blocks in the primary kernel exit.”
- `cudaGridDependencySynchronize` czeka na zakończenie primary i flush pamięci, więc poprawność nie zależy od miejsca triggera.

U nas:
- `mul_mat_vec_q` (gęsty, `mmvq.cu:1480`): `pdl_sync` w linii 1530, zanim cokolwiek zostanie wczytane. W tym kernelu nie ma `pdl_lc`.
- Następny kernel startuje dopiero po wyjściu ostatniego bloku MMVQ, a sam MMVQ nie zaczyna strumienia wag przed końcem poprzednika.
- Wagi gęstego matvec (bez `ids`) nie zależą od poprzednika. Adres jest znany przed `pdl_sync`; `channel_x` dla gęstego to `fastdiv(channel_dst, channel_ratio)`, bez odczytu z pamięci.

Zmiana (bitowo z konstrukcji, bo wagi są tylko do odczytu):
1. `ggml_cuda_pdl_lc()` na początku `mul_mat_vec_q`.
   - Trigger zadziała, gdy wszystkie bloki wystartują, czyli w ostatniej fali. Wtedy bloki następnego kernela wypełniają ogon.
   - Te bloki czekają w `griddepcontrol.wait` i zajmują sloty dopiero wtedy, gdy wszystkie bloki MMVQ już wystartowały, więc nie odbierają slotów blokom primary `[INFERENCE z semantyki dokumentu]`.
2. Przed `pdl_sync`: `prefetch.global.L2` (lub `cp.async.bulk.prefetch.L2` na sm_90+) pierwszych 1–2 iteracji wag bloku. Gdy pasmo pozwala, także ładowanie pierwszej iteracji do rejestrów, analogicznie do VGPR-prefetchu z X1 na XTX.

Rachunek `[SZACUNEK]`:
- ~110 gęstych matvec/token w LFM: mmvq1 75 + in_proj/conv 29 + głowa (16a §2). Odzysk 0.5–2 µs na kernel daje 0.055–0.22 ms/token:
  - 5060 Ti: **+1.1–4.6%** (z 4.81 ms);
  - 5090: **+2.5–11%** (z ~2.0 ms).
- Qwen: ~450 gęstych matvec × 0.5–2 µs = 0.23–0.9 ms:
  - 5060 Ti plain: ~34.6 ms (28.9 t/s, `15d:0`) → **+0.7–2.6%**;
  - 5090 (~13–14.5 ms) → **+1.6–7%**.

Dowody przeciw (p ≈ 0.35):
- na XTX prefetch do L2 przed konsumentem nie dał nic (16a X3), a prefetch do VGPR pomagał tylko przy siatkach ≥1536 bloków (16a X1);
- upstream w testach DGX Spark widział przy ncols = 1 tylko ~0% z prefetchu w pętli.

Dowody za:
- PDL w upstream daje +5–13% tg na Blackwell (#22522), więc granica na Blackwellu realnie kosztuje;
- rampa strumienia to dokładnie to, co MonoKernel/Hazy zyskują prefetchem przed czekaniem (15a §2.2).

Dotyczy tylko sm_90+, z naszych kart: 5060 Ti i 5090. 3090/4090: 0.

### 3.3 L2 persisting window (NVIDIA)
API: `cudaDeviceSetLimit(cudaLimitPersistingL2CacheSize, min(0.75·l2CacheSize, persistingL2CacheMaxSize))` + `accessPolicyWindow{base, num_bytes, hitRatio, hitProp=Persisting, missProp=Streaming}` na strumieniu albo na węźle grafu (`cudaKernelNodeAttributeAccessPolicyWindow`). Źródło: CUDA PG 4.13 (https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/l2-cache-control.html).

Co przypiąć: dane czytane **w każdym tokenie**, których mniejsza część mieści się w set-aside. Strumień wag raz na token przy LRU nie trafia nigdy (18 §3.5), a przypięte linie przetrwają strumień, bo zwykłe dostępy używają set-aside tylko wtedy, gdy jest wolny.
- LFM: głowa `token_embd` Q6_K 215 MB czytana co token. Przypięcie W MB z `hitRatio = W/215` oszczędza W MB DRAM na token.
- 5090 (60 MB): 60 MB / 1.792 TB/s = 33 µs z ~2.0 ms → **+1.7%**.
- 4090 (persist max nieznany, ≤ 54 MB przy 75%): 54 µs z ~2.7 ms `[SZACUNEK]` → **+2%**.
- 5060 Ti (≤ 24 MB): 54 µs z 4.81 ms → **+1.1%**.
- 3090 (6 MB): 0.
- Qwen: 60 MB / 16.5 GB → 0.36%, pomijalne. Wyjątek to blok MTP czytany 4× na krok: 60 MB × 3 trafienia na 5090 ≈ 180 MB z ~19 GB/krok → ~1% `[SZACUNEK]`.

Ryzyko: set-aside zmniejsza L2 dla FA (kvq czyta drugi kafel z L2, 16c §1). Trzeba to zmierzyć przy 32k, a nie tylko przy 0.

### 3.4 XTX bez PM4: trwała siatka wraca do gry (warunkowo)
- Fakty:
  - AQL nie zejdzie poniżej 2.08 µs na pakiet nawet bez barier i fence’ów (round4:37-38,47-50);
  - granica w HIP graph to 2.75 µs;
  - bariera trwałej siatki to 0.48–0.77 µs (15a §4.1);
  - PM4 0.46–0.86 µs, ale z 8 resetami w produkcji (17).
- LFM: 305 granic × (2.75 − ~0.6) µs ≈ 0.66 ms upper bound. Zmierzona strata po wyłączeniu PM4 to 3.40 → 3.86 ms = 0.45 ms (293.7 → 259.3 t/s), co jest spójne.
- Warianty bez PM4:
  - (i) trwały blok MoE na warstwę (norm+router+top-k → gate+up → down) z barierami w kernelu usuwa ~4–5 granic × 38 warstw ≈ 170 granic → `[SZACUNEK]` ~0.3–0.36 ms → **+8–10% LFM** wobec PM4-off;
  - (ii) cała warstwa LFM w trwałej siatce — 15a D, 25–35 dni.
- Ryzyko: co-residency na GPU z wyświetlaczem i zawieszenia (gfx1250: 200× wolniej przy współlokatorze, 15a #6). Według 17 fault w zwykłej kolejce AQL zabija tylko proces, bez resetu, więc ten tryb może być bezpieczniejszy od PM4. Konieczne: bounded spin + słowo błędu (15a E) oraz dynamiczny indeks zadań zamiast „CTA (base+t)%G” (15a §4.4).
- **Decyzja zależy od Pm4Fix:** jeśli guard (`7cd12f993`) da 0 faultów na ≥1000 requestów, ta pozycja spada na koniec listy.

---

## 4. Lista priorytetów (zysk × p / dni-agenta)

| # | technika | platforma | zysk (na czym) | p | dni | wynik | bezstratne? | stan |
|---|---|---|---|---|---|---|---|---|
| 1 | Pomiar 4090/5090 + rozkład przerw (nsys bez node-trace, PDL 0/1) | NVIDIA | decyzyjny: czy narzut = 40–63% (§3.1) | 0.8 | 1 (+~$1.5) | **wysoki** | n/d | nie mierzone |
| 2 | PDL: trigger na starcie MMVQ + prefetch przed `pdl_sync` | 5060 Ti, 5090 | LFM +1–4.6% / +2.5–11%; Qwen +0.7–2.6% / +1.6–7% | 0.35 | 1.5 | 1.5–2.5 | **tak, bitowo** | nie |
| 3 | Prefetch L2 w pętli MMVQ dla 2–8 kolumn (włączyć poza DGX Spark) | 3090, 4090, 5060 Ti | weryfikacja MTP 0…+3% | 0.3 | 0.5 | 1.8 | tak, bitowo | upstream tylko GB10 |
| 4 | L2 persisting window (głowa LFM, blok MTP) | 4090, 5090, 5060 Ti | LFM +1–2%, Qwen MTP ~1% (5090) | 0.4 | 1 | 0.6 | tak, bitowo | nie |
| 5 | Granica grafu CUDA na Ampere/Ada (X5) → bramka dla trwałego bloku MoE na NVIDIA | 3090, 4090 | decyzyjny; LFM na 54% pasma | 0.7 | 1 (+$0.5) | wysoki (tani) | n/d | 15a: czeka |
| 6 | Trwały blok MoE z barierami jako ścieżka bez PM4 | XTX | LFM +8–10% wobec PM4-off `[SZACUNEK]` | 0.3 (zależne od Pm4Fix) | 10–12 | 0.25 | tak (ta sama kolejność redukcji) | warunkowe |
| 7 | cpol 0 dla głowy Q6_K w weryfikacji (per typ) | XTX | Qwen MTP ~+0.5% | 0.5 | 0.5 | 0.5 | tak, bitowo (bity cache nie zmieniają numeryki) | nie (pomiar jest w komentarzu kodu) |
| 8 | Physics-floor check w weryfikatorze fabryki (czas kernela ≥ bajty/pasmo) | wszystkie | wiarygodność (KernelGuard/SOL-ExecBench) | 0.9 | 0.5 | wysoki | n/d | nie |
| 9 | Combine split-KV / ticket przez DSMEM w klastrze | 5060 Ti, 5090 | ≤1.5% LFM | 0.3 | 2.5 | 0.2 | zmiana kolejności? (do zachowania) | nie |
| 10 | TMA w GEMV | sm_120 | ~0 (cp.async już ~92%) | 0.1 | 5 | ~0 | — | nie robić |
| 11 | FP8/FP4 w decode, FP8 KV/atencja | Ada/Blackwell | 0 w decode; prefill tylko z NVFP4 | — | — | — | nie | nie robić |
| 12 | FA3/FA4/tcgen05/wgmma/DeepGEMM/TMA multicast | — | niedostępne na sm_120/86/89 | — | — | — | — | odrzucone |
| 13 | Sztuczki AQL/HIP graph na XTX | XTX | podłoga 2.08 µs | — | — | — | — | zmierzone (round4) |

Uwaga do kolejności: pozycje 1 i 5 są tanimi pomiarami, od których zależy wartość pozycji 2, 4, 6 i 9. Pozycje 2–4 są bitowo bezpieczne i nie wymagają bramki KLD.

---

## 5. Pięć najlepszych eksperymentów

Zasady bezpieczeństwa (18 §6.1, 17):
- XTX: jedno zadanie GPU naraz pod `flock`, `gpu-guard`, `GGML_HIP_PM4=0`;
- NVIDIA: lokalna 5060 Ti tylko po zgodzie, wynajem tylko z gotowym i przetestowanym na CPU pipeline’em (`lekcja-5060ti-bezczynna`);
- monitor temperatur VRAM, bez zmian limitów mocy i zegarów;
- buildy `nice -n 10 -j6`.

### E1 — PDL: trigger + prefetch przed czekaniem w MMVQ (5060 Ti lokalnie, $0; potem 5090 w E2)
- **Krok 0 (20 min):** `GGML_CUDA_PDL=0` vs `1` (przełącznik istnieje, `common.cuh:1913-1916`), llama-bench tg128 `-r 5`, 3 rundy ABBA, LFM Q4_K_M i Qwen Q3_K_XL. To mierzy, ile PDL daje dziś (nigdy u nas nie mierzone; X6 z 15a niewykonany).
- **Krok 1:** gałąź od `cuda-compat`. W `mul_mat_vec_q` dla `ids == nullptr` i bez `shared_expert`:
  - `ggml_cuda_pdl_lc()` na starcie;
  - `prefetch.global.L2` linii wag pierwszych 2 iteracji przed `ggml_cuda_pdl_sync()`;
  - wariant B: ładowanie pierwszej iteracji do rejestrów.
  - Przełącznik `GGML_CUDA_MMVQ_PREWAIT=0/1/2`.
- **Pomiar:** ABBA tg128 + spec_sweep `lfm none` i Qwen MTP n=3. nsys bez `--cuda-graph-trace=node`, tylko do potwierdzenia kierunku.
- **Poprawność:** test-backend-ops `MUL_MAT`, `MUL_MAT_ID` z PDL=1, greedy md5 bez zmian (zmiana z definicji nie dotyka numeryki), soak 4 min.
- **Kill:** < +1.5% LFM tg128 na 5060 Ti przy krok 0 ≥ +3%, albo jakakolwiek różnica md5. Jeśli krok 0 daje < +2%, przenieść całość na 5090 (E2).

### E2 — Pierwsza kampania RTX 4090 + 5090 (Vast, ~$1–2)
- Zestaw jak kampania 2026-10-16 (`BENCHMARKI-NVIDIA-2026-10-16.md` §metoda): A0 upstream, A1 flagi, nasz fork; Qwen Q4_K_XL (24/32 GB), LFM Q4_K_M i Q5_K_M.
- Do tego:
  - (i) `GGML_CUDA_PDL=0/1` (tylko 5090);
  - (ii) % pasma = bajty z GGUF / czas;
  - (iii) nsys: suma przerw między kernelami / token;
  - (iv) binarka z E1 na 5090.
- **Hipoteza (§3.1):** 5090 LFM ≤ 48% pasma, 4090 ≤ 55%.
- **Decyzja:** jeśli 5090 LFM ≥ 60% pasma, pozycje 2, 6 i 9 spadają w rankingu. Jeśli ≤ 48%, trwały blok MoE na CUDA (15a C) staje się pozycją nr 1 dla 5090.

### E3 — L2 persisting window dla LFM (5060 Ti lokalnie, potem 4090/5090 w E2)
- Zapytać `persistingL2CacheMaxSize` i `accessPolicyWindowMaxSize` na każdej karcie (sekundy).
- W backendzie CUDA przy tworzeniu strumienia, przed przechwyceniem grafu:
  - `cudaLimitPersistingL2CacheSize = max`;
  - okno na bufor głowy `token_embd`, `hitRatio = setaside/215 MB`;
  - przełącznik `GGML_CUDA_L2_PERSIST=MB`.
- Sprawdzić, czy atrybut strumienia trafia do węzłów grafu `[NIEZWERYFIKOWANE]`; jeśli nie, ustawić `cudaKernelNodeAttributeAccessPolicyWindow`.
- **Pomiar:** tg128 ABBA przy d0 i d32k (żeby złapać koszt dla FA), Qwen MTP spec_sweep z oknem na `blk.64`.
- **Kill:** < +0.7% LFM d0 na 4090/5090 albo regresja przy d32k > 0.5%.

### E4 — Prefetch L2 w pętli MMVQ dla weryfikacji (5060 Ti lokalnie; 3090 przy następnym wynajmie)
- Zmiana: warunek `__CUDA_ARCH__ == GGML_CUDA_CC_DGX_SPARK` (`mmvq.cu:1703`) zamieniony na przełącznik kompilacji/env dla sm_86/sm_89/sm_120, tylko dla `ncols_dst ≥ 2`.
- **Pomiar:** `test-backend-ops -o MUL_MAT perf` dla ne11 = 1..8 i typów Q3_K/Q4_K/Q5_K/Q6_K/IQ4_XS, potem spec_sweep Qwen MTP ABBA.
- Odniesienie upstream (GB10, ne11=5, „branchless + prefetch” vs base): Q4_K +2.89%, Q5_K +3.90%, Q6_K +6.19% (https://github.com/ggml-org/llama.cpp/pull/26705#issuecomment-5569335031).
- **Kill:** < +1% spec_sweep albo jakakolwiek regresja ne11=1 (wtedy ne11=1 zostawić bez prefetchu).

### E5 — Koszt granicy na Ampere/Ada i bariera trwałej siatki bez PM4 na XTX ($0.5 + lokalne XTX)
- **NVIDIA (X5 z 15a):** port `~/wt/lfm4-prof/boundary.cpp` na CUDA: łańcuch N kerneli (pusty / copy2k / matvec Q5_K 2048²) w grafie CUDA na 3090 i 4090 oraz trwały łańcuch cooperative z flagami. Metryka (T(1000) − T(200))/800.
  - **Kill** trwałego kernela na NVIDIA: granica ≤ 0.8 µs i pula (wall − strumień) < 20%.
- **XTX (tylko jeśli Pm4Fix nie zabezpieczy PM4):** mikrobench trwałej siatki (96 bloków × 512) z dynamicznym indeksem zadań i bounded spin, łańcuch gate+up → down LFM w kształcie produkcyjnym, normalna kolejka AQL.
  - **Kill:** oszczędność < 1.5 µs na granicę wobec HIP graph albo jakiekolwiek wygaśnięcie spinu przy 10⁵ replayach z równolegle działającym kompozytorem.

---

## 6. Zasoby do nauki dla zespołu (kolejność czytania)

**Rdzeń, batch 1 i bajty/token:**
1. kipply, Transformer Inference Arithmetic — https://kipply.github.io/blog/transformer-inference-arithmetic/ (bajty wag i KV na token; to nasz podstawowy rachunek).
2. How to Scale Your Model: Inference — https://jax-ml.github.io/scaling-book/inference/
3. Roofline (Williams i in.) — https://users.cs.duke.edu/~lkw34/papers/roofline-cacm2008.pdf; Volkov SC08 (latencja i ILP zamiast occupancy) — https://mc.stanford.edu/cgi-bin/images/6/65/SC08_Volkov_GPU.pdf. Volkov to najlepsze źródło do problemu „85% w `s_waitcnt vmcnt`”.
4. Online softmax — https://arxiv.org/abs/1805.02867; FlashAttention-2 (podział pracy) — https://arxiv.org/abs/2307.08691
5. Thinking Machines, batch-invariance — https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/ (podstawa naszego trybu bit-exact, 12).

**Kernele i praktyka (NVIDIA):**
6. siboehm, CUDA MMM — https://siboehm.com/articles/22/CUDA-MMM; Gordić, Inside NVIDIA GPUs — https://www.aleksagordic.com/blog/matmul
7. CUDA PG: PDL — https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/programmatic-dependent-launch.html; L2 control — https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/l2-cache-control.html
8. CUTLASS SM120 (czego GeForce nie ma) — https://docs.nvidia.com/cutlass/latest/media/docs/cpp/blackwell_functionality.html#blackwell-sm120-gemms
9. Nsight Compute Profiling Guide — https://docs.nvidia.com/nsight-compute/ProfilingGuide/; Compute Sanitizer — https://docs.nvidia.com/compute-sanitizer/ComputeSanitizer/
10. GPU MODE lectures — https://github.com/gpu-mode/lectures

**AMD/RDNA3 (luka listy wafer; dodaję spoza niej):**
11. AMD RDNA3 ISA Reference Guide (gfx11) — https://www.amd.com/content/dam/amd/en/documents/radeon-tech-docs/instruction-set-architectures/rdna3-shader-instruction-set-architecture-feb-2023_0.pdf `[link nie otwierany w tej sesji]`
12. LLVM AMDGPU memory model dla gfx10/gfx11 (GLC/DLC, `buffer_gl*_inv`) — https://llvm.org/docs/AMDGPUUsage.html#memory-model-gfx10-gfx11 (potrzebne do każdego hand-offu przez pamięć, 15a §4.4).
13. Nasze: `wiki/rocm/pm4.md`, `hip-graph-narzut.md`, `lekcja-handoff-rdna3.md`, `att-gfx1100` (16g), `lfm-decode-round4.md` §1.
14. HIP hardware implementation — https://rocm.docs.amd.com/projects/HIP/en/latest/understand/hardware_implementation.html. Czytać ze świadomością, że opisuje CDNA.

**Megakernele / dataflow:**
15. Hazy „No Bubbles” — https://hazyresearch.stanford.edu/blog/2025-05-27-no-bubbles; MPK — https://arxiv.org/abs/2512.22219; vLLM MonoKernel RFC — https://github.com/vllm-project/vllm/issues/60904 (omówione w 15a).

**Weryfikacja kerneli pisanych przez agentów:**
16. KernelBench-Verified — https://arxiv.org/html/2607.16241; SOL-ExecBench — https://github.com/nvidia/sol-execbench; KernelGuard — https://icml.cc/virtual/2026/67922

**Praktyczne notatki o sm_120 (z zastrzeżeniami):**
17. kekzl/imp `docs/sm120.md` — https://github.com/kekzl/imp/blob/1e4fad60bd9b8c5da7c0489a40a6ff44cc605614/docs/sm120.md. Lista „co nie ruszyło decode” (FP8 scores, warp specialization, TMA dla KV) jest cenna; „L2 persistence for KV: measurable” jest bez liczby.
18. fengwang RTX 5090 guide — https://github.com/fengwang/ncu-report-skill-rtx-5090/blob/main/blackwell-cuda-programming.md. Dobra tabela zasobów; błędna teza „FP4 library-only” (§1.2).

Pomijalne dla nas: dział 5 (distributed), TPU/Trainium, Gateway API/llm-d, NCCL, DeepEP/EPLB, tcgen05 for dummies (B200), DeepGEMM (Hopper).

---

## 7. Źródła (zebrane)
- wafer-ai README: https://github.com/wafer-ai/gpu-perf-engineering-resources (sekcje 1–6, Frontier, Source policy).
- Blackwell Tuning Guide 13.4: https://docs.nvidia.com/cuda/blackwell-tuning-guide/ (§1.4.1.1 occupancy, §1.4.1.2 klastry, §1.4.2.2 L2, §1.4.2.3 carveout).
- NVIDIA RTX Blackwell whitepaper v1.1, tab. 1 (SM, pasmo, L2 dla 3090/4090/5090): https://images.nvidia.com/aem-dam/Solutions/geforce/blackwell/nvidia-rtx-blackwell-gpu-architecture.pdf
- 5060 Ti (32 MB L2, 448 GB/s): https://en.wikipedia.org/wiki/GeForce_RTX_50_series (tabela specyfikacji, za TechPowerUp).
- CUTLASS SM120: https://docs.nvidia.com/cutlass/latest/media/docs/cpp/blackwell_functionality.html
- CUDA PG PDL / L2: linki w §6, poz. 7.
- llama.cpp PR #26705, komentarz z danymi prefetchu: https://github.com/ggml-org/llama.cpp/pull/26705#issuecomment-5569335031; PDL #22522 (za 15a).
- Stream-K: https://arxiv.org/abs/2301.03598; NVFP4: https://developer.nvidia.com/blog/introducing-nvfp4-for-efficient-and-accurate-low-precision-inference/
- Kod (`~/wt/topka`, `eb7509cb9`):
  - `ggml/src/ggml-cuda/mmvq.cu:30-34,55-57,197-231,345-350,1480,1530,1703-1721,1954,1980,3260`;
  - `common.cuh:124-142,1825-1826,1913-1916`;
  - `fattn-common.cuh:1155-1235,1278-1322`;
  - `mmq.cuh:173,346`;
  - `mma.cuh:1276-1286`;
  - `ggml-cuda.cu:5917`.
- Nasze raporty:
  - 15a §1, §3, §4;
  - 16a §1–3;
  - 16c TL;DR;
  - 16g §1–2;
  - 17 §0 (17:8-26);
  - 18 §3.1–3.5, §4;
  - `qwen-opt/research/lfm-decode-round4.md:26-55`;
  - `wiki/rocm/hip-graph-narzut.md:14-16`;
  - `wiki/nvidia/sm-86-89-120.md:20-24`;
  - `wiki/nvidia/nvfp4.md:18-25`;
  - `wiki/metody/wyniki-negatywne.md:13-17`;
  - `wiki/kernele/wmma-small-n.md:10-17`;
  - `BENCHMARKI-PRZED-PO-2026-10-19.md:17,96-99`.

---

## Do bazy wiedzy

| folder | tytuł (plik) | streszczenie | kluczowe liczby (źródło) |
|---|---|---|---|
| research | Raport 21b: zasoby GPU perf + Blackwell TG (`raport-21b-gpu-perf-zasoby.md`) | Mapa technik z listy wafer-ai i Blackwell TG na XTX/RTX; większość już mamy albo zmierzyliśmy negatywnie; nowe: PDL trigger/prefetch w MMVQ, L2 persist, prefetch MMVQ 2–8 kol., kampania 5090 | ranking §4; E1–E5 §5 |
| nvidia | sm_120 czego nie ma (`sm-120-braki.md` lub aktualizacja `sm-86-89-120.md`) | Brak tcgen05/TMEM/wgmma/2-CTA/multicast; CUTLASS GEMM klaster 1×1×1; 48 warpów/SM, 128 KB shared/SM, 99 KB/blok; FP4 `mma.sync` jest (sm_120a) | Blackwell TG §1.4.1.1; CUTLASS SM120; `mma.cuh:1276-1286` |
| nvidia | Karty NVIDIA: pasmo/L2/SM (`karty-nvidia-parametry.md`) | 3090 936/6 MB/82; 4090 1008/72 MB/128; 5060 Ti 448/32 MB/36; 5090 1792/96 MB/170 (persist ≤ 60 MB) | whitepaper tab. 1; Wikipedia RTX 50; fengwang |
| kernele | PDL w MMVQ tylko w połowie (`pdl-mmvq-trigger.md`) | Gęsty `mul_mat_vec_q` ma `pdl_sync` przed odczytem wag i brak triggera, więc PDL nie ukrywa rampy wag | `mmvq.cu:1530`, `:1980`; CUDA PG 4.5; szac. 5060 Ti LFM +1.1–4.6%, 5090 +2.5–11% (21b §3.2) |
| nvidia | L2 persisting window (`l2-persist.md`) | API i rachunek: przypinać dane czytane co token (głowa LFM 215 MB, blok MTP); strumień wag nie trafia | 5090 +1.7%, 4090 +2%, 5060 Ti +1.1%, 3090 0 (21b §3.3) |
| kernele | Prefetch L2 w MMVQ tylko na DGX Spark (`mmvq-prefetch-l2.md`) | Upstream GB10 przy ne11=5: Q4_K +2.9%, Q5_K +3.9%, Q6_K +6.2%; ne11=1 ≈ 0; teza o kartach z większym pasmem bez danych | PR #26705 komentarz 5569335031; `mmvq.cu:30-34,1703-1721` |
| research | Projekcja RTX 5090 (`2026-10-19-projekcja-5090.md`) | Stały narzut kerneli z 5060 Ti daje na 5090 LFM tylko 37–48% pasma; tam narzut = 40–63% tokenu | LFM 435–571 t/s, Qwen plain 69–76 t/s `[SZACUNEK]` (21b §3.1) |
| rocm | XTX bez PM4: trwała siatka bije HIP graph (`trwala-siatka-bez-pm4.md`) | Podłoga AQL 2.08 µs, HIP graph 2.75, bariera siatki 0.48–0.77 µs; bez PM4 trwały blok MoE to jedyna bezstratna droga do −12% LFM | round4:30-50; 17:24; szac. +8–10% LFM vs PM4-off (21b §3.4) |
| lekcje | Little’s law dla GEMV (`lekcja-littles-law-gemv.md`) | Każda karta potrzebuje ~5–8 KB w locie na SM/CU; TMA niepotrzebne, liczy się liczba ładowań w locie | 21b §1.3 (założenie 600 ns); 16g §1 (85% `s_waitcnt vmcnt`) |
| metody | Physics-floor check w fabryce (`physics-floor-check.md`) | Każdy czas kernela porównać z bajtami/pasmem; wynik ponad peak = błąd pomiaru (KernelGuard, SOL-ExecBench) | `wyniki-negatywne.md:17` (1075 GB/s = 112%); 21b §4 #8 |
| research | Lista wafer-ai: ocena (`wafer-gpu-perf-lista.md`) | Dobry spis lektur; dział AMD tylko CDNA, brak RDNA3 i batch 1; opis Blackwell TG („tensor memory”) niezgodny z treścią | 21b §1.1, §6 |
