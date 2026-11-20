# llama.cpp (mainline) i ik_llama.cpp: backend HIP/CUDA na RDNA3 i spekulacja (delta dla Turbo)

Autor: LlamaCppIk, 2026-11-20. Tylko CPU: czytanie kodu i stron, bez uruchomień na GPU.
Nie powtarzam `63c-amd-rocm-llamacpp.md` (tabela zmian v0.9.0, RDNA-FAST, QSA). Tutaj jest to, co z kodu wynika dla **naszego** dekodu, weryfikacji i prefillu na XTX.

## 1. Co to jest

- **llama.cpp**: `~/research/engines/llama.cpp`, commit `5f83714` (2026-11-20). Backend CUDA/HIP to jeden kod (`ggml/src/ggml-cuda/`), a HIP kompiluje go przez `vendors/hip.h`.
- **ik_llama.cpp**: `~/research/engines/ik_llama.cpp`, commit `8768464` (2026-11-20). Fork ikawrakow nastawiony na CPU i NVIDIA. README mówi wprost, że zgłoszeń o ROCm nie obsługują (`README.md:14`).

## 2. Architektura (to, co dotyczy RDNA3 i naszego modelu)

1. **Harmonogram.** Graf ggml jest liczony węzeł po węźle. Fuzje wykrywa się wzorcem na grafie (`ggml_cuda_can_fuse`, `ggml-cuda.cu:4153`, lista wzorców `ggml-cuda.cu:5243-5305`). Na RDNA3 nie ma PDL: `ggml_cuda_pdl_sync()` działa tylko od Hoppera (`common.cuh:146-155`).
2. **Grafy HIP.** Są domyślnie włączone (`ggml/CMakeLists.txt:217`, `GGML_HIP_GRAPHS ON`). Graf ggml jest nagrywany w kawałkach po 512 węzłów (`ggml-cuda.cu:3468-3474`, zmienna `GGML_CUDA_GRAPH_CHUNK_SIZE`), żeby GPU liczyło jeden kawałek, gdy CPU nagrywa następny. Rozgrzewka wymaga 2 wywołań bez zmian (`ggml-cuda.cu:5580-5590`). W ik grafy wymagają `CUDART_VERSION >= 12000` (`ik: ggml-cuda/common.cuh:970-972`), a flaga jest dodawana tylko w gałęzi CUDA (`ik: ggml/src/CMakeLists.txt:320`). Na HIP grafów więc praktycznie nie ma `[INFERENCE]`.
3. **Dekod GEMV (MMVQ).** Na RDNA3 obowiązuje osobna tabela `MMVQ_PARAMETERS_RDNA3_0` (`mmvq.cu:96-110`):
   - przy N=1: Q4_0/Q8_0/IQ4_NL mają 8 fal na blok, Q6_K 2 fale, **Q4_K 1 fala** (`mmvq.cu:520-540`);
   - przy N=2..8: 1 fala i 1 wiersz na blok (`mmvq.cu:540`, `mmvq.cu:667`);
   - MMVQ obsługuje do 8 kolumn (`mmvq.cuh:3`), a RDNA3_0 nie ma własnego progu, więc N≤8 idzie przez MMVQ (`mmvq.cu:438`);
   - fuzja gate/up+GLU w MMVQ działa tylko przy N=1 (`ggml-cuda.cu:2353-2356`).
4. **Prefill GEMM (MMQ).** Ścieżka int8 WMMA dla RDNA3. Kafle Q4_K: 128 wątków, I=64, J do 128, occupancy 1–2, **bez stream-k** (`mmq-config-rdna3.cuh:113-123`). Dla **Q6_K przy >128 tokenach** RDNA3_0 wybiera dekwantyzację i hipBLAS zamiast MMQ (`mmq.cu:499-500`); komentarz mówi, że MMQ ma tu niższy szczyt niż hipBLAS (`mmq.cu:494-495`).
5. **FlashAttention na RDNA3** (GQA 6, head 256):
   - `gqa_ratio_eff` = 2, bo 6 nie dzieli się przez 4 (`fattn.cu:725-729`);
   - kernel WMMA (`fattn-mma-f16.cuh`) rusza dopiero przy `Q->ne[1]*2 > 16`, czyli od 9 tokenów (`fattn.cu:762-766`);
   - dekod z KV f16 idzie przez kernel **tile**, a z KV kwantyzowanym (≤2 tokeny) przez **vec** (`fattn.cu:768-782`).

   ik na AMD zawsze używa kernela vec (`ik: fattn.cu:111-118`, komentarz „On AMD the tile kernels perform poorly”).
6. **Gated DeltaNet:**
   - **Sekwencyjna rekurencja** (`gated_delta_net.cu:9-175`). Stan siedzi w rejestrach, transponowany (wiersz `col` ciągły). Fala dzieli się na 4 segmenty po 8 lane'ów, a każdy segment liczy jedną kolumnę stanu i redukuje ją shuffle'em, bez `__syncthreads` (`:7`, `:43-46`, `:100-121`).
   - **Siatka.** Grid to `(H, n_seqs, S_v/(4·num_warps))` (`:203`), a `num_warps` maleje, gdy CTA jest mniej niż CU (`:198-201`). Dla 27B (H=48, S_v=128) wychodzi 48×8 = **384 CTA po 128 wątków**.
   - **Migawki stanu.** Do K slotów na token, pod cofanie przy spekulacji (`:157-170`), wpisywane wprost do cache dzięki fuzji z `cpy` (`ggml-cuda.cu:3589-3651`, `:4509-4520`).
   - **Chunked GDN** (`gated-delta-net-mma.cu`): kawałki C=16, bf16 rozbite na hi/lo, żeby mnożenia MMA dawały dokładność bliską fp32 (`:8-45`). Kod urządzenia **kompiluje się dla RDNA3 WMMA** (`:64`), ale host włącza go tylko na RDNA3.5 (≥2048 tokenów) i CDNA. Na gfx1100 zostaje `ar`, czyli sekwencyjnie (`:443-463`). Warunki: H_k=16 i H∈{16,32,48,64} (`:439`), S_v=128 i K<n_tokens (`gated_delta_net.cu:276`). **Qwen3.8-27B je spełnia.**
   - **ik.** Jest kernel rekurencyjny dla ≤8 tokenów (256 wątków) i „tiled” (128 wątków, 8 tokenów naraz w LDS) dla dłuższych. Oba sekwencyjne, tylko head 64/128 (`ik: delta-net.cu:436-466`).
7. **Spekulacja w serwerze (mainline):**
   - **Typy.** `draft-simple`, `draft-eagle3`, `draft-mtp`, `draft-dflash`, `dflash2`, `dspark`, `lilicorr`, `ngram-simple/map-k/map-k4v/mod/cache` (`common/common.h:176-191`). Implementacje są próbowane po kolei i wygrywa pierwsza, która da draft (`speculative.cpp:3432-3520`).
   - **Domyślne parametry draftu:** `n_max=3`, `n_min=0`, `p_min=0`, losowanie draftu na GPU (`common.h:343-351`). MTP przerywa łańcuch, gdy top-1 < `p_min` (`speculative.cpp:2208`).
   - **T>0.** Klasyczny rejection sampling (`sampling.cpp:744-815`). Sampler draftu jest przebudowywany na temperaturę celu z top_k=10 (`speculative.cpp:35-70`). Przy T=0 rejection jest wyłączony (`server-context.cpp:580-583`).
   - **Cofanie stanu hybrydy.** Mainline ma migawki GDN w K = `n_max` slotach (`common.h:424-428`). Gdy draft jest dłuższy niż `n_rs_seq`, przywraca pełny checkpoint i powtarza (`server-context.cpp:4917-4921`).
   - **ngram-mod.** Wspólna tablica haszy 4M wpisów, czyli 16 MB (`speculative.cpp:2452`). Domyślnie `n_match=24`, `n_max=64`, `n_min=48` (`common.h:375-380`).
8. **ik: spekulacja.**
   - **Domyślne:** `n_max=16`, `p_min=0.75` (`ik: common/common.h:236,246`).
   - **Typ `suffix`** (SuffixDecoding, drzewo sufiksów, `ik: common/suffix-tree.cpp:105-176`).
   - **Adaptacyjne `p_min`:** +0,1 po 3 słabych rundach (akceptacja <0,5), −0,05 po dobrej, z sufitem 0,5 (`ik: speculative.cpp:1025-1028`, `:1083-1091`).
   - **`--spec-autotune`:** bandyta ε-greedy (ε=0,15) po `n_max`/`p_min`/`n_min`. Nagroda to t/s kroku, a zmianę zadania wykrywa EMA α=0,05 (`ik: common/spec-tuner.h:34,53`, `spec-tuner.cpp:95-107`).
   - **Weryfikacja liniowa**, bez drzewa `[INFERENCE: nie znalazłem drzewa w kodzie]`.
9. **ik: kwanty i fuzje.**
   - **Własne typy** IQ2_K..IQ6_K, IQ4_KS, IQ4_KSS, IQ*_KT (trellis) i Q6_0 (`ik: ggml.h:410-497`). Wymagają zmiany formatu wag, więc dla nas wchodzą w grę tylko na głowicy draftu.
   - **Fuzje:** FUSED_RMS_NORM, FUSED_UP_GATE, MULTI_ADD, FUSED_MUL_UNARY i fuzja kopii stanu delta-net (`ik: ggml.h:657-665`, PR #2251). Fuzja w MMVQ działa tylko przy N=1 (`ik: ggml-cuda.cu:2957`).
   - **MMVQ na RDNA2/3:** zawsze 1 fala na blok (`ik: iqk_mmvq_templates.cuh:46-52`).

## 3. Techniki z liczbami

| technika | gdzie | liczby (źródło) | znaczenie dla nas |
|---|---|---|---|
| **Few-row MMQ** (int8 MMA dla 2–24 kolumn) | `mmq-few.cu:10-19`, bramka `:873-929`; na HIP wyłączony (`:931-941`) | Qwen3.8-27B Q4_K_M, krok przy 8 kolumnach: 3090 Ti ×1,42, 5090 ×1,17; spec DFlash2 7 tok.: **3090 Ti 57,6 → 77,7 t/s (+34,9%)**, 5090 +20,6%. Port HIP na RDNA3.5: **21 → 37 t/s** ([PR #31533](https://github.com/ggml-org/llama.cpp/pull/31533)). Mikrobench 34816×5120, 8 kolumn: 501 → 149 µs (komentarz mercant1982 w PR) | **największa dźwignia weryfikacji**, patrz 4.1 |
| Konstrukcja few-row | j.w. | blok = 16 wierszy × wszystkie kolumny. 4 fale dzielą K po 256/512, każda ma własny pierścień `cp.async`, w pętli K nie ma barier, fala 0 sumuje części w **stałej kolejności** (deterministycznie). Zysk przy 8 tok.: ~44% z układu aktywacji „jak fragment MMA”, 13–20% z kopiowania wag przed PDL-wait (PR #31533) | układ aktywacji da się przenieść na WMMA RDNA3 `[INFERENCE]` |
| Chunked GDN (C=16, bf16 hi/lo) | `gated-delta-net-mma.cu` | pp Qwen3.8-27B Q4_K_M: 5090 +5,5…5,8%, 4090 +3,1…3,2%, 3090 +0,9…2,2%; Strix Halo +6,75…6,98% (Q8_K_L). KLD 0,000463, zgodność top-1 98,8% ([PR #29353](https://github.com/ggml-org/llama.cpp/pull/29353)). 0cc4m w tym PR: CUDA-owy skan GDN jest „około 2× wolniejszy” niż ten na Vulkanie | u nas GDN to 9% prefillu (COLLAB: 75 z 825 ms przy 512) |
| GDN sekwencyjny 384 CTA, shuffle zamiast LDS | `gated_delta_net.cu:7-46,198-203` | brak osobnego benchmarku | Turbo w prefillu: `k_gdn_conv_norm` z 1 blokiem na głowę = 48 bloków na 96 CU (`gpu_forward.hip:2342`), a `k_gdn` ma 4 `__syncthreads` na token (`gpu_forward.hip:1555-1575`) |
| MMVQ RDNA3 Q6_K: 8 → 2 fale | `mmvq.cu:531-532` | W7800: tg Llama-3.2-3B 125 → 145 t/s, Qwen3.6-35B-A3B 76 → 86 t/s ([PR #23349](https://github.com/ggml-org/llama.cpp/pull/23349)) | Turbo GEMV ma już ~89% pasma i 45,9 > 42,2 t/s llama.cpp, więc nic do wzięcia |
| Q6_K przy >128 tokenach przez hipBLAS (RDNA3_0) | `mmq.cu:499-500` | brak liczby w kodzie; to decyzja strojenia upstream | Turbo liczy Q6_K przez MMQ przy kawałku 512 (`mmq_shim.hip`), więc warto sprawdzić |
| Fuzja gate/up+GLU w MMQ | `ggml-cuda.cu:2496-2530`, wywołanie `:5042` | Qwen3.8-27B pp16384 na GB10: Q4_K_M +7,1% ([#29948](https://github.com/ggml-org/llama.cpp/pull/29948), za 63c) | Turbo wziął MMQ z topki (b11528), która tej fuzji nie ma (63c) |
| ngram-mod + MTP na Qwen3.8-27B | `speculative.cpp:2425+` | 2×B70 SYCL: ciepły kod 44 → **96–103 t/s (×2,2–2,3)**, bez regresji na JSON/refactor. `suffix`: JSON 43 → 10–13 t/s, refactor 38 → 30 ([Captain-Tripps, 2026-08-26](https://github.com/Captain-Tripps/suffix-decoding/blob/main/docs/RESULTS-2026-08-26-suffix-bench.md)) | suffix odrzucamy, ngram-mod (n_match 24) bierzemy jako politykę |
| Autotune spekulacji (ik) | `ik: spec-tuner.cpp` | najlepsze `n_max` zależy od zadania: quicksort 15, ekstrakcja 3, opowiadanie 1; ngram-mod 38 → 45,7 t/s po dostrojeniu. MTP w ik zbiegało do `draft-max 1` (14 t/s), bo MTP było tam słabe ([PR #1595](https://github.com/ikawrakow/ik_llama.cpp/pull/1595)) | nasze sweepy w COLLAB dają rozrzut 2–4% między K i `p_min` |
| Fuzja zapisu stanu GDN w kernelu (ik) | PR #2251 | CUDA GTX 1650: tg +2,0…2,3%. ikawrakow na 2×3090: ~1% TG, z MTP efekt niemierzalny ([PR #2251](https://github.com/ikawrakow/ik_llama.cpp/pull/2251)) | Turbo ma ping-pong bez kopii, więc nic do wzięcia |
| Migawki K slotów (mainline) zamiast powtórki | `gated_delta_net.cu:157-170` | stan 27B = 48 warstw × 48 głowic × 128² × 4 B ≈ 151 MB na migawkę; zapis 8 migawek ≈ 1,2 GB, czyli ~1,3 ms przy 960 GB/s `[INFERENCE]` | Turbo: taśma + powtórka 0,35–0,5 ms (COLLAB), czyli taniej. **Nie bierzemy** |
| „ik 26× szybszy prompt na Qwen 3.5 27B” | wątek r/LocalLLaMA, 03.2026 ([vibingtalk](https://vibingtalk.com/index.php?threads%2Fik_llama-cpp-gives-26x-faster-prompt-processing-on-qwen-3-5-27b-real-world-numbers.588392%2F)) | niezweryfikowane. Pewnie chodzi o ponowne użycie prefiksu i checkpointów, a nie o kernel `[INFERENCE]` | Turbo ma reuse prefiksu (runda 7) |

Czego **nie ma** dla RDNA3 w żadnym z nich:
- programowego ukrywania przerw między kernelami (PDL tylko na Hopperze; u nas przerwy to ~2,4 ms z 21,7);
- megakernela;
- FA WMMA dla dekodu (WMMA FA działa dopiero od 9 tokenów przy GQA 6).

ik na AMD jest wręcz słabszy od mainline:
- FA tylko vec;
- grafy HIP wyłączone `[INFERENCE]`;
- MMVQ zawsze z 1 falą na blok.

## 4. Co bierzemy do Turbo (ranking według oczekiwanego zysku)

### 4.1 Wąska weryfikacja przez int8 WMMA („few-row” na RDNA3) z kolejnością sum jak w dekodzie

- **Co.** Port idei `mmq-few.cu`:
  - blok liczy 16 wierszy wag × wszystkie N kolumn;
  - fale dzielą K, każda ma własny pierścień LDS (na RDNA3 zamiast `cp.async` zwykłe ładowania z wyprzedzeniem);
  - aktywacje q8_1 trzymamy od razu w układzie fragmentu B dla WMMA `i32_16x16x16_iu8`;
  - fala 0 sumuje części w stałej kolejności.

  U nas to nowy kernel obok GEMV weryfikacji w `src/gpu/gpu_forward.hip` (ścieżka `r_ver_small` i NMAX).
- **Bezstratność.** Iloczyny int8 sumowane w int32 są dokładne w każdej kolejności. Różnić może się tylko część float: skala superbloku `d·Σ sc·isum − dmin·Σ m·ysum` i sumowanie superbloków. Jeśli epilog odtworzy kolejność float z GEMV N=1 (ta sama kolejność superbloków na lane i to samo drzewo redukcji), wynik ma szansę być bit w bit `[INFERENCE, do sprawdzenia testem |dlogit|=0]`. W przeciwnym razie trzeba puścić przez ten kernel także dekod N=1, ale wtedy trzeba zmierzyć, czy N=1 dalej trzyma pasmo.
- **Zysk.** Dziś weryfikacja kosztuje N=8 32,1 ms, N=16 58,5 ms, a N=1 21,8 ms (COLLAB). Upstream przy 8 kolumnach zszedł ×1,17–1,42 na krok.
  - Jeśli N=8 spadnie do ~24–25 ms, krok spec K=3..7 tanieje o 10–25%. Kopie kodu: 190–222 → ~230–270 t/s `[INFERENCE]`.
  - Jeśli N=16 zejdzie z 58 do ~28–30 ms, sensowny staje się ogon lookup W=16 jak w produkcji. Długie prompty: 95–99 → ~130–150 t/s (produkcja ma 140–159) `[INFERENCE]`.
- **Koszt:** 5–8 dni (kernel Q4_K i Q6_K, układ aktywacji, test bitowy).
- **Ryzyko dla bezstratności:** średnie. Do czasu dowodu bitowego zostaje bramka `--compare-spec`.

### 4.2 GDN w prefillu: więcej CTA, bez barier, potem chunked WMMA

- **Krok 1.** W prefillu oddzielić normę (gated RMSNorm i int8) od rekurencji. Rekurencję liczyć układem z `gated_delta_net.cu`: 4 kolumny na falę, segmenty po 8 lane'ów, stan w rejestrach, redukcja shuffle'em, 384 CTA zamiast 48 bloków. Kolumny stanu są od siebie niezależne, więc podział jest darmowy.
- **Krok 2.** Przenieść `gated-delta-net-mma.cu` (C=16, hi/lo bf16, ścieżka `slice64`: `gdn_single<16,64>`, 2 bloki na głowę, `:498`). Kod RDNA3 WMMA już się kompiluje (`:64`), upstream tylko go nie włączył na gfx1100. Trzeba zmierzyć od 512 tokenów, bo nasz kawałek prefillu ma 512.
- **Zysk.** GDN to 9% prefillu. Krok 1: −30…50% czasu GDN, czyli prefill +3…5%. Krok 2: dodatkowo +2…4% (upstream dla dense 27B daje +3…7%). Szacunek łączny 844 → ~890–920 t/s przy 2k `[INFERENCE]`. Przy okazji tanieje powtórka w `accept` (0,35–0,5 ms), jeśli użyje tego samego kernela.
- **Koszt:** krok 1 to 1–2 dni, krok 2 to 3–4 dni.
- **Ryzyko.** Prefill liczą tak samo ścieżka spec i plain, więc tekst spec == plain się nie zmienia. Zmienia się tylko numeryka względem dzisiejszego Turbo (chunked: KLD ~5e-4 wg PR). Rekurencja w weryfikacji i dekodzie musi zostać jednym kernelem dla obu ścieżek.

### 4.3 Q6_K w prefillu: dekwantyzacja do f16 + GEMM f16 (WMMA lub hipBLASLt) zamiast MMQ przy >128 tokenach

- **Skąd.** Decyzja upstream dla gfx1100 (`mmq.cu:499-500`).
- **Zysk.** Zależy od udziału Q6_K w FLOP-ach prefillu (w Q4_K_M m.in. `ffn_down` części warstw, `attn_v` i `output` `[INFERENCE]`). Jeśli GEMM Q6_K przyspieszy o ~20% przy ~20% udziału, prefill zyska +3…4% `[INFERENCE]`.
- **Koszt:** 0,5 dnia na pomiar (sam GEMM Q6_K przez MMQ vs dequant + rocBLAS przy 512×5120×17408), potem 1–2 dni.
- **Ryzyko:** brak, to tylko prefill.

### 4.4 Fuzja gate/up+GLU w MMQ (#29948)

- **Co.** Jeden kernel MMQ liczy gate i up z tego samego kafla aktywacji i od razu stosuje SiLU·mnożenie. Port z `mmq.cuh` mainline do `third_party/ggml-mmq`.
- **Zysk.** Upstream +7,1% pp na GB10. Na RDNA3 `[INFERENCE]` +2…4% (mniej zapisu i odczytu FFN, jedno uruchomienie mniej).
- **Koszt:** 2–3 dni (rebase naszego wycinka MMQ na nowszy mainline).
- **Ryzyko:** brak, to tylko prefill.

### 4.5 Polityka draftu: ngram-mod jako pierwszy drafter, MTP jako zapasowy, oraz autotune n_max/p_min

- **Co.**
  - Wspólna tablica haszy (n_match 24, `n_min` wysokie, czyli drafty tylko przy pewnym dopasowaniu) i kolejność „ngram, potem MTP” (`speculative.cpp:3432-3520`).
  - Do tego bandyta z ik (`spec-tuner.cpp`): ε=0,15, nagroda t/s kroku, reset przy zmianie zadania. Ewentualnie tylko prosta reguła adaptacyjnego `p_min` z `ik: speculative.cpp:1083-1091`.
  - To kod serwera (`src/server`), nie kerneli.
- **Zysk.** Na Qwen3.8-27B ngram-mod+MTP dał ×2,2–2,3 na ciepłych powtórkach kodu bez regresji gdzie indziej (B70). U nas efekt zależy od 4.1, bo długie drafty potrzebują taniej szerokiej weryfikacji. Sam autotune: +2…5% na mieszanych zadaniach `[INFERENCE]`.
- **Koszt:** 1–2 dni.
- **Ryzyko:** żadne. Polityka draftu nie zmienia tekstu przy weryfikacji bit w bit i sprzężonym losowaniu.

### 4.6 Większy kawałek prefillu (512 → 1024/2048)

- **Skąd.** Produkcja ma 933 t/s przy 8k vs 882 przy 2k.
- **Zysk:** +1…3% `[INFERENCE]`. Przy ≥2048 włącza też próg chunked GDN z upstream.
- **Koszt:** 0,5–1 dnia (pamięć MTP i taśmy, patrz „MTP lean reserve” w 63c).
- **Ryzyko:** brak.

### Nie bierzemy

- **Tabela MMVQ RDNA3:** nasz GEMV jest szybszy (45,9 vs 42,2 t/s, ~89% pasma).
- **Kawałkowanie grafów HIP:** host u nas ≈ 0.
- **PDL:** brak na AMD.
- **Migawki K slotów GDN:** droższe niż nasza powtórka z taśmy.
- **Rejection sampling z top_k=10:** nasze sprzężone Gumbel-max jest bit w bit przy T>0.
- **Suffix tree:** regresje na B70.
- **Kwanty ik (IQ4_KS/KT):** zmiana formatu wag. Najwyżej jako typ głowicy MTP, ale bez kerneli HIP.
- **FA ik:** tylko vec na AMD.

## 5. Werdykt

Mainline llama.cpp nie ma nic, co przyspieszy nasz dekod N=1. Ma za to dwa gotowe, zmierzone wzorce, które biją w nasze słabe miejsca:
- **few-row int8 MMA** dla weryfikacji 2–24 tokenów: +35% spec na 3090 Ti, 21 → 37 t/s na RDNA3.5;
- **GDN z podziałem kolumn i chunked WMMA** dla prefillu.

ik_llama.cpp jest na RDNA3 wolniejszy od mainline i daje nam tylko pomysły po stronie serwera: autotune draftu i adaptacyjne `p_min`.
