# 18 — tensara/tensara (+ tensara/problems)

Repo: https://github.com/tensara/tensara (płytki klon, commit `fae96618`, 2026-07-21) oraz zadania z https://github.com/tensara/problems (commit `5adad3f4`, 2026-04-23). Oba klony usunięte po analizie.

## 1. Co to jest

Tensara to platforma do zawodów w pisaniu kerneli GPU (CUDA, Triton, Mojo, CuTe DSL, cuTile, pyptx). Repo `tensara` zawiera stronę (Next.js/Prisma) i silnik oceny w Pythonie, który uruchamia się na Modal. Zadania leżą w osobnym repo `problems`: 84 zadania, w dużej mierze port KernelBench L1/L2 (`problems/README.md:2`). Licencja GPL-3.0, repo aktywne (commity z lipca 2026). Sprzęt jest **wyłącznie NVIDIA**: T4, A10G, L4, L40S, A100, H100, H200, B200 (`engine/utils.py:23-32`). Kompilacja idzie tylko przez `nvcc -arch=compute_XX` (`utils.py:363-372`), telemetria tylko przez pynvml (`engine/gpu_monitor.py:8`). **Nie ma żadnego wsparcia AMD/HIP/ROCm** (grep po `amd|rocm|hip|gfx` daje zero trafień w kodzie). Rozwiązania użytkowników są domyślnie prywatne (`prisma/schema.prisma:149`, `isPublic @default(false)`), a w repo leżą tylko trywialne rozwiązania testowe (`testing/solutions/*`, np. matvec z redukcją w shared memory). Strona tensara.org zwracała 14.10.2026 HTTP 522. Blog czytałem przez Wayback Machine.

## 2. Kluczowe techniki (z dowodami)

### 2a. Harness oceny (`engine/`)

| Co | Dowód | Uwagi |
|---|---|---|
| Pomiar: para zdarzeń CUDA wokół **jednego** wywołania `solution(...)`, potem `synchronize` | `utils.py:1095-1112,1129` | Przy zadaniach rzędu 10–20 µs (np. cumsum B200 10.44 µs na stronie leaderboardu) wynik zawiera narzut uruchomienia i hosta, a często jest nim zdominowany. |
| Zimny L2 przed każdą iteracją: alokacja i `fill_` 40M float = 160 MB, potem `empty_cache` | `utils.py:952-960,1089` | 160 MB > 96 MB MALL, więc u nas też wystarczy. Alokacja i zwalnianie w każdej iteracji to jednak koszt hosta, który nie jest mierzony. |
| Adaptacyjna liczba iteracji: min 5, max 20, stop gdy CV < 1%; kernele ≥ 1 s mają stałe 12 iteracji | `runner.py:418-431`, `utils.py:1071-1077,1151-1158` | Wynik to **średnia** (`utils.py:1165`). Między przypadkami testowymi liczona jest średnia geometryczna (`runner.py:465-475`). |
| Rozgrzewka: 10× matmul 5000² fp32, potem `sleep(0.5)` | `utils.py:934-949`, wołane raz na zgłoszenie i przed każdym przypadkiem (`runner.py:403`, `utils.py:1042`) | Uśpienie po rozgrzewce częściowo ją unieważnia (zegar spada), zob. §5. |
| Anty-no-op: wyjście wypełnione 1.0, suma przed i po; jeśli bez zmian, to WRONG_ANSWER | `utils.py:1045-1067,1091-1127` | Słaba ochrona: wystarczy zapisać jeden element. Fałszywy alarm, gdy poprawne wyjście ma sumę równą liczbie elementów. |
| Telemetria per iteracja: wątek co 5 ms czyta zegar SM, temperaturę, P-state i bity throttlingu, a każda próbka ma `run_key` iteracji. Na wyjściu min/max/mean oraz OR bitów throttlingu | `gpu_monitor.py:14,39-76,137-181`, `utils.py:1098-1149` | To jedyny element harnessu, którego nie mamy w tej postaci (zob. P2). |
| Kalibracja tolerancji: rtol/atol z percentyla `|x−y|/(s*+|x|)` między referencją FP32 a tą samą referencją w FP16, zaokrąglone do jednej cyfry znaczącej. **Wymóg: tolerancja musi odrzucać wynik FP16** (inaczej błąd „too loose”) | `tolerance.py:47-94`, `utils.py:1616-1686` | Kontrola negatywna dla bramki jakości (zob. P1). Domyślny percentyl endpointu to 75 (`tolerance.py:121`), funkcji 10 (`:22`). Wybierana jest mediana przypadków (`:90-94`). |
| Referencja w trybie deterministycznym IEEE (bez TF32, `use_deterministic_algorithms`) | `utils.py:1579-1613` | Odpowiednik naszego bitowego greedy md5 i hashy logitów. |
| Statyczne zakazy (thrust, `std::sort`, `torch.topk` w Tritonie…) | `utils.py:402-660` | Bez znaczenia dla nas. |

### 2b. Zadania (`problems/`) istotne dla LLM

| Zadanie | Kształty / tolerancja | Dowód |
|---|---|---|
| matrix-vector | M = 4096–9216, K = 4096, dane U[−1,1], `rtol 2e-4, atol 3e-3` | `matrix-vector/def.py:49-55,66-67,106` |
| nvfp4-gemv (tylko B200) | M×K do 8192×4096, `rtol 2e-2, atol 5e-2` | `nvfp4-gemv/def.py:80-86,95`; `problem.md` `gpus: ["B200"]` |
| mxfp4/mxfp8 GEMM i quantize (tylko B200) | GEMM do 8192×4096×8192 | `mxfp4-gemm/def.py:89-96` |
| rms-norm | wiersze 512–2048 × 1024–16384 (kształty prefillu, nie decode) | `rms-norm/def.py:57-61,109` |
| scaled-dot-attention | b·h·s·e do 8·16·2048·64, **bez maski przyczynowej, bez GQA**, Q/K/V = randn·0.01 | `scaled-dot-attention/def.py:42-43,55-61,76-78,152` |
| softmax, argmax (`is_exact`), cumsum | ogólne tensory 3D/4D | `softmax/def.py:47-54`, `argmax/def.py:9,114` |

Brak zadań z formatami GGUF (Q4_K/Q5_K/Q6_K/IQ4_XS), z wieloma kolumnami (weryfikacja spekulacji), z MoE/top-k routingu, z atencją decode przy długim KV ani z GDN/shortconv.

### 2c. Metodologia „top” zawodników (blog, nie repo)

Kodu najlepszych rozwiązań nie da się przejrzeć: domyślnie są prywatne, a strona nie działała. Dostępne są posty na blogu. Najbardziej techniczny jest „Tutorial: Optimizing For Small Datasets” (H. T. Büyükışık, 13.11.2025, [archiwum](https://web.archive.org/web/20251130050635/https://tensara.org/blog/tutorial-for-optimizing-for-small-datasets-4820018)). To deklaracje autora na NVIDIA, bez danych:
- Pierwsze uruchomienie kernela kosztuje 500–600 µs (JIT/lazy loading), drugie 50 µs. Kernel trzeba więc uruchomić przy ładowaniu modułu.
- Kilka kerneli łączyć w CUDA graph („3–5 µs na launch po stronie hosta”). Zostać na domyślnym strumieniu. Alokować wszystko przy ładowaniu.
- Mapować wątki na relacje (pary), a nie na obiekty, i robić segmentowaną redukcję. To w praktyce split-K/split-KV.
- Uruchamiać tyle bloków, ile trzeba (occupancy API) i stroić rozmiar bloku mikrobenchmarkiem przy ładowaniu modułu.
- `__ldcs/__stcs` (streaming) dla danych używanych raz: „+20–30%” na małych zbiorach.
- Kernel kooperacyjny, w którym blok czeka na atomiku tylko na potrzebne mu dane, zamiast `grid.sync()`: „3–4 µs vs 0.5–1 µs”. Komunikacja drzewiasta.
- Zamiana wskaźników zamiast kopii i zerowania. Osobne instancje szablonu dla każdego rozmiaru.

Post „Benchmarking Solutions” ([archiwum](https://web.archive.org/web/20251203185020/https://tensara.org/blog/benchmarking-solutions-6746465)) opisuje ten sam harness co §2a. Inne posty na liście: rozwiązania conv-1d/conv-2d przez FFT, vector-add, Mojo patterns i lokalny harness uruchomieniowy. Nie dotyczą ani GEMV, ani atencji, ani normy.

## 3. Przeniesienie na AMD/HIP/RDNA3

| Technika | Przenosi się? | Jak / dlaczego nie / stan u nas |
|---|---|---|
| Graf zamiast osobnych launchy | Tak, już mamy | HIP graphs. Nasz zmierzony koszt granicy w grafie to ~2.53 µs (`lfm-decode-round2.md:23-31`), więc problemem jest koszt granicy po stronie GPU, a nie hosta. Tutorial tego nie rozróżnia. |
| Czekanie na atomiku zamiast `grid.sync` | Tak, zmierzone | gfx1100: bariera w trwałym kernelu 0.48–0.77 µs, ogon „ostatni blok” ~1 µs, łańcuch dużych faz ze spinującymi blokami 8–11 µs/fazę (`lfm-decode-round2.md:30-41`). Nasz wzorzec „ostatni przybyły liczy ogon” (NORM_ROUTER, INPROJ_CONV) jest lepszy od spinowania z tutorialu, bo nikt nie zajmuje slotów CU w oczekiwaniu. |
| `__ldcs/__stcs` | Tak, już mamy | Odpowiednik to bity GLC/DLC/SLC w buffer loads. Wagi czytamy z GLC|DLC (K1). Osobne SLC/GLC nie działało (`NOTES.md:250`). |
| Wątki na relacje / segmentowana redukcja | Tak, już mamy | Split-K dla small-M (alpha/beta, router), split-KV w FA (nsplit), kafel FA kvq dla GQA. |
| Szablon na rozmiar | Tak, częściowo | Szablony po liczbie kolumn i typie mamy. Rozwijanie pętli K dla stałych wymiarów nic nie dało (`NOTES.md:351`). |
| Strojenie przy ładowaniu (occupancy, rozmiar bloku) | Technicznie tak (`hipOccupancyMaxActiveBlocksPerMultiprocessor`) | Dla jednej, stałej karty to tylko dodatkowy czas startu. Stroiliśmy offline, a rocprofv3 w modelu jest wyrocznią (`NOTES.md:247-248`). |
| Zamiana wskaźników zamiast kopii | Tak | Już stosowane w stanie GDN/conv z opóźnieniem (S4, T1). Zostało 12 kopii wejść grafu na token (P3). |
| Telemetria per iteracja | Tak | `/sys/class/drm/card0/device/gpu_metrics` (`-r--r--r--`, czytelne bez roota), `pp_dpm_{sclk,mclk,fclk}`, hwmon. `gpu-power.sh monitor` próbkuje co 1 s i nie wiąże próbek z przebiegami (P2). |
| Kalibracja tolerancji z kontrolą negatywną | Tak (to metodologia) | P1. |
| Formaty NVFP4/MXFP4/MXFP8, FP8 E4M3 | Nie | gfx1100 nie ma FP8/FP4 w WMMA. Nasze modele to GGUF K-quanty. |
| Harness (Modal, nvcc, pynvml, CuTe/cuTile/pyptx) | Nie | Tylko NVIDIA. Mojo umie celować w AMD, ale platforma go na AMD nie uruchamia. |

## 4. Pomysły dla nas

**P1. Kontrola negatywna dla bramki jakości zmian niebitowych** (z `tolerance.py:72-76`: tolerancja, która przepuszcza znany gorszy wariant, jest błędna).
- Co: do procedury KLD (llama-perplexity, batch 6) dodać celowo zepsute warianty za przełącznikiem testowym, np. `GGML_HIP_TEST_DEGRADE=1|2|3`: (1) akumulacja KQ w FA kvq w f16 zamiast f32, (2) q8_1 z obciętym zaokrągleniem (truncate zamiast round) w `quantize_q8_1`, (3) pominięcie clampu S1. Bramka (KLD i same-top vs szum batch 6/512, `NOTES.md:225`) musi każdy z nich wykryć. Jeśli któregoś nie wykryje, to na tej klasie zmian jest ślepa.
- Zysk: 0 t/s [SZACUNEK], ale niebitowe łatki (A4, S2, przyszłe FA q8_0 na iu8 WMMA z raportu 09) dostają bramkę o znanej czułości.
- Koszt: 0.5 dnia, plus ~10 min GPU na 3 warianty × 1 model. Ryzyko: brak (tylko kod testowy).
- Pomiar: tabela KLD/same-top: baza, szum, warianty zepsute. Wymaganie: każdy zepsuty wariant > 2× szum.

**P2. Telemetria per przebieg w A/B (`spec_sweep.sh`, `ab.sh`, `kbench.sh`)** (z `gpu_monitor.py:39-76,175-177`).
- Co: wątek/proces próbkujący `gpu_metrics` co 5–10 ms: `average_gfxclk_frequency`, `current_uclk`, `current_fclk`, `throttle_status`, `temperature_hotspot`, `average_socket_power`. Każda próbka dostaje identyfikator przebiegu i ramienia A/B. W wyniku per przebieg: min/mean zegarów i OR bitów throttlingu, obok ms/krok.
- Po co: (a) wyjaśnienie „slow mode” gate+up ekspertów LFM (24.3 → 27.2 µs w 4/8 profili, `lfm-decode-round2.md:79-81`). Wykluczono tam tylko zegar globalny (porównując inne klasy MMVQ), a nie uclk/fclk ani stan DPM pamięci, które zostawiają ALU bez zmian [WNIOSEK]. (b) Odrzucanie przebiegów z innym stanem DPM zamiast dokładania seedów. Uzupełnia pomysł 3 z raportu 04 (A/A + amd-smi co przebieg) o rozdzielczość 5 ms i powiązanie z przebiegiem.
- Zysk: 0 t/s bezpośrednio. Jeśli slow mode okaże się stanem uclk/fclk, to do odzyskania ~0.11 ms/token LFM (~2.7%) [SZACUNEK z notatek], np. przez utrzymanie DPM pamięci.
- Koszt: 2–3 h (parser struktury `gpu_metrics_v1_3` dla SMU13 w Pythonie). Ryzyko: odczyt `gpu_metrics` to komunikat do SMU; przy 5 ms może minimalnie zaburzać pomiar. Sprawdzić A/A z próbkowaniem i bez.
- Pomiar: korelacja czasu gate+up (rocprofv3) z uclk/fclk w 8 profilach.

**P3. Wejścia grafu bez kopii (zero-copy / zamiana wskaźników)** (tutorial: „pointer swap”, „alokuj przy ładowaniu”).
- Stan: 12 węzłów `rocclr copyBuffer` na token, ~32 µs (`lfm-decode-round2.md:60,112`). W planie jest jedna spakowana kopia.
- Wariant: małe wejścia (token id, pozycje, indeksy wierszy KV, maska dla 1 sekwencji) zapisywać do `hipHostMalloc(..., hipHostMallocMapped)` w dwóch buforach naprzemiennie (parzystość kroku). Pierwszy kernel grafu czyta je bezpośrednio przez PCIe. Graf zawiera stały wskaźnik do slotu, a host przełącza slot argumentem albo słowem w pamięci urządzenia. Znika ostatni węzeł kopii; odczyt kilkudziesięciu bajtów przez PCIe kosztuje ~1–2 µs, ale w kernelu, który i tak startuje [WNIOSEK].
- Zysk: LFM ~25–30 µs/token (~0.7%), Qwen mniej [SZACUNEK]. Spakowana kopia zostawiłaby jedną granicę ~2.5 µs, więc różnica między wariantami to ~3 µs.
- Koszt: 1 dzień (`ggml-cuda.cu` ścieżka set_tensor wejść, `llama-graph` wejścia). Ryzyko: wyścig host–GPU przy nadpisaniu przed końcem poprzedniego grafu (stąd dwa sloty i event). Maska KQ przy długim kontekście jest za duża na PCIe i musi zostać w VRAM.
- Pomiar: liczba węzłów kopii w rocprofv3 (12 → 0), ms/token llama-bench tg128, przeplatane A/B. Greedy md5.

**P4. Testy FA z ostrym softmaxem** (lekcja z błędu Tensary, §5: Q/K·0.01 daje prawie równomierną uwagę).
- Co: sprawdzić, jakie rozkłady Q/K dostaje `test-backend-ops -o FLASH_ATTN_EXT` dla naszego `flash_attn_ext_kvq` i dodać przypadki z dużą normą Q (logity różniące się o 10–30). To samo w `logit_hash` przy głębokości.
- Po co: przy prawie równomiernym softmaxie wynik ≈ średnia V niezależnie od skali, maksimum i kolejności chunków. Błąd w online-softmax (rescale, max między chunkami, combine split-KV) przechodzi test. U nas rośnie to ryzyko przy FA q8_0 na iu8 WMMA (raport 09 P1), gdzie kwantyzujemy Q.
- Koszt: 2 h. Zysk: 0 t/s, mniejsze ryzyko cichych błędów. Pomiar: nowe przypadki przechodzą na bazie i wykrywają celowo zepsuty rescale (jak w P1).

**P5 (outside the box, niski priorytet). Lokalny „leaderboard” kształtów naszego modelu dla agentów.** Format `def.py` Tensary (referencja, przypadki, `verify_result`, `get_flops`), ale z naszymi zasadami: referencja = bieżący kernel (bitowo), przypadki = dokładne kształty Qwen/LFM (MMVQ 1/5 kolumn, FA kvq d=33k/98k, rms_norm 5120/2048, expert gate+up 2048×1536×4), metryka GB/s względem 960, zimny MALL (≥ 160 MB jak `utils.py:953`) i **czas w grafie z sąsiednimi węzłami**, bo izolowany mikrobenchmark mylił się co do Q6_K i GLC|DLC (`NOTES.md:247-248`). Mamy już `mmvq-bench` + `verify_mmvq.py`, więc to raczej uporządkowanie niż nowa zdolność. Koszt 1–2 dni. Warto tylko, jeśli planujemy równoległe próby kerneli przez agentów.

Świadomie **nie** proponuję megakernela/trwałego grida dla warstwy LFM. Tutorial podaje tylko liczby z NVIDIA bez kodu. Nasze pomiary już pokazują, że tanie są tylko małe gridy z barierą, a duże fazy ze spinowaniem przegrywają (`lfm-decode-round2.md:33-41`). TensorFold potwierdza to na M5 (raport tensorfold, „megakernel z grid barrier przegrał”). Tensara nie wnosi tu nowego argumentu.

## 5. Krytyka

- **Brak treści kernelowej.** W repo nie ma szybkich rozwiązań. Najlepsze są prywatne, a w `testing/solutions` leżą wersje naiwne. Wartość ogranicza się do harnessu i jednego posta-tutoriala, którego tezy są deklaracjami bez kodu ani danych („+20–30%”, „70–80% mniej opóźnienia”).
- **Pomiar nagradza narzut uruchomienia, a nie jakość kernela.** Jedno wywołanie w parze zdarzeń (`utils.py:1105-1112`) przy zadaniach 10–50 µs. Tutorial sam przyznaje, że wynik dla małych przypadków potrafi się różnić o 50% między zgłoszeniami („submit again”). Leaderboard w µs to w dużej mierze ranking latencji hosta i launchy na konkretnej maszynie Modal.
- **Statystyka:** średnia (nie mediana) i wczesne zatrzymanie, gdy CV < 1% po 5 iteracjach (`utils.py:1151-1158,1165`). To obciążony estymator: kończymy przy pierwszym „spokojnym” oknie. Brak przeplatania wariantów. Nasz proces (przeplatane A/B, przełączniki w jednym binarium, rocprofv3 w modelu) jest dojrzalszy.
- **Rozgrzewka z `sleep(0.5)`** (`utils.py:949`) po matmulu pozwala zegarom spaść przed pomiarem. Na AMD (DPM, runtime PM po 5 s, `NOTES.md:122-126`) byłoby to jeszcze gorsze.
- **Zadanie atencji jest słabym testem:** Q, K = randn·0.01 i E ≤ 256 (`scaled-dot-attention/def.py:76-78`) dają logity rzędu 1e-4, więc softmax jest prawie równomierny, a wynik ≈ średnia V. Błąd skali 1/√E, brak odejmowania maksimum albo zły rescale w online-softmax przechodzą przy `rtol 2e-2, atol 5e-3` [WNIOSEK z kodu]. Brak maski przyczynowej, GQA i kształtów decode (s_q = 1).
- **matrix-vector:** fp32/fp16 bez kwantyzacji. 4096–9216 × 4096 w fp32 to 64–151 MB, czyli na granicy L2/MALL współczesnych kart. Nic o naszym problemie (K-quanty, 1–16 kolumn, ~700/960 GB/s).
- **rms-norm** w kształtach prefillu (≥ 512 wierszy, `rms-norm/def.py:57-61`). Dla decode istotny jest 1 wiersz × 5120 i latencja, nie przepustowość.
- **Drobny błąd:** `mxfp4-gemm/def.py:89-96` deklaruje krotki `(m, n, k)`, a rozpakowuje je jako `m, k, n`, więc nazwy przypadków nie odpowiadają wymiarom (FLOPs się zgadzają, bo iloczyn jest symetryczny).
- **Anty-no-op przez sumę** (`utils.py:1045-1067`) da się obejść jednym zapisem. Wypełnienie 1.0 daje fałszywy alarm, gdy poprawne wyjście sumuje się do numel.
- Formaty NVFP4/MXFP4/MXFP8 (tylko B200) są dla gfx1100 bez znaczenia.

## 6. Werdykt

**Niska.** Tensara to harness i zadania wyłącznie pod NVIDIA, bez dostępnych szybkich rozwiązań. Do wzięcia są tylko tanie lekcje metodologiczne (kontrola negatywna bramki jakości P1, telemetria per przebieg P2, test FA z ostrym softmaxem P4) i drobna eliminacja kopii wejść grafu (P3, ~0.7% LFM). Metody z tutoriala „top” zawodników już mamy, i to w lepiej zmierzonej formie.
