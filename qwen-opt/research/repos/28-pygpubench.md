# 28 — gpu-mode/pygpubench: pomiar krótkich kerneli w warunkach adwersarialnych

Klon płytki, potem `--unshallow` tylko po statystyki historii. HEAD `286841bf` (2026-08-18), po analizie usunięty. Ścieżki `plik:linia` są względem korzenia repo. Nic nie było budowane ani uruchamiane na GPU. Źródła dodatkowe:
- RDNA3 ISA Reference Guide (AMD, 2023), §4.1.1 „Cache Controls: SLC, GLC and DLC”, s. 35–36 (mirror: https://github.com/azhirnov/cpu-gpu-arch/blob/main/pdf/AMD-rdna3_isa.pdf);
- LLVM AMDGPUUsage, „Memory Model GFX10-GFX11” (https://llvm.org/docs/AMDGPUUsage.html);
- topologia KFD tej maszyny (`/sys/class/kfd/kfd/topology/nodes/*/caches`, tylko odczyt plików).

Raporty 04 (KernelBench) i 18 (Tensara) opisały już: zdarzenia vs zegar hosta, czyszczenie cache zapisem 160–256 MB, średnią vs medianę, A/A, ABBA, telemetrię, zatruwanie buforów i kontrolę negatywną. Poniżej jest **tylko to, co nowe**.

## 1. Co to jest

Biblioteka Pythona z rdzeniem w C++/CUDA (nanobind) do mierzenia krótkich kerneli zgłaszanych przez **niezaufany** kod, czyli przez LLM-y na leaderboardach gpu-mode. Pomiar i sprawdzanie poprawności siedzą w skompilowanym rozszerzeniu, w osobnym procesie, za seccomp/landlock/mseal. Wynik wraca szyfrowany AES-GCM (`README.md:41-62`, `python/pygpubench/__init__.py:169-291`).

Stan repo:
- licencja Apache-2.0 (`pyproject.toml`);
- 160 commitów między 2026-02-15 a 2026-08-18, z czego 110 to E. Schultheis;
- CI na NVIDIA L4 przez Modal (`ci/modal_gpu_test.py`, `test/l2_persistence.py:22`);
- **tylko CUDA**: `CMAKE_CUDA_ARCHITECTURES "80;90"` (`CMakeLists.txt:8`), inline PTX, NVTX, PDL. Grep po `rocm|hip|amd|gfx` nie trafia w żaden kod.

## 2. Kluczowe techniki (dowody; [N] = nowe względem 04/18)

| Technika | Dowód | Komentarz |
|---|---|---|
| [N] **Głęboka kolejka zamiast synchronizacji na iterację.** Pętla pomiaru wrzuca do strumienia kolejno: przywrócenie wejść (D2D), czyszczenie cache, kanarki, `event_start`, kernel, `event_end` i kernel sprawdzający. Hosta synchronizuje dopiero raz, na końcu. Czasy odczytuje po wszystkim | `csrc/manager.cpp:496-528`, `:533`, `:576-580` | Host jest zawsze przed GPU, bo GPU w każdej iteracji ma do odrobienia czyszczenie i kanarki. Narzut Pythona i launchy nie trafia więc do pary zdarzeń. Tensara robiła `synchronize` po każdej iteracji (raport 18). |
| [N] **Kalibracja podłogi zdarzeń.** 100 pustych par zdarzeń wrzuconych za kernel czyszczący, żeby GPU było zajęte, gdy host je wstawia. Raportowana jest mediana | `manager.cpp:457-467`, `:611-630` | Podłoga jest raportowana (`event-overhead`), ale **nie** jest odejmowana. |
| [N] **Rozmiar czyszczenia z atrybutu urządzenia**: 2 × `cudaDevAttrL2CacheSize` | `manager.cpp:194-195`, `:318-320` | Na NVIDIA wystarcza. Na AMD to pułapka, zob. §3. |
| [N] **Zapis, a po nim `discard.global.L2`.** Linie zabrudzone przez czyszczenie są wyrzucane **bez zapisu do DRAM**, więc ich writeback nie obciąża mierzonego kernela | `csrc/clear_l2.cu:12-27`, `:65-77` (domyślnie `discard=True`, `__init__.py:53,176`) | Takiego problemu w KernelBench i Tensarze nie zauważono: oba czyszczą zwykłym zapisem. |
| [N] **Rozbrojenie „L2 persistence”** przed czyszczeniem: limit carve-out → 0, `cudaCtxResetPersistingL2Cache`, zerowe okno access-policy na strumieniu. Do tego test regresyjny: wariant „uczciwy” vs „przypięty w L2” musi mieć medianę w stosunku ≥ 0.88 | `clear_l2.cu:28-63`, `test/l2_persistence.py:1-23`, `:150-157` | Lekcja ogólna: **polityka cache ustawiona przez jeden kernel zmienia czas innych**. Na AMD odpowiada temu bit DLC (§3). |
| [N] **Inne dane w każdej iteracji i losowa kolejność.** Generowane jest `repeats+1` przypadków, każdy z własnym seedem. Kopie „cieniowe” leżą poza torchem, a oryginały są nadpisywane 0xFF. Kolejność przypadków jest tasowana | `manager.cpp:233-255`, `:262-289`, `:442-445` | Działa przeciw memoizacji po wskaźniku (krytyka w 04 §5). |
| [N] **Kanarki**: 1/256 linii wejścia jest zmienione (XOR) i poprawiane dopiero po czyszczeniu. Kernel kooperacyjny zajmuje cały LDS, żeby nic nie biegło równolegle | `csrc/check.cu:136-182`, `manager.cpp:512-518` | Kompromis między „zimnym” cache a oknem na oszustwo. Do cache wraca < 1% danych. |
| [N] **Rozgrzewka mierzona czasem** (1 s pętli czyszczenie + kernel + sync). Liczba iteracji wynika z budżetu 1 s, a przy mniej niż 3 pomiar kończy się błędem | `manager.cpp:376-394`, `:474-482`, `manager.h:102-103` | W przeciwieństwie do Tensary nie ma wczesnego stopu po CV. Własny exploit pokazuje jednak, że rozgrzewkę łatwo wykryć, bo zawsze dostaje to samo wejście (`exploits/submission_warmup.py:1-19`). |
| [N] **Sprawdzenie w każdej iteracji**, tuż po `event_end`. Kernel sprawdzający startuje z atrybutem PDL i czyta bloki w losowej kolejności. Licznik błędów leży pod losowym offsetem w 2 MB szumu, z przesunięciem o wartość początkową | `manager.cpp:525-527`, `:428-441`; `check.cu:13-18`, `:85-98` | Wyłapuje pracę na innym strumieniu, która nie zdążyła się skończyć. Uwaga: losowanie bloków ma błąd, zob. §5. |
| Statystyki: best/worst/median/mean/std/**SEM**. Wynik bez kompletu iteracji ma flagę `full=False` | `__init__.py:118-159`, `:105-114`, `:290` | Od raportów 04/18 nowe jest tylko SEM i flaga kompletności. |
| Izolacja: proces `spawn`, seccomp-notify, landlock, mseal, wynik podpisany | `README.md:41-62`, `csrc/seccomp.cpp`, `csrc/landlock.cpp`, `python/pygpubench/utils.py:30-45` | Nie dotyczy nas (nie uruchamiamy wrogiego kodu). |
| 22 exploity i 2 kontrole („poprawny”, „błędny”): ptrace, `/proc/self/mem`, łatanie GOT, skan sterty pod klucz AES, zerowanie licznika błędów, NaN w oczekiwanym wyniku przez `gc`… | `exploits/run_all.py:28-63`, `exploits/submission_*.py` (24 pliki) | Wzorzec „macierz exploit × obrona” jest już w 04 (pomysł 9). Konkretne ataki są in-process i dla nas nieistotne. |

## 3. Przeniesienie na AMD/HIP/RDNA3

| Element | Na gfx1100 | Szczegóły |
|---|---|---|
| Zdarzenia w głębokiej kolejce | Tak, ale nam niepotrzebne | Mierzymy grafy HIP zegarem ściennym (`mmvq_bench.cpp:67-73`, llama-bench) i kernele przez rocprofv3 (`ktime.py`, `verify_mmvq.py`). Zasada „GPU zajęte, host z przodu” jest spełniona, bo graf jest jednym zgłoszeniem. |
| Rozmiar czyszczenia z atrybutu urządzenia | **Pułapka** | KFD na tej karcie podaje osobno L2 = 6144 KB i L3 = 98304 KB (sysfs, odczyt). `hipDeviceAttributeL2CacheSize` odpowiada L2 [WNIOSEK], więc port 1:1 czyściłby 12 MB i zostawiał ciepły MALL. Rozmiar trzeba wziąć z poziomu 3 topologii KFD albo wpisać na stałe ≥ 2 × (6 + 96) MB. |
| `discard.global.L2` | Brak odpowiednika dla shaderów obliczeniowych [WNIOSEK: nie znalazłem w ISA RDNA3 instrukcji „odrzuć brudne linie”] | MALL jest cache'em po stronie pamięci, „fully coherent with GPU memory” (AMDGPUUsage, GFX10.3/GFX11), więc brudne linie po zapisie 256 MB wrócą do DRAM przy wyrzuceniu, czyli w trakcie mierzonego kernela [WNIOSEK]. Zamiennik to **czyszczenie odczytem**: po jednorazowej inicjalizacji czytać ≥ 256 MB bufora i niczego nie zapisywać, wtedy wyrzucenia są czyste. |
| Persistence (okno access-policy) | **Odpowiednik istnieje i już go używamy, choć nie wprost:** bit **DLC = MALL NOALLOC** | Tabela RDNA3 ISA §4.1.1 (s. 35–36): dla loadów kolumna „MALL (NOA)” ma 1, gdy `DLC=1` lub gdy `llc_noalloc` w deskryptorze bufora (V#) ∈ {2,3}. Opis: „DLC — Temporal Hint for Infinity Cache: 1 = Non-temporal”. W LLVM dla GFX11 load `nontemporal` daje `slc=1 dlc=1` (AMDGPUUsage, tabela kodu GFX10-GFX11). |
| Stan u nas | Wiele-kolumnowe MMVQ (n ≥ 2) czyta wagi z `cpol = 5` (GLC\|DLC) | `~/llama-master/ggml/src/ggml-cuda/mmvq.cu:345-349`, `:361-383`. Komentarz w kodzie mówi „stream past the per-CU caches”. W rzeczywistości DLC znaczy też **„nie alokuj w MALL”**. Ścieżka n = 1 (`use_multi` wymaga `ncols_dst >= 2`, `mmvq.cu:28`, `:1488`) czyta przez zwykłe wskaźniki, czyli **alokuje w MALL**. Dotyczy to całego dekodu LFM (w tym `mul_mat_vec_q_moe`, `moe_down_reduce`, `mul_mat_vec_q_conv`), draftu MTP Qwena i Qwena bez spekulacji. |
| Wyjaśnienie znanej anomalii | [WNIOSEK, spójne z danymi] | `NOTES.md:247-248`: „mikrobench myli się co do GLC\|DLC (w modelu zysk)”. `mmvq_bench` czyta 512 MB kopii po kolei (`mmvq_bench.cpp:29-30`), więc w MALL nie ma nic do ochrony i NOALLOC jest neutralny. W modelu NOALLOC na 15 GB wag weryfikacji zostawia MALL dla KV, aktywacji, q8_1 i małych wag. To dokładnie lekcja z `l2_persistence.py`, tylko w przeciwnym kierunku. |
| PDL dla kernela sprawdzającego | Nie | Brak na gfx1100 (raporty 07 i 14). |
| Kanarki (launch kooperacyjny) | Technicznie tak (`hipLaunchCooperativeKernel`) | Nie potrzebujemy. |
| seccomp/landlock/AES | Nie dotyczy | Nasz kod jest zaufany. |

## 4. Pomysły dla nas

**P1. Wagi n = 1 z MALL NOALLOC (LFM: cały dekod; Qwen: draft MTP).** To jedyny pomysł z bezpośrednim zyskiem w t/s.
- **Co zmienić.** W ścieżce `ncols_dst == 1` dla K-quantów (`mul_mat_vec_q` przy `!use_multi`, `mul_mat_vec_q_moe`, `mul_mat_vec_q_moe_down_reduce`, `mul_mat_vec_q_conv`; `vecdotq.cuh` czyta wagi przez wskaźniki) wprowadzić ładowanie wag z polityką ustawianą makrem `MMVQ_N1_X_CPOL`, wzorem `MMVQ_R3_X_CPOL`. Dwie drogi:
  - (a) `__builtin_nontemporal_load` na wagach, co na GFX11 daje `slc=1 dlc=1`;
  - (b) buffer loads (`mmvq_make_src`) z `cpol = 4` (sam DLC) lub `5` (jak K1).

  Warianty do A/B: 0 (dziś), 4, 5, oraz (a) jako `slc|dlc`. SLC osobno już przegrał (`NOTES.md:250`), ale to był test bez DLC.
- **Dlaczego może dać zysk** [WNIOSEK].
  - LFM przepuszcza ~1.76 GB wag MMVQ na token (`lfm-decode.md:164`), cyklicznie i z alokacją. Przy dostępie cyklicznym większym niż cache LRU daje 0 trafień, a każdy token wyrzuca z MALL wszystko inne: wagi routera F32, KV q8_0, q8_1, stan conv, embedding.
  - Około 1.3 ms/token przypada na małe kernele ograniczone latencją i przerwy między nimi (`NOTES.md:340`). Pierwsze chybienie do DRAM leży na ich ścieżce krytycznej.
  - K1 dla n ≥ 2 dał w modelu 22.95 → 22.08 ms mmvq na weryfikację (−3.8%, `mmvq.cu:345-347`). Mikrobench tego nie pokazywał.
- **Zysk** [SZACUNEK]: LFM 0–3% (0–0.12 ms/token). Qwen ≤ 0.5%, bo dotyczy tylko draftu, ~0.65 ms/poziom (`NOTES.md:309`).
- **Koszt:** 0.5–1 dnia, bo ścieżka wskaźnikowa ma wiele typów.
- **Ryzyko:** niskie. Zmienia się tylko polityka cache, więc wynik jest **bitowo identyczny**. Głowica Q6_K przy GLC traciła ~0.14 ms (`mmvq.cu:347`), więc warto osobno sprawdzić `cpol=4` bez GLC.
- **Pomiar:**
  - `ab.sh` z 6–8 rundami (przełącznik w jednym binarium);
  - rocprofv3 per klasa (`trace_breakdown.py`): czy zysk siedzi w małych kernelach (rms_norm, router mmvf, topk), czy w samym MMVQ;
  - serwer `spec_sweep` `lfm none`, bo llama-bench karmi model losowymi tokenami (`llama-bench.cpp:2205,2219`), a routing ekspertów na prawdziwym tekście jest inny.

**P2. „Budżet MALL”: wybrana część wag celowo alokowana.** Robić po P1, jeśli MALL okaże się szybszy od DRAM (bramka z P3).
- Przy cyklicznym dostępie większym niż cache opłaca się alokować **stały podzbiór ≤ ~80 MB**, a resztę czytać z NOALLOC. Podzbiór zostaje wtedy trafiony przy każdym przejściu, zamiast LRU tracącego wszystko [WNIOSEK: klasyczny wynik dla LRU; polityka wymiany MALL nie jest udokumentowana].
- Kandydaci:
  - **Qwen, warstwa MTP + głowica draftu.** Czytana 4× na krok, ~0.65 ms na poziom (`NOTES.md:285,309`). Weryfikacja ma już NOALLOC, więc podzbiór przetrwałby także między krokami. Zysk ≈ 4 × 80 MB/700 GB/s × (1 − 1/s), gdzie s to przyspieszenie z MALL. Przy s = 1.3–2 daje to **0.1–0.23 ms/krok (0.3–0.8%)** [SZACUNEK].
  - **LFM.** Wagi atencji 10 warstw GQA, ok. 72 MB w Q5_K [SZACUNEK z kształtów 2048×2048 i 2×2048×512]. Te kernele są jednak ograniczone latencją (q/o 5.1 µs, `lfm-decode.md:164`), więc zysk ≤ 20 µs/token.
  - **Długi kontekst.** Prefiks KV ≤ 80 MB z alokacją, reszta KV z NOALLOC. Dla LFM q8_0 przy 98k: +2.38 ms/token za KV (`lfm-decode-round2.md:89-90`), z czego ~1% do odzyskania [SZACUNEK].
- **Co zmienić:** flaga per tensor (np. `tensor->extra` albo zakres adresów) przekazana do kernela jako argument jednolity w bloku. Do tego dwie gałęzie ładowania z różnym `cpol`. Rozgałęzienie jest jednolite w bloku, więc koszt instrukcji pomijalny.
- **Koszt:** 1–2 dni. **Ryzyko:** średnie. Zysk zależy od nieudokumentowanej polityki MALL, a efekt może zniknąć przy innych procesach GPU.

**P3. `mmvq_bench` widzący efekty MALL: tryb „ciepły” i metryka „szkody w cache”.** Przeniesienie testu `l2_persistence.py` na nasz grunt.
- (a) `MMVQ_BENCH_BYTES` (dziś stałe 512 MB, `mmvq_bench.cpp:29`). Wartość 48 MB daje kopie mieszczące się w MALL, czyli pomiar s = t_zimny / t_ciepły dla n = 1 i n = 5. To bramka zerokosztowa dla P2 i dla P3 z raportu 05 („prefetch do MALL”).
- (b) Nowa metryka: kernel „ofiara” czyta stały zbiór 32–64 MB (symulacja KV, routera, aktywacji) przed i po mierzonym MUL_MAT. Mierzony jest przyrost czasu ofiary (rocprofv3). Wariant MMVQ z DLC=0 powinien ofiarę spowalniać, a z DLC=1 nie.
- Taki mikrobench przestaje „mylić się co do GLC|DLC” (`NOTES.md:247-248`) i pozwala stroić politykę cache bez pełnego modelu.
- **Koszt:** 3–4 h. **Ryzyko:** brak. **Zysk:** 0 t/s bezpośrednio, ale P1/P2 dostają tani, wiarygodny pomiar.

**P4. Czyszczenie odczytem, nie zapisem; rozmiar z KFD.** Korekta pomysłu 8 z raportu 04.
- Raport 04 zalecał „zapisać 256 MB” przed iteracją mikrobenchmarku małych kerneli (router, conv, rms_norm, `chain_cost.hip`).
- Lekcja z `clear_l2.cu:18-27,65-77`: po zapisie w L2/MALL zostaje do ~102 MB brudnych linii, których writeback trafia w mierzony kernel. NVIDIA ma na to `discard`, RDNA3 nie ma.
- Lepiej: jednorazowo zapełnić bufor ≥ 256 MB, a przed każdą iteracją go **czytać** (kernel sumujący do martwego rejestru, zwykłe loady). Rozmiar brać z `/sys/class/kfd/.../caches` (L2 + L3), nie z atrybutu HIP.
- **Koszt:** 1 h. **Pomiar:** czas małego kernela po czyszczeniu zapisem vs odczytem. Różnica pokazuje, ile stary sposób zawyżał.

**P5. Statystyka i powiązanie wyniku z poprawnością w `ab.sh`.** Drobne.
- `ab.sh` bierze tylko `avg_ts` (`$(NF-1)` z CSV, `~/wt/lfm2-prof/ab.sh:19-20`). llama-bench w `-o jsonl` wypisuje `samples_ns` każdego powtórzenia (`llama-bench.cpp:1843-1844`). Wystarczy je zbierać i raportować medianę, min, std i **SEM** jak `basic_stats` (`__init__.py:148-159`), z flagą „niekompletne” jak `full`, gdy któryś przebieg padł (dziś `timeout 200` po cichu daje pusty wynik).
- Sprawdzanie przy pomiarze (pygpubench sprawdza każdą iterację, `manager.cpp:525-527`): raz na ramię uruchomić `logit_hash` z **tym samym** `BIN::ENV` co ramię A/B, nie tylko z domyślnym buildem. Łapie to przełącznik `GGML_HIP_*`, który psuje wynik tylko w swojej konfiguracji.
- **Koszt:** 1–2 h. **Ryzyko:** brak.

**P6. Podłoga znaczników czasu w rocprofv3** (odpowiednik `measure_event_overhead`, `manager.cpp:611-630`).
- Jednorazowo zmierzyć czas trwania pustego kernela w śladzie rocprofv3 (`Start/End_Timestamp`). `trace_breakdown.py` i `ktime.py` mogłyby wtedy pokazywać obok czasów małych kerneli (rms_norm 2.7 µs, topk 3.5 µs) „czas − podłoga”.
- Dziś znamy koszt **granicy** (2.53 µs, `NOTES.md:358`), ale nie wiadomo, ile z 2–3 µs „małego kernela” to stała profilera i dispatchu, a ile praca. To ustala dolną granicę zysku z kolejnych fuzji.
- **Koszt:** 1 h. **Zysk:** lepsza priorytetyzacja fuzji.

Świadomie **nie** proponuję: szyfrowania i podpisywania wyników, seccomp ani ochrony przed agentami-oszustami in-process. Nasi agenci piszą łatki, a pomiar robi nasz własny skrypt. Wystarczą bramki z 04 (histogram kerneli, A/A) i P5.

## 5. Krytyka

- **Błąd w losowaniu bloków kernela sprawdzającego.** `random_index` (`check.cu:13-18`) liczy `(blockIdx * 2654435761u + seed) % gridDim` w 32-bitowym `unsigned`. Mnożenie przepełnia się przed `%`, więc to **nie jest permutacja**, gdy liczba bloków nie jest potęgą dwójki. Część bloków jest sprawdzana dwa razy, część wcale. Moje przeliczenie w Pythonie (bez GPU), odsetek sprawdzanych bloków w jednej iteracji:
  - 100 bloków: ~58%;
  - 1000: ~73%;
  - 3000: ~95%;
  - 10000: ~93%;
  - 100000: ~69%;
  - potęgi dwójki: 100%.

  Błąd w części wyjścia jest więc łapany w danej iteracji z prawdopodobieństwem ~60–95%. Przy wielu iteracjach z różnymi seedami w końcu wyjdzie, ale gwarancja „każda iteracja jest sprawdzona” nie obowiązuje.
- **„2 × L2” to założenie NVIDIA** (`manager.cpp:194-195`). Na kartach z MALL (RDNA2/3, MI300) pomiar byłby „ciepły”. To nie jest błąd dla ich CI na L4, ale biblioteka nie ostrzega przed tym.
- **Mierzony jest tylko scenariusz całkowicie zimny.** Kernel w prawdziwym potoku zastaje cache z danymi sąsiadów i sam zostawia po sobie szkody. Test `l2_persistence` dowodzi, że autorzy wiedzą, jak bardzo polityka cache zmienia wynik. Mimo to kernel o dobrej polityce (NOALLOC dla strumienia) jest tu oceniany tak samo jak kernel, który niszczy cache. Dla nas właśnie ta różnica była zyskiem (K1).
- **Sprawdzanie przez PDL zaburza ogon pomiaru.** Autorzy sami to przyznają (`README.md:73-77`): bloki kernela sprawdzającego mogą zajmować SM w końcówce mierzonego kernela. Nie podają, jak duży to efekt.
- **Szacunek czasu z rozgrzewki zawiera czyszczenie, synchronizację i narzut Pythona** (`manager.cpp:383-392`). Dla kerneli mikrosekundowych liczba iteracji zależy więc głównie od hosta. Rozgrzewka używa zawsze `args.at(0)`, co ich własny exploit wykorzystuje (`exploits/submission_warmup.py:1-19`), i ta luka pozostaje otwarta.
- **Statystyka.** `median = sorted[runs//2]` daje górną medianę dla parzystego `runs` (`__init__.py:153`). `__str__` wypisuje średnią ± std jako wynik główny (`:141-145`). Podłoga zdarzeń jest raportowana, ale nieodejmowana. Brak przeplatania wariantów: to narzędzie do jednego kernela, a nie do A/B.
- **Zakres.** Jeden kernel, jedno wyjście („TODO handle multiple outputs”, `manager.cpp:596`), tylko dane ciągłe, tylko CUDA. Do pomiaru end-to-end dekodowania LLM nie nadaje się w ogóle.

## 6. Werdykt

**Średnia.** Sam harness jest dla nas nieprzenośny (tylko CUDA, obrony in-process). Jego lekcja o polityce cache, czyli „persistence” i „discard”, przeniesiona na RDNA3 prowadzi do konkretnego, taniego i bitowo neutralnego eksperymentu: DLC = MALL NOALLOC dla wag w ścieżce n = 1, która dziś alokuje w MALL. Daje też poprawki metodologii: mikrobench widzący MALL, czyszczenie odczytem i rozmiar czyszczenia z KFD.
