# FLA (flash-linear-attention): chunked Gated DeltaNet + krótko PowerInfer / llamafile

Klony i commity:
- `fla` `479745d 2026-11-20`;
- `llama.cpp` `5f83714 2026-11-20` (do porównania, bo upstream ma już chunked GDN dla HIP);
- `PowerInfer` `8bd56d6 2026-05-11`;
- `llamafile` `334e664 2026-11-05`.

Liczby Turbo pochodzą z `~/praca/enigma-turbo-k` (`COLLAB.md`, `src/gpu/gpu_forward.hip`).

## 1. Co to jest

FLA to biblioteka kerneli Triton (Yang, Zhang i in.) dla atencji liniowej. Jest wzorcową implementacją GDN dla treningu i prefillu: vLLM i SGLang dla Qwen3-Next/3.5 biorą z niej te kernele. Interesują nas dwie operacje:
- `chunk_gated_delta_rule` – forma kawałkowa (prefill, trening);
- `fused_recurrent_gated_delta_rule` – rekurencja token po tokenie (dekod).

Algorytm pochodzi z dwóch prac:
- DeltaNet z reprezentacją WY/UT: Yang i in., NeurIPS 2024, https://arxiv.org/abs/2406.06484;
- Gated DeltaNet: Yang, Kautz, Hatamizadeh, ICLR 2025, https://arxiv.org/abs/2412.06464.

Najważniejsze dla nas jest to, że **upstream llama.cpp ma już połączony kernel chunked GDN dla CUDA i HIP z WMMA RDNA3**: `ggml/src/ggml-cuda/gated-delta-net-mma.cu`, PR https://github.com/ggml-org/llama.cpp/pull/29353. Na gfx1100 (XTX) jest on jednak **wyłączony**, bo `select_gdn_mma_path` zwraca `ar` dla wszystkiego poza RDNA3.5 i CDNA (`gated-delta-net-mma.cu:444-463`). Produkcja na XTX liczy więc GDN tak samo sekwencyjnie jak my.

## 2. Architektura (to, co dotyczy GDN)

1. **Rekurencja (u nas i w FLA jest to ta sama matematyka).** Stan S ma wymiar d_k×d_v = 128×128 i jest w fp32. Dla każdego tokenu:
   - α_t = exp(g_t), gdzie g_t = softplus(a_t + dt_bias)·ssm_a < 0;
   - S ← α_t·S;
   - δ = β_t·(v_t − Sᵀk_t);
   - S ← S + k_t δᵀ;
   - o_t = Sᵀ q_t.

   U nas to `k_gdn` w `gpu_forward.hip:1559-1575`, a w FLA `fused_recurrent.py:131-161` i `naive.py:50-59`.
2. **Pipeline prefillu w FLA ma 5 kerneli** (`gated_delta_rule/chunk.py:52-91`):
   1. `chunk_local_cumsum(g)` w log2 (`scale=RCP_LN2`);
   2. `chunk_gated_delta_rule_fwd_intra`, czyli połączone KKᵀ + odwracanie trójkąta, potem `recompute_w_u`;
   3. `chunk_gated_delta_rule_fwd_h`, czyli przekazanie stanu między kawałkami (jedyna część sekwencyjna);
   4. `chunk_fwd_o`, czyli wyjście.
3. **Kawałek BT = 64**, dozwolone 16/32/64 (`chunk.py:557-559`, `chunk_fwd.py:369-370`). Wewnątrz kawałka są podbloki BC = 16 (`chunk_fwd.py:383`).
4. **Siatki:**
   - części równoległe: (liczba kawałków NT) × (B·HV) programów (`chunk_fwd.py:386`, `chunk_o.py` grid `(V/BV·NT, B·HV)`);
   - przejście stanu: tylko (V/BV)·N·HV programów, a pętla po kawałkach idzie w środku (`chunk_delta_h.py:175`, `:726`).
5. **Dekod (`fused_recurrent`):**
   - siatka NV·N·HV programów po 1 warpie, BV = 8 kolumn stanu na program (16 na Hopperze) (`fused_recurrent.py:206-226`, `num_warps=1` w `:254`);
   - stan BK×BV fp32 siedzi w rejestrach przez całe T tokenów, redukcje przez `tl.sum`;
   - L2-norm q/k, sigmoid β i bramka liczone są w kernelu (`:118-137`).
6. **Precyzja w FLA (tryb treningowy, bf16):**
   - akumulatory stanu są fp32 (`chunk_delta_h.py:101-115`), ale do iloczynu w·S stan jest rzutowany na bf16 (`:214-216`), a v_new na bf16 przed kᵀ·v_new (`:288`);
   - macierz T = (I+A)⁻¹ zapisywana jest w dtype k, czyli bf16 (`chunk_fwd.py:385`);
   - stany pośrednie h są w dtype k (`chunk_delta_h.py:722`), stan końcowy w fp32 (`:723`);
   - odwracanie trójkąta działa w tf32 na NVIDIA (`chunk_fwd.py:20-23`) albo ieee (`utils/solve_tril.py:19-21`);
   - `u` liczone jest z `allow_tf32=False` (`wy_fast.py:89`).
   - Dla nas to za mało dokładne: wzorujemy się na schemacie, nie na typach.
7. **llama.cpp, kernel `gdn_single<C,V>`:**
   - jeden blok 256 wątków na (głowę v, wycinek V kolumn); stan fp32 w rejestrach WMMA (`gated-delta-net-mma.cu:177-188`);
   - kawałek C = 16, na HIP V = 64, więc siatka H·2 bloków (`:498`) – na 27B 96 bloków, czyli jeden na CU XTX;
   - operandy WMMA to bf16 hi+lo (rozbicie fp32 na dwa bf16) i 3 iloczyny na kafel: lo·hi + hi·lo + hi·hi (`:117-130`, `:27-46`);
   - stan i stała zaniku liczone są w fp32.
8. **Bramka włączenia w llama.cpp:** n_tokens ≥ 64, H_k = 16, H ∈ {16, 32, 48, 64}, d = 128 (`:439-441`). Na RDNA3.5 dopiero od 2048 tokenów (`:445-449`), na gfx1100 kernel jest wyłączony.
9. **Wynik llama.cpp (PR 29353):**
   - dense Qwen3.8-27B: +3,1…+6,4% PP na NVIDIA (4090 2k +3,1%, 5090 +5,5%, PRO 6000 +6,4%);
   - Strix Halo +6,75% (pp2048);
   - dokładność wobec rekurencji: KL 0,000463, zgodność top-1 98,8%. **Nie jest bit w bit.**

   Źródło: https://github.com/ggml-org/llama.cpp/pull/29353.

## 3. Algorytm chunked krok po kroku (do wdrożenia w HIP)

Oznaczenia dla jednego kawałka tokenów [t0, t0+C) i jednej głowy v:
- Q, K ∈ R^{C×128}; q ma już skalę 1/√d_k, bo u nas robi to `k_conv_l2`;
- V ∈ R^{C×d_v}, β ∈ R^C, g ∈ R^C;
- S0 ∈ R^{128×d_v} to stan na wejściu kawałka; nasz układ to `S[h][wiersz k][kolumna v]` (`gpu_forward.hip:1548`);
- γ_i = Σ_{s≤i} g_s to suma prefiksowa w obrębie kawałka, Γ_i = e^{γ_i}.

**Wyprowadzenie.** Po rozwinięciu rekurencji wewnątrz kawałka:
- δ_i = β_i (v_i − Γ_i·S0ᵀk_i − Σ_{j<i} e^{γ_i−γ_j}(k_i·k_j) δ_j).

W postaci macierzowej:
- (I + A)·Δ = β ⊙ (V − diag(Γ)·K·S0), gdzie A_ij = β_i·e^{γ_i−γ_j}·(k_i·k_j) dla j < i (ściśle dolnotrójkątna);
- T = (I + A)⁻¹ to „transformacja UT” (reprezentacja WY iloczynu macierzy Householdera).

FLA rozpisuje to tak:
- u = T(β⊙V), w = T(β⊙Γ⊙K), Δ = u − w·S0 (`wy_fast.py:82-106`, `chunk_delta_h.py:211-239`).

Wyjście:
- O = diag(Γ)·Q·S0 + (QKᵀ ⊙ M)·Δ, gdzie M_ij = e^{γ_i−γ_j} dla j ≤ i (z przekątną) (`chunk_o.py:126-154`).

Stan na koniec kawałka:
- S_end = Γ_C·S0 + Kᵀ·(e^{γ_C−γ} ⊙ Δ) (`chunk_delta_h.py:245-316`).

Wszystkie e^{…} to różnice γ_i − γ_j ≤ 0 albo Γ_i ≤ 1. Nic nie przepełnia, najwyżej dochodzi do niedomiaru do 0, co jest poprawną granicą. Trzeba jednak maskować 0·inf na brzegu kawałka (`chunk_fwd.py:176-193`).

**Odwracanie trójkąta.** FLA najpierw robi podstawienie wprzód na 4 blokach przekątnych 16×16 w rejestrach, potem scala bloki: Ai10 = −Ai11·A10·Ai00 itd. (`chunk_fwd.py:222-291`). llama.cpp bierze jeden wiersz na falę i robi podstawienie przez shuffle (`gated-delta-net-mma.cu:317-341`). U nas przy C = 16/32 prościej rozwiązać od razu (I+A)Δ = Δ̃ podstawieniem wprzód, wiersz po wierszu, wektorowo po kolumnach V. To C kroków po ≤ C FMA i nie trzeba tworzyć T.

**Proponowany kernel `k_gdn_chunk` (jeden na warstwę GDN w prefillu, wzorowany na `gdn_single`):**

```
// pre: k_conv_l2 dla wszystkich N tokenów (już istnieje, gpu_forward.hip:862) -> q|k|v w tconv,
//      g_t = softplus(a+dt_bias)*ssm_a, beta_t = sigmoid(b) liczone raz dla [N][Hv] (mały kernel albo w prologu)
// grid = Hv * (128/VS)   (VS = 64 -> 96 bloków = 96 CU XTX), block = 256 wątków (8 fal wave32)
// rejestry: wycinek stanu S[128][VS] fp32 = 32 float/wątek (jak acc state[PER_WARP] w llama.cpp)
// LDS (C=16, fp32): Q,K [C][128] 16 KB, Sst [128][VS] 32 KB, V/Δ [C][VS] 4 KB, A,P [C][C] 2 KB, γ,β  -> ~55 KB < 64 KB
for t0 in 0..N step C:
  1. ładuj Q,K (głowa k = h % Hk), V[:, v0:v0+VS], g, β do LDS; fala 0: scan γ (shfl_up), Γ = exp(γ)
     (prefetch następnego kawałka do rejestrów, jak COLLAB:262 / gated-delta-net-mma.cu:202-209)
  2. zrzuć stan z rejestrów do LDS (Sst)                                       // __syncthreads
  3. Gram:  A[i][j] = β_i·exp(γ_i-γ_j)·(K_i·K_j)  (j<i);  P[i][j] = exp(γ_i-γ_j)·(Q_i·K_j) (j<=i)   C×C×128
     Proj:  KS = K·Sst, QS = Q·Sst   (C×128×VS);  Δ̃ = β⊙(V − Γ⊙KS);  base = Γ⊙QS                  // sync
  4. podstawienie wprzód: for i in 1..C-1: Δ_i = Δ̃_i − Σ_{j<i} A[i][j]·Δ_j  (wektor VS; fala na kolumny)  // sync
  5. O = base + P·Δ  -> o[t0+i][h][v0+..]   (C×C×VS)
  6. S = Γ_C·S + Kᵀ·(exp(γ_C − γ) ⊙ Δ)   w rejestrach (128×C×VS)                            // sync
zapisz S do bufora ping-pong Sout (pp_state jak dziś)
// post: gated RMSNorm·silu(z) + int8 dla wszystkich N tokenów (równolegle po tokenach; wycinki VS<128 nie mają
//       całej głowy w bloku, więc fuzji normy jak w k_gdn_norm nie będzie)
```

- Dla N < 64 i w ścieżce weryfikacji/accept (N ≤ NMAX) zostaje obecna rekurencja `k_gdn_conv_norm` (`gpu_forward.hip:2341-2352`).
- Prefill ma dziś kawałek NPF = 1024 (`gpu_forward.hip:1952`), czyli 64 kroki C = 16 na warstwę.
- GQA: 3 głowy v (h, h+16, h+32, bo mapowanie `h % Hk`, `gpu_forward.hip:1553`) mają te same Q i K. KKᵀ i QKᵀ można by liczyć raz, ale to tylko ~15% FLOPs kawałka, więc na start nie warto `[INFERENCE]`.

**Co idzie na WMMA (RDNA3: `v_wmma_f32_16x16x16_f16/bf16`, akumulator fp32, wave32, A/B duplikowane w połówkach fali, https://gpuopen.com/learn/wmma_on_rdna3/):**
- iloczyny macierzowe: KKᵀ, QKᵀ, K·S, Q·S, P·Δ, Kᵀ·Δ;
- zostają na VALU: scan γ, exp, maski, podstawienie wprzód (sekwencyjne po C).

Brak WMMA fp32 oznacza, że dokładność wymaga rozbicia hi+lo. Przy bf16 to 3 iloczyny zamiast 1, jak w llama.cpp `:126-128`. Przy f16 hi+lo daje to ~22 bity mantysy, ale z ograniczonym zakresem: k i q są po L2, więc zakres dla nich jest w porządku; dla S i v trzeba to sprawdzić `[INFERENCE]`.

**FLOPs i pamięć (d = 128, Hv = 48, 48 warstw GDN):**
- rekurencja: ~7d² = 115 kFLOP na token·głowę, czyli 5,5 MFLOP na token·warstwę i 264 MFLOP na token. Wzór na podstawie `gpu_forward.hip:1564-1571`, policzone `[INFERENCE]`.
- chunked: 6d² (K·S, Q·S, Kᵀ·Δ) + ~10·C·d (Gram ×2, P·Δ, solve) na token·głowę:
  - C = 16: ≈ 98k + 20k = 118 kFLOP, czyli tyle samo co rekurencja;
  - C = 64: ≈ 180 kFLOP.
  - Na 1024 tokeny przy C = 16 to ≈ 279 GFLOP; z hi/lo bf16 ×3 ≈ 840 GFLOP-ekwiwalentu `[INFERENCE]`.
  - **Zysk nie bierze się więc z mniejszej liczby FLOPs, tylko z usunięcia 4 barier i łańcucha opóźnień na każdy token.**
- dziś: 75 ms GDN na 512 tokenów prefillu (`COLLAB.md:135`, `:261`), czyli ~3,0 µs na token·warstwę. Wynika to z 48 bloków (połowa z 96 CU) i 4× `__syncthreads` na token (`gpu_forward.hip:1601-1628`), co daje ~1,8 TFLOP/s `[INFERENCE]`.
- pamięć w wersji połączonej (fused) to tylko q, k, v, g, β na wejściu i o na wyjściu, ~64 KB na token·warstwę, czyli ~3 GB na 1024 tokeny i ≈ 3 ms przy 960 GB/s. Stan czytany i pisany jest raz na 1024 tokeny.
  - Pipeline FLA w 4–5 kernelach dokłada w, u, v_new, T i h (~250–300 KB na token·warstwę), czyli ~12–15 GB na 1024 tokeny, ≈ 13–15 ms samego ruchu. Dlatego robimy wersję połączoną, nie kopię FLA `[INFERENCE]`.
- dekod (dla porządku): stan 48×128×128×4 B = 3,1 MB na warstwę czytany i pisany na każdy token, czyli 302 MB na token i ≥ 0,31 ms przy 960 GB/s. Mierzymy 0,47 ms (`CONTEXT.md`), więc dekod GDN jest już na ~66% pasma. Szybciej się nie da bez zmiany precyzji stanu, a to łamie bezstratność `[INFERENCE]`.

**Szacunek dla kawałka 1024 na XTX `[INFERENCE]`:**
- 96 bloków × 64 kroki × 48 warstw. Krok bloku to ~1 MFLOP (fp32), czyli ~3 MFLOP-ekw. z hi/lo.
- Przy realnych 0,3–0,6 TFLOP/s na CU (VALU fp32 albo WMMA ×3 z synchronizacjami) to ~2–5 µs na krok, czyli 0,13–0,32 ms na warstwę, czyli **~6–15 ms na 1024 tokeny**.
- Dziś to ~150 ms (75 ms/512 × 2), a według profilu 9–12% z 1213 ms (844 t/s): 110–145 ms.
- Oszczędność ~100–140 ms na 1024 tokeny, czyli **prefill 844 → ~920–960 t/s (+9–13%)**, ponad produkcję na 2k (882) i blisko 8k (933).
- Wariant tylko fp32 VALU (bez WMMA) wychodzi podobnie, bo ×3 za hi/lo zjada przewagę WMMA przy kaflach C = 16. Na start prościej i dokładniej jest wziąć fp32 FMA z kaflowaniem w LDS.

## 4. Co bierzemy do Turbo

1. **`k_gdn_chunk` (opis wyżej) dla N > NMAX w prefillu**, w miejsce `k_gdn_conv_norm` w gałęzi `N > NMAX` (`gpu_forward.hip:2338-2352`). Przed nim `k_conv_l2` dla N tokenów (równolegle, już mamy), po nim osobna gated norma + int8 po tokenach.
   - Kolejność: (a) fp32 VALU, C = 16, VS = 64, 96 bloków; (b) potem WMMA bf16 hi/lo jak llama.cpp, jeśli (a) okaże się ograniczone FLOPs.
   - Zysk: +9–13% prefillu `[INFERENCE]`.
   - Koszt: 3–4 dni (kernel 2, testy zgodności i bench 1–2).
2. **Tańszy krok pośredni, jeśli chunked się opóźni:** rekurencja w stylu llama.cpp AR, czyli kolumna stanu na 8 lanach jednej fali i redukcje tylko przez shuffle, bez `__syncthreads` (`llama.cpp gated_delta_net.cu:65-123`). Siatka (H, 1, 128/(4·num_warps)) bloków, więc więcej równoległości niż nasze 48 bloków.
   - Tylko w prefillu. Wymaga osobnej normy, a COLLAB:138 pokazuje, że bez fuzji przy N = 64 było −1%, więc zysk jest niepewny.
   - Koszt: 1 dzień.
3. **Ryzyka dla bezstratności:**
   - Spec vs bez spec: **bez zmian**. Obie ścieżki dostają ten sam prefill, a weryfikacja i accept zostają na rekurencji `k_gdn_conv_norm`/`k_gdn`.
   - **`--multiturn` EXACT (COLLAB:202-222) przestanie być bit w bit.** W turze N+1 z cache tokeny odpowiedzi przeszły przez rekurencję dekodu, a w pełnym re-prefillu przez chunked. Inne sumowanie, exp(γ_i−γ_j) zamiast iloczynu exp(g), inne granice kawałków. llama.cpp z bf16 hi/lo mierzy KL 4,6e-4 i 1,2% różnych top-1 (PR 29353). fp32 FMA da błędy rzędu 1e-6 względnie, ale przy T = 0 i długich odpowiedziach rzadkie przestawienia argmax są nadal możliwe `[INFERENCE]`.
   - Rozwiązanie: flaga `TURBO_GDN_RECURRENT_PREFILL=1` do testów EXACT i bramek, a test multiturn zmienić na „cache vs cache” albo na tolerancję logitów.
   - Wynik zależy od podziału na kawałki: (N mod C) i od tego, gdzie zaczyna się przyrostowy prefill (cached_n). Deterministyczne przy tych samych granicach, ale różne między cache a pełnym prefillem.
   - Odwracanie trójkąta: (I+A) z |A_ij| ≤ 1 (k po L2, β ∈ (0,1)) w najgorszym razie ma elementy T rzędu 2^{i−j}. W fp32 przy C ≤ 32 jest bezpiecznie, w czystym bf16 nie, dlatego FLA potrzebuje tf32 lub ieee, a llama.cpp hi/lo `[INFERENCE]`.
   - Maska brzegowa: niepełny ostatni kawałek nie może dać 0·inf (`chunk_fwd.py:176-178`).
4. **Czego nie bierzemy:**
   - pipeline'u FLA w 5 kernelach i bf16 (ruch HBM, precyzja);
   - kawałka 64 (LDS: Q,K 64×128 fp32 = 64 KB już się nie mieści);
   - backendu FlashQLA (TileLang, tylko SM90/SM100/SM120, `backends/flash_qla.py:34-40`).

**PowerInfer (krótko):** opiera się na rzadkości aktywacji w modelach z ReLU. Ma predyktor gorących i zimnych neuronów oraz rzadkie GEMV/axpy z progiem (`PowerInfer/ggml-cuda.cu:119`, `:4418-4685`), a gałąź `smallthinker/` to własne modele MoE na urządzenia. Qwen3.8 ma SwiGLU, więc pomijanie neuronów przez predyktor jest stratne. **Nie dotyczy nas.**

**llamafile tinyBLAS (krótko):**
- GPU GEMM fp16/fp32 z kaflowaniem w stylu siboehm (`tinyblas.cu:32-39`, `:142-160`), bez kwantów i bez WMMA;
- GEMV z sumowaniem Kahana (`tinyblas.cu:90-97`);
- CPU sgemm z kaflowaniem rejestrów.
- Jedyna myśl dla nas: kompensowane sumowanie (Kahan) jako tani sposób na mniejszy błąd w redukcjach wariantu chunked. Nie przywraca jednak bitowej zgodności. Poza tym nic dla XTX.

## 5. Werdykt

Robimy jeden połączony kernel chunked GDN dla prefillu (C = 16, wycinki V = 64, 96 bloków, stan fp32 w rejestrach, najpierw FMA fp32, potem ewentualnie WMMA hi/lo jak `gated-delta-net-mma.cu`). Daje to ~+9–13% prefillu za ~3–4 dni, a jedynym kosztem dla bezstratności jest utrata bitowej zgodności multiturn (cache vs pełny prefill), którą trzeba świadomie przyjąć albo trzymać za flagą.
