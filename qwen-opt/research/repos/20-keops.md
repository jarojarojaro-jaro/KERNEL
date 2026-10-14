# 20 — getkeops/keops (KErnel OPerationS): symboliczne map-reduce, redukcje online

Klon: `git clone --depth 1` z HEAD `ef72bc90` (2026-06-24, merge #446 „test_fp16”). Ścieżki `plik:linia` są względem `keopscore/keopscore/`, chyba że podano inaczej. Nic nie było budowane ani uruchamiane. Artykuł: [JMLR 22(74) 2021, „Kernel Operations on the GPU, with Autodiff, without Memory Overflows”](http://jmlr.org/papers/v22/20-275.html).

## 1. Co to jest

Biblioteka (Python/R/Matlab) liczy redukcje $a_i = \mathrm{Red}_j\,F(x_i, y_j, p)$ dla dowolnej formuły $F$ i nie materializuje macierzy M×N. Formuła jest drzewem symbolicznym. Z niego Python generuje tekst CUDA, który NVRTC kompiluje w locie, z cache po hashu formuły (`binders/LinkCompile.py:24-51`, `binders/nvrtc/nvrtc_jit.cpp:70-77`). Repo jest aktywne: wersja 2.4b, ostatni commit 2026-06-24, 1.19k gwiazdek, 147 otwartych issues, licencja MIT. Wspiera tylko CUDA/NVIDIA i CPU. W kodzie nie ma żadnego wystąpienia `hip`, `rocm` ani `amd`, a wyszukiwarka issues GitHuba nie zwraca nic dla „rocm” i „AMD”. Typowe zastosowania to D ≤ ~100: kernele gaussowskie, k-NN, transport optymalny. Benchmarki autorów są z RTX 2080 Ti.

## 2. Kluczowe techniki (z dowodami)

1. **Schemat 1D: jeden wątek na wiersz wyjścia, kafel j w LDS, F tylko w rejestrach** (`mapreduce/gpu/GpuReduc1D.py:47-93`).
   - Wątek ładuje $x_i$ do rejestrów.
   - Blok kopiuje kafel $y_j$ (blockDim wierszy) do shared memory, a każdy wątek przechodzi po całym kafelku: `formula(fout)` → `accumulate_result(acc)`.
   - Wartości $F_{ij}$ nigdy nie trafiają do pamięci.
   - Rozmiar bloku: `min(CUDA_BLOCK_SIZE=192, maxThreads, smem/dimY)` (`include/CudaSizes.h:12`, `binders/nvrtc/keops_nvrtc.cpp:442-459`).
   - Nie ma tensor cores, wektoryzacji wierszy ani podziału D między wątki.
2. **Redukcja jako monoid** (`formulas/reductions/Reduction.py`).
   - Każda redukcja definiuje `InitializeReduction`, `ReducePairShort(acc, x, j)` (dodanie jednego elementu z indeksem) i `ReducePair(acc, acc')` (złączenie dwóch częściowych wyników) oraz `FinalizeOutput`.
   - Ten jeden interfejs daje schemat 1D, split-K (2D) i block-sparse bez nowego kodu dla każdej redukcji.
3. **Online log-sum-exp / softmax-ważona suma** (`formulas/reductions/Max_SumShiftExpWeight_Reduction.py:16-61`).
   - Stan to $(m, s_{1..d})$, gdzie $s$ może być wektorem $g_{ij}$ (np. V).
   - Złączenie ma gałąź. Jeśli $m > m'$, liczy jeden `exp(m'-m)` i robi `acc += x*e`. W przeciwnym razie przeskalowuje akumulator i podmienia max (`:46-61`).
   - Jest też wariant Kahana (`:66-87`).
   - Wyszukiwarka commitów GitHuba pokazuje „LogSumExp” w KeOps od **2018-01-16**. To przed [Milakov & Gimelshein, maj 2018](https://arxiv.org/abs/1805.02867) i FlashAttention (2022). `[WNIOSEK]`: nie sprawdzałem, czy wersja ze stycznia 2018 była już strumieniowa; obecna jest.
4. **Schematy sumowania dla precyzji** (`formulas/reductions/sum_schemes.py:50-92`).
   - `block_sum`: kafel sumowany do tymczasowego akumulatora, potem dodany do głównego. W kodzie jest też okres ~√N (`:55-58`).
   - `kahan_scheme`: kompensacja Kahana.
   - Cel: float32 przy N do 10⁷.
5. **Schemat 2D = split-K + osobny kernel combine** (`mapreduce/gpu/GpuReduc2D.py`).
   - `GpuConv2DOnDevice` zapisuje częściowy akumulator per `blockIdx.y`.
   - `reduce2D` składa partie sekwencyjnie po `y` tym samym `ReducePair`, więc działa to także dla LSE/argmax.
   - To dokładnie flash-decoding + `flash_attn_combine_results`.
   - Uwaga: opcja „GPU” (automatyczny wybór 1D/2D, `pykeops/torch/generic/generic_red.py:582`) w praktyce **zawsze wybiera 1D**, bo `_find_grid()` zwraca 0 (`pykeops/pykeops/common/get_options.py:127-129`).
6. **Top-K w rejestrach** (`formulas/reductions/KMin_ArgKMin_Reduction.py`).
   - `ReducePairShort` (`:71-100`): rozwinięte insertion sort, czyli wątek trzyma posortowaną listę K par (wartość, indeks) w rejestrach.
   - `ReducePair` (`:47-69`): merge dwóch posortowanych list.
   - Argmax (`Max_ArgMax_Reduction_Base.py:27-31`) używa ścisłego `>`, więc przy remisie wygrywa pierwszy indeks, deterministycznie.
7. **Block-sparsity („ranges”)** (`mapreduce/gpu/GpuReduc1D_ranges.py:77-168`, `keops_nvrtc.cpp:157-300`).
   - Zamiast maski dense są listy przedziałów `[start,end)` j dla każdego przedziału i.
   - Host buduje tablicę lookup (range_id, start_x, end_x) per blok.
   - Kernel skleja sąsiednie przedziały (`:131`) i nie dotyka pustych kafli.
8. **Tryb „chunks” dla D > ~146** (`config/ReductionTuning.py`, `mapreduce/gpu/GpuReduc1D_chunks.py`).
   - Wymiar cech jest cięty na kawałki po 64.
   - Każdy wątek trzyma tablicę `fout_chunk[blockDim*dimout_chunk]` (`:163-165`), np. 192 floaty. `[WNIOSEK]` to prawie na pewno pamięć lokalna/scratch, nie rejestry.
   - Progi to magiczne liczby: `_dim_treshold_chunk=146`, `_specdims_use_chunk=[99,100,102,120,...]`.
   - Shared memory jest na sztywno 49152 B (`keops_nvrtc.cpp:455-458`).
9. **Ograniczenia przyznane w dokumentacji**: spadek wydajności przy D > 100 przez rozlewanie rejestrów (`doc/introduction/why_using_keops.rst:418-424`). Tensor cores są „planowane” (`doc/introduction/road-map.rst:59-74`), ale issue #100 jest otwarte od 2020-09-12 z 0 komentarzy.
10. **Liczby autorów** (`benchmarks/README.md`, RTX 2080 Ti, fp32, gaussowskie mat-vec, D=3):
    - N=10k: 0.7 ms (PyKeOps) vs 9 ms (PyTorch);
    - N=1M: 1.39 s, gdzie PyTorch i XLA wychodzą poza pamięć.
    - To pomiary autorów dla D=3, nieprzenośne na D=128/256.

## 3. Przeniesienie na AMD/HIP/RDNA3

| Technika | Czy da się | Jak / odpowiednik | Co się nie przeniesie |
|---|---|---|---|
| 1D: wątek na wiersz + kafel j w LDS | Tak, trywialnie (zwykły HIP, `extern __shared__`, `__syncthreads`) | Blok 192 = 6 fal wave32. NVRTC → hipRTC | Skalarne FMA bez WMMA. Przy D=128/256 (nasze głowy) wektor q nie mieści się w VGPR wątku. To jest powód, dla którego nasz `fattn-kvq` robi KQ i VKQ przez `wmma_f16_16x16x16` (`ggml/src/ggml-cuda/fattn-kvq.cu:80-83`) |
| Online LSE z gałęzią | Tak | `v_exp_f32` (exp2) w domenie log2 | U nas jest już **lepiej**: `fattn-kvq.cu:35-37,362-396` podnosi max dopiero przy wzroście > 8 (log2) i przeskalowuje VKQ tylko przy `__any(raise_max)` (leniwe przeskalowanie w stylu FA4). Gałąź KeOps per element na GPU dzieliłaby falę |
| block_sum / Kahan | Tak | Dwupoziomowa suma per kafel | Nie potrzebujemy: VKQ i KQ_sum w kvq są w f32 („VKQ is accumulated as f32”, `fattn-kvq.cu:179`), a split-K już daje sumę dwupoziomową |
| Monoid + split-K + combine | Tak | Combine jako **ogon ostatniego bloku** (atomowy ticket + `__threadfence`) zamiast osobnego kernela. U nas zmierzone: ogon ~0.8–1.1 us vs granica kernela 2.53 us (`research/lfm-decode-round2.md:23-41`) | — |
| Top-K w rejestrach (insertion + merge) | Tak dla K ≤ ~8–16 | Lista w VGPR, merge między lane'ami przez DPP / `ds_swizzle` (bitonic) | Dla K ~ 100 (próbkowanie) lista w rejestrach nie ma sensu, lepszy jest wybór progowy (radix/threshold select) |
| Ranges (block-sparse) | Tak | Tablica lookup per blok w kernarg/SGPR (`s_load`), przedziały kv_end liczone z pozycji | Losowe dostępy przy drobnych przedziałach (sami to przyznają, `why_using_keops.rst:256-264`) |
| JIT z cache po hashu | Tak: hipRTC + cache kodu w `~/.cache` | Specjalizacja kształtów jako stałe kompilacji | Czas kompilacji przy starcie. Nasze kernele i tak są szablonami po (typ, n) |
| Tryb chunks | Technicznie tak | — | Na RDNA3 scratch jest drogi, a sposób z tablicą per wątek to antywzorzec |

## 4. Pomysły dla nas

Arytmetyka bazowa: Qwen 29 ms/krok, więc 1 ms ≈ 3.4% t/s. LFM 4.10 ms/token, więc 0.1 ms ≈ 2.4%. Granica kernela w grafie HIP to 2.53 us, ogon „ostatni blok” ~1 us (pomiary własne, `lfm-decode-round2.md`).

### 4.1 Combine FA (+ FWHT wyjścia) jako ogon ostatniego bloku split-K

- **Co zmienić.** W `fattn-kvq.cu:541-577` i w `fattn-vec.cuh` (ścieżka q8_0 LFM) zastąpić osobny `flash_attn_combine_results<D>` (`fattn-kvq.cu:574`) ogonem:
  - licznik per (kafel kolumn, głowa KV);
  - ostatni z `nsplit` bloków czyta `dst_meta`/`dst_tmp` i składa wynik;
  - w tym samym ogonie robi FWHT wyjścia atencji (pozycja „fwht V/wyjścia (do set_rows / FA combine)” z NOTES K2).
- **Bitowość.** Zachowana, jeśli ogon składa splity w tej samej kolejności 0..nsplit-1 i tą samą arytmetyką co `flash_attn_combine_results`. KeOps `reduce2D` robi dokładnie to: sekwencyjny `ReducePair` po `y`.
- **Zysk LFM** `[SZACUNEK]`: dziś `flash_attn_combine_results` to 10 wywołań, 18.6 us/token, a fwht 20 wywołań, 20.4 us (`lfm-decode-round2.md:61`).
  - Usunięcie 10 combine + 10 fwht wyjścia: −20 granic × 2.53 us − ~28 us pracy + ~10–13 us ogonów ≈ **−0.06 ms/token (≈ −1.5%)**.
- **Zysk Qwen** `[SZACUNEK]`: 16 warstw atencji, ≈ −0.07–0.1 ms/krok (−0.3%).
- **Koszt i ryzyko.** 1–2 dni. Ryzyko niskie: ticket już działa w `norm_router_topk` i `INPROJ_CONV`.
  - Trzeba resetować licznik w ogonie, bo graf HIP odtwarza kernel bez memsetu.
  - Przy `nsplit == 1` nic się nie zmienia.
- **Pomiar.** rocprofv3 kernele/token (416 → ~396), llama-bench tg128 przeplatane A/B, hash logitów (`lh.sh`), test-backend-ops FLASH_ATTN_EXT.

### 4.2 Najpierw pomiar: ile kosztuje D2H pełnych logitów weryfikacji; potem ewentualnie top-K' na GPU

- **Skąd pomysł.** Fork kopiuje `n_outputs*n_vocab*4` B (`~/llama-master/src/llama-context.cpp:2089`). Dla Qwen przy MTP n=4 to 5 × ~248k × 4 ≈ **5 MB/krok**.
  - Przy PCIe 4.0 ~13–25 GB/s daje to 0.2–0.4 ms, a do tego host przechodzi po 5×248k wartościach `[SZACUNEK]`.
  - Dla LFM 0.5 MB/token i `--backend-sampling` nie dało tam zysku (NOTES 0048), więc na LFM sprawa jest zamknięta.
- **Pomiar (zero kodu).** `rocprofv3 --memory-copy-trace` na `qwen mtp`: czas D2H logitów na krok i to, czy nakłada się z czymkolwiek.
- **Jeśli D2H ≥ 0.2 ms/krok:** kernel wyboru top-K' na GPU per kolumna, wzorowany na KeOps `KMin_ArgKMin`, ale dla K' ~ 100–128 jako threshold/radix select, nie insertion. Do hosta idzie K' par (wartość f32 bit w bit, id), czyli ~5 KB.
  - Dokładność: sampler z `top_k = k` potrzebuje tylko k najlepszych.
  - Kary tylko obniżają logity (ten sam argument co w 0048), więc nadzbiór top-(k + liczba ukaranych tokenów) daje wynik identyczny z obecnym.
  - Fallback do pełnej kopii, gdy `top_k = 0`, `logit_bias > 0`, `n_probs`/logprobs albo gramatyka.
- **Zysk** `[SZACUNEK]`: 0.15–0.35 ms/krok (+0.5–1.2%) tylko przy pozytywnym pomiarze.
- **Koszt i ryzyko.** 2–4 dni. Ryzyko średnie: semantyka API samplera i rejection sampling MTP przy T=1. Ten ostatni po obcięciu top_k potrzebuje p tylko w obrębie top-k.

### 4.3 Argmax draftu w epilogu MMVQ głowicy draftu (monoid max/argmax + ticket)

- **Co zmienić.** Bloki `mul_mat_vec_q` głowicy draftu (64k wierszy) redukują swoje wiersze do pary (max, argmax). Do redukcji między lane'ami używają DPP z remisem na niższy indeks, jak `>` w KeOps (`Max_ArgMax_Reduction_Base.py:27-31`). Ostatni blok składa wynik. Odpada osobny argmax (4.3 us, NOTES K2) i zapis 64k×4 B logitów.
- **Zysk** `[SZACUNEK]`: 4 przebiegi × (4.3 + 2.53 − 1) us ≈ −23 us/krok (−0.08%).
- **Koszt i ryzyko.** 1 dzień. Ryzyko niskie, jeśli remis jest rozstrzygany identycznie. **Niski priorytet.**

### 4.4 Maska przyczynowa jako przedziały (KeOps „ranges”) zamiast dense KQ mask (outside the box, pomiar najpierw)

- **Co zmienić.** Dla jednej sekwencji bez SWA kernel FA dostaje `kv_end[col] = n_past + t + 1` (kilka intów) zamiast maski f16 n_kv×n_tokens. Odpada budowa maski na hoście i jej kopia H2D.
- **Stan wyjściowy.** T1 już przyspieszył maskę („szybka maska KQ dla jednej sekwencji”). Notatka K3 szacowała pełną maskę na ~0.65 ms/krok przy 94k.
- **Pomiar.** Rozmiar i czas kopii wejścia maski oraz czas budowy przy 94k po T1 (rocprofv3 `copyBuffer` + timer hosta).
- **Zysk** `[SZACUNEK]`: 0–0.15 ms/krok przy 94k, ~0 przy krótkim kontekście. Odczyt maski w kernelu (~1 MB/warstwę, trafia w MALL) jest bez znaczenia.
- **Koszt i ryzyko.** 2–3 dni. Ryzyko średnie: maska jest wejściem grafu ggml (SWA, wiele sekwencji, ALiBi), więc potrzebna ścieżka szybka + fallback.

### 4.5 Czego z KeOps nie robić (z powodem)

- **Atencja decode w stylu KeOps 1D (wątek na zapytanie, q w VGPR).** Przy D=128/256 rozlewa rejestry (autorzy sami to piszą, `why_using_keops.rst:418-424`) i nie używa WMMA. Nasz kvq jest lepszy w każdym aspekcie.
- **Gałęziowe przeskalowanie online.** Mamy już leniwe przeskalowanie z progiem 8 i `__any`.
- **Router/top-k MoE.** Już złożone w `norm_router_topk` (0053). Insertion sort KeOps dla top-4 z 64 to to samo, co robi `topk_moe_select`.
- **GDN.** Rekurencja liniowa jest asocjacyjna (złożenie map afinicznych), więc formalnie to też monoid i daje się zrównoleglić skanem. Chunked WY na gfx1100 jest jednak już negatywny (Strata #888), a decode GDN jest ograniczony pasmem stanu (~13 us/warstwę). KeOps nic tu nie wnosi.
- **JIT hipRTC ze specjalizacją kształtów (formuły → kod).** Pozostałe uruchomienia leżą na granicach z MMVQ, nie w łańcuchach elementwise, więc generyczny JIT-fuser nie usunąłby wielu kerneli. MMVQ jest ograniczone pamięcią, więc stałe kompilacji nic nie dadzą `[WNIOSEK]`. Koszt startu i utrzymania jest wysoki.
- **Kahan/block_sum w FA.** Akumulacja jest już w f32 ze split-K.
- **Instancja q8_0 kernela kvq.** KeOps tylko potwierdza zasadę „kafel y_j raz dla wszystkich i w bloku” = jeden odczyt KV dla wszystkich głów Q w grupie GQA. To już jest zidentyfikowane w `lfm-decode-round2.md` §4, z szacunkiem −1.1 ms przy 98k. Nie liczyć tego jako pomysłu z KeOps.

## 5. Krytyka

- **„Predates FlashAttention”** jest prawdą historyczną (LogSumExp od 01.2018), ale bez znaczenia praktycznego. KeOps nie ma kafelkowania pod MMA ani podziału D między wątki, a wariant ze stałym kosztem gałęzi per element jest gorszy od leniwego przeskalowania per kafel, które mamy.
- **Dokumentacja obiecuje automatyczny wybór 1D/2D** (`generic_red.py:582`), a `_find_grid()` zwraca na sztywno 0 (`get_options.py:127-129`). Przy małym M i dużym N (nasz przypadek decode: kilka zapytań × 100k kluczy) schemat 1D daje kilka bloków na 96 CU. Domyślnie KeOps byłby więc bardzo wolny dla atencji decode.
- **Tryb chunks** to magiczne progi (`ReductionTuning.py`: 146, lista „specdims”) i tablica per wątek wielkości blockDim. Obejście, nie projekt.
- **Tensor cores** czekają od 2020 (#100). Brak AMD/HIP. Brak typów skwantyzowanych (road-map mówi o nich jako przyszłości).
- **Benchmarki** dotyczą D=3 na RTX 2080 Ti, wobec PyTorcha materializującego macierz. To słuszne dla ich niszy, nieistotne dla LLM.
- **Wartość dla nas** leży w czystym formalizmie (Init / ReducePairShort / ReducePair / Finalize). To dobra checklista dla każdej naszej fuzji z „ostatnim blokiem”: jeśli operację da się zapisać jako monoid, split-K + ogon jest poprawny i może być bitowo zgodny przy ustalonej kolejności złączeń.

## 6. Werdykt

**Niska.** KeOps to historycznie ważny prekursor online-LSE i czysty formalizm map-reduce. Kernele są skalarne, bez WMMA, bez AMD i ograniczone do D<100. Wszystko, co pasuje do naszych kerneli, już mamy, często w lepszym wariancie. Wyprowadzone pomysły (combine+FWHT w ogonie ostatniego bloku, top-K' logitów na GPU po pomiarze D2H) są warte ~0.3–1.5% każdy.
