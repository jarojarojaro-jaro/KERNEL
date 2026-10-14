# 15 — openxla/tokamax

Klon: HEAD `b500ee4` (2026-10-14), płytki, nic nie budowane ani uruchamiane. Ścieżki `plik:linia` są względem `tokamax/_src/` w repo, chyba że zaznaczono inaczej. Kod forka cytuję jako `fork:` (`~/llama-master/ggml/src/ggml-cuda/...`). Repo nie podaje prawie żadnych liczb wydajności. Wszystkie zyski poniżej to nasze `[SZACUNEK]`, liczone z pomiarów z `NOTES.md` i `lfm-decode*.md`.

## 1. Co to jest

Biblioteka kerneli Google/DeepMind w JAX + Pallas (Triton, Mosaic GPU, Mosaic TPU) z autotunerem, cache konfiguracji per urządzenie i narzędziami do benchmarków. Na GPU są: attention (FA fwd/bwd), ragged_dot (MoE GEMM), GLU, normy. Reszta, w tym cały świeży kod inference (fused MoE z EP, ragged paged attention ze spekulacją, GDN/KDA z causal conv1d, MLA, top-k), jest **tylko pod TPU**. Licencja Apache-2.0, ~1600 commitów, 307 gwiazdek, push z dnia klonu. README samo pisze „heavily under development”. GPU = tylko NVIDIA sm80/sm90/sm100 (`gpu_utils.py:48-93`). AMD/ROCm nie występuje nigdzie w kodzie. Główny cel repo to trening (VJP), a od niedawna serwowanie na TPU (vLLM-TPU).

## 2. Kluczowe techniki (z dowodami)

### 2a. Ragged dot / MoE grouping (GPU)
1. **Lista zadań kafli z wyrównanym startem (`GroupInfo.create_aligned`).** Grupy (eksperci) leżą posortowane w jednym buforze. Każdy kafel `block_m` należy do jednej grupy, ale może **zacząć przed grupą**, na granicy wyrównanej do 8. Wiersze sąsiedniej grupy są wtedy liczone i odrzucane przy zapisie. Przykład z kodu: grupy [17,31,24] przy `block_m=32` dają 3 kafle zamiast 5 (`ops/ragged_dot/pallas_mosaic_gpu_common.py:88-151`). Rozmiar siatki to statyczna górna granica `cdiv(m,bm)+G-1`, a nadmiarowe zadania kończą się przez `actual_size > 0` (`pallas_mosaic_gpu_kernel_sm80.py:115,170`). Wersja TPU (megablox) zamiast tego odwiedza kafel na granicy dwa razy, raz dla każdej grupy (`pallas_mosaic_tpu_kernel.py:69-104`).
2. **Epilog wiersz po wierszu przez SMEM**, żeby kafel na granicy grup nie nadpisał wierszy sąsiada (`pallas_mosaic_gpu_kernel_sm80.py:194-206`).
3. **Swap-AB dla wag kwantyzowanych (sm90).** Wagi to operand M (`w = rhs.qvalue.mT`), tokeny to N, a wynik jest transponowany (`pallas_mosaic_gpu_kernel_sm90_quant.py:81,177,202`). int4/int8 są ładowane w układzie rejestrów „UPCAST_2X/4X”, dopasowanym do fragmentu MMA, więc rozpakowanie odbywa się bez przetasowań (`:161-173`).
4. **int8 × int4 z akumulatorem int32 przeskalowywanym co kafel K** (`row_scale·col_scale`, `pallas_mosaic_gpu_kernel_sm100_i8_quant.py:51-102,178-186`). Heurystyka „generate” to `block_m=16` (`pallas_mosaic_gpu.py:309-316`), a autotuning dla małego M przeszukuje `block_m ∈ {8,16,32,64}` (`:511-522`). To ten sam projekt co nasze MMQ i K4 (iu8 WMMA dla 9–16 kolumn).
5. **„Biased encoding” int4 → fp8 bez jawnego dequantu:** `w = 512·w_fp8_biased − 8`, a człon `−8·Σx` idzie z sum wierszy aktywacji policzonych w kernelu kwantyzacji (`pallas_mosaic_gpu_kernel_sm100_fp8_quant.py:268-273,773-782`, komentarz `pallas_mosaic_gpu.py:251-260`). U nas to odpowiednik `0x6400 | nibble` w FA i członu min z `ds.y` w MMVQ.
6. **„Height rungs” / „bucket rows”**: kernel jest kompilowany na kilka wysokości kafla, a krótki kafel ogonowy eksperta używa najmniejszej, która go pokrywa (`experimental/fused_moe/kernel.py:76-83,158-186`, `experimental/routing_moe/gmm/plan.py:66-70`).
7. **Visit list ekspertów**: odwiedzani są tylko niepuści eksperci, w kolejności od największej liczby tokenów. Ranking powstaje przez porównanie wszystkich par zamiast sortowania, bo przy 64 elementach sieć sortująca była jednym z największych modułów programu (`experimental/fused_moe/host.py:1047-1076`). Wagi eksperta e+2 są ładowane w trakcie liczenia e (`host.py:49-62`).
8. **Reprezentatywny rozkład `group_sizes`** w kluczu autotuningu i w benchmarku, bo czas ragged_dot zależy od rozkładu routingu (`ops/ragged_dot/base.py:63-78`).

### 2b. Attention
9. **Maska rozkładana na `is_causal` + `k_start/k_end` per wiersz Q**, liczona z indeksów w kernelu, bez gęstego tensora maski. Zakres pętli KV (`lo/hi`) wynika z tych granic (`ops/attention/pallas_triton.py:240-246,281-296,474-515`).
10. **Softmax bez odejmowania maksimum**, gdy logity są ograniczone (soft-cap ≤ 60): `m_i = 0`, bez przeskalowania akumulatora (`ops/attention/base.py:753-768`, `pallas_triton.py:155-160,253-261`). Opcja `use_base2`: exp2 z log2e wliczonym w skalę (`pallas_triton.py:215-220`).
11. Split-K przez `vmap` plus osobny combine LSE (`pallas_triton.py:626-640`, `base.py:894-908`). „fold_q_sequence_heads” pakuje tokeny × głowy Q w jeden wymiar (`pallas_mosaic_gpu_common.py:54,183`).
12. **RPA (TPU) ze spekulacją**: nowe K/V są czytane z wejścia `new_kv`, a nie z cache, i zapisywane do cache w tym samym kernelu (`experimental/batched_rpa/kernel/kernel.py:265-286,392-410`). Komentarz o błędzie: przy `skip_kv_update` zła formuła „splice unfetched garbage over the newest real token … silently costs ~24 points of MTP acceptance” (`kernel.py:267-277`). Test `speculative_decode_test.py` celuje w „padded-query leakage, cross-page writeback”.

### 2c. GDN / KDA (tylko TPU)
13. **conv1d + SiLU + GDN w jednym kernelu**, okno weryfikacji `num_spec_tokens+1`, jeden checkpoint stanu na pozycję w oknie (`ops/causal_conv1d_gated_delta_rule/wrapper.py:327-424,647-664`). **Kontrakt numeryczny:** okno weryfikacji musi zaokrąglać pośrednie wartości tak jak dekod 1-tokenowy, „otherwise its target logits can drift” (`wrapper.py:125-132`).
14. **Chunked GDN pod jednostkę macierzową**: [v·β | k·β·γ] sklejone w jeden GEMM z T⁻¹, [w; q·γ] sklejone w jeden GEMM ze stanem („weight stationary”), q·kᵀ liczone na głowach kq **przed** powieleniem na głowy v (`compute_gdn.py:117-119,178-205,229-238`). **Odwrotność trójkątna** przez skończony szereg Neumanna z podwajaniem na blokach 8×8/16×16 zamiast podstawiania wiersz po wierszu, exp2 w przestrzeni log2, „punkt odniesienia” w środku podbloku zawężający zakres wykładników, zerowanie wykładników poza przyczynowością przed exp2 (`docs/ops/kda/chunk_kda_fwd_design_doc.md:351-357,386-441,771-781`).

### 2d. Autotuning, benchmark, numeryka
15. **Autotuner**: przeszukiwanie wyczerpujące, kompilacja równolegle na CPU, pomiar sekwencyjny, wybór po medianie z 5 iteracji (`autotuning/autotuner.py:48-60,140-160`, `benchmarking.py:590,640`). Cache to JSON per `device_kind`/op, a kluczem jest **pełna specyfikacja argumentów** (kształty, typy, opcje). Przy chybieniu w cache brana jest heurystyka (`autotuning/cache.py`, `ops/op.py:491-535`). `xplane_to_bound_args.py` wyciąga z profilu listę wywołań do strojenia (`docs/autotuning.md`). README ostrzega, że autotuning jest niedeterministyczny, a wybór konfiguracji zmienia numerykę, więc zalecają serializację wyników (`README.md:129-133`).
16. **Benchmark**: czas kernela z CUPTI, a nie zegar ściany. Dane losowe zamiast zer, bo rozkład danych zmienia moc i zegary (`docs/benchmarking.md:58-66`, link do thonking.ai). Pamięć podręczna nie jest czyszczona między iteracjami (brak flush w `benchmarking.py`).
17. **Numeryka**: `array_diff_summary` (max diff z lokalizacją, `percent_close`, L2, `numerics.py:61-113`). Tolerancja stopniowana według kwantyla, np. `atol={0.99: 1e-5, 1.0: 1e-4}` (`test_utils.py:23-71`). Poza tym zwykłe allclose względem referencji w f32/HIGHEST. KDA ma `atol=rtol=0.05` z fallbackiem 1 ULP (`chunk_kda_fwd_design_doc.md:840-846`).
18. Router top-k: k przebiegów „max i maskuj”, O(kN) zamiast sortowania. NaN, −inf i −FLT_MAX są przycinane, żeby indeks zawsze wskazywał prawdziwego eksperta. Wiersz bez poprawnego maksimum zostaje NaN, żeby błąd był widoczny („poisonous”) (`experimental/tpu/router_topk/pallas_mosaic_tpu_kernel.py:17-64`).

## 3. Przeniesienie na AMD/HIP/RDNA3

| # | Technika | Da się? | Jak na gfx1100 / co się nie przenosi |
|---|---|---|---|
| 1–2 | Lista kafli z wyrównanym startem | Tak | Dotyczy MMQ ids w prefillu i hipotetycznego wielotokenowego MMVQ ids. Fork liczy kafle per ekspert (`fork: mmq.cuh:1349-1350` `expert_bounds`), a J wybiera pod **średnią** liczbę tokenów na eksperta (`fork: mmq.cu:194-202`). Kafle tracą więc na ogonach. Odpowiednik „rungs” na WMMA: pętla po podkaflach 16 kolumn z dynamiczną granicą (P5). |
| 3 | Swap-AB | Już jest | WMMA 16×16×16 jest symetryczne. K4 (iu8 small-N) i kvq stawiają wagi lub KV w wymiarze 16 wierszy, a tokeny w kolumnach. Nic nowego. |
| 4 | int8×int4 → i32 → przeskalowanie co kafel K | Już jest | MMQ i K4 (`v_wmma_i32_16x16x16_iu8`, skale q8_1). Specjalizacja warpgroup (TMA WG, store WG, `setmaxnreg`) się nie przenosi: RDNA3 nie ma kopii asynchronicznej i realokacji VGPR per rola (por. 13-cutile „Czego nie proponuję”). |
| 5 | Biased encoding | Tak, dla q8_0 | Dla q4_0 fork już to ma (`fork: fattn-kvq.cu:144-163`, 0x6400). Dla q8_0: `x ^ 0x80808080` → `v_perm_b32` wkłada bajty do mantysy f16 z górnym bajtem 0x64, potem `(h − 1152)` dokładnie w f16 i mnożenie przez `d`. Zobacz P2. |
| 6–7 | Rungs, visit list, prefetch e+2 | Częściowo | Rungs: patrz 1–2. Visit list przy 1 tokenie nic nie daje (4 aktywnych z 64, MMVQ ids już czyta tylko je). Prefetch DMA: brak DMA, jedyny odpowiednik to kernel „touch” do MALL (05-pplx P3). |
| 9 | Maska z indeksów | Tak | `fattn-kvq` czyta maskę f16 dla każdego wiersza KV i robi `fmaf` (`fork: fattn-kvq.cu:244-248,319-367`). Przy jednej sekwencji wystarczy `k_end` per kolumna Q (P3). |
| 10 | Softmax bez maksimum | Raczej nie | Qwen3.8 i LFM2 nie mają soft-capu. QK-norm daje granicę `|s| ≤ √d·max|γ_q|·max|γ_k|` `[WNIOSEK]`, ale P w f16 w kvq wymaga `exp2 < 2^16`, czyli `|s|·log2e < 16`. Na to raczej nie ma szans. exp2 z log2e w skali już mamy (`fork: fattn-kvq.cu:240,380-386`). |
| 11 | Split-K + combine, fold heads | Już jest | kvq: wszystkie głowy GQA i do 8 tokenów w jednym przejściu, parallel blocks + combine. |
| 12 | Nowe K/V z wejścia + zapis w kernelu attention | Tak | To fuzja `set_rows` (już w roadmapie: 07-flashinfer P3, 11-vllm-xpu P2). Tokamax dodaje dwie lekcje: czytać nowe tokeny ze świeżego wejścia, a nie z cache, bo nie ma wtedy zależności zapis→odczyt w jednym launchu; błąd w tej ścieżce ujawnia się jako spadek akceptacji, nie crash. |
| 13 | conv1d+SiLU w kernelu GDN | Tak | U nas conv jest osobnym gridem razem z alpha/beta (K2, `GGML_HIP_GDN_CONV_AB`, 5.54 µs). Checkpointów per pozycja nie bierzemy, bo S4 lag/replay jest lepszy (mniej zapisów). P1. |
| 14 | Chunked GDN (sklejone GEMM-y, Neumann) | Tak, ale mało warte | Bloki 16×16 Neumanna pasują wprost do WMMA 16×16×16 (f16, akumulacja f32). Wcześniejsza analiza ogranicza zysk chunked prefill do ≤2–3% (`research/v2/rr-prefill-kv.md:47,265-276`, `roadmap.md` B8). Notuję tylko jako przepis na ewentualny kernel. |
| 15–17 | Autotuning / benchmark / numeryka | Tak (proces) | Patrz P4, P8. Mediana z 5 gorących przebiegów bez flushu jest dla nas zła: mikrobench MMVQ już raz pokazał złe decyzje (`NOTES.md:247-248`). |
| 18 | Top-k max-and-mask, NaN-poison | Już jest / drobiazg | `topk_moe` liczy top-4 z 64. Warto tylko sprawdzić, czy NaN w logitach routera nie daje cichego „eksperta 0” (P4d). |

## 4. Pomysły dla nas

Baza: Qwen 28.9 ms/krok, LFM 4.10 ms/token, granica kernela w grafie HIP ~2.53 µs (`lfm-decode-round2.md` §1).

### P1. Qwen: conv1d (+SiLU) w kernelu GDN, alpha/beta jako trzeci człon pary MMVQ
- **Co zmienić:**
  - `fork: gated_delta_net.cu` (ścieżka LAG). Blok głowy v liczy conv swoich kanałów v oraz kanałów q/k swojej głowy kq. Conv q/k jest liczony 3× redundantnie (48 v / 16 kq), ale to 4 FMA na kanał. Okno historii z T1 czyta GET_ROWS jak dziś `ssm_conv_fused`, a zapis okna przechodzi do GDN.
  - alpha/beta (48 wierszy, softplus/sigmoid) przechodzą z gridu `GGML_HIP_GDN_CONV_AB` do pary `GGML_HIP_MMVQ_PAIR` (qkv + z + ab: ten sam src1 q8_1).
  - Wzorzec: `ops/causal_conv1d_gated_delta_rule/wrapper.py:100-175`.
- **Zysk `[SZACUNEK]`:** −48 uruchomień na weryfikację. Znika ~2.5 µs granicy plus większość z 5.54 µs kernela conv+ab, a GDN rośnie o ~1 µs na warstwę. Razem ≈ 48 × 5 µs ≈ **0.2–0.3 ms/krok (+0.7–1%)**. Plain decode zyskuje proporcjonalnie.
- **Koszt:** 3–5 dni (maszyneria T1: okno conv, transponowany zapis). **Ryzyko:** średnie. Bitowo jest możliwe, jeśli conv liczy się w tej samej kolejności FMA. Para MMVQ z trzecim, małym członem nie może stracić pasma.
- **Pomiar:** rocprofv3 weryfikacji (kernele/krok, µs GDN, µs pary MMVQ), `spec_sweep` ms/krok A/B, greedy md5 plain + MTP, `test-backend-ops -o GATED_DELTA_NET,SSM_CONV`.

### P2. LFM: q8_0 w `fattn-kvq` z dequantem „biased” (szczegół wykonawczy dla 07-flashinfer P1b / round2 §4)
- **Co zmienić:** instancja `GGML_TYPE_Q8_0` w `fork: fattn-kvq.cu`. Dla K (fragmenty A) i V (transponowany kafel f16 w LDS):
  - `u = x ^ 0x80808080`;
  - dwa `v_perm_b32` pakują bajty jako `0x64uu` (f16 = 1024 + q + 128);
  - `v_pk_add_f16(h, −1152)`, co jest dokładne, bo liczby całkowite ≤ 2048 są w f16 dokładnie reprezentowalne;
  - `v_pk_mul_f16` przez `d`.
  To ~2 operacje VALU na parę wartości, jak w ścieżce q4_0. Kernel zostaje związany z pamięcią, mimo że bajtów na wiersz jest 1.9× więcej. Odjęcie stałej przed mnożeniem przez `d` chroni przed przepełnieniem `1152·d` w f16 przy dużych skalach K.
- **Zysk `[SZACUNEK]`** (za `lfm-decode-round2.md:95-101`): 98k **−1.1 ms/token (+19% t/s)**, 32k −0.3 ms, krótki kontekst ~0. Tokamax wnosi tylko technikę dequantu. Sam pomysł q8_0 w kvq jest już w roadmapie.
- **Koszt:** 2–4 dni. **Ryzyko:** numeryka różna od `flash_attn_ext_vec` (decyzja użytkownika, KLD). **Pomiar:** `llama-bench -fa 1 -ctk q8_0 -ctv q8_0 -d 0,8192,32768,98304`, rocprofv3 µs/wywołanie FA, `llama-perplexity` KLD.

### P3. FA bez maski dla jednej sekwencji: `k_end` per kolumna Q zamiast tensora maski
- **Co zmienić:**
  - W `llama-graph` / `llama-kv-cache` (`set_input_kq_mask`): przy jednej sekwencji bez SWA i ALiBi zamiast wypełniać maskę `n_kv × n_tokens` przekazać mały tensor `k_end[n_tokens]` (pozycja ostatniej widocznej komórki). Maska zostaje ścieżką ogólną.
  - W `fork: fattn-kvq.cu` (i w `fattn-vec` dla LFM q8_0): zamiast `mask_h2` (`:319-367`) porównanie `kv_idx < k_end[col]` tylko w ostatnim kaflu, bo pozostałe kafle są w całości widoczne.
  - Wzorzec: `ops/attention/pallas_triton.py:240-246,281-296,474-515`.
- **Zysk `[SZACUNEK]`:** Qwen przy 94k do **~0.65 ms/krok** (szacunek przyrostowej maski z `NOTES.md:281`) plus kilkadziesiąt µs na odczyty maski w 16 warstwach. Przy krótkim kontekście ~0. LFM: mniejszy upload przy każdym tokenie (część z 12 kopii H2D, `lfm-decode.md:80-82`). Pokrewne z TensorFold #3 („maska na GPU”), ale tu maski nie ma wcale.
- **Koszt:** 2–3 dni (zmiana kontraktu op-a, fallback). **Ryzyko:** niskie. Wynik bitowy, bo dodanie maski 0.0 jest tożsamością, a −inf daje ten sam zerowy wkład. **Pomiar:** `long_ctx_bench` (94k) ms/krok, czas hosta `set_input_kq_mask`, greedy md5, `test-backend-ops -o FLASH_ATTN_EXT`.

### P4. Testy numeryczne i „kanarki” (tanio, zero t/s wprost)
- (a) **Test row-invariance per op:** `op(n=5)` == 5 × `op(n=1)` bitowo dla kerneli deklarowanych jako bitowe (GDN_LAG, SSM_CONV, kvq, MMVQ 1–16 kolumn, K4). Odpowiada kontraktowi z `wrapper.py:125-132`. Dziś łapiemy to pośrednio przez greedy md5, a test per op wskazuje winny kernel od razu.
- (b) **Tolerancja stopniowana per kwantyl + lokalizacja max diff** (`test_utils.py:23-71`, `numerics.py:61-113`) dla kerneli niebitowych (P2, stan GDN f16 z 11-vllm-xpu P1). Mówi więcej niż sam NMSE z test-backend-ops.
- (c) **Testy padded width:** grafy weryfikacji per szerokość (T2) i kubełki K4. Kolumny dopełnienia nie mogą przeciec do KV/stanu GDN/conv (`batched_rpa/kernel/speculative_decode_test.py`).
- (d) **Akceptacja jako kanarek:** w RPA błąd zapisu KV dał tylko −24 pkt akceptacji MTP (`kernel.py:267-277`). Do `spec_sweep` dodać alarm, gdy tok/krok spada > 3% przy tym samym ziarnie. Dla `topk_moe`: test z NaN/−inf w logitach routera.
- **Koszt:** 1–2 dni. **Ryzyko:** brak.

### P5. LFM prefill: „rungs” po 16 kolumn w MMQ ids
- **Co zmienić:** w `fork: mmq.cuh` (ścieżka `expert_bounds`) pętla po podkaflach 16 kolumn z dynamiczną granicą `ceil((col_high − col_low − j0)/16)`. Ogonowy kafel eksperta nie liczy WMMA dla pustych kolumn. Alternatywa: kafle z wyrównanym startem (technika 1), ale ta wymaga wierszy innego eksperta, a MMQ zbiera kolumny przez `ids_dst`, więc rungs są prostsze.
- **Bramka (zero kodu GPU):** histogram tokenów na eksperta przy ub=512 (log `ids`) i sprawność `Σn_e / Σ ceil(n_e/J)·J`. Robić tylko przy sprawności < ~75%.
- **Zysk `[SZACUNEK]`:** przy sprawności 65% i MoE związanym z obliczeniami: część MoE prefillu −15…−25%, cały prefill LFM +3…8%. Jeśli przy J≈32 MoE jest związane z wagami (intensywność ≈ 93 FLOP/B < 128 FLOP/B progu 7900 XTX `[WNIOSEK]`), zysk ≈ 0. **Koszt:** 1–2 dni. **Ryzyko:** niskie, wynik bitowy (te same sumy na element).

### P6. (outside the box) MoE z wieloma tokenami: grupowanie po ekspercie (ragged multi-column MMVQ)
- **Kontekst:** dziś `mul_mat_vec_q_moe` liczy każdą parę (token, slot) osobną falą i czyta wagi eksperta osobno dla każdego tokenu (`fork: mmvq.cu:1859-1861,1925`). To blokuje spekulację na LFM (`NOTES.md:341`: „weryfikacja k tokenów czyta do 4k ekspertów”).
- **Co zmienić:** posortować pary po ekspercie (jak `ggml_cuda_launch_mm_ids_helper`), wyznaczyć grupy (ekspert, lista tokenów) i uruchomić wielokolumnowe MMVQ K1 per ekspert z dynamiczną liczbą kolumn (1–8). Każdy unikalny ekspert jest czytany raz.
- **Bramka:** z logów routera dla okien k=2..5 kolejnych tokenów policzyć średnią liczbę unikalnych ekspertów na warstwę. Losowo przy k=4 to ~14.6 z 16 (bez zysku), więc pomysł ma sens tylko przy silnej lokalności routingu. Drugi test: czy duplikaty i tak trafiają w MALL (czas MMVQ ids przy n=4 vs 4 × n=1).
- **Zysk `[SZACUNEK]`:** nieznany. Przy ≥50% wspólnych ekspertów weryfikacja jest tańsza o ~30–40% na token, co może uczynić n-gram/draft dla LFM opłacalnym. **Koszt:** duży (tydzień+). **Ryzyko:** średnie.

### P7. (outside the box, raczej martwe) Statyczne przesunięcie softmaxu w warstwach z QK-norm
- Zmierzyć rozkład `max|s|` per warstwę na realnych promptach i granicę `√d·max|γ_q|·max|γ_k|`. Jeśli granica < ~11 (P w f16 bezpieczne), kvq może pominąć redukcję maksimum i przeskalowanie VKQ (technika 10). Spodziewam się, że granica nie wyjdzie. Zysk przy długim kontekście jest mały, bo kernel jest związany z pamięcią. Zmienia numerykę. Tylko jeśli pomiar wyjdzie zaskakująco dobrze.

### P8. Proces: tabela strojenia per kształt
- Dziś decyzje typu waves_per_eu per (typ, n), rows per block czy J w MMQ są zaszyte w makrach. Wzorzec tokamax:
  - JSON per urządzenie z kluczem (op, typ, kształt, n kolumn) → konfiguracja, z heurystyką jako fallbackiem;
  - kształty wyciągane z trace rocprofv3 modelu (analog `xplane_to_bound_args.py`);
  - **pomiar w modelu, nie w mikrobenchu** (to nasza lekcja z K1, tokamax jej nie ma);
  - wyniki serializowane, żeby wybór kafla nie zmieniał bitów między buildami.
- Plus z `docs/benchmarking.md:58-66`: mikrobenchmarki na prawdziwych wagach i aktywacjach, bo przy limicie 285 W przełączanie bitów zmienia zegary. Losowe lub zerowe dane dają inne µs niż model.
- **Koszt:** 2–3 dni. Zysk pośredni.

## 5. Krytyka

- **Prawie nic pod nasz sprzęt.** Kod GPU to Hopper/Blackwell: TMA, wgmma, tcgen05/TMEM, kolektywne MMA 2-CTA, `setmaxnreg`, specjalizacja warpgroup. Kod inference (fused MoE z EP i all-to-all po ICI, RPA, GDN/KDA, top-k na SparseCore) jest w całości TPU. Detekcja GPU parsuje `compute_capability` jako float, więc na ROCm nic by nie ruszyło (`gpu_utils.py:63-93`).
- **Triton ragged dot jest naiwny:** siatka `(batch·cdiv(m,bm), grid_n, G)` uruchamia `G × cdiv(m,bm)` bloków z wczesnym wyjściem (`ops/ragged_dot/triton.py:102-114,347`), a heurystyka ma „TODO: Create heuristics” (`:597`). Dobra jest dopiero ścieżka Mosaic (technika 1).
- **Autotuner jest prymitywny:** wyczerpujący (dla sm90 ragged ~384 konfiguracji, `pallas_mosaic_gpu.py:383-409`), mediana z 5 gorących przebiegów bez flushu cache i bez interferencji z resztą modelu. Dla kerneli związanych z pamięcią w decode daje to złe decyzje, co u nas potwierdzono (`NOTES.md:247-248`). Klucz cache to dokładny kształt: bez interpolacji, chybienie oznacza heurystykę.
- **Numeryka to allclose**, czasem luźne (KDA `atol=rtol=0.05`). Nie ma infrastruktury bitowej ani row-invariance poza pojedynczymi komentarzami. Nasz kontrakt (greedy md5, hash logitów, KLD) jest mocniejszy.
- **GDN ze spekulacją zapisuje checkpoint stanu na każdą pozycję okna** (`wrapper.py:394-398`). To podejście, które porzuciliśmy w S4 (lag + replay, −720 MiB zapisów na weryfikację).
- **Brak liczb.** Jedyny pomiar w docs to CP dla KDA na TPU: 1.54× przy idealnych 4× (`chunk_kda_fwd_design_doc.md:900`). Tezy o wydajności są więc nieweryfikowalne.
- Duża część repo jest dla nas nieistotna: VJP/trening, cross-entropy, triangle attention (AlphaFold), MLA/DSA (DeepSeek), mHC, sharding.

## 6. Werdykt

**Niska.** Repo jest zbudowane pod Hopper/Blackwell/TPU i pod trening. Prawie wszystko, co ma sens na RDNA3 (swap-AB, int8×int4 z przeskalowaniem, dequant przez magiczną liczbę, fold głów GQA, split-K), fork już ma. Z tokamaxa zostają małe, konkretne rzeczy: conv w kernelu GDN (P1, ~1%), maska z `k_end` (P3, do ~2% przy 94k), technika dequantu dla q8_0 kvq (P2) i lekcje testowe (P4).
