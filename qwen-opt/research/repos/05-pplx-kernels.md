# 05 — perplexityai/pplx-kernels (+ następca pplx-garden/lily)

Klon: `pplx-kernels` HEAD `f70d1eb7` (2025-11-06), `pplx-garden` HEAD `1ed972ed` (2026-09-02). Nic nie budowane ani uruchamiane. Ścieżki `plik:linia` są względem korzenia danego repo. Liczby z repo to pomiary autorów (H100 / M5 Max), nie nasze.

## 1. Co to jest

- **pplx-kernels**: kernele MoE all-to-all (dispatch/combine) dla expert parallelism na 8+ GPU NVIDIA (sm90a, `README.md:21`). Transport przez NVLink (CUDA IPC + flagi w pamięci, `csrc/all_to_all/intranode_*.cu`) albo NVSHMEM/IBGDA (`internode_*.cu`). Mały kod (~2.5 tys. linii C++/CUDA), licencja MIT.
- Repo jest **porzucone**: `README.md:1-3` („DEPRECATION… check out pplx-garden”). Ostatni commit 2025-11.
- **pplx-garden** to następca. Dla nas liczy się w nim nie RDMA (`fabric-lib`, `p2p-all-to-all`), tylko **`lily/`**: silnik Rust+Metal pod jeden model, Qwen3.6-35B-A3B (hybryda GDN + MoE, 4 bit). To właśnie przypadek „MoE decode na jednym GPU, batch 1”. Autorzy mierzą 194.7 t/s przy kontekście 256 na M5 Max, 1.31x względem MLX (`lily/docs/2026-09-02-performance-mlx-0.32.2.md`, tabela „Results”). Licencja Apache-2.0.

## 2. Kluczowe techniki (z dowodami)

### pplx-kernels
1. **Jeden kooperacyjny launch na fazę komunikacji, wewnątrz bariery gridu.** Dispatch ma do 4 `cooperative_groups::this_grid().sync()` (`intranode_dispatch.cu:90,184,248,278`). Grid to `min(numSMs, …)` bloków (`intranode_dispatch.cu:301-306`, `intranode_combine.cu:206`), więc wszystkie bloki są rezydentne i bariera jest tania. Launch przez `cudaLaunchCooperativeKernel` (`:357-384`).
2. **Podział send/recv jednego kernela** (`SplitMode`, `all_to_all.h:9-12`; `do_send`/`do_recv` w `src/pplx_kernels/all_to_all.py:35-37`). Ten sam szablon kompiluje się jako send, recv albo oba (`intranode_dispatch.cu:15,75,196`). Między send a recv można wstawić obliczenia (overlap).
3. **Liczba tokenów jako wskaźnik do pamięci urządzenia** (`boundM`): `numSendTokens = boundM ? __ldg(boundM) : m` (`intranode_dispatch.cu:64`, `intranode_combine.cu:132`). Graf CUDA nagrany raz obsługuje zmienne `m` bez ponownego nagrywania.
4. **Sygnalizacja flagami z acquire/release i kodowaniem `count+1`.** Producent zapisuje `tokenCount+1` (`intranode_dispatch.cu:191`), konsument czeka na `!= 0`, sam zeruje flagę i odejmuje 1 (`:214-218`). Dzięki temu „0 tokenów” różni się od „jeszcze nie dotarło”, a flagi same się czyszczą bez memsetu w grafie. Prymitywy: `ld.acquire.sys` / `st.release.sys` / `atom.release.sys.add` (`core/atomic.cuh:17-31`).
5. **Combine z licznikiem przybycia na token zamiast globalnej bariery.** Blok tokenu `i` czeka, aż `localCount[i] == expertsPerToken` (`intranode_combine.cu:135`). Potem sumuje ważone wyjścia ekspertów w stałej kolejności `k` (`:151-161`), więc wynik jest deterministyczny mimo atomowego przydziału slotów (`intranode_dispatch.cu:140`).
6. **Token kopiowany raz do shared memory, potem warp na każde docelowe miejsce** (`intranode_dispatch.cu:101-180`). Internode: ostatni warp liczy histogram ekspertów, pozostałe wysyłają (`internode_dispatch.cu:82-169`, nazwana bariera `bar.sync 1` w `:144`).
7. Liczby autorów (`README.md:60-91`): 1 token/GPU, EP8 NVLink, dispatch 41.6 µs i combine 41.7 µs. Przy 128 tokenach EP8 dispatch 83.6 µs wobec DeepEP 163 µs.

### lily (pplx-garden) — single-GPU MoE decode
8. **Decode z wyprzedzeniem 2 kroków, token nie wraca do hosta.** Argmax na GPU zapisuje token do jednego z dwóch slotów `next_token` (`lily/src/model.rs:174-178`). Krok N+1 czyta go na GPU (`model.rs:658-676`). Host zgłasza krok N+1 *przed* czekaniem na N (`lily/src/generate.rs:104-112`).
9. **Encoder „concurrent” plus bariery tylko na prawdziwych krawędziach danych.** `MTLDispatchType::Concurrent` (`lily/src/metal.rs:208-222`), `level_barrier` = memory barrier (`metal.rs:308-311`). Niezależne dispatche w jednym poziomie nakładają się w czasie. W MoE: router GEMV, gate_up shared expert i shared_gate są w poziomie 0, a top-k i gather gate_up ekspertów w poziomie 1 (`model.rs:1342-1404`).
10. **Fuzje MoE decode**: gate+up+SwiGLU ekspertów w jednym gather-GEMV, grid (wiersz, slot) (`moe.metal:145-211`). Down + ważenie scores + shared expert z bramką sigmoid w jednym kernelu (`moe.metal:213-280`). Na warstwę MoE wychodzi ~6 dispatchy.
11. **Mapa „union experts” dla małego M (≤8 tokenów).** Jeden kernel buduje mapę expert-major: unikalni eksperci plus wiersze, które do nich trafiły (`moe.rs:104-140`, `moe.metal:394-460`). Trzy projekcje ekspertów dzielą tę mapę, każdy ekspert czytany jest raz dla wszystkich swoich wierszy. Grid ma rozmiar pojemności, a bloki ponad licznikiem z pamięci urządzenia wychodzą od razu (`moe.metal:303-305`). To ta sama idea co `boundM`.

## 3. Przeniesienie na AMD/HIP/RDNA3

| # | Technika | Na gfx1100 | Co się nie przeniesie |
|---|---|---|---|
| 1 | kooperacyjny grid ≤ liczba CU, bariera gridu | Tak. Już zmierzone u nas: bariera atomowa 0.48-0.58 µs/fazę przy 16-96 blokach (`lfm-decode-round2.md:30-31`) wobec ~2.5 µs granicy kernela. `hipLaunchCooperativeKernel` jest w `vendors/hip.h:84`. Działa też zwykły launch z gridem ≤ rezydentnych bloków + własna bariera (tak jak nasz `chain_cost.hip`). | Wymaga, żeby **każda** faza mieściła się w ~96-192 blokach (pętla grid-stride). Duże fazy z czekającymi blokami przegrywają (u nas 1024 bloki: 8-11 µs/fazę). |
| 2 | split send/recv | Na jednym GPU nie ma czego nakładać na komunikację. Analog „pamięciowy” opisuje pomysł P3 (prefetch). | Sama semantyka EP. |
| 3 | `boundM` z urządzenia | Tak, trywialnie (wskaźnik w argumentach kernela, wczesne wyjście bloków). | — |
| 4 | flagi `count+1`, samoczyszczące | Mamy to: tickety są zerowane przez ostatni blok (`ggml-cuda/topk-moe.cu:433-441`, `mmvq.cu:3449-3453`). Odpowiedniki acquire/release: `__hip_atomic_load/store` z `__ATOMIC_ACQUIRE/RELEASE`, scope agent (nie system). | Scope `.sys` jest nam niepotrzebny (jedno urządzenie). |
| 5 | licznik przybycia na token | Tak (atomik + spin z `s_sleep`). Na jednym GPU bardziej opłaca się wariant „ostatni przybyły liczy” (nasz ticket) niż czekanie. | Spin konsumentów przegrywa przy wielu blokach (nasz wynik negatywny). |
| 6 | kopia do LDS + warp na cel | Bez znaczenia: aktywacja 2048×q8_1 i tak siedzi w L2. | — |
| 8 | decode z wyprzedzeniem, token na GPU | Tak: dwa `hipGraphExec` (sloty ping-pong) albo jeden graf z węzłem kopiującym token z bufora urządzenia. Wymaga próbkowania na GPU (llama.cpp ma `--backend-sampling`, u nas szybkie, ale nie bitowo zgodne z CPU: `lfm-decode.md:105`). | API `llama_decode` jest synchroniczne względem logitów, więc trzeba zmienić pętlę serwera. |
| 9 | concurrent dispatch | HIP: `hipExtLaunchKernel(..., flags=hipExtAnyOrderLaunch)` czyści bit bariery pakietu AQL (`/opt/rocm/core-10.0/include/hip/hip_runtime_api.h:1031`, `hip_ext.h:44-52`; nieobsługiwane tylko na GFX9). To już jest w `research/v2/roadmap.md:102-105` i `rr-hip.md:122-125`; lily jest drugim, niezależnym potwierdzeniem, że wzorzec działa produkcyjnie. | Nie wiadomo, czy stream capture zachowuje flagę (do sprawdzenia: `AMD_LOG_LEVEL=4`, pole `barrier=`). |
| 10 | gate+up+SwiGLU, down+combine | Mamy to (`GGML_HIP_MOE_DOWN_REDUCE`, fused SwiGLU w ids-MMVQ). | — |
| 11 | union experts | Tak, jako wariant ids-MMVQ dla 2-8 tokenów: bloki indeksowane (unikalny ekspert, wiersz), wewnątrz pętla po tokenach tego eksperta, jak nasze wielokolumnowe MMVQ. | Dla LFM bez spekulacji i batcha 1 nic nie daje. |

## 4. Pomysły dla nas

**P1. MoE LFM jako jeden persistent launch z barierami gridu (wzorzec pplx #1). Najbardziej obiecujące.**
- Co: dziś warstwa shortconv+MoE to 8 launchy, z czego 4 to MoE: norm_router_topk → gate+up(SwiGLU) → quantize_q8_1 → down+reduce+res (`lfm-decode-round2.md:64-65`). Nowy kernel w `mmvq.cu` + `topk-moe.cu` (przełącznik `GGML_HIP_MOE_PERSIST`):
  - grid = k×96 rezydentnych bloków;
  - faza A: norm + router + topk (ticket jak dziś);
  - bariera;
  - faza B: gate+up po 4×1536 wierszach w pętli grid-stride, z epilogiem q8_1 w grupach 32 wierszy (ticket per grupa, jak `mul_mat_vec_q_conv`);
  - bariera;
  - faza C: down + ważenie + residual.
- Zysk `[SZACUNEK]`: zostają 2 bariery zamiast 3 granic, (3×2.5 − 2×0.6) ≈ 6 µs/warstwę × 38 ≈ **0.2-0.25 ms/token (~5-6%)**, plus znika ogon/rozbieg 3 kerneli.
- Koszt: duży, bo MMVQ trzeba przepisać na grid-stride przy stałym obłożeniu. Ryzyko: pasmo gate+up przy ograniczonym gridzie spada poniżej dzisiejszych ~715 GB/s. Wtedy strata MMVQ zje zysk z granic (gate+up 24 µs × 38: 5% pasma = 0.05 ms).
- Najpierw tani test bramkujący: wersja persistent samego gate+up (grid 96/192/288 bloków, grid-stride) porównana z dzisiejszym kernelem, w µs/wywołanie na rocprof. Idziemy dalej tylko przy ≤3% straty pasma. Bitowość: ta sama kolejność sum na wiersz.

**P2. Persistent „ogon atencji” LFM (10 warstw).**
- Co: rms_norm_mul_rope(q), rms_norm_mul_rope(k), fwht(v), set_rows K/V, FA vec, FA combine i fwht(out)+q8_1 to dziś ~8 małych launchy na warstwę (`lfm-decode.md:66-68`). Wszystkie poza FA mieszczą się w ≤96 blokach.
- Jeden kernel z 3-4 barierami gridu. FA vec w pętli grid-stride po (głowa, parallel_block).
- Zysk `[SZACUNEK]`: ~5 granic × 2.5 − 4 × 0.55 ≈ 10 µs × 10 warstw ≈ **0.1 ms/token (~2.5%)**. Koszt średni, ryzyko niskie (małe kernele, bez MMVQ). Uwaga: przy długim kontekście FA potrzebuje więcej bloków; wtedy wracamy do ścieżki wielokernelowej.
- Pomiar: `prof.sh`/`tok.py`, kernele/token i ms/token w A/B `ab.sh`, logit hash.

**P3 (outside the box). Wykorzystać bezczynny DRAM w czasie granic kernela do prefetchu wag do MALL (analog split send/recv: oddzielić pobranie od użycia).**
- Obserwacja: z 4.10 ms/token tylko 3.23 ms to praca GPU. Do tego ~0.6 ms to małe kernele latency-bound. DRAM stoi więc ~1.4 ms/token, a 96 MB MALL mieści wszystkie wagi jednej warstwy (~44 MB/warstwę).
- Kandydaci (adresy znane z góry albo znane po top-k):
  - wagi down 4 wybranych ekspertów (8.65 MB) w czasie quantize_q8_1 + 2 granic;
  - in_proj następnej warstwy (8.65 MB) w czasie down→rms_norm;
  - out_proj (2.9 MB).
- Mechanizm: gałąź grafu na drugim strumieniu z kernelem „touch” (load bez użycia wyniku; adresy z `ids`) albo blok-ogon w norm_router/quantize.
- Zysk `[SZACUNEK]`: jeśli MMVQ z gorącego MALL jest wyraźnie szybsze, 0.2-0.5 ms/token. Niepewność bardzo duża.
- Bramka zerokosztowa, rozstrzyga przed jakimkolwiek kodem: mikrobench uruchamiający ten sam in_proj MMVQ 2× pod rząd (drugi na gorącym MALL) wobec zimnego. Jeśli gorący ≈ zimny, MMVQ jest ograniczone liczbą bajtów w locie, nie DRAM, i pomysł umiera. Drugi test: czy kernel na drugim strumieniu w grafie HIP faktycznie biegnie równolegle z łańcuchem małych kerneli.
- Ryzyko: polityka alokacji MALL przy naszych hintach GLC|DLC (`NOTES.md:243-244`) może wykluczać trafienia; trzeba to sprawdzić w tym samym mikrobenchu.

**P4. Decode z wyprzedzeniem 2 (lily #8) dla LFM bez spekulacji.**
- Co: token z argmax/samplera GPU do slotu ping-pong; serwer zgłasza graf N+1 przed odczytem N.
- Zysk `[SZACUNEK]`: tylko przerwa host→GPU między tokenami. Bez profilera bezczynność 0.87 ms/token to głównie ~416 granic (~2 µs każda), więc na stronę hosta zostaje szacunkowo ≤0.1-0.15 ms (2-3%). Plus 12 kopii H2D (~32 µs), które w tym schemacie znikają (wejścia na GPU).
- Najpierw pomiar: timeline rocprofv3, przerwa między ostatnim kernelem tokenu N a pierwszym N+1 w llama-server (nie w llama-bench).
- Koszt duży (pętla serwera, próbkowanie GPU nie bitowo zgodne z CPU). Pokrywa się z TensorFold `lookahead` (`research/tensorfold/spec-host.md:135`). Robić tylko, jeśli zmierzona przerwa > 0.1 ms.

**P5. Any-order dla niezależnych sąsiadów w LFM (lily #9).**
- To już jest w roadmapie dla Qwen. Lista dla LFM: q/k/v MMVQ (3), set_rows K‖V, para rope(q)‖fwht(v) w 10 warstwach atencji, czyli ~40 barier.
- Zysk `[SZACUNEK]` ≤0.05-0.08 ms/token. Tani, jeśli flaga przeżywa capture. Wspólny test z Qwen.

**P6. Union experts (lily #11), tylko gdy LFM dostanie spekulację albo `-np >1`.**
- Ids-MMVQ dla 2-8 tokenów: blok = (unikalny ekspert, wiersze), wagi czytane raz.
- Najpierw sprawdzić na rocprof, czy dzisiejszy `mul_mat_vec_q` z ids przy `ne2>1` czyta wagi eksperta raz na (token, slot). Część może już łapać MALL.
- Zysk zależy od pokrycia ekspertów między tokenami (64 eksperci / 4 aktywnych: dla 5 tokenów oczekiwane ~17.5 unikalnych z 20 par `[SZACUNEK]`, czyli ~12% mniej bajtów ekspertów). Mało, robić tylko przy okazji spekulacji.

**P7. `boundM`: jeden graf dla zmiennej szerokości weryfikacji (Qwen).** Niski priorytet. Mamy graf per szerokość, a przełączenie kosztowało 1.6 ms (`NOTES.md:316`). Wzorzec pplx przydałby się, gdyby liczba grafów (VRAM, czas nagrywania) stała się problemem.

## 5. Krytyka

- pplx-kernels rozwiązuje inny problem (komunikacja EP między GPU). Jego „single-token” liczby (41.6 µs dispatch na NVLink) są o rząd wielkości większe od całego naszego budżetu na warstwę (~100 µs/warstwę dla LFM). Tu nie ma technik obliczeniowych.
- Porównanie z DeepEP w `README.md:80-87` jest bez rozrzutu i bez opisu warunków DeepEP (inne kolumny mają ±). Traktować marketingowo.
- Kod combine jest nieoptymalny: skalarne odczyty `(T*)buffer[j+l]` z przeliczaniem `getTokenPtr` w najgłębszej pętli (`intranode_combine.cu:157-161`). Busy-wait na `volatile` bez backoffu (`intranode_dispatch.cu:87`). Repo porzucone.
- Wyniki lily są z M5 Max (pamięć zunifikowana, Metal) i to production throughput, nie identyczny graf. Autorzy uczciwie to zaznaczają (dok. „Measurement contract”). Brak liczby dispatchy/token, więc koszt granicy na Metal jest nieporównywalny z naszym HIP.
- Wiele elementów już mamy (fuzje MoE, tickety samoczyszczące, any-order w roadmapie, lookahead w notatkach TensorFold). Realnie nowe dla nas są: zastosowanie persistent-grid do MoE/atencji LFM (P1/P2) i prefetch MALL w czasie granic (P3).

## 6. Werdykt

**Niska** (dla pplx-kernels). Kernele EP/RDMA nie przenoszą się na jedno GPU, a wartość dają tylko wzorce, które już znamy (kooperacyjny grid ≤ #CU z barierą, samoczyszczące flagi, licznik z urządzenia). Następca `pplx-garden/lily` jest dla nas „średni”: potwierdza concurrent dispatch i decode z wyprzedzeniem na produkcyjnym silniku MoE.
