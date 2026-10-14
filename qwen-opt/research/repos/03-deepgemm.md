# 03 — deepseek-ai/DeepGEMM

Klon: `--depth 1`, HEAD `1fc9c66` (2026-10-14), ~2.8 MB, 160 plików. Nic nie było budowane ani uruchamiane. Ścieżki `plik:linia` są względem korzenia repo. „Nasz kod” to `~/llama-master/ggml/src/ggml-cuda/` (gałąź robocza `5909da1f1`). Liczby z repo to pomiary DeepSeek na ich sprzęcie (H800/B200), nie nasze.

## 1. Co to jest

DeepGEMM to biblioteka kerneli tensor-core od DeepSeek: GEMM FP8/FP4/BF16 (dense, grouped MoE contiguous/masked, k-grouped do wgrad), skoring MQA dla indeksera DSA, HyperConnection i od 2026 „Mega MoE” (dispatch EP + L1 + SwiGLU + L2 + combine w jednym kernelu). Wszystkie kernele są kompilowane przez JIT (NVCC w runtime) z kształtem i konfiguracją jako stałymi szablonu. Repo jest bardzo aktywne (newsy 2026-04, 09-10, 09-30; port na Ascend), licencja MIT. Działa tylko na NVIDIA SM90/SM100 (README:31); kod mocno zależy od TMA, WGMMA/tcgen05, TMEM, klastrów 2-CTA, PDL i NVLink. **Nie ma tu żadnego kodu, który dałoby się skompilować na gfx1100.** Wartość dla nas leży w pomysłach na harmonogramowanie, synchronizację i skalowanie.

## 2. Kluczowe techniki (z dowodami)

1. **Dwupoziomowa akumulacja z „promocją” co blok skali.** WGMMA FP8 akumuluje po `BLOCK_K = 128` (`impls/sm90_fp8_gemm_1d2d.cuh:56`, `305-319`). Potem wynik jest mnożony przez `scale_a * scale_b` i dodawany do akumulatora FP32 na CUDA cores (`:329-345`, `final_accum` w `:254`). Powód na Hopperze: akumulator FP8 tensor core ma ograniczoną precyzję. Skala aktywacji ma ziarno 1×128 (per token), skala wag 128×128. SM100 obsługuje też `gran_k` = 32 (`docs/scaling-factor-format.md:29`). Skale muszą być potęgami 2 (UE8M0, `:33`).
2. **Grouped GEMM tylko po osi M** (README:76-86):
   - *contiguous*: tokeny ekspertów sklejone, każdy segment wyrównany do `BLOCK_M`, a `m_indices = -1` w paddingu pomija obliczenia (`scheduler/gemm.cuh:296-300`; legacy Triton `legacy/m_grouped_gemm.py:35-40`);
   - wariant *psum*: prefiks sum końców ekspertów (`scheduler/gemm.cuh:205-225`);
   - *masked*: liczba tokenów na eksperta czytana na GPU, więc całość przechwytuje się w CUDA graph bez wiedzy CPU (`:188-204`).
3. **Trwały (persistent) grid ze swizzlingiem kafli pod L2.** Grid ma rozmiar = liczba SM (`sm90_fp8_gemm_1d2d.hpp:202`), a pętla to `get_next_block` z krokiem `kNumSMs` (`scheduler/gemm.cuh:185-187`). Kafle są grupowane po 8 albo 16 bloków, a rozmiar grupy wybiera minimalizacja „śladu” A+B (`:14-26`, `108-144`).
4. **Heurystyka konfiguracji jako model kosztu.** Kandydaci (BM, BN, klaster) są filtrowani: co najmniej 3 etapy pipeline'u, a dla małych kafli co najmniej 4 (`heuristics/sm90.hpp:105-108`). Wybór robi model cykli L1/L2 podzielony przez efektywność ostatniej fali (`:202-238`, `wave_efficiency` w `:231`). Dla MoE model używa *oczekiwanego* M, nie maksymalnego (`expected_m`, `sm90_fp8_gemm_1d2d.hpp:169-171, 238`).
5. **JIT ze specjalizacją kształtu.** Kod kernela jest generowany z wartościami szablonu: BM/BN/BK, swizzle, etapy, wątki i opcjonalnie stałe M/N/K (`sm90_fp8_gemm_1d2d.hpp:30-61`). Domyślnie `compiled_dims="nk"`: wymiary wag są stałe, M (tokeny) dynamiczne (`csrc/apis/gemm.hpp:842`, `runtime_utils.hpp:31-33`). Do tego jest dyspozycja runtime→constexpr dla małego zbioru wartości (`dispatch_num_former_iters`, `1d2d.cuh:26-35, 273-279`).
6. **Specjalizacja warp-group.** Jeden warp TMA jest producentem, warp-groupy WGMMA konsumentami, a `setmaxnreg` przenosi rejestry: 40 dla producenta, 232-248 dla matmul (`1d2d.cuh:145-146, 165-215`). PDL (`cudaGridDependencySynchronize`, `:149`) nakłada prolog na ogon poprzedniego kernela.
7. **Mega MoE: trwały kernel z kolejką zadań i drobnoziarnistymi zależnościami** (`scheduler/mega_moe.cuh`):
   - zadania L1 (gate/up) i L2 (down) są pobierane z atomowych liczników (`:344-361`);
   - **zadanie L2 jest wydawane dopiero wtedy, gdy wszystkie potrzebne zadania L1 zostały już *pobrane*** przez działające CTA (`:398-402`). Zakleszczenie jest więc niemożliwe bez gwarancji współrezydencji;
   - liczba „rozgrzewkowych” fal L1 jest wyliczana w closed-form (`:15-45`);
   - gotowość wejścia L2 jest śledzona **per blok K** maską bitową: producent robi `red.xor.release` swojego bitu, konsument czeka tylko na bity potrzebnego bloku K (`:140-166`). Parzystość maski per generacja ringu pozwala obejść się bez zerowania;
   - opcjonalny work-stealing między domenami lokalności, wyłączany przy małej liczbie zadań (`:223-228, 363-370`).
8. **Epilog L1 w Mega MoE.** SwiGLU, potem mnożenie przez wagę top-k, potem amax i kwantyzacja do FP8 ze skalą, wszystko przed zapisem (`impls/sm100_fp8_fp4_mega_moe.cuh:1066-1155`). Żeby gate i up tego samego kanału trafiały do jednego kafla, wagi L1 są przeplatane co 8 wierszy (`deep_gemm/mega/__init__.py:112-113, 154-162`). Kombinacja top-k jest robiona na końcu tego samego kernela (`:1365-1424`; komentarz „1 token 1 topk latency: ~3 us”).
9. **Bariery z epoką zamiast zerowania.** Stan bariery koduje `(grid_idx+1)*N + liczba_przybyłych`, więc nie trzeba go resetować między uruchomieniami grafu (`scheduler/mega_gate.cuh:11-39`). Mega Gate to fuzja BF16 router GEMM + top-k (`csrc/apis/mega_gate.hpp`, komentarz API), czyli odpowiednik naszego 0053.
10. **Liczby z repo (pomiary DeepSeek, EP8, PR #316):** Mega MoE dla V4-Flash przy 1 tokenie/rank trwa 56.5 µs, to 1311 GB/s i 1.96× vs legacy; przy 512 tokenach 1056 TFLOPS. README:25: do 1550 TFLOPS FP8 na H800. Komentarz w PR #316: na Hopperze (bez TMEM) Mega MoE „performance is not significant”. https://github.com/deepseek-ai/DeepGEMM/pull/316

## 3. Przeniesienie na AMD/HIP/RDNA3

| Technika | Da się? | Jak na gfx1100 / dlaczego nie |
|---|---|---|
| (1) Promocja co blok skali | **Tak, ale w innej formie.** | Na RDNA3 iu8 WMMA akumuluje w int32 **dokładnie**, więc jedynym powodem promocji jest ziarno skal. U nas promocja jest co K=32 (q8_1): `mmq-vec-dot.cuh:352-362` dla każdego z 8 elementów C robi cvt i32→f32, odczyt `x_dm` z LDS w pętli `j0`, cvt f16→f32, mul, 2×fma. To ok. 6 instrukcji VALU na element na 2 instrukcje WMMA. Q6_K już częściowo trzyma skale całkowite (`:1143-1160`, `dA` raz na 256). Odpowiednik DeepGEMM: aktywacje z jedną skalą na 128/256 K, a całkowite sub-skale K-quantów (6/8 bit) wliczane w int32 (`v_mad_i32_i24`), czyli jedna FMA float na 128/256 zamiast na 32. Int32 nie przepełnia się (Q4_K: 15·127·32·63·8 ≈ 3.1e7). **Uwaga:** int8 per-128 to nie FP8 per-128, bo int8 nie ma zakresu dynamicznego w bloku, więc outlier w bloku 128 zjada rozdzielczość pozostałych wartości. |
| (2) Grouped contiguous/masked | Już mamy. | `mmq.cu:308-322` (`ids_dst`, `expert_bounds` = psum), `mmq.cu:193-202` (dobór kafla wg średniej liczby tokenów na eksperta na RDNA3, czyli `expected_m`). Masked dla dekodu odpowiada `mmvq` z `ids` w grafie. Nic nowego. |
| (3) Persistent + swizzle L2 | Częściowo. | RDNA3 MMQ nie używa stream-k (`mmq-config-rdna3.cuh:113-147`, 8. pole `false`). Kolejność kafli `jt`-najszybciej już daje reuse wag. Aktywacje prefillu (512×5120 q8 ≈ 2.8 MB) mieszczą się w L2 6 MB, warstwa wag w MALL 96 MB. Swizzle da mało `[WNIOSEK]`. Ważniejsza jest efektywność ostatniej fali przy 96 CU i occupancy 1–2. |
| (4) Model kosztu w heurystyce | Tak. | Liczy się na hoście w `mmq.cu` przy wyborze `J_best`/I/occupancy. Mamy już punktową poprawkę K5 (alpha/beta 5120×48). Brakuje ogólnej reguły „fale × efektywność ostatniej fali” dla wszystkich kształtów. |
| (5) JIT per kształt | Tak, AOT zamiast JIT. | Model ma kilka różnych K/N, więc zamiast NVCC w runtime można wygenerować instancje szablonu dla kształtów modelu (hipRTC istnieje, ale nie jest potrzebny). Dla MMVQ mamy wynik negatywny dla rozwijania pętli K (NOTES:351), więc tam spodziewany zysk jest mały. |
| (6) Warp specialization + pipeline TMA | Tylko idea. | Brak TMA, `cp.async`, `setmaxnreg` i nazwanych barier (jest jedno `s_barrier` na workgroup). Odpowiednik to prefetch global→VGPR następnego kafla K przed obliczeniem bieżącego plus podwójny bufor LDS (64 KB/CU wystarcza). Nasz MMQ tego nie robi: `mmq.cuh:909-942` to load → `__syncthreads` → vec_dot → `__syncthreads` (4 bariery na iterację K=256, bez nakładania). Opóźnienie ukrywa tylko occupancy 1–2. |
| (7) Kolejka zadań + zależności per blok K | **Tak, bezpośrednio.** | Atomiki `__hip_atomic_fetch_add` (scope agent), polling `__hip_atomic_load(..., __ATOMIC_ACQUIRE, __HIP_MEMORY_SCOPE_AGENT)` z `s_sleep`, maska bitów `atomicXor` z release. Niezmiennik „konsument czeka tylko na zadania już pobrane” działa na HIP bez cooperative launch. Nie przeniosą się klastry 2-CTA, NVLink i TMEM. |
| (8) Epilog SwiGLU, przeplot gate/up | Tak. | Wiersze K-quantów są niezależne, więc przeplot wierszy gate/up co g da się zrobić przy ładowaniu modelu, gdy typy gate i up są równe. W MMQ epilog liczyłby silu(g)·u i od razu pisał q8_1 (mamy już producentów q8_1, A6). Mnożenie przez wagę top-k przed kwantyzacją zmienia numerykę (u nas waga jest w down, 0051). |
| (9) Bariery z epoką | Tak, drobiazg. | Na AMD nie ma `%gridid`. Epokę może inkrementować ostatni blok w liczniku urządzenia. Nasze tickety już działają; daje to tylko uproszczenie (bez resetu). |
| FP8/FP4, UE8M0, TMEM, PDL, domeny lokalności | Nie. | gfx1100 nie ma FP8 ani PDL. iu4 WMMA wymaga 4-bitowych *obu* operandów (aktywacje int4 zabiłyby jakość) `[WNIOSEK]`. Domeny lokalności (dwa die B200) nie mają odpowiednika: 7900 XTX ma jeden GCD, a MCD/MALL są przeplatane adresowo. |

## 4. Pomysły dla nas

### P0. Ablacja „speed-of-light” promocji w MMQ (prefill, Qwen i LFM)
- **Co zmienić:** wariant diagnostyczny (makro) w `mmq-vec-dot.cuh` (`ggml_cuda_mmq_vec_dot_q8_1_q8_1_mma` z `:313` i Q6_K z `:1011`). Druga połowa robi to samo ze stagingiem LDS.
  - Najpierw sprawdzić w ISA (`--save-temps`), czy `x_dm[...]` (`:359`) jest wyciągane z pętli `j0`. Jeśli nie, przenieść `dmA` do rejestrów jak w ścieżce NVIDIA (`:382-406`). To jest bitowo identyczne.
  - Potem wariant błędny celowo: `sum += (float)C` bez skal.
  - Osobno wariant bez `load_tiles` (stałe kafle).
- **Zysk:** to pomiar, nie optymalizacja. Rozstrzyga, czy ~50 z 123 TFLOPS to promocja, ładowanie i bariery, czy WMMA. `[SZACUNEK]`: jeśli WMMA iu8 16×16×16 zajmuje ~32 cykle SIMD i nie nakłada się z VALU, promocja (~48 VALU na 2 WMMA) może kosztować 30–45% czasu matmul. Samo wyciągnięcie `dmA` mogłoby dać kilka %.
- **Koszt:** 0.5–1 dnia. **Ryzyko:** brak. **Pomiar:** `llama-bench -p 4096 -n 0` i rocprofv3 `mul_mat_q` na kształtach Qwen (5120×17408, 17408×5120) oraz LFM MoE.

### P1. Pipeline MMQ na RDNA3: prefetch global→VGPR + podwójny bufor LDS (prefill)
- **Co zmienić:** `mul_mat_q_process_tile` (`mmq.cuh:909-942`):
  - globalne odczyty `x`/`y` dla `kb0+blocks_per_iter` wydawać przed `vec_dot` bieżącego kafla, do rejestrów;
  - po obliczeniu zapisać je do drugiego bufora LDS;
  - liczba barier na iterację spada z 4 do 1–2.
  
  Odpowiada to wymaganiu DeepGEMM „≥3–4 etapy” (`sm90.hpp:105-108`) w wersji bez TMA. Prefetch w GDN/FA był negatywny (NOTES:324), ale MMQ ma inny profil: duże kafle, occupancy 1–2.
- **Zysk `[SZACUNEK]`:** +5–15% przepustowości MMQ, czyli +3–10% prefillu, jeśli P0 pokaże, że winne są ładowanie i bariery.
- **Koszt:** 2–4 dni (VGPR dla bufora prefetchu przy occupancy 1 jest; trzeba ponownie zbalansować I/J). **Ryzyko:** spill rejestrów, spadek occupancy. Wynik bitowo identyczny, bo kolejność akumulacji się nie zmienia.
- **Pomiar:** jak w P0 plus `test-backend-ops -o MUL_MAT` i hash logitów.

### P2. Aktywacje q8 z jedną skalą na 128 (albo 256) K i całkowite sub-skale K-quantów w int32 (prefill)
- **Co zmienić:**
  - nowy format aktywacji MMQ: `block_q8_128` = 128 int8 + d + sumy per 32 dla członu min;
  - nowe `load_tiles` dla Q4_K/Q5_K/Q6_K/IQ4_XS, które zostawiają w LDS całkowite `sc`/`m` (jak układ Q6_K);
  - vec_dot: `acc_i32 += C*sc` (`v_mad_i32_i24`) przez 4 (8) sub-bloków, potem 1 FMA float.
  
  To bezpośrednie przeniesienie promocji 1×128 z DeepGEMM (`1d2d.cuh:329-345`).
- **Zysk `[SZACUNEK]`:** do 4–8× mniej VALU na promocję. Realnie +10–25% MMQ, jeśli P0 wskaże promocję jako wąskie gardło.
- **Koszt:** 1–2 tyg. **Ryzyko:** **jakość** (int8 per-128 ma gorszą rozdzielczość niż per-32 przy outlierach po RMSNorm) i brak bitowej zgodności.
- **Pomiar:** KLD/PPL (`llama-perplexity`, batch 512) vs baza; porównać z szumem batch 6 vs 512 (KLD 0.0036–0.0098 z NOTES). Tylko prefill; dekod (MMVQ) bez zmian.

### P3. LFM2.5 dekod: trwały kernel bloku MoE (gate+up → SwiGLU+q8_1 → down+reduce+res) w stylu Mega MoE
- **Co zmienić:** nowy kernel obok `mul_mat_vec_q` dla `MUL_MAT_ID` n=1, przełącznik `GGML_HIP_MOE_PERSIST`.
  - Grid = rezydentne bloki, np. 96 CU × W.
  - Zadania L1 to wiersze gate/up (4 eksperty × 1536 / R). Zadanie L1 kończące grupę 32 kanałów pisze blok q8_1 (jak tickety w 0054) i ustawia bit w masce eksperta (`atomicXor`, release).
  - Zadania L2 to wiersze down (2048 / R, suma po 4 ekspertach jak w 0051) i są pobierane z drugiego licznika.
  - Konsument L2 przetwarza bloki K w kolejności gotowości i czeka tylko na bity potrzebnego bloku K (`mega_moe.cuh:140-166`).
  - Kluczowy jest niezmiennik z `mega_moe.cuh:398-402`: L2 pobierane dopiero po pobraniu wszystkich L1, więc brak zakleszczenia i krótkie czekanie. Nasz test łańcucha z 1024-blokowymi fazami (8–11 µs/fazę, `lfm-decode-round2.md:33-37`) tracił, bo tysiące czekających bloków głodziły producentów. Tu czekających jest najwyżej tyle, ile bloków rezydentnych, i czekają na pojedyncze bity, a nie na całą fazę.
  - Krok 2: dołożyć fazę 0 = norm+router+top-k (0053) jako pierwsze zadania, a L1 czeka na bit „top-k gotowe”.
- **Zysk `[SZACUNEK]`:** −2 granice i −1 kernel `quantize_q8_1` na warstwę MoE: 38 × (2×2.5 + 1.3 − ~1.5 µs ogona/czekania) ≈ 0.18 ms. Z krokiem 2 ≈ 0.27 ms, czyli z 4.10 do ~3.85 ms/token (+6–7% t/s). Obliczenia per wiersz takie same jak w obecnych kernelach, więc wynik może być bitowo identyczny.
- **Koszt:** 1–1.5 tyg. **Ryzyko:**
  - pasmo matvec w formie grid-stride może spaść poniżej ~700 GB/s (mniej fal w locie);
  - ogon L1→L2;
  - „slow mode” gate+up (round2 3b) utrudnia pomiar.
- **Pomiar:** `ab.sh` (przeplatany llama-bench tg128), rocprofv3 `tok.py`, hash logitów `lh.sh`, `test-backend-ops MOE_DOWN_REDUCE`/`MUL_MAT_ID`.

### P4. Przeplot wierszy gate/up przy ładowaniu + epilog SwiGLU→q8_1 w MMQ (prefill Qwen, LFM)
- **Co zmienić:** przy ładowaniu, gdy `type(gate)==type(up)`, zbudować tensor [2·ffn, K] z wierszami przeplatanymi co g ≤ I/2 (`mega/__init__.py:112-113`), zamiast dwóch osobnych. MMQ z flagą epilogu: para (g,u) w tym samym kaflu daje silu(g)·u, które od razu idzie do q8_1 (`block_q8_1_mmq`) dla down.
- **Zysk `[SZACUNEK]`:** Qwen, ubatch 512: znika zapis i odczyt 2 × 35.7 MB f32 na warstwę oraz kernel swiglu, ok. 9 GB na ubatch, ≈11 ms z ~540 ms, czyli ~2%. Plus jeden launch mniej na warstwę w dekodzie, ale MMVQ_PAIR już to częściowo daje.
- **Koszt:** 3–5 dni. **Ryzyko:**
  - UD-quanty mogą mieć różne typy gate/up (sprawdzić GGUF);
  - zmiana layoutu wag psuje mmap; potrzebna kopia, a VRAM jest ciasny przy ctx 204800, więc przeplot trzeba robić w miejscu podczas uploadu.
- **Pomiar:** pp4096, hash logitów (powinny być bitowo równe, jeśli swiglu i q8_1 liczą to samo w tej samej kolejności).

### P5. Model kosztu dla wyboru kafla MMQ na RDNA3
- **Co zmienić:** w `mmq.cu:205-247` zamiast „najmniej kafli w J” liczyć `waves = ceil(tiles / (CU·occupancy))` i efektywność ostatniej fali (`sm90.hpp:202-238`) dla (I, J, occupancy) z `mmq-config-rdna3.cuh`, plus ewentualnie split-K przy mniej niż 1 fali.
- **Zysk `[SZACUNEK]`:** 0–5% na nierównych kształtach (down 17408→5120, LFM MoE z ragged ekspertami). K5 pokazał, że przypadki skrajne istnieją (932→249 ms).
- **Koszt:** 1–2 dni. **Ryzyko:** niskie. **Pomiar:** sweep `test-backend-ops perf -o MUL_MAT` na kształtach modelu.

### Outside the box
- **„Claim-order” jako ogólny wzorzec fuzji w dekodzie.** Każda para producent→konsument z małymi fazami (attn: q-norm/rope → set_rows → FA → combine; ~11 launchy na warstwę w LFM, round2 §5) może iść jednym trwałym gridem z kolejką atomową i bitami gotowości. To uogólnienie P3, które może zjechać z 416 kerneli/token wyraźnie niżej bez spinających się tysięcy bloków.
- **Skale UE8M0 dla q8 aktywacji** (potęgi 2): promocja jako `v_ldexp_f32` zamiast mul. Ma sens tylko w parze z P2; sam zysk mały.
- **Epoka zamiast resetu liczników** (`mega_gate.cuh:17-38`): upraszcza tickety 0053/0054 i chroni przed „brudnym” licznikiem po przerwanym grafie.

## 5. Krytyka
- Prawie cały kod to Hopper/Blackwell (TMA, WGMMA, tcgen05/TMEM, setmaxnreg, klastry, PDL, NVLink symmetric memory). Do przeniesienia nadają się tylko algorytmy harmonogramu i formaty, nie implementacja.
- Liczby (1550 TFLOPS, 1.96×) są dla serwerów EP8 i FP8/FP4. Przy 1 tokenie Mega MoE osiąga 1311 GB/s, czyli ~16% pasma B200 (PR #316). Nawet DeepSeek nie zrobił z dekodu batch-1 kernela pasmowego: fuzja skraca latencję, ale nie nasyca pamięci. Zgadza się to z naszym obrazem (MoE w LFM jest launch-bound, nie FLOP-bound).
- Sam autor przyznaje, że bez TMEM (Hopper) Mega MoE niewiele daje (komentarz w PR #316). Dla RDNA3 realna część to kolejka zadań i zależności, nie nakładanie komunikacji.
- Grouped GEMM contiguous/masked i dobór kafla wg oczekiwanego M już są w llama.cpp (`mmq.cu:193-202, 308-322`), więc tu nic nowego.
- Promocja co 128 u DeepSeek wynika z precyzji akumulatora FP8. U nas int32 jest dokładny, a ograniczeniem jest ziarno skal q8_1/K-quantów. Przeniesienie wymaga zmiany formatu aktywacji (ryzyko jakości), nie tylko kernela.
- JIT per kształt rozwiązuje problem PyTorch (dowolne kształty w runtime). My znamy kształty przy ładowaniu, a rozwijanie K w MMVQ już okazało się bez zysku. JIT (hipRTC) nie jest wart infrastruktury.

## 6. Werdykt
**Średnia.** Kod jest nieprzenośny, ale dwa mechanizmy trafiają w nasze wąskie gardła: kolejka zadań z niezmiennikiem „konsument czeka tylko na pobrane zadania” plus maski gotowości per blok K (P3, launch-bound MoE LFM) oraz dwupoziomowa promocja i pipeline (P0–P2, prefill ~50 z 123 TFLOPS). Zacząć od taniej ablacji P0, bo ona rozstrzyga, czy P1 albo P2 mają sens.
