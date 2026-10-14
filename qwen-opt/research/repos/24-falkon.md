# 24 — FalkonML/falkon

Repo: https://github.com/FalkonML/falkon (klon `--depth 1`, HEAD `04f168e` z 2026-05-13 „Simplify TRSM (#71)”). Artykuł: [Kernel methods through the roof (arXiv 2006.10350)](https://arxiv.org/abs/2006.10350).

## 1. Co to jest
Biblioteka do aproksymowanej regresji grzbietowej z jądrem (Nyström + PCG) w PyTorch, z rozszerzeniem C++/CUDA (cuBLAS/cuSOLVER/cuSPARSE) i opcjonalnie KeOps. Celem są miliardy punktów: macierzy jądra nigdy nie trzyma się w całości, liczy się ją blokami, także poza pamięcią GPU (out-of-core), na wielu GPU. Licencja MIT, repo utrzymywane (wheels dla torch 2.4–2.7, CUDA 11.8–12.8), ale ostatnie zmiany to porządki. Docelowy sprzęt to NVIDIA i operacje FP32/FP64. Build ROCm istnieje tylko jako hipify przez PyTorch (`setup.py:102-106`).

## 2. Kluczowe techniki (z dowodami)
1. **Iloczyn macierz jądra × wektor bez materializacji macierzy**: pętla po blokach (N×M), blok `K(X1_i, X2_j)` liczony w buforze GPU, od razu `addmm_` z `v` (`mmv_ops/fmmv.py:337-400`). To ten sam pomysł co flash-attention („przelicz zamiast zapisywać”), tylko na poziomie wywołań torch, bez fuzji w jednym kernelu.
2. **Podwójny iloczyn `K^T (K v + w)` z jednym obliczeniem bloku** (`fmmv.py:697`, `755-760`): każdy blok `K` jest użyty dwa razy, w `w += K v` i `out += K^T w`, więc koszt generacji bloku rozkłada się na dwa GEMV.
3. **Strumieniowanie CPU→GPU na 2 strumieniach**: `_init_two_streams` (`fmmv.py:43-57`). Kopia `v`/`w` idzie na `s2`, obliczenie na `s1`, ale **po każdym bloku jest `s2.synchronize()` i `s1.synchronize()` z hosta** (`fmmv.py:296-299`, `390-393`, `757-762`). Nakładanie jest więc tylko wewnątrz jednej iteracji i blokuje hosta.
4. **Pamięć hosta pinned dla wejść i wyników** (`models/falkon.py:277-285`, `mmv_ops/utils.py:145-154`, `ooc_ops/ooc_potrf.py:178`, `utils/tensor_helpers.py:36-50`). Kopie 2D idą przez `cublasSetMatrixAsync`/`GetMatrixAsync` (`c_ext/ops/cuda/parallel_potrf.cu:55-102`).
5. **Out-of-core Cholesky na wielu GPU** (`parallel_potrf.cu`):
   - 3 strumienie na urządzenie (`:128-130`);
   - podwójne buforowanie kolumn `col0/col1` z naprzemiennym strumieniem odsyłania (`:220-241`);
   - tablica atomowych liczników `work[i][j]` jako graf zależności, inkrementowana z `cudaStreamAddCallback` (`:46-52`, `:258`, `:285`, `:329`);
   - wątki CPU czekają w pętli `while (work[..] != ..) yield()` (`:247`, `:265`, `:306`, `:310`).

   Po prawie każdej operacji jest `cudaStreamSynchronize(s1)` (`:252`, `:282`, `:327`, `:333`), więc GPU nie dostaje kolejki pracy, tylko pojedyncze kroki.
6. **Out-of-core LAUUM** (`ooc_ops/parallel_lauum.py:49-222`): jeden płaski bufor GPU alokowany z góry i dzielony na widoki (`:70-82`), kopiowanie tylko potrzebnych wierszy kolumny (`:86-94`), `threading.Barrier` między GPU (`:95-99`), drugi strumień dla LAUUM (`:120-155`).
7. **Siatka trójkątna 1D**: `blockIdx.x` → (wiersz, kolumna) kafla przez `row = (-1+sqrt(8i+1))/2` (`cuda_helpers.cuh:96-110`), uruchamia tylko `g(g+1)/2` kafli (`cuda_lauum.cu:161-166`, `cuda_vec_mul_triang.cu:22,45,68,91`). Sam kernel LAUUM jest podręcznikowy: kafel 32×32 w shared, 1 wynik na wątek, padding +1 przeciw konfliktom banków (`cuda_lauum.cu:13-80`).
8. **Precyzja**: domyślnie `no_single_kernel=True`, czyli bloki pełnej macierzy jądra dla danych FP32 są liczone w FP64 (`options.py:37-41`, `:173`, `mmv_ops/fmm.py:619-622`). Odległości liczy przez `‖x‖²+‖y‖²−2xyᵀ` (GEMM) z `clamp_min_(1e-20)` przeciw ujemnym wartościom z kasowania (`kernels/distance_kernel.py:88-101`). Akumulator KeOps jest konfigurowalny (`options.py:98-104`, `mmv_ops/keops.py:217-218`).
9. **Dobór rozmiaru bloków pod budżet pamięci**: maksymalizacja `n·m` przy `coef_nm·nm + coef_n·n + coef_m·m ≤ mem` (`utils/helpers.py:188-195`). Podział pracy między GPU proporcjonalnie do zmierzonej szybkości (`helpers.py:198-206`, `options.py:30-36`). Progi „mały problem → CPU” (`options.py:42-61`).
10. Liczby: w repo nie ma tabel wydajności, tylko skrypt drabinki ulepszeń bez wyników (`benchmarks/timing_benchmarks/time_improvements.py:1-10`: FP64 → FP32 → preconditioner na GPU → 2 GPU → KeOps). Abstrakt artykułu mówi tylko o „dramatic speedups” na miliardach punktów (pomiary autorów, NVIDIA).

## 3. Przeniesienie na AMD/HIP/RDNA3
- **1/2 (blok liczony w locie, reużycie bloku)**: przenosi się trywialnie, ale u nas już jest. FA liczy KQ w locie. Reużycie odczytanego kafla dla kilku iloczynów to multi-column MMVQ (2–16 kolumn) i fuzje gate/up/down. Nic nowego.
- **3/4/5 (strumienie, pinned, callbacki)**: odpowiedniki istnieją: `hipStreamAddCallback`/`hipLaunchHostFunc`, `hipHostMalloc`, `hipMemcpy2DAsync`. Dla nas to jednak nie ma znaczenia, bo przy dekodowaniu wszystko siedzi w VRAM. Budżet PCIe 4.0 x16 (~25 GB/s praktycznie [WNIOSEK]) w kroku Qwena 28.9 ms daje ≤ ~0.7 GB/krok przy idealnym nakładaniu, a model czyta ~16 GB wag na krok. Strumieniowanie czegokolwiek „per token” z RAM jest więc ~20–40× za wolne. Ładowanie modelu w llama.cpp już robi to samo lepiej: pierścień 4 buforów pinned z eventami zamiast synchronizacji hosta (`~/llama-master/src/llama-model-loader.cpp:1511-1519`, `1566-1568`, `1683-1734`).
- **5 (dataflow na hoście ze spin-wait)**: u nas ślepa uliczka. Zmierzyliśmy, że granica kernela w grafie HIP kosztuje ~2.5 µs, a host w pętli zależności to rząd 10–50 µs na krok synchronizacji [WNIOSEK]. Model „GPU wykonuje jeden krok, host decyduje” jest przeciwieństwem tego, czego potrzebuje LFM (launch-bound). Węzły hosta w grafie HIP też wymagają przejścia przez hosta [WNIOSEK].
- **7 (siatka trójkątna)**: przenosi się 1:1 (HIP ma `sqrt`, lepiej `sqrtf` + korekta całkowitoliczbowa zamiast `double`, bo FP64 na gfx1100 ma 1/32 przepustowości [WNIOSEK ze specyfikacji RDNA3]). Jedyne miejsce u nas, gdzie maska trójkątna ma znaczenie, to causal FA w prefillu. Tam ggml już pomija w pełni zamaskowane kafle KV (`flash_attn_mask_to_KV_max`, `~/llama-master/ggml/src/ggml-cuda/fattn-common.cuh:671-723`, `1114-1133`). Przy ubatch 512 i KV rzędu dziesiątek tysięcy tokenów trójkąt to ułamek procenta pracy.
- **8 (FP64 dla FP32)**: nie przenosi się. gfx1100 ma FP64 w tempie 1/32 FP32 [WNIOSEK], a w LLM kumulujemy int32/FP32 z kwantyzacji, gdzie problem kasowania `‖x‖²+‖y‖²−2xy` nie występuje. Uwaga poboczna: Falkon uruchomiony na 7900 XTX z domyślnym `no_single_kernel=True` byłby bardzo wolny.
- **9 (solver rozmiaru bloków pod budżet pamięci)**: koncepcyjnie to strojenie kafli MMQ/FA pod LDS/rejestry. U nas już ręcznie strojone pod RDNA3. Liniowy model pamięci Falkona nie modeluje obłożenia, LDS ani VGPR, więc nic nie daje.

## 4. Pomysły dla nas
Mówiąc wprost: **brak eksperymentów z sensownym oczekiwanym zyskiem dla Qwen3.8 ani LFM2.5.** Repo rozwiązuje inny problem (dane > VRAM, FP64, dużo GPU, praca compute-bound w cuBLAS). Nasze wąskie gardła (koszt uruchomień, pasmo MMVQ, FA decode, małe kernele) nie mają tu odpowiednika. To, co przenośne, sprawdziłem w naszym kodzie:
- *Siatka trójkątna dla causal prefill FA*: niepotrzebne, bo pokrywa ją `KV_max` (wyżej). `[SZACUNEK]` zysk < 0.5% prefillu. Nie robić.
- *Pinned ring + async upload*: już w loaderze llama.cpp. Nie robić.
- *Warstwa KV albo zimnych ekspertów w 64 GB RAM*: wyklucza ją rachunek PCIe z §3, nawet dla LFM, które czyta ~1.8 GB/token przy 4.1 ms/token (PCIe przeniesie ~0.1 GB w tym czasie). To ma sens tylko jako sposób na **większy kontekst lub wyższą kwantyzację kosztem t/s**, nie na przyspieszenie. Poza celem.
- *Outside the box, jedyna rzecz warta 15 minut, bez GPU*: kopia stanu GDN/rollbacku MTP. Jeśli kiedykolwiek pojawi się potrzeba zrzutu stanu (np. checkpoint promptu przy 200k kontekście do RAM, żeby nie robić prefillu od nowa), to wzorzec Falkona (płaski, prealokowany bufor pinned + `hipMemcpyAsync` na osobnym strumieniu, `parallel_lauum.py:70-82`) jest właściwy. To kwestia UX serwera (czas ponownego prefillu ~200 s przy 950 t/s vs ~0.2–0.4 s kopiowania kilku GB [SZACUNEK]), nie kerneli. Nie mam dowodu, że jest taka potrzeba, więc tylko notuję.

## 5. Krytyka
- „Multi-stream overlap” jest w praktyce słabe: synchronizacja hosta po każdym bloku (`fmmv.py:296-299`, `757-762`; `parallel_potrf.cu:252,282,327,333`) serializuje GPU i hosta. Działa tylko dlatego, że bloki to duże GEMM-y (ms), przy których kilkadziesiąt µs synchronizacji ginie. Dla naszych kerneli 2–25 µs ten wzorzec byłby katastrofą.
- `dmmv`/`fmmv` bez KeOps to sekwencja wywołań torch (`fill_` + kernel jądra + `addmm_` na blok). Brak fuzji, materializacja bloku w HBM. KeOps (por. raport 20) robi to w jednym kernelu.
- Kernele CUDA (LAUUM, vec_mul_triang) to poziom podręcznika: 1 wynik/wątek, brak kafli rejestrowych, brak tensor cores. Wydajność zależy od cuBLAS/cuSOLVER, nie od własnego kodu.
- `tri_index_*` liczy `sqrt` w `double` na każdy blok (`cuda_helpers.cuh:97,106`). Na RDNA3 (FP64 1/32) to drobny, ale niepotrzebny koszt.
- Brak opublikowanych pomiarów w repo. Twierdzenia o przyspieszeniach pochodzą z artykułu (NVIDIA, 2020), więc nie da się ich odnieść do gfx1100.

## 6. Werdykt
**Brak**: to dobrze zrobiona biblioteka out-of-core dla FP32/FP64 i KRR. Jej techniki (streaming przez PCIe, synchronizowane z hosta strumienie, FP64, siatka trójkątna) albo już są u nas lub w llama.cpp, albo są sprzeczne z naszym reżimem (decode memory-/launch-bound w całości w VRAM).
