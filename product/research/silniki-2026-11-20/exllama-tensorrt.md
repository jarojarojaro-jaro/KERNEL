# ExLlamaV3 i TensorRT-LLM: co z nich wziąć do Turbo (2026-11-20)

Skróty ścieżek:
- `ex3/` = `~/research/engines/exllamav3/`;
- `ext/` = `ex3/exllamav3/exllamav3_ext/`;
- `trt/` = `~/research/engines/TensorRT-LLM/`;
- `KB/` = `~/KERNEL/`.

Notatka dopisuje tylko to, czego nie ma w bazie wiedzy (KB). W KB są już: EXL3/QTIP jako format i jakość/bajt (R15e, 32c), SASS `LDG.E.EF` w exl3 (23c), issue #543 w skrócie (68a), PM4/PDL na XTX (15a, 16a), prefetch do MALL (16a, KILL), block verification (18 #10), DFlash2 (32f).

## 1. Co to jest

- **ExLlamaV3** v1.6.7, commit `8c593e4` (2026-11-13), `ex3/exllamav3/version.py`. Biblioteka Python + rozszerzenie C++/CUDA (HIP dla ROCm) z własnym formatem EXL3 (trellis QTIP, Hadamard 128 po obu stronach macierzy). Dla nas to wzorzec kerneli GEMV/GEMM dla małego M, przechwytywania grafów i spekulacji (MTP, DFlash2, n-gram/SAM).
- **TensorRT-LLM** 1.4.0rc5, commit `d55d8575` (2026-11-20), `trt/tensorrt_llm/version.py`. Silnik NVIDIA na PyTorch z ręcznymi kernelami CUDA/CuTe/Triton. Nie obsługuje AMD. Dla nas to wzorzec PDL, flash-decoding (XQA), spekulacji jednym silnikiem (MTP/EAGLE3/SA/PARD/DFlash), weryfikacji blokowej i rollbacku GDN przez „replay”.

## 2. Architektura

### ExLlamaV3
1. **Harmonogram.** `Generator` w Pythonie, ciągłe wsadowanie, stronicowany cache KV. Ścieżka dekodu modułów („BC”: attention, GDN, MLP) to jedno wywołanie C++ na moduł, przechwycone jako graf (`ex3/doc/env_vars.md:36-45,115-119`).
2. **Grafy.** Jeden graf na kształt (bsz, q_len). Przy odtworzeniu łatane są tylko wskaźniki i pozycje przez `cudaGraphExecKernelNodeSetParams` (`ext/graph.cuh:102-139`, `ext/graph.cu:248`). **Na ROCm grafy są domyślnie wyłączone** (`env_vars.md:24-34`): węzeł grafu HIP startuje nie szybciej niż zwykły kernel, a każdy exec rezerwuje 2 MB, które rosną z każdym łataniem.
3. **Kernele.** Ręczne CUDA/HIP dla matmul EXL3, GDN, norm i samplera. Triton dla atencji i skanu GDN w prefillu (fla). Na RDNA osobny katalog `ext/rocm/` z GEMV na `v_dot2_f32_f16` i GEMM na WMMA.
4. **Kwantyzacja.**
   - Dekod (≤ 144 wiersze): kernel GEMV/GEMM czyta trellis bez rozpakowywania do pamięci.
   - Prefill (> 144 wierszy): odtworzenie całej macierzy do fp16, potem hgemm (`ex3/exllamav3/modules/quant/exl3.py:10,140-142`).
   - Od 1024 wierszy oba Hadamardy są wliczone w kernel odtwarzania (`exl3.py:186-189`).
5. **KV.** Cache stronicowany, 2–8 bit (stratny). Stan rekurencji GDN trzymany jako punkty kontrolne w RAM i na dysku.
6. **Spekulacja.**
   - Model draftu, MTP (Qwen3.5/3.8: `architecture/qwen3_5_mtp.py`), DFlash/DFlash2, n-gram/SAM, „hybrid” (długie dopasowanie sufiksu nadpisuje draft).
   - Dynamiczna długość draftu z kalibracją online.
   - Rzadka głowica draftu (dynamiczny podzbiór słownika).
7. **AMD consumer.**
   - ROCm jest w głównym drzewie: tablice WMMA dla gfx1100/1101/1151 (`ext/rocm/wmma_gemm.cuh:13-19`).
   - Grafy na ROCm są wyłączone.
   - Na gfx1100 dekod był 10–19% wolniejszy niż w niezależnym porcie phoenixhaxor ([#543](https://github.com/turboderp-org/exllamav3/issues/543)). PR-y #547/#548/#549 z kernelami RDNA3 są **otwarte**, a #550 (residual do następnej normy) **zamknięty bez merge** (API GitHub, 2026-11-20).
   - Upstream ma własne „tiles core” RDNA (`ext/rocm/quant/exl3_gemv_tiles_rdna.cuh`).

### TensorRT-LLM
1. **Harmonogram.** PyExecutor z „overlap scheduler”: host przygotowuje krok n+1, gdy GPU liczy krok n. Spekulacja jest „one-model”: draft i cel są w jednym silniku i w jednym grafie CUDA (`trt/docs/source/features/speculative-decoding.md:355-361`).
2. **Grafy.** Grafy CUDA dla dekodu, z dopełnieniem do przechwyconych rozmiarów batcha. Osobne grafy dla wariantów próbkowania: greedy, tylko temperatura, pełne (`speculative-decoding.md:475-485`). Strumień dekodu ma najwyższy priorytet przy ≤ 256 tokenach na krok (`trt/tensorrt_llm/_torch/utils.py:68-77`).
3. **PDL.** Włączone domyślnie od sm90 (`trt/cpp/tensorrt_llm/common/envUtils.cpp:235-250`). 112 plików kerneli ma `griddepcontrol` albo `cudaGridDependencySynchronize`.
4. **Kernele.** Atencja dekodu to XQA (`trt/cpp/kernels/xqa/mha.cu`). Są osobne „min-latency” GEMV/GEMM dla małego M (`trt/cpp/tensorrt_llm/kernels/dsv3MinLatencyKernels/`, `llama4MinLatencyKernels/`), a do tego fuzje AR+norm+quant i QK-norm+RoPE.
5. **Kwantyzacja.** FP8/NVFP4/W4A16 dla nowych kart NVIDIA; nic dla nas.
6. **Spekulacja.**
   - Metody: MTP (vanilla i MTP-Eagle), EAGLE3 (także dynamiczne drzewo), PARD, DFlash, DSpark, SA (automat sufiksowy na GPU), n-gram (wycofywany).
   - Weryfikacja: ścisła, blokowa (Sun i in. 2024) albo „relaxed” (stratna).
   - SpeculationGate wyłącza spekulację, gdy akceptacja spada.
7. **Hybrydy GDN (Qwen3.5/3.8).**
   - Stan GDN fp32/bf16/fp16 do wyboru (`trt/docs/source/deployment-guide/deployment-guide-for-qwen3.8-qwen3.5-on-trtllm.md:35`).
   - Rollback po weryfikacji przez „GDN replay” (`trt/tensorrt_llm/_torch/modules/fla/cached_replay.py`).
   - Replay jest niezgodny z dynamicznym drzewem (`fla/cache_manager.py:799-800`).

## 3. Techniki z liczbami

### 3.1 GEMV EXL3 dla małego M (dekod i weryfikacja)

| Co | Liczba / fakt | Źródło |
|---|---|---|
| CUDA: GEMV oparty na **tensor-core MMA m16n8k16 nawet przy m = 1**; ten sam kernel dla m 2..8 (MMODE 1) | koszt prawie płaski w m `[INFERENCE]` | `ext/quant/exl3_gemv_kernel.cuh:13,20-22,30` |
| Warpy dzielą K i nie robią barier w pętli głównej; wagi idą wprost do rejestrów przez `__ldcs` (evict-first) z pierścieniem prefetchu | PF = 4 (512 wątków, 16 podziałów K) albo 2 (256 wątków, 8 podziałów K) | `exl3_gemv_kernel.cuh:6-8,206-209,305-311` |
| Akumulacja fp16 w MMA, co FOLD kroków składana do fp32 | FOLD 4 / 2 | `exl3_gemv_kernel.cuh:13-14,414-425` |
| Kara za zbyt wiele VGPR: 81–85 rejestrów daje 1 blok/SM zamiast 2 | −18…−28% na kształtach projekcji atencji (3090) | `exl3_gemv_kernel.cuh:191-194` |
| Hadamard wejścia, GEMV i Hadamard wyjścia w **jednym kernelu kooperacyjnym** z 2 × `grid.sync` | 1 launch zamiast 3 | `exl3_gemv_kernel.cuh:16-18,222-239,468-495` |
| Wariant int8: aktywacje int8 + dp4a; tryb „residual” liczy drugi dp4a na błędzie zaokrąglenia | ~15–16 bitów efektywnej precyzji aktywacji | `ext/quant/exl3_gemv_int8_kernel.cuh:20-30`; `env_vars.md:277-283` |
| RDNA: kooperacyjny launch zastąpiony 3 zwykłymi (transformacje osobno, potem wliczone w prolog/epilog kernela) | — | `ext/rocm/quant/exl3_gemv_rdna.cu:8-17`; `exl3_gemv_kernel_rdna.cuh:603-615` |
| RDNA: **GEMV dekodu jest ograniczony przez VALU, nie DRAM**. `v_mul_lo_u32` idzie z ¼ szybkości, `v_dot4` z ½, więc zastąpiono je pełnoszybkościowymi `v_pk_mul_lo_u16` + `v_mad_u32_u16`, `v_sad_u8`/`v_sad_hi_u8`, `v_alignbit` | wynik bit w bit jak stary rdzeń | `ext/rocm/quant/exl3_gemv_tiles_rdna.cuh:13-47` |
| RDNA: adresowanie przez SGPR (baza jednolita dla fali, `global_load v, vOff, s[base] offset:imm`, licznik pętli skalarny) | zero VALU na adresy w kafelku | `exl3_gemv_tiles_rdna.cuh:42-47` |
| RDNA: split-K wewnątrz bloku dla wąskich wyjść | 3072→1024 to tylko 64 fale w 8 blokach na 80 SIMD | `exl3_gemv_kernel_rdna.cuh:480-499` |
| RDNA: grid zwykłego launchu z programową barierą urządzenia. API zajętości bywa błędne (gfx1150) i wtedy jest zakleszczenie | limit 1 blok/WGP | `ext/quant/exl3_gemm.cu:335-346`; `env_vars.md:327-336` |
| Port phoenixhaxor na XTX: pasmo GEMV dla wag 4-bit | **700–770 GB/s przy 1 wierszu**, 450–530 przy 8 (VALU); 8 wierszy kosztuje 1,4× tyle co 1 | [README](https://github.com/phoenixhaxor/exllamav3-rocm) |
| Turbo dla porównania | ~89% pasma (~855 GB/s), weryfikacja N = 8: 1,45× N = 1 | `CONTEXT.md`, `COLLAB.md:120` |

### 3.2 Prefill w ExLlamaV3

| Co | Liczba | Źródło |
|---|---|---|
| Powyżej 144 wierszy: odtworzenie wag do fp16, potem hgemm | próg 144 | `exl3.py:10,140-142` |
| Hadamardy wliczone w kernel odtwarzania (od 1024 wierszy) | samodzielne Hadamardy brały ~14% czasu GPU prefillu; zysk +6–7% prefillu | `env_vars.md:308-321`; `exl3.py:186-189` |
| RDNA: rocBLAS/hipBLASLt nie mają WMMA dla fp16×fp16→**fp32**. ExLlamaV3 dołącza `rocm_wmma_gemm` (MIT), a port phoenixhaxor wybiera wyjście fp16 + kopię poszerzającą | ~16 vs ~80 TFLOPS; prefill ×2,3 | `ext/rocm/wmma_gemm.cuh:1-19`; `ext/hgemm.cu:72-78`; [README phoenixhaxor](https://github.com/phoenixhaxor/exllamav3-rocm) |
| Prefill Qwen3.8-27B EXL3 3,5 bpw na XTX (port phoenixhaxor) | **~1180–1200 t/s przy 32K**, ~1090 przy 64K, ~945 przy 99K | [README](https://github.com/phoenixhaxor/exllamav3-rocm) |
| Turbo dla porównania | 844 t/s (2k), 818 (4k); GEMM ~80% czasu, epilog skal Q4_K ~18% GEMM | `CONTEXT.md`; `COLLAB.md:181` |
| Skan GDN w prefillu dzielony na pod-zakresy | 2048 najszybsze, 1024 kosztuje ~40% więcej; wynik bit w bit | `env_vars.md:121-129` |

### 3.3 Narzut launchy i grafy

| Co | Liczba | Źródło |
|---|---|---|
| Grafy CUDA w ExLlamaV3 | „kilka procent” szybciej w dekodzie | `env_vars.md:29` |
| Grafy HIP w ExLlamaV3 | zysk w szumie; 2 MB na exec rośnie z każdym łataniem, przy setkach execów spekulacji to >1 GB VRAM | `env_vars.md:29-33`; komentarz turboderpa w [#543](https://github.com/turboderp-org/exllamav3/issues/543) |
| Port phoenixhaxor: koszt dispatchu na XTX | **~3,3 µs na kernel**, niezależnie od `HIP_FORCE_DEV_KERNARG`, `GPU_MAX_HW_QUEUES`; każde `hipGraphLaunch` dokłada ~8 µs bezczynności; grafy wyłączone dla mlp/gdn: +0,5% | [README](https://github.com/phoenixhaxor/exllamav3-rocm) |
| Port phoenixhaxor: `grid.sync` (cooperative launch) na ROCm | +10–20 µs na launch; zastąpione atomową barierą epokową | tamże |
| Fuzje zmniejszające liczbę launchy (SelfRef, XTX, Qwen3.8-27B + DFlash2) | 66,8k → 51,1k kerneli na generację daje −1,7% czasu rundy; residual do następnej normy −0,4…−0,8% | [#543](https://github.com/turboderp-org/exllamav3/issues/543) |
| `EXL3_HC_FOLD` domyślnie włączony tylko na ROCm, bo „koszt launchu dominuje małe kernele” | 2 launche mniej na miejsce, bit w bit | `env_vars.md:20,87-95` |
| TRT: PDL na DeepSeek-R1, 8×B200, min-latency | 168 → 173 TPS/użytkownika (+3%) | `trt/docs/source/blogs/tech_blog/blog01_*.md:132-133` |
| TRT: Fuse_A_GEMM ładuje większość wag do SMEM przed czekaniem PDL (nakłada się na AllReduce) | duży zysk przy < 16 tokenach (wykres bez liczb) | `blog01_*.md:232` |
| TRT: GEMV per-warp llama4 robi `prefetch.global.L2` wag **przed** `cudaGridDependencySynchronize()`, a trigger daje na końcu | wzorzec | `trt/cpp/tensorrt_llm/kernels/llama4MinLatencyKernels/llama4Fp8Bf16GemmPerWarpTemplate.cuh:64-94,266` |
| TRT: dsv3 FusedAGemm daje sync i trigger zaraz po inicjacji barier SMEM | wzorzec „tylko prolog” | `dsv3MinLatencyKernels/dsv3FusedAGemm.cu:619-622,680-682` |
| TRT: PDL powodował prawdziwe błędy i NaN (TinyGEMM, quant, FMHA, dsv3 MoE, Qwen3-235B); są obejścia per kernel | ryzyko | `trt/.claude/skills/perf-optimization-casebook/references/runtime-execution/pdl.md:32` |
| llama.cpp PDL (sm120 RTX PRO 6000) | qwen35 27B Q4_K_M tg **+2–3%**, qwen35moe +10–22%; DGX Spark +2%; trigger w `mul_mat_vec_q` szkodzi | [PR #22522](https://github.com/ggml-org/llama.cpp/pull/22522) |
| Łańcuch kerneli z PDL vs trwały megakernel | +2,7% (PDL) vs +18,9% (bez PDL) | [blog Qiang](https://tie-pilot-qxw.github.io/blog/reconstructing-a-megakernel-with-pdl) |
| PDL istnieje tylko od sm90 | z naszych kart tylko 5060 Ti (sm120); 3090 (sm86) i 4080S (sm89) nie mają PDL | `envUtils.cpp:243`; PR #22522 („does not include Ada”) |

### 3.4 Atencja dekodu (flash-decoding)

| Co | Liczba | Źródło |
|---|---|---|
| XQA: liczba kawałków sekwencji | `min(max(1, SM / (batch × kv_heads)), ceil(seq / ctaTile))` | `trt/cpp/kernels/xqa/mha.cu:2851-2867` |
| XQA: scalanie robi **ostatni CTA** (`atom.acq_rel.inc` z zawijaniem, licznik sam się zeruje); bez osobnego kernela combine | — | `mha.cu:2656-2672` |
| XQA: przepustowość Llama-70B H200 | 1227 → 2941 tok/s/GPU (×2,4) | `trt/docs/source/blogs/XQA-kernel.md` |
| Port phoenixhaxor: atencja HIP (q_len 1: `v_dot2`, lane na token; q_len 2–8: WMMA na cache 8-bit, K/V raz na głowę kv w LDS) | 32K: ~10 → ~2,7 ms/token; weryfikacja 100K: ~45 → ~14 ms/rundę | [README](https://github.com/phoenixhaxor/exllamav3-rocm) |

### 3.5 Spekulacja

| Co | Liczba / fakt | Źródło |
|---|---|---|
| ExLlamaV3: **kalibrowane cięcie draftu**. Wynik pewności draftu jest mapowany online (koszyki, zanik 0,995, burn-in 64) na zaobserwowaną akceptację; łańcuch MTP/AR staje, gdy iloczyn warunkowych szans < cel | cel domyślny 0,4 | `ex3/exllamav3/generator/draft_confidence.py:5-19`; `generator.py:156-170` |
| ExLlamaV3: **rzadka głowica draftu**. Kolumny lm_head najczęstszych tokenów z bieżących liczników (przebudowa co 128 tokenów, histereza 0,25), zapisywane między sesjami per tokenizer; włączana tylko, gdy odsetek „chybień poza zbiorem” < 2 × oszczędność / czas rundy; co 128 rund próba przez pełną głowicę | weryfikacja zawsze pełną głowicą, więc bezstratne | `ex3/exllamav3/modules/sparse_head.py:1-25,61-80`; `ext/sparse_head.cu:1-9` |
| ExLlamaV3: hybrid suffix draft (długie dopasowanie w kontekście nadpisuje draft) | — | `generator.py:137-145` |
| ExLlamaV3 na 3090 (turboderp) | DFlash2 166, MTP-4 129, **MTP-7 157** t/s | `KB/product/research/63a-silniki-lokalne.md:56,227` |
| Port phoenixhaxor na XTX (Qwen3.8-27B 3,5 bpw) | bez draftu 38,5, MTP 108, **DFlash2 157 t/s** (2K); 147 (32K); 107 (99K) | [README](https://github.com/phoenixhaxor/exllamav3-rocm) |
| Port phoenixhaxor, wyniki negatywne | dynamiczna długość draftu i głowica „hot-token” wolniejsze e2e (DFlash2); rollback GDN przez replay wolniejszy niż zapis historii | tamże, „Tried and dropped” |
| TRT: liczba warstw MTP na DSR1 (B200) | 111 / 198 / 250 / **253** / 245 / 239 TPS dla 0–5; optimum 3 | `blog01_*.md:151-158` |
| TRT: relaxed acceptance | +8–9% przy akceptacji 2,82 → 3,10; **stratne** | `blog01_*.md:163-173` |
| TRT: Qwen3.8 MoE, GB300 TP16, konkurencja 1 | 133,5 → 383 tok/s/użytkownika z MTP3 przy **sztucznej** akceptacji 2,3 | `deployment-guide-for-qwen3.8-qwen3.5-on-trtllm.md:56-63` |
| TRT: **block verification** (Sun i in. 2024): bezstratna, przyjmuje ≥ tyle co weryfikacja tokenowa; bez synchronizacji hosta, mieści się w grafie | gotowa implementacja referencyjna | `trt/tensorrt_llm/_torch/speculative/block_verification.py:1-25` |
| TRT: SA, automat sufiksowy na GPU w bocznym strumieniu; nadpisuje draft MTP/EAGLE przy dopasowaniu ≥ 4 | — | `speculative/sa_enhancer.py:15-45`; `speculative-decoding.md:312-345` |
| TRT: n-gram | średnia przyjęta długość 1,37 (czat), 1,66 (druga tura), >4 (tłumaczenie) | `blog07_*.md:8-10` |
| TRT: „draft row picking”: warstwa draftu liczy atencję (zapis KV) na wszystkich wierszach, a normy i MLP tylko na wierszu, który czyta draft | — | `speculative-decoding.md:526-538` |
| TRT: **GDN replay**. Stały punkt kontrolny stanu + historia ≤ max(16, tokeny/krok) wektorów aktualizacji (u, k, skumulowany log-zanik); każdy krok weryfikacji liczy tylko T nowych aktualizacji; stan jest zapisywany przy „commit”, a nie w każdym kroku | — | `fla/cached_replay.py:116-123`; `fla/cache_manager.py:57,303-327` |
| TRT: L2 prefetch ekspertów z bocznego strumienia, bo „DRAM stoi przez większość łańcucha zależności warstwy” | — | `trt/tensorrt_llm/_torch/modules/expert_l2_prefetch.py:1-15` |

## 4. Co bierzemy do Turbo (ranking)

Liczby Turbo: dekod 21,8 ms/token (GEMV 18,9; przerwy 2,47; GDN 0,47; norma 0,79), weryfikacja N = 1/4/8: 21,7/26,4/31,95 ms, prefill 844 t/s (`CONTEXT.md`, `COLLAB.md:120,142,324`).

| # | Co | Skąd | Gdzie w Turbo | Zysk (szacunek) | Koszt | Ryzyko bezstratności |
|---|---|---|---|---|---|---|
| 1 | **Prefill przez odtworzenie wag do fp16 + GEMM fp16 na WMMA z wyjściem fp16** (lub vendorowany `rocm_wmma_gemm` dla fp32). Działa przy kawałkach ≥ 1024 tokenów; ≤ 144 zostaje obecny GEMM int8. Odtwarzanie macierz po macierzy do bufora ~200 MB (największa ffn 5120×17408 fp16 = 178 MB) | ExLlamaV3 `exl3.py:140-189`, `rocm/wmma_gemm.cuh`; phoenixhaxor 1180–1200 t/s @32K na tym samym modelu i karcie | nowa ścieżka obok `k_gemm_wmma`/`k_gemm_lds` w `src/gpu/gpu_forward.hip`, wybierana w pętli prefillu po liczbie tokenów | **+15–30% prefillu** (844 → ~1000–1100 t/s) `[INFERENCE]`. Rachunek: na RDNA3 iu8 i f16 WMMA mają ten sam szczyt (~123 T); dziś GEMM ~55 TOPS z epilogiem skal Q4_K (~18%); fp16 GEMM ~80 TFLOPS (phoenixhaxor); odtwarzanie ≈ 15,5 GB odczytu + 54 GB zapisu na kawałek ≈ 70 ms, czyli ~4–7% przy kawałku 2–4k | 3–4 dni | brak dla reguły spec == plain (prefill nie jest na ścieżce weryfikacji); zmienia bity prefillu względem dziś (aktywacje fp16 zamiast q8, czyli dokładniej); trzeba sprawdzić przepełnienie fp16 aktywacji Qwena (ExLlamaV3 jedzie na fp16, więc raczej OK `[INFERENCE]`) |
| 2 | **Taśma PM4 dla grafu dekodu** (z naszego forka llama.cpp `hip-pm4.cu`). ExLlamaV3 i phoenixhaxor niezależnie potwierdzają, że grafy HIP nic nie dają, a dispatch AQL ma podłogę ~3,3 µs; Turbo zmierzyło, że pokrętła env nic nie dają (`COLLAB.md:139`) | KB `qwen-opt/research/lfm-decode-round4.md:24-44` (granica 2,75 → 0,46–0,86 µs); produkcja z PM4 +6,4% (`KB/wiki/REKORDY.md:27`) | wymiana `hipGraphLaunch` na odtwarzanie taśmy PM4 per (n, k) | 541 × ~1,9 µs ≈ 1,0 ms/token, czyli **+4–5% dekodu**, podobnie w kroku spec `[INFERENCE]` | 3–5 dni | brak dla liczb (ta sama kolejność kerneli); ryzyko sprzętowe: fault zamienia się w reset GPU (lekcja-pm4-zamienia-fault-w-reset, raport 17) |
| 3 | **Kalibrowane cięcie łańcucha MTP** zamiast stałego `TURBO_P_MIN` 0,5: mapowanie prawdopodobieństwa draftu na akceptację online, cięcie po iloczynie; potem test głębszych łańcuchów (K = 5–7) | ExLlamaV3 `draft_confidence.py`, `generator.py:156-170`; MTP-7 157 vs MTP-4 129 na 3090 | logika draftu MTP przy `TURBO_P_MIN` (host, ~110 linii) | **+3–8% spec T=0** na długich/kodowych tekstach `[INFERENCE]`; przy T=0,7 kalibracja jest odporniejsza od stałego progu | 1 dzień | brak: zmienia się tylko długość draftu, weryfikacja ta sama |
| 4 | **Dynamiczna głowica draftu**: podzbiór kolumn lm_head z liczników tokenów sesji (zapis między sesjami, histereza, bramka „chybienie poza zbiorem”) zamiast statycznego pliku 64k z llama.cpp | ExLlamaV3 `sparse_head.py:1-25` | `draft_head` + `TURBO_DRAFT_VOCAB` (`gpu_forward.hip:2223-2240`) | dziś głowica 64k to ~1/2 draftu (269 z 532 MB, `COLLAB.md:197`); przy 16–32k kolumnach z tą samą akceptacją krok spec −0,2…−0,4 ms (**+1–2%**); polski czat może mieć dużo tokenów spoza statycznych 64k `[INFERENCE]` | 1–2 dni | brak (weryfikacja pełną głowicą); kontra: phoenixhaxor zmierzył „hot-token head” wolniej dla DFlash2; Turbo zmierzyło spadek akceptacji przy statycznych 16–48k (`COLLAB.md:124,199`). Najpierw pomiar: odsetek tokenów wyjścia PL spoza pliku 64k |
| 5 | **Block verification przy T>0** zamiast/obok sprzężonego losowania | TRT `block_verification.py` (gotowy, w grafie) | weryfikacja przy T>0 | KB 18 #10: +3–6% przy T=1 `[SZACUNEK z KB]`; Turbo T=0,7 72 vs produkcja 92 | 2 dni | rozkład zachowany (dowód w artykule), ale tekst przy tym samym seedzie inny niż przy sprzężonym losowaniu; wymaga q z draftu, nie samego argmax |
| 6 | **GDN: leniwy commit stanu (replay TRT)**: punkt kontrolny + historia ≤ 16 wektorów u/k/g; zapis stanu S (151 MB) co ~16 tokenów zamiast co krok | TRT `fla/cached_replay.py`, `cache_manager.py:303-327` | `k_gdn*` i `accept` (dziś ping-pong + taśma, accept 0,35 ms, `COLLAB.md:125`) | zapis S ~0,15 ms/token mniej, accept prawie 0; **+0,5–1,5%** `[INFERENCE]` | 3–4 dni | wysokie: inna kolejność działań na stanie, więc dekod i weryfikacja muszą iść tą samą ścieżką replay, inaczej spec ≠ plain. Kontra: phoenixhaxor zmierzył replay wolniej (rekurencja ograniczona opóźnieniem) |
| 7 | **Flash-decoding: liczba kawałków z heurystyki XQA i scalanie w ostatnim bloku** (licznik `atomic inc` z zawijaniem) zamiast stałego S = 16 i osobnego `k_attn_comb` | TRT `mha.cu:2656-2672,2851-2867` | `k_attn_w`/`k_attn_comb` | −16 launchy/token (~80 µs) + mniej kawałków przy średnim kontekście: **+0,3–1%** `[INFERENCE]` | 1 dzień | trzeba zachować regułę „n_kv ≤ split_min → 1 kawałek” (`COLLAB.md:140`); kolejność scalania musi być stała |
| 8 | **Build NVIDIA**: PDL tylko na sm90+ (z naszych kart 5060 Ti). Sync przed pierwszym odczytem danych, wcześniej `prefetch.global.L2` wag; trigger wcześnie tylko w kernelach ograniczonych opóźnieniem (norma, quant), nie w MMVQ. Na 3090/4080S: grafy + fuzje. Dla GEMV CUDA wzorzec ExLlamaV3: MMA nawet przy m = 1, żeby weryfikacja ≤ 8 kosztowała tyle co dekod | TRT llama4 GEMV:64-94; PR #22522; `exl3_gemv_kernel.cuh` | przyszły port CUDA | +2–3% tg na sm120 (PR #22522: qwen35 27B) | 2–3 dni po porcie | PDL miał realne wyścigi w TRT; potrzebny test bit w bit z `PDL=0` |

**Nie bierzemy:**
- relaxed acceptance (stratne);
- emulacja PDL na XTX przez `hipExtAnyOrderLaunch`/flagi (16a: synchronizacja zjada 94% zysku; flaga ignorowana w grafach);
- prefetch do MALL (16a: KILL);
- `grid.sync` na ROCm (+10–20 µs/launch, phoenixhaxor);
- łatanie parametrów grafów HIP (wyciek 2 MB/exec);
- format EXL3 (reguła „nie zmieniamy wag”; do tego na RDNA3 GEMV trellis jest ograniczony przez VALU: 700–770 GB/s wobec naszych ~855);
- RMSNorm w prologu GEMV (Turbo zmierzyło −43%, `COLLAB.md:142`; phoenixhaxor: Hadamard w kernelu matmul to +13% VALU).

Fuzje elementwise w stylu #548 Turbo już ma: `k_norm_q8` z residualem, `k_gemv_swiglu_q8`, `k_gated_norm_q8`.

**Uwaga obok rankingu:** dla długich promptów najmocniejszą liczbą w tym badaniu jest DFlash2 na XTX (157/147/107 t/s przy 2K/32K/99K) wobec Turbo 95–99. To temat notatki o DFlash2 (KB 32f), nie tej.

## 5. Werdykt

Z ExLlamaV3 bierzemy prefill przez odtworzenie wag do fp16 + GEMM WMMA fp16 (największy pojedynczy zysk: +15–30% prefillu) i dwie bezstratne sztuczki draftu (kalibrowane cięcie, dynamiczna głowica). Z TRT-LLM bierzemy block verification i heurystykę flash-decoding. Na launch overhead na XTX obie biblioteki potwierdzają, że grafy HIP i PDL-podobne triki nie działają, więc jedyną dźwignią zostaje nasza taśma PM4 (+4–5% dekodu).
