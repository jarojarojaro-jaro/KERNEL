# 12 — openai/blocksparse

Klon: `--depth 1`, HEAD `89074c5` (2020-07-13), ~3 MB, 116 plików. Nic nie było budowane ani uruchamiane. Ścieżki `plik:linia` są względem korzenia repo. „Nasz kod” to `~/llama-master/ggml/src/ggml-cuda/` (HEAD `5909da1f1`). Liczby z repo pochodzą z pomiarów OpenAI (Titan X Pascal, CUDA 8), nie z naszego sprzętu.

## 1. Co to jest

Biblioteka operacji TensorFlow 1.x z kernelami CUDA dla wag blokowo-rzadkich (bloki 8/16/32/64) od Scotta Graya, autora maxas. Zawiera:
- matmul i konwolucję blokowo-rzadką;
- „Blocksparse Transformer” (atencja z rzadkim layoutem bloków, użyta w Sparse Transformer, Child i in. 2019);
- layernorm, softmax, LSTM gates, optymalizatory i kwantyzację do treningu.

Repo jest martwe od 2020 r. (README:1 nadal mówi „Active”). Licencja MIT (`setup.py:20`, `LICENSE.md`). Kernele w asemblerze SASS działają tylko na Maxwell i Pascal (README:11-20). Volta ma ścieżkę CUDA-C z `mma.sync` m16n16k16. Nie ma wsparcia dla Ampere i nowszych. Blog: https://openai.com/index/block-sparse-gpu-kernels/ (2017-12-06). Następcą tych kerneli jest Triton (`triton.ops.blocksparse`).

## 2. Kluczowe techniki (z dowodami)

1. **Rzadkość przez LUT, budowany na hoście z layoutu.** Każdy wiersz wyjścia ma nagłówek `(offset, size)`, po nim lista `(blok, kolumna)` (`blocksparse/transformer.py:161-181`). Atencja ma trzy osobne LUT-y: `nt` dla QKᵀ, `nn` dla PV i `tn` dla gradientu (`transformer.py:89-127`). Kernel na starcie kopiuje swój fragment LUT do shared i od razu przelicza indeksy na offsety w bajtach (`src/bst_hgemm_op_gpu.cu:56-66`; `bst_softmax_op_gpu.cu:45-77`).
2. **Atencja to trzy kernele z wynikami QKᵀ zapisywanymi do pamięci**, czyli nie jest fuzją typu FlashAttention:
   - `query_key_op` (QKᵀ do bf16/f16 w HBM, tylko bloki z layoutu, `transformer.py:337-346`, kernel `bst_hgemm_64x64x64_nt` w `bst_hgemm_op_gpu.cu:651-768`);
   - `masked_softmax` (`transformer.py:357-375`);
   - `weight_value_op` (PV, `bst_hgemm_64x64x64_xn` w `bst_hgemm_op_gpu.cu:16-175`).
3. **Maska wewnątrz bloku jako bitmapa** (uint32 lub uint64 na wiersz bloku). Bity zamieniane są na −inf instrukcją `prmt` na parze bf16 (`bst_softmax_op_gpu.cu:98-114`). Exp liczony jest jako `ex2`, z log2(e) wliczonym w skalę (`:154-156`). Redukcja dwupoziomowa: najpierw shfl_xor, potem przez shared (`:125-185`). Warpy, które wypadają poza długość LUT, są wycinane na starcie (`:80`).
4. **Równoważenie obciążenia:**
   - przy causal najpierw idą wiersze z najdłuższą redukcją: `idx_M = grid_M - idx_M` (`bst_hgemm_op_gpu.cu:41-43`), czyli harmonogram LPT;
   - w matmul zbyt długie kolumny LUT są dzielone na segmenty, gdy max/min > 2 (`blocksparse/matmul.py:94-105`);
   - bloki są numerowane w kolejności Mortona (z-order), żeby lepiej wykorzystać L2 (`matmul.py:119-126`).
5. **Split-K pod spinlockiem.** Pierwszy blok, który zdobędzie lock, zapisuje wynik (nie trzeba memsetu). Kolejne bloki czytają, dodają i zapisują w sekcji krytycznej opartej na `atomicCAS` (`src/blocksparse_matmul_gated_op_gpu.cu:225-281`). Kolejność sumowania jest więc niedeterministyczna.
6. **Bramkowanie w czasie wykonania z kompaktacją LUT.** Wpisy z `gate == 0` są usuwane w kernelu przez `vote.ballot` + `popc(mask_niższych_lane & ballot)`, czyli kompaktację strumienia w warpie (`blocksparse_matmul_gated_op_gpu.cu:83-123`).
7. **Blokowanie w rejestrach i redukcja przez wymianę połówek.** W kernelu 8×64×8 wątek trzyma kafel akumulatorów 4×8 (`blocksparse_matmul_gated_op_gpu.cu:180-195`). Połówki warpa liczą różne K. Epilog wymienia połowę wyników jednym `shfl_xor(…,16)`, więc każdy lane kończy z gotową sumą połowy wyjść, bez liczenia nadmiarowego (`:207-218`).
8. **Split-K między warpami wewnątrz CTA.** 8 warpów liczy kafel 64×64, po 4 wzdłuż K. Częściowe sumy są składane w LDS jako suma 4×float4 (`bst_hgemm_op_gpu.cu:140-158`).
9. **Sztuczki asemblerowe (maxas, `src/sass/*.sass`):**
   - jawne przypisanie rejestrów pod banki rejestrów Maxwella (`xgemm_blocksparse_32x32x32_xprop.sass:75-104`);
   - ręczne kody sterujące (stall, yield, scoreboard) przy każdej instrukcji (`:572-578`);
   - 64 FFMA w kolejności „swirl” pod reuse cache (`:541-550`), a między nie wstawione LDG/STS/LDS na konkretnych pozycjach (`:426-539`);
   - podwójny bufor LDS (`swapBuf`): globalne ładowania kafla k+1 są wydawane w trakcie liczenia kafla k, a pętla ma **jedną barierę na iterację** (`:387-395`, `:527-532`);
   - LUT przetwarzany od końca (`:417-419`);
   - bf16→f32 przez samo maskowanie i przesunięcie (`:429-438`).
10. **Drobne triki CUDA-C:**
    - po pętli `tid` i `ctaid` są czytane ponownie przez `asm volatile`, żeby nie zajmowały rejestrów w pętli głównej (`bst_hgemm_op_gpu.cu:122-127`);
    - dzielenie przez magiczną stałą (`src/gpu_hmma.h:4-20`);
    - offsety 32-bitowe składane w 64-bitowy wskaźnik w asm (`blocksparse_matmul_gated_op_gpu.cu:148-157`);
    - listy wskaźników `Plist<T,8>`: jedno uruchomienie obsługuje do 8 tensorów (`blocksparse_hgemm_nc_op_gpu.cu:554-556`, `ew_op_gpu.cu:864`).
11. **Layernorm.** Jeden blok na wiersz i jednoprzebiegowe E[x²]−E[x]² (`src/layer_norm_nc_op_gpu.cu:31-79`). Drugi przebieg czyta X ponownie (`:88-102`). Wariant CN to 3 kernele: moments1, moments2 i apply (`layer_norm_cn_op_gpu.cu:8, 84, 149`).
12. **Brak trwałych kerneli RNN.** LSTM to tylko fuzja elementwise bramek (`src/lstm_op_gpu.cu:7-44`), a macierze rekurencyjne idą zwykłym bsmm co krok. Słowo „persistent” pojawia się w repo tylko w zakomentowanym `PersistentTensor` (`src/ew_op.cc:998`).
13. **Liczby z repo:** wykres przyspieszenia vs cuBLAS dla 12288 jednostek ukrytych, bloków 32×32 i minibatcha 32 na Titan X Pascal („orders of magnitude” przy dużej rzadkości; blog). W tekście nie ma tabeli z liczbami, tylko wykres.

## 3. Przeniesienie na AMD/HIP/RDNA3

| Technika | Da się? | Odpowiednik na gfx1100 / dlaczego nie |
|---|---|---|
| (1) LUT + prefetch do LDS | Tak, trywialnie | Już to robimy w innej formie: `ids`/`expert_bounds` w MMQ/MMVQ. Upstream ma w FA rzadki gather z listy indeksów (styl DSA), ale tylko na CUDA i F16 KV (`fattn.cu:129-132`, `fattn-mma-f16.cuh:421-424`). |
| (2) Atencja w 3 kernelach z zapisem wyników | Nie warto | Przestarzałe. Nasz `fattn-kvq` to online softmax w rejestrach i LDS. Zapis QKᵀ do HBM przy 94k kontekstu byłby katastrofą dla pasma. |
| (3) Bitmapa maski + ex2 | Częściowo już mamy | `fattn-kvq.cu:13, 226, 380` liczy w domenie log2 (`__builtin_amdgcn_exp2f`). Bitmapa ma sens tylko przy nieregularnych maskach. U nas maska jest causal lub pełna. |
| (4) LPT, segmentacja, z-order | Tak, ale mały zysk | FA prefill w HIP używa `KV_max` (`fattn-tile.cuh:954`), ale skan maski włącza się dopiero przy `Q->ne[1] >= 1024` (`fattn-common.cuh:1117`). Przy ub=512 każdy kafel Q liczy całe KV. Szacunek kosztu w §4 (idea 3): ~0.2%, więc nie warto. Kolejność kafli MMQ: zob. raport 03 (swizzle). |
| (5) Split-K pod spinlockiem | **Nie** | Kolejność sumowania jest niedeterministyczna, a my wymagamy bitowej zgodności. Nasz deterministyczny odpowiednik to „ostatni blok” z ticketem (0053, 0054). |
| (6) Kompaktacja ballot/popc | Tak | `__ballot` w wave32 daje maskę 32-bitową, a `v_mbcnt_lo_u32_b32` to dokładnie `popc(mask_niższych & ballot)`. Zastosowanie u nas jest wąskie, zob. §4. |
| (7) Redukcja przez wymianę połówek | Już mamy | K1: „transponowany butterfly DPP w epilogu”. Na RDNA3 `shfl_xor 16` to `v_permlanex16_b32` albo DPP row_share. |
| (8) Split-K między warpami przez LDS | Już mamy | `mmvq.cu:2517` (K podzielone między fale bloku, redukcja w shared). |
| (9a) Ręczne przypisanie rejestrów i kody sterujące | Nie wprost | Na gfx11 nie ma odpowiednika maxas, a HIP nie daje kontroli nad przydziałem VGPR. Najbliższy odpowiednik ograniczeń banków to **VOPD (dual-issue)**: operandy X i Y muszą leżeć w różnych bankach VGPR (nr % 4), a dst muszą mieć różną parzystość. Pilnuje tego tylko kompilator. Ma to znaczenie wyłącznie dla kerneli ograniczonych przez VALU (dekwantyzacja w `load_tiles` MMQ), a nie dla MMVQ. |
| (9b) Przeplot ładowań z matematyką + podwójny bufor + 1 bariera | **Tak, to najcenniejszy element** | `__builtin_amdgcn_sched_group_barrier(mask, n, id)` wymusza przeplot VMEM / DS / WMMA (używamy już w `fattn-common.cuh:422`). Prefetch global→VGPR kafla k+1 przed `vec_dot` kafla k. Nasza pętla MMQ (`mmq.cuh:909-942`) robi load → bariera → vec_dot → bariera dwa razy na iterację, czyli 4 bariery i zero nakładania. |
| (10a) Ponowny odczyt `tid` po pętli | **Nie** | Na gfx11 ID wątku jest w `v0` (spakowane x/y/z). Po nadpisaniu nie da się go odczytać ponownie (brak odpowiednika `S2R`). `blockIdx` jest w SGPR, więc nic nie kosztuje. Indeks lane można odtworzyć dwoma `v_mbcnt`. |
| (10b) Dzielenie magiczną stałą | Już jest | `init_fastdiv_values` / `fastdiv` w ggml-cuda. |
| (10c) `Plist`: wiele tensorów w jednym uruchomieniu | Już w dużej mierze mamy | MMVQ_PAIR, fuzje A3-A6, 0049-0054. |
| (11) Layernorm | Nie warto | Nasz `rms_norm*mul(+q8_1)` z DPP (4.51 µs) jest lepszy. E[x²]−E[x]² jest gorsze numerycznie. Wariant 3-kernelowy kosztowałby u nas ~2.5 µs na każdą granicę. |
| (12) Trwały kernel RNN | n/d | W repo go nie ma. Nasze pomiary (`lfm-decode-round2.md` §1) już dały odpowiedź: bariera siatki 0.5–0.8 µs vs granica 2.5 µs. Wymaga przepisania dużych matvec na pętle grid-stride. |

## 4. Pomysły dla nas

**1. MMQ (prefill): prefetch kafla k+1 do VGPR plus jedna bariera na iterację, czyli wzorzec `swapBuf` z `xgemm_blocksparse_32x32x32_xprop.sass:387-395, 527-532`.**
- Co zmienić: `mul_mat_q_process_tile` w `mmq.cuh:909-942`, tylko RDNA3:
  1. na początku iteracji wydać `load_tiles` i `tile_y` dla kafla k+1 do rejestrów (bez zapisu do LDS);
  2. policzyć `vec_dot` na kaflu k z LDS;
  3. bariera;
  4. zapis rejestrów do LDS;
  5. bariera.
  Dwie połówki `tile_y` (`:912-918` i `:928-934`) można scalić w jeden kafel, jeśli LDS pozwala.
- Dlaczego rejestry zamiast podwójnego LDS: przy Q4_K I=64 i J=128 (`mmq-config-rdna3.cuh:113-123`) kafle x+y to ~36 KB, więc podwójny bufor nie mieści się w 64 KB na workgroup `[WNIOSEK, przybliżony rachunek z MMQ_DP4A_TXS_* / MMQ_TILE_Y_K]`. Staging w VGPR to ~18 (x) + ~36 (y) VGPR na wątek przy 128 wątkach, co przy obłożeniu 1 jest do przyjęcia `[WNIOSEK]`.
- Przeplot: `__builtin_amdgcn_sched_group_barrier` (VMEM read 0x20, WMMA/MFMA 0x8, DS read 0x100) rozkłada ładowania między instrukcje WMMA w `vec_dot`. To odpowiednik wstawek `j0c52` i podobnych w SASS.
- Oczekiwany zysk `[SZACUNEK]`: MMQ ma dziś obłożenie 1–2 i opóźnienie pamięci ukrywa tylko ILP. Realistycznie +10–20% przepustowości MMQ, czyli +6–12% prefillu (MMQ to większość czasu przy 1.7–30k).
- Bitowość: tak, bo arytmetyka i kolejność sum się nie zmieniają.
- Koszt: 1–3 dni. Ryzyko: średnie (spille VGPR, kompilator może przestawić ładowania z powrotem; stąd `sched_group_barrier`). Nie dotyczy kerneli z `fixup` w inny sposób.
- Pomiar: `llama-bench -p 4096 -d 0,16384` (pp t/s), rocprofv3 czasy `mul_mat_q<*>` per typ, `test-backend-ops -o MUL_MAT`, hash logitów.
- Uwaga: raport 03 (DeepGEMM, §3 pkt 6) proponuje to samo z innej strony. blocksparse daje gotowy, sprawdzony wzorzec pętli.

**2. Draft MTP z blokowo-rzadką atencją (sink + okno lokalne + top-k bloków), weryfikacja gęsta, więc wynik bezstratny.** To pomysł spoza schematu.
- Nowy argument wobec negatywnego S3 (NOTES:327): S3 z oknem W=8192 wycinało cały daleki kontekst i akceptacja spadała 3.31 → 2.78. Layout w stylu Sparse Transformer / Quest zachowuje bloki, które pasują do zapytania. Do tego potrzebne są:
  - streszczenie każdego bloku 64 tokenów K (np. min/max per kanał), dopisywane przy `set_rows` K;
  - wybór top-k bloków per głowa KV;
  - gather w `fattn-kvq` według LUT (jak `Lut2s` w `bst_hgemm_op_gpu.cu:56-66`).
- Górna granica zysku z pomiarów S3: −0.5 ms/krok przy 27k, −1.6 ms przy 62k, przy 94k pewnie ~−2.5 ms z ~30 ms, czyli ≤8%, i tylko jeśli akceptacja się utrzyma `[SZACUNEK]`.
- Koszt: 1–2 tygodnie (streszczenia, top-k, gather, osobna ścieżka dla draftu). Ryzyko: wysokie. Dochodzą +2–3 uruchomienia na przebieg draftu (~2.5 µs każde) i niepewna akceptacja.
- Pomiar: `long_ctx_bench` przy 29.5k i 94k, tok/krok vs gęsty draft, ms/krok.
- Priorytet: niski, dopiero po wyczerpaniu tańszych pomysłów na długi kontekst.

**3. Pomijanie bloków causal w FA prefill (KV_max przy ub=512): sprawdzone rachunkiem, nie warto.**
- Zmiana progu w `fattn-common.cuh:1117` (`>= 1024` → `>= 512` na HIP) jest jednolinijkowa i prawdopodobnie bitowa: pominięte kafle są w całości −inf, więc wnoszą dokładnie 0.
- Rachunek `[WNIOSEK, model liniowy]`:
  - z NOTES:331 (prefill 985 t/s przy 6.6k, 766 t/s przy 94k) koszt FA to ~0.29 ms/token na 44k dodatkowych wierszy KV, czyli ~6.6 ns na parę (token, wiersz KV);
  - zmarnowane wiersze to ~256 (trójkąt w ubatchu) plus ~128 (padding n_kv do 256), czyli ~2.5 µs na token przy ~1 ms na token;
  - zysk ≈ **0.2%**.
- Harmonogram LPT (`bst_hgemm_op_gpu.cu:41-43`) ma sens dopiero przy dużej nierównowadze, a przy ub=512 i długim prefiksie jej nie ma. Nie robić.

**4. Kompaktacja ballot/mbcnt w kernelu (`blocksparse_matmul_gated_op_gpu.cu:83-123`) dla MoE z wieloma tokenami.**
- Przydałoby się tylko przy spekulacji dla LFM (weryfikacja k tokenów, do 4k różnych ekspertów na warstwę, NOTES:341): para (ekspert, token) kompaktowana w MMVQ_ID bez osobnego kernela sortującego.
- Dziś LFM nie ma spekulacji, więc pomysł jest **odłożony**. Zysk = jedna granica uruchomienia na warstwę MoE (~2.5 µs × 38), ale tylko w tym scenariuszu `[SZACUNEK]`.

**5. Diagnostyka VOPD (z §3, 9a).**
- Po pomyśle 1, w ISA kernela MMQ policzyć `v_dual_*` względem par VALU, które mogłyby iść razem (`--save-temps`).
- Jeśli dekwantyzacja Q4_K/Q5_K w `load_tiles` prawie nie korzysta z VOPD, pomóc może przestawienie niezależnych operacji (np. przetwarzanie dwóch wierszy naprzemiennie).
- Zysk nieznany `[SZACUNEK: 0–5% MMQ]`. Koszt: godziny na samą diagnozę.

## 5. Krytyka

- **Nieaktualne:**
  - SASS/maxas (tylko Maxwell i Pascal, README:11-20);
  - TF1 i treningowa reszta: stochastic rounding (`quantize_op_gpu.cu:7-101`), Adam/Adafactor, dropout, `group_param_grads`;
  - atencja z wynikami QKᵀ w pamięci (przed FlashAttention);
  - layernorm jednoprzebiegowy E[x²]−E[x]² (słaba numeryka);
  - spinlock split-K (niedeterministyczny).
- **Przesadzone:** „orders of magnitude faster than cuBLAS” (blog) dotyczy dużej rzadkości (wiele zerowych bloków) i trenowania od zera z rzadkim layoutem. Dla gęsto wytrenowanych modeli (Qwen3.8, LFM2.5) rzadkość wag lub atencji to przybliżenie zmieniające wyjście. Wymagałoby to przycinania i dotrenowania, a dekodowanie zależne od pamięci zyskałoby tylko proporcjonalnie do gęstości bloków.
- **Nieistotne dla dekodowania u nas:** nasze wąskie gardła to koszt uruchomień (LFM) i pasmo MMVQ przy 1 i 5 kolumnach. Repo nie ma nic o matvec, kwantyzowanych wagach ani grafach i launch overhead.
- **Pytania z briefu:**
  - trwałych kerneli RNN w repo nie ma (zob. pkt 12 w §2);
  - redukcje blokowane w rejestrach, które ma, już stosujemy (K1, `mmvq.cu:2517`);
  - rzadka atencja blokowa dla długiego kontekstu ma u nas sens wyłącznie jako przybliżenie w drafcie (§4.2).
- **Wartość historyczna:** wzorzec potoku ładowań (§3, 9b) i dyscyplina „jedna bariera na iterację” są uniwersalne. To najważniejsza nauka z kodu Graya, ale nie jest unikalna dla tego repo.

## 6. Werdykt

**Niska.** Jedyny przenośny, konkretny element to wzorzec potokowania pętli GEMM (prefetch + podwójny bufor + jedna bariera) dla naszego MMQ w prefillu, a ten pomysł mamy już z raportu 03. Reszta jest przestarzała (SASS dla Maxwella, atencja z zapisem wyników), nie pasuje do bitowej zgodności (spinlock split-K) albo dotyczy rzadkości, której nasze gęste modele nie mają.
