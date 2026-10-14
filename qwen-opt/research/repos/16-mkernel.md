# 16 — uccl-project/mKernel

Repo: https://github.com/uccl-project/mKernel (HEAD `97e916b`, 2026-10-01). Artykuł: arXiv 2609.13585 (https://arxiv.org/html/2609.13585v1), blog: https://uccl-project.github.io/posts/mkernel

## 1. Co to jest

Biblioteka **wielo-GPU/wielowęzłowych** kerneli trwałych (persistent) z UC Berkeley Sky/UCCL. Każdy kernel łączy obliczenia, NVLink i RDMA w jednym uruchomieniu: AllGather+GEMM, GEMM+AllReduce, GEMM+ReduceScatter, MoE dispatch+GEMM(+SwiGLU+combine), Ring Attention. Bloki CTA mają role według `blockIdx` (compute / intra-comm / send / recv-reduce). Gotowość danych sygnalizują flagi i liczniki per kafel/chunk, nie granice kerneli. Kod: MIT, ~107 commitów, 297 gwiazdek, aktywny (push 2026-10-11). Sprzęt: **tylko NVIDIA Hopper sm_90a** (plus częściowo Blackwell), CUDA 12.9, H200 ×16, CX7/EFA (`README.md` „Requirements”). **Brak wsparcia AMD**: grep `hip|rocm|amd|gfx` nic nie znajduje. Nie jest to megakernel modelu. Każdy kernel to jedna operacja rozproszona. Artykuł sam odsyła do megakerneli Hazy/MPK (§6).

**Dla nas:** komunikacji między GPU nie mamy, więc zostają tylko wzorce **synchronizacji wewnątrz trwałego kernela**. Są dobrze opisane w kodzie i pasują do naszego otwartego tematu: „trwała siatka wymagałaby przepisania matvec na grid-stride” (`research/lfm-decode-round2.md:39-41`).

## 2. Kluczowe techniki (z dowodami)

| # | Technika | Dowód | Liczby (czyje) |
|---|---|---|---|
| T1 | **Trwała siatka = liczba SM, 1 CTA/SM, role według blockIdx**. Po fazie z rolami podział znika i cała siatka robi gemm2 → combine, rozdzielone barierami siatki | `src/dispatch_gemm_glu_combine.cu:6-34, 908-1008, 1021` (`fused_kernel<<<SM_COUNT,…>>>`, `__launch_bounds__(…,1)`), `src/gemm_ar.cu:1344-1358` | brak osobnych liczb dla mechanizmu |
| T2 | **Zależności per blok wierszy zamiast bariery siatki**. Producent zwiększa `barrier[row_idx]`, konsument czeka na `== ROW_BLOCK`. Czeka tylko lane 0 warpu producenta TMA, reszta stoi na semaforze/`__syncwarp` | `src/dispatch_gemm_glu_combine.cu:316-325`, `src/dispatch_gemm_blackwell.cu:99-103` | — |
| T3 | **Kolejność zadań według gotowości wejść**: najpierw lokalne bloki wierszy (już gotowe), potem zdalne (pass 0/1). AllGather+GEMM: najpierw lokalny shard, potem węzeł, potem zdalne | `src/dispatch_gemm_glu_combine.cu:297-311, 866-901`; artykuł §4 | — |
| T4 | **Hierarchiczne liczniki „ostatni kafel podnosi flagę chunka”**: kafle → chunk (licznik atomowy, ostatni robi `atomicOr` bitu w bitmapie gotowości właściciela) | `src/gemm_rs.cu:912-947`, `src/gemm_rs.cu:170-183` | GEMM+AR: 4 kafle = 256 KiB chunk (artykuł §3.1) |
| T5 | **Kolejka gotowych zadań w kernelu**: producent CAS-em zajmuje flagę i dopisuje `chunk_id+1` przez `atomicAdd(tail)`. Konsument robi `atomicCAS(head)` i czeka, aż wpis ≠ 0. Do tego bitmapy z `__ffs` + CAS (claim bez kolejności) | `src/gemm_rs.cu:640-682` (queue), `src/gemm_rs.cu:243-279` (bitmapa) | — |
| T6 | **Recykling ról / work stealing**: CTA po skończeniu roli przechodzą do puli redukcji (`atomicAdd(next_reduce)`) | `src/gemm_rs.cu:5-21, 731-733`, `src/gemm_ar.cu:1053-1057` | — |
| T7 | **Flagi epokowe/monotoniczne bez zerowania**: czekanie na `flag == epoch` albo `val >= epoch*NUM_DEVICES`. Pierścień slotów z numerem generacji | `include/operators/ag_gemm/ag_gemm.cuh:157-172`, `src/gemm_ar_blackwell.cu:385, 414-429`, `src/dispatch_gemm_warp_specialization.cu:10-16, 53-60` | — |
| T8 | **Bariera siatki przez „ostatni przybyły”**: `atomicAdd(count)`, ostatni zeruje licznik i ustawia `ready[bi]`, reszta odpytuje `ready`. **Osobny slot `bi` na każdą barierę w uruchomieniu** (bez sense reversal) | `src/dispatch_gemm_glu_combine.cu:1044-1090` | — |
| T9 | **Higiena odpytywania**: jeden wątek odpytuje, potem `__syncthreads`. Najpierw ciasna pętla (64 iteracji), potem `__nanosleep(32-100)`. Sleep jako parametr (`reduce_poll_sleep_ns`, „1000 ns zmniejsza thrash cache bez widocznej latencji”). Relaxed poll i acquire dopiero po trafieniu | `src/gemm_rs.cu:758-777`, `include/operators/gemm_rs/gemm_rs.cuh:251-264`, `include/comm/atomic_u32.cuh:102-106` | brak liczb |
| T10 | **Flagi w pamięci urządzenia, nie hosta** („for fast polling”) | `include/comm/internode/arrival.cuh:63-70` | — |
| T11 | **Specjalizacja warpów w CTA**: warpgroup komunikacji synchronizuje tylko swoje 4 warpy, bez `__syncthreads` z warpami GEMM | `src/dispatch_gemm_warp_specialization.cu:57-61, 172-193` | — |
| T12 | **Kolejka host→GPU** (ring SPSC: CPU dopisuje work-id, CTA biorą przez `atomicAdd(head)`). Kolejka GPU→host z backpressure | `include/comm/internode/ready_queue.cuh:1-15, 36-42`, `include/comm/internode/d2h_fifo.cuh:47-71` | artykuł: proxy hosta ≈ IBGDA (Fig. 4) |
| T13 | Rasteryzacja „super-M” kafli dla reużycia wag w L2 | `src/dispatch_gemm_glu_combine.cu:217-239` | — |
| T14 | Duża struktura `__grid_constant__` przekazywana przez const-ref. Lokalna kopia spillowała 3 KB/wątek do STACK | `src/dispatch_gemm_glu_combine.cu:918-923` | komentarz autorów (STACK:7024) |
| T15 | Adaptacyjny podział SM (kontroler na GPU, wzór n* = B·RsCs/(RpCp+RsCs)) | artykuł §3.2, §5.5 | geomean 1.18× gorzej niż najlepszy statyczny (21 konf.); najgorszy statyczny AR 25× wolniejszy (autorzy, H100) |

Wyniki zbiorcze (autorzy, 2×8 H200): GEMM+AR do 1.72×, Ring Attention do 1.88×, AG+GEMM do 1.41× względem cuBLAS/FA + NCCL. MoE 3.1-4.5× wobec bazy, która nie grupuje GEMM ekspertów; artykuł sam to przyznaje (§5.3).

## 3. Przeniesienie na AMD/HIP/RDNA3

| Technika | Przenośna? | Jak na gfx1100 / co odpada |
|---|---|---|
| T1 trwała siatka z rolami | Tak, z zastrzeżeniem | Siatka = 96 CU × k WG przy znanym obłożeniu. **Statyczne role według blockIdx wymagają współrezydencji wszystkich WG.** W HIP API obłożenia potrafi kłamać (Strata #2226 waliduje przy starcie z timeoutem 50 ms, `research/strata/README.md:146`). Bezpieczniej robić jak nasz `chain_cost.hip`: dynamiczny indeks zadania z atomowego biletu w kolejności. Blok czeka wtedy tylko na zadania już pobrane przez działające bloki, więc nie ma zakleszczenia bez gwarancji rezydencji. `hipLaunchCooperativeKernel` w przechwytywaniu grafu: niesprawdzone `[WNIOSEK]`, lepiej go unikać. |
| T2/T4 liczniki per chunk | Tak | `__hip_atomic_fetch_add(…, __ATOMIC_RELEASE, __HIP_MEMORY_SCOPE_AGENT)` u producenta. Konsument: `__hip_atomic_load(…, __ATOMIC_RELAXED, AGENT)` w pętli, potem `__atomic_thread_fence(acquire, agent)`. Na gfx11 release/acquire na scope agent dają `s_waitcnt` + inwalidację `buffer_gl0_inv/gl1_inv` `[WNIOSEK]`. T4 to dokładnie nasz „ostatni blok/ticket” (0051/0053/0054), więc nic nowego. |
| T3 kolejność według gotowości | Tak | Kolejność pobierania biletów = kolejność produkcji. Konsument dostaje zadanie, którego wejście właśnie powstało. |
| T5 kolejka gotowych zadań | Tak | Te same atomiki na L2. Na RDNA3 CAS na jednym słowie z 96+ CU serializuje się w jednym kanale L2. Przy małej liczbie zadań na token (dekodowanie) to nieistotne. |
| T7 flagi epokowe | Tak | W grafie HIP argumenty kernela są zamrożone przy przechwyceniu, więc `epoch` jako argument odpada. Trzeba go trzymać w słowie urządzenia, które inkrementuje ostatni blok poprzedniego przebiegu. Zysk: brak zerowania liczników, odporność na przerwany przebieg. |
| T8 bariera „ostatni przybyły” | Tak, mamy zmierzone | 0.5-0.8 µs na fazę przy 16-192 blokach (`lfm-decode-round2.md:30-31`). Uwaga: mKernel odpytuje `atomicAdd(x,0)` (`dispatch_gemm_glu_combine.cu:1063,1088`, `ag_gemm.cu:92`). Na AMD to RMW w L2 przy każdym odpytaniu. Lepiej czytać relaxed z GLC/DLC. |
| T9 odpytywanie | Tak | `__builtin_amdgcn_s_sleep(n)` (≈64·n taktów) zamiast `__nanosleep`. Jeden lane odpytuje, reszta WG stoi na `s_barrier`, który nie zajmuje slotów issue. To jest właśnie lekarstwo na nasz wynik „1024 czekających bloków zagładza producentów” (`lfm-decode-round2.md:35-36`): mKernel nigdy nie ma więcej czekających niż CU. |
| T10 flagi w VRAM | Tak, trywialne | Już tak robimy. |
| T11 specjalizacja warpów | Częściowo | RDNA3 nie ma `setmaxnreg`: VGPR są jednolite dla całego kernela, więc wave „komunikacyjny” płaci rejestry wave'u obliczeniowego. Rozdział ról na poziomie WG jest tańszy. |
| T12 kolejka host→GPU | Technicznie tak | Pamięć hosta mapowana (`hipHostMallocCoherent`). Odczyt z GPU przez PCIe 4.0 to ~1-2 µs na odpytanie `[WNIOSEK]`. Kernel daemon blokuje kolejkę. Dla llama.cpp z próbkowaniem na CPU zysk jest wątpliwy (patrz §4 P6). |
| T13 super-M | Tak, mała wartość | Prefill MMQ: macierz 5120×17408 Q4 ≈ 50 MB i tak mieści się w 96 MB MALL `[WNIOSEK]`. |
| T14 `__grid_constant__` | Analogicznie | W HIP kernarg ładuje się przez `s_load` do SGPR. Kopia dużej struktury z dynamicznym indeksowaniem ląduje w scratch (u nas był podobny przypadek `__byte_perm`, Strata). Warto sprawdzić `scratch_size` nowych fuzji. |
| TMA, wgmma, tcgen05, klastry, multimem/NVSwitch, RDMA/EFA, IBGDA | **Nie** | Brak odpowiedników na RDNA3 i brak sensu na jednym GPU. Odpowiedniki ładowań: buffer loads z SGPR (już w K1). |

## 4. Pomysły dla nas

Kontekst negatywny: megakernel z barierą siatki przegrał u TensorFold (4.6-18 µs/fazę, `research/tensorfold/README.md:70, 257`). U nas łańcuch dużych faz z czekającymi blokami to 8-11 µs/fazę (`lfm-decode-round2.md:35`). Pomysły poniżej różnią się od tamtych prób trzema rzeczami z mKernel: **(a)** liczba czekających ≤ liczba CU i czeka jeden lane, **(b)** zależności per chunk zamiast bariery siatki, **(c)** nowy element, którego mKernel nie robi: **ładowanie wag przed czekaniem**. Wagi nie zależą od poprzedniej operacji, zależy tylko mały wektor aktywacji.

### P1. Mikrobench „czy trwały łańcuch matvec ma sens” (go/no-go dla P2)
- **Co:** rozszerzyć `~/wt/lfm2-prof/chain_cost.hip`. Fazy to prawdziwe matvec Q5_K 4×(2×1536×2048) (gate+up ekspertów LFM), potem down 4×(2048×1536). Siatka 96×k WG z biletem w kolejności. Każdy WG pobiera zadanie, **najpierw ładuje kafel wag do VGPR**, potem czeka (1 lane + `s_sleep`) na licznik ekspertu, wylicza i dodaje się do licznika. Porównanie: dwa osobne kernele w grafie HIP.
- **Zysk:** to tylko pomiar. Decyduje, czy fill/drain (~2-3 µs na mały launch, `lfm-decode.md:52-53`) da się schować.
- **Koszt:** ~1 dzień. **Ryzyko:** niskie. **Pomiar:** czas pary faz w µs i GB/s matvec w formie grid-stride wobec ~700 GB/s obecnych.

### P2. Trwały blok MoE dla LFM: norm+router+top-k → gate+up(SwiGLU) → down+ważenie+residual w jednym uruchomieniu
- **Co:** w `ggml-cuda` (nowy kernel obok `GGML_HIP_NORM_ROUTER` / `GGML_HIP_MOE_DOWN_REDUCE`, przełącznik `GGML_HIP_MOE_PERSIST`) jedna siatka z biletami:
  1. zadania routera (ostatni blok liczy top-k i publikuje `ids` + licznik);
  2. zadania gate+up per (ekspert, plaster wierszy): wagi ładowane spekulatywnie dopiero po `ids`, bo ekspert nie jest znany wcześniej. Można za to wcześniej ładować aktywacje i wagi down;
  3. zadania down per (ekspert, plaster), czekające na licznik ekspertu (T2/T4) zamiast bariery, z **wagami down załadowanymi przed czekaniem**;
  4. redukcja i residual przez ostatni blok, jak teraz.
  
  Kolejność biletów według gotowości (T3): down ekspertu 0 przed gate+up ekspertu 3 nie ma sensu, więc kolejność to router, gate+up e0..e3, down e0..e3.
- **Zysk `[SZACUNEK]`:** −2 granice na warstwę MoE × 38 = −76 × 2.5 µs = 0.19 ms. Koszt czekań w kernelu 76 × ~0.6 µs = −0.05 ms. Schowane fill/drain +0.05-0.15 ms. Netto **0.15-0.3 ms/token, czyli 4-7% z 4.1 ms**. Warunek: GB/s matvec w formie trwałej nie spada (P1).
- **Koszt:** duży (kilka dni + testy bitowe). Kolejność sum per wiersz da się zachować, więc wynik może być bitowo identyczny. **Ryzyko:** zakleszczenie przy złej kolejności biletów; spadek obłożenia (VGPR na wagi „w locie” + czekanie). „Losowe spowolnienie gate+up” (`NOTES.md:359`) utrudni pomiary. **Pomiar:** rocprofv3 kernele/token, llama-bench tg128 A/B naprzemiennie, hash logitów (`lh.sh`).

### P3. Rola „rozgrzewacz MALL” w kernelach ograniczonych latencją (przeniesienie T1 z ról komunikacji na role pamięci)
- **Co:** do siatki kerneli, które nie wysycają DRAM, dodać kilka WG z rolą „dotknij następnej znanej macierzy wag”. Dla LFM: `NORM_ROUTER` (4.9 µs), `topk`, `rms_norm*mul`, conv. Następna macierz to `in_proj`/`out_proj` kolejnej warstwy shortconv, ~8.6 MB Q5_K dla in_proj 6144×2048 `[WNIOSEK]`. Dla Qwen: GDN (13 µs/warstwę), `rms_norm_mul_rope`, FA przy krótkim kontekście. Następne macierze to qkv/z projekcji. Ładowania bez użycia wyniku (asm volatile / sumowanie do martwego rejestru), bez GLC/DLC dla L2. Cel: wagi w Infinity Cache (MALL), zanim wystartuje matvec.
- **Zysk `[SZACUNEK]`:** ograniczony przez bajty = czas kernela-gospodarza × ~900 GB/s, czyli ~4-7 MB na krótki kernel. Jeśli matvec z MALL osiąga ≥1.3× pasma DRAM, to ~3-5 µs/warstwę, czyli **LFM ~0.1-0.15 ms/token (2-3.5%)**, Qwen ≤1%.
- **Najpierw zmierzyć okazję:** w `mmvq-bench` uruchomić ten sam kształt „na zimno” i tuż po dotknięciu wag przez osobny kernel (MALL ciepły). Jeśli różnica <15%, porzucić.
- **Ryzyko:** prefetch konkuruje o DRAM z gospodarzem (wydłuża go). MALL może wyrzucić dane, zanim przyjdzie matvec (strumień 1.8 GB/token). Przerwy między kernelami (2.5 µs) są martwe, bo nic wtedy nie biegnie. **Koszt:** średni (1-2 dni na prototyp w jednym kernelu).

### P4. Higiena synchronizacji w istniejących fuzjach z biletem (tanie, małe)
- **Co:** przejrzeć nasze ścieżki „ostatni blok” (0051, 0053, 0054, A3-A6) i pary MMVQ. Ani razu odpytywanie przez RMW (`atomicAdd(x,0)` jak w `ag_gemm.cu:92`); jeden release `fetch_add` na scope agent. Rozważyć liczniki monotoniczne z epoką w słowie urządzenia (T7) zamiast zerowania przez ostatni blok, co usuwa jeden zapis i zależność kolejności.
- **Zysk `[SZACUNEK]`:** <0.1 µs/kernel z biletem, łącznie <0.02 ms. Wartość głównie jako fundament P2. **Koszt:** godziny. **Pomiar:** czas pojedynczego kernela w rocprofv3.

### P5. „Outside the box”: split-K wyrównany do ziarna producenta (GDN → out_proj w Qwen)
- **Co:** matvec ma zależność „wszystko od wszystkiego”, bo każdy wiersz wyjścia potrzebuje całego wektora, więc drobne flagi T2 degenerują się do bariery. Wymiar K out_proj można jednak pociąć **po głowach GDN**. WG liczące częściową sumę dla grupy głów h startują, gdy GDN skończy h (licznik per grupa). Plastry składa ostatni blok w stałej kolejności, deterministycznie, ale **nie bitowo** względem obecnego kernela. Wagi out_proj ładowane przed czekaniem.
- **Zysk `[SZACUNEK]`:** przykrycie części rekurencji GDN (13 µs/warstwę, latency-bound) strumieniem wag out_proj. Maksymalnie ~8-10 µs × 48 ≈ 0.4-0.5 ms/krok (~1.5%).
- **Koszt/ryzyko:** wysokie (GDN z opóźnieniem S4, 5 kolumn, KLD do sprawdzenia). Robić dopiero, jeśli P1/P2 pokażą, że trwały łańcuch działa na gfx1100.

### P6. (Odradzane) kernel-demon z kolejką host→GPU (T12)
Pętla spekulacji wymaga próbkowania i akceptacji na CPU. Odpytywanie mapowanej pamięci przez PCIe i blokowanie kolejki HIP przez demon zjada zysk z braku uruchomienia grafu. Sensowna ścieżka to „pętla spekulacji bez synchronizacji hosta” z raportu TensorFold (#3), nie demon. Wymieniam dla kompletności.

## 5. Krytyka

- **Nieistotne dla jednego GPU w ~90%:** RDMA, EFA/CX7, proxy, NVSwitch multimem, IBGDA, TMA/wgmma/tcgen05. Wszystko pod Hopper/Blackwell.
- **Adaptacyjny kontroler z artykułu (§3.2, T15) nie jest w publicznym kodzie.** W repo „adaptive” to heurystyki hosta po M i zmiennych środowiskowych (`include/operators/ag_gemm/ag_gemm.cuh:411-430`, `bench/gemm_ar_bench.py:198-200`). Nawet według artykułu przegrywa ze statycznym strojeniem średnio o 18%.
- **Liczby MoE (3.1-4.5×) są zawyżone** bazą bez grupowania GEMM ekspertów (przyznane w §5.3). Baseline DeepEP na EFA to w ogóle pomiar z innego klastra.
- **Brak liczb kosztu samych mechanizmów** (bariera, flaga, kolejka). Są tylko wyniki end-to-end operacji, więc nasze własne pomiary (`lfm-decode-round2.md` §1) są cenniejsze niż cokolwiek z tego repo.
- **Odpytywanie przez `atomicAdd(x,0)`** (`dispatch_gemm_glu_combine.cu:1063,1088`, `ag_gemm.cu:92`): RMW przy każdym odpytaniu. Na AMD nie kopiować.
- **Wagi ładowane dopiero po czekaniu na barierę wierszy** (`dispatch_gemm_glu_combine.cu:316-343`): `B` (wagi ekspertu) nie zależy od dispatchu, a TMA B startuje po pętli czekania. To przegapiona okazja na nakładanie, którą P1/P2 chcą wykorzystać.
- **Statyczne role zakładają, że cała siatka jest rezydentna** (grid = SM_COUNT, 1 CTA/SM). Na dedykowanym H200 to działa, na współdzielonym GPU grozi zakleszczeniem.
- Dużo martwego/debugowego kodu: stuby `get_ready_queue_device` zwracają pusty uchwyt (`include/comm/internode/session.h:816-819`, `session_efa.h:942-945`), dziesiątki przełączników env, flagi `debug_skip_phase*`.

## 6. Werdykt

**Niska.** Repo dotyczy komunikacji wielowęzłowej na Hopperze i nie ma AMD. Dla dekodowania na jednym 7900 XTX zostają wzorce synchronizacji trwałego kernela (≤CU czekających, jeden lane odpytuje z `s_sleep`, liczniki per chunk, kolejność biletów według gotowości). One mówią, jak ominąć zmierzoną przez nas porażkę łańcucha faz. Wartościowe stają się dopiero w połączeniu z naszym pomysłem ładowania wag przed czekaniem (P1 → P2).
