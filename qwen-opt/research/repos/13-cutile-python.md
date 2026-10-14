# 13 — NVIDIA/cutile-python (cuTile)

Klon: `--depth 1`, commit d9d8520 (2026-10-13). Pliki cytowane względem korzenia repo.

## 1. Co to jest
cuTile Python to język kafelkowy (DSL w Pythonie) NVIDIA. Kod jest kompilowany do Tile IR (`tileiras`), a nie do PTX. Programista opisuje pracę **bloku** na kafelkach: `ct.load`/`ct.mma`/`ct.store`. Wątki, układ danych w rejestrach i synchronizacja wewnątrz bloku nie są widoczne (`docs/source/execution.rst:23-27`). Repo jest bardzo aktywne: wydanie 1.6.0 z 2026-09-09 (`CHANGELOG.md:7-8`) i commity z 2026-10-13. Licencja Apache-2.0. Wymaga sterownika r580+. `tileiras` obsługuje Blackwell i Ampere/Ada, a Hopper „w kolejnych wersjach” (`README.md:53-56`). W `experimental/` są jeszcze `cuda.lang` (SIMT w Pythonie) i `task_scheduling` (specjalizacja warpów, potoki mbarrier/TMA/tcgen05, w tym **kernel FMHA decode dla sm100a**). W repo nie ma żadnych opublikowanych pomiarów wydajności.

## 2. Kluczowe techniki (z dowodami)
1. **Model kafelkowy, schedule jako podpowiedzi.** Algorytm to operacje na kafelkach, a resztę wybiera kompilator na podstawie podpowiedzi: `latency` 1–10 (głębokość prefetchu, `docs/source/performance.rst:35-38`), `allow_tma` (`:40-43`), `occupancy`/`num_ctas` per architektura przez `ByTarget` (`:12-27`), `assume_divisible_by` (wyrównanie aż do szerokich ładowań, `:62-88`). W 1.6.0 doszły też `check_bounds=False` i stałe strides z annotacji (`CHANGELOG.md:25-45`). Przykład FA: K ładowane z `latency=2`, V z `latency=4`, kernel z `occupancy=2` (`samples/AttentionFMHA.py:26, 86-90, 123-126`).
2. **PDL jako operacja języka.** `grid_dependency_control_launch_dependents()` / `grid_dependency_control_wait()` (`src/cuda/tile/_stub.py:4682-4698`, `CHANGELOG.md:21-24`). W `task_scheduling` są to zasoby `PdlWaitBarrier`/`PdlLaunchBarrier`, umieszczane w konkretnym miejscu harmonogramu zadania, a nie jako globalna synchronizacja (`experimental/task_scheduling/README.md:25`).
3. **Dzielenie pętli wg maski** (blog NVIDIA, [link](https://developer.nvidia.com/blog/tuning-flash-attention-for-peak-performance-in-nvidia-cuda-tile)): pętla K/V jest podzielona na kafle bez maski, z częściową maską i pominięte. To „największa pojedyncza optymalizacja, do +32%” FA prefill (pomiar NVIDIA, nie nasz). W samplu maska jest liczona z indeksów tylko dla `j >= mask_start` (`samples/AttentionFMHA.py:73-106`).
4. **FMHA decode sm100a** (`experimental/task_scheduling/tutorial/08_fmha_decode_sm100a/`):
   - „SwapsMmaAb”: KV jako M=128, Q jako N=8 (`fmha_decode_config.py:4`). `groups_tokens_heads_q` pakuje tokeny × głowy GQA w N (`:43, 49-55`).
   - Specjalizacja warpów w CTA 512 wątków: 2× softmax (po 4 warpy), korekcja (4), MMA (1), load (1), page-offsets (1), scheduler/CLC (`fmha_decode_config.py:24-32`).
   - **Dwie instancje K/V naprzemiennie** w jednym CTA, z obranym początkiem QK i końcem PV (`fmha_decode_tasks.py:4, 298-309`). Każda instancja ma własne max/sumę i akumulator O. Scalenie następuje w epilogu (`fmha_decode_resources/tmem_resources.py:356-391`), więc nie ma osobnego kernela combine.
   - Korekcja O jest pomijana, gdy max się nie zmienił (`vote_all_sync(unchanged)`, `tmem_resources.py:341-352`). Porównanie jest dokładne, bez progu.
   - Kodowanie float→uint z zachowaniem porządku, do atomowego max w smem (`tmem_resources.py:30-37`).
   - **Brak split-KV między CTA**: grid = (q_ctas, heads_kv, batch) (`fmha_decode_kernel.py:278`).
5. **Ograniczony, wyczerpujący model checker harmonogramów** (`experimental/task_scheduling/src/task_scheduling/exhaustive_checker.py:4`, README:27, 114, 124). Na hoście sprawdza wszystkie przeploty acquire/wait/commit/release: zakleszczenia, wyścigi i aliasy buforów. Działa bez GPU. Sami autorzy przyznają, że **nie modeluje kolejności PDL** (README:128).
6. **MoE (sample)**: tokeny posortowane wg eksperta i dopełnione do TILE_M, gather wierszy A, ważenie w epilogu down, scatter, `torch.sum` po top-k (`samples/MoE.py:45-85, 114-174, 288`). To klasyczny fused_moe z vLLM/Triton dla prefillu.
7. **Autotuner** `tune.exhaustive_search` z timeoutem na uruchomienie (izolacja zawieszonych kerneli) i wczesnym odcinaniem wolnych konfiguracji (`src/cuda/tile/tune/_tune.py:141-158`, `CHANGELOG.md:122, 179`).

## 3. Przeniesienie na AMD/HIP/RDNA3
| # | Technika | Da się? | Jak / dlaczego nie |
|---|---|---|---|
| 1 | Kafelki + podpowiedzi `latency`/`occupancy` | Tylko styl | Nie ma kompilatora Tile IR na AMD. Odpowiedniki już mamy ręcznie: `amdgpu_waves_per_eu` per (typ, n), prefetch rejestrowy następnego kafla w `fattn-kvq.cu:316, 357, 416`, buffer loads. Najwyżej warto ujednolicić głębokość prefetchu jako parametr szablonu, który da się przemiatać. |
| 2 | PDL | **Nie ma natywnie** (gfx1100/ROCm 10.0: `07-flashinfer.md:68`), **ale da się zbudować ręcznie** | `hipExtAnyOrderLaunch` (czyści bit bariery AQL, `hip_runtime_api.h:1031`, `hip_ext.h:44-52`) + w kernelu: najpierw ładowania niezależne od poprzednika (wagi), potem spin `__hip_atomic_load(acquire, agent)` z `s_sleep` na fladze, którą zapisuje ostatni blok poprzednika (release). Zob. pomysł P1. |
| 2b | `hipLaunchAttributeExtDynDataPrefetch` (prefetch do L2 przed kernelem, `hip_runtime_api.h:1683-1726`) | Raczej nie | Nagłówek mówi „Valid for launches”, a nie dla węzłów grafu. W `libamdhip64.so` nie ma napisów związanych z tą funkcją [WNIOSEK: prawdopodobnie tylko MI/gfx12xx]. Pod grafami HIP bezużyteczne. |
| 3 | Dzielenie pętli wg maski | **Tak** | Bitowo identyczne (x + 0 = x, jedynie −0 → +0, a exp2 daje to samo). Zob. P3. |
| 4 | Swap A/B + pakowanie tokeny×głowy | Już mamy | `fattn-kvq.cu`: K wprost do fragmentów A WMMA, kolumny = GQA × tokeny, jedno przejście po KV. |
| 4 | Dwie instancje KV + scalenie w CTA | Już mamy | `fattn-kvq` dzieli KV między warpy w bloku i scala w LDS (`fattn-kvq.cu:436-497`). Między blokami jest split + `flash_attn_combine_results`. Scalenie przez „ostatni blok” zamiast combine zaproponował już raport 07. |
| 4 | Pomijanie korekcji O | Mamy lepiej | U nas `__any(raise_max)` z progiem 8 (log2) (`fattn-kvq.cu:362-396`), czyli w stylu FA4. Dokładne `==` w cuTile pomija rzadziej. |
| 4 | Specjalizacja warpów, TMA, TMEM, CLC | Nie | Brak TMA/async-copy/nazwanych barier/`setmaxnreg` na RDNA3. Producent musiałby przechodzić przez VGPR. Wniosek jak w raporcie 03 (§3 pkt 6). |
| 5 | Model checker przeplotów | **Tak, na hoście** | Python, bez GPU. Zob. P2. |
| 6 | Sortowanie MoE + pad do TILE_M | Już jest | MMQ ids w llama.cpp. Dla dekodu batch 1 nieistotne. |
| 7 | Autotuner z timeoutem | Proces | U nas mikrobench myli się co do Q6_K i GLC/DLC (NOTES:247-248), więc tuner musiałby mierzyć w modelu (rocprofv3). |

## 4. Pomysły dla nas

### P1. „Ręczny PDL”: kernel zależny wystartowany wcześniej, wagi pobierane przed czekaniem (LFM, potem Qwen)
- **Co zmienić**:
  - `ggml_cuda_kernel_launch` (`common.cuh`, ścieżka z roadmapy `rr-hip.md:136`): flaga any-order także dla **zależnych** sąsiadów, nie tylko niezależnych.
  - W `mul_mat_vec_q` n=1 (wersja bez ids: in_proj+conv, out_proj, attn q/k/v/o, gęste FFN, głowica) dochodzi prolog. Blok liczy adresy i ładuje **cały** swój wycinek wag do VGPR: K=2048 Q5_K, 2 wiersze na blok to ok. 22 dword/lane, a mamy tylko 4 obiegi pętli K (`lfm-decode.md:51-52`). Potem czeka (spin z `s_sleep 1`, acquire/agent) na `flag[k] == gen`, a dopiero potem czyta q8_1 aktywacji.
  - Poprzednik: ostatni blok (ticket, który już mamy) zapisuje `flag[k] = gen` z release. `gen` jest licznikiem replayów grafu w pamięci urządzenia, zwiększanym przez pierwszy kernel grafu, więc niczego nie trzeba resetować.
  - Kernele ids (gate+up, down) i małe kernele mogą dostać samo nakładanie narzutu CP, bez prefetchu wag.
- **Dlaczego to nie jest powtórka wyniku negatywnego** („łańcuch dużych faz z czekającymi blokami 8–11 µs/faza”, `lfm-decode-round2.md:33-36`): nakładamy tylko **sąsiednie** kernele. Bloki B czekają wyłącznie w ogonie A. Dyspozytor kolejki wydaje paczki po kolei, więc pierwsza grupa robocza B dostaje miejsce dopiero po wydaniu ostatniej grupy A. Wszystkie bloki A są już wtedy rezydentne albo skończone, a zakleszczenie jest niemożliwe [WNIOSEK: kolejność wydawania grup przez SPI w jednej kolejce do potwierdzenia mikrobenchmarkiem]. Mierzony koszt czekania na barierze to 0.5–0.8 µs (`lfm-decode-round2.md:30-31`), a granica kernela kosztuje 2.53 µs.
- **Zysk [SZACUNEK]**: LFM ma 416 granic i ~0.87 ms bezczynności na token (~2.1 µs na granicę). Około 106 uruchomień MMVQ bez ids może ukryć ~50% (plus część narzutu rampy małych launchy, 2–3 µs, `lfm-decode.md:52-53`), a ~300 pozostałych ~30%. Razem **0.2–0.45 ms/token (5–11%, 244 → ~260–270 t/s)**. Qwen: weryfikacja ~831 kerneli i ~2.8 ms przerw, czyli ok. 0.3–0.6 ms/krok (1–2%).
- **Wymagania wstępne (blokujące)**:
  - (a) czy przechwytywanie strumienia zachowuje flagę any-order (`AMD_LOG_LEVEL=4`, pole `barrier=`; to samo otwarte pytanie co `rr-hip.md:138`);
  - (b) mikrobenchmark w `launch_cost.hip`: pary A→B (A z 32..4096 bloków) z barierą vs any-order + flaga. Mierzyć czas od końca A do końca B i sprawdzić brak zawieszeń przy gridach większych niż GPU mieści naraz.
- **Koszt**: średni do dużego (protokół, gen-counter w grafie, test). **Ryzyko**: zawieszenie GPU przy błędzie protokołu. Dlatego najpierw P2, a w buildzie debug spin z limitem iteracji i `__builtin_trap()`. Sprawdzanie bitowej zgodności bez zmian (te same obliczenia).
- **Pomiar**: `ab.sh` llama-bench tg128 przeplatany, przerwy w rocprofv3 (`tok.py`), hashe logitów `lh.sh`.

### P2. Model checker protokołów synchronizacji na hoście
- **Co**: mały skrypt w Pythonie (wzorzec: `exhaustive_checker.py`, BFS po przeplotach z limitem stanów). Modeluje nasze protokoły: tickety „ostatni blok” (NORM_ROUTER, MOE_DOWN_REDUCE), tickety grupowe INPROJ_CONV (64 grupy × 48 bloków), drugi slot cache q8_1 (alias odczyt/zapis, `lfm-decode-round2.md:82-86`), a w przyszłości P1 i kernele trwałe. Model musi uwzględniać skończoną liczbę slotów fal i kolejność wydawania bloków, czyli właśnie to, czego NVIDIA nie modeluje dla PDL (README:128).
- **Zysk**: 0 t/s wprost. Zmniejsza ryzyko zawieszeń przy P1 i przy ewentualnym kernelu trwałym. **Koszt**: 1–2 dni. **Ryzyko**: brak. **Pomiar**: wykrycie celowo wstrzykniętego błędu (np. release przed zapisem).

### P3. Prefill FA: kafle w pełni pod przekątną bez ładowania i dodawania maski (Qwen, długi kontekst)
- **Co**: w kernelu FA prefillu, który wybieramy na RDNA3 (do sprawdzenia, który to; w `fattn-mma-f16.cuh:643-645, 746, 808` maska jest ładowana do LDS dla **każdego** kafla, gdy `mask_h != nullptr`), dodać `KV_min_masked` per kafel Q, analogicznie do istniejącego `KV_max` (`fattn-mma-f16.cuh:1937`). Kafle `< KV_min_masked` idą ścieżką bez maski (szablon `use_mask=false`), a kafle z przekątną jak dotąd. `KV_min` liczy ten sam kernel, który liczy `KV_max`.
- **Zysk [SZACUNEK]**: przy ub 512 i kontekście 30k ~98% kafli jest bez maski. Ładowanie maski to ~nbatch·ncols·2 B na kafel (~12% bajtów kafla K+V f16) plus dodawanie na VALU, a FA to ~20% prefillu przy 30k. Daje to 3–8% czasu FA, czyli **1–2% prefillu przy ≥30k**. NVIDIA podaje +32% dla prefillu FA (blog), ale tam zysk pochodzi głównie z maskowania przyczynowego w kafelkach przekątnych przy krótkich sekwencjach.
- **Koszt**: mały (1–2 dni). **Ryzyko**: małe, wynik bitowo identyczny. **Pomiar**: `llama-bench -p 4096 -d 32768`, rocprofv3 dla kernela FA, `test-backend-ops -o FLASH_ATTN_EXT`.

### P4. (proces) Tuner w modelu z timeoutem
Zamiast ręcznych przemiatań (K1: W, waves_per_eu, GLC/DLC): skrypt, który dla każdego (typ, n, kształt) buduje warianty makr, mierzy rocprofv3 **w modelu** (NOTES:247-248: mikrobench myli się) i ma timeout na uruchomienie, wzorem `exhaustive_search` (`_tune.py:141-158`). Zysk pośredni (szybsze iteracje), mały koszt. Nie obiecuję t/s.

### Czego nie proponuję (świadomie)
- Specjalizacja warpów producent/konsument w kernelach FA lub MMQ: brak TMA/async-copy na gfx1100, VGPR-y producenta zjadają obłożenie. Patrz też negatyw „prefetch w GDN/FA” (NOTES:324).
- Głębszy prefetch w `fattn-kvq` w stylu `kv_stages=4`/`latency=4`: z prawa Little'a (~960 GB/s × ~2 µs ≈ 1.9 MB w locie) nasze ~192 bloki × warpy × ~4.6 KB na warp już to pokrywają [WNIOSEK]. Najpierw trzeba by zmierzyć bajty w locie.
- Statyczne K w MMVQ (pełne rozwinięcie): negatyw „rozwijanie pętli K” (NOTES:351, `lfm-decode.md:143-144`).
- q8_0 dla `fattn-kvq` (LFM, długi kontekst) jest ważne, ale już opisane (`lfm-decode-round2.md:95-101`). cuTile tylko potwierdza układ „KV jako M, tokeny×głowy jako N”.

## 5. Krytyka
- Brak liczb w repo. Jedyne liczby to blog NVIDIA (prefill FA, Blackwell/Ada), bez porównania z cuDNN/FA3. „Production-ready” dotyczy kodu, nie wydajności.
- FMHA decode to kernel serwerowy: brak split-KV między CTA (`fmha_decode_kernel.py:278`). Przy batch 1 i 8 głowach KV zająłby kilka SM. Do pojedynczego użytkownika z długim kontekstem (nasz przypadek) się nie nadaje. Nasz `fattn-kvq` jest pod tym względem dojrzalszy (split + combine, leniwy rescale z progiem).
- `task_scheduling` to eksperyment: duża część typów potoków rzuca `NotImplementedError`, persistent `WorkTileLoop` działa tylko w analizie na hoście (README:120-122), a w kernelu decode `exhaustive_deadlock_race_check=False` (`fmha_decode_kernel.py:193`). Checker nie obejmuje PDL ani stanu CLC (README:128).
- Sample MoE to fused_moe dla prefillu, bez ścieżki batch-1 i bez kwantyzacji wag. Dla LFM (launch-bound przy 1 tokenie) nieistotny.
- Abstrakcja kafelkowa świadomie ukrywa wątki i synchronizację w bloku (`execution.rst:23-27`). To dokładnie te miejsca, w których my zarabiamy (DPP, `swap_halves`, układ fragmentów WMMA gfx11, `sched_barrier`). Na RDNA3 model „kompilator wybiera układ” nie ma realizacji. Odpowiednikiem byłby Triton/TileLang na AMD (raport 10).

## 6. Werdykt
**Niska–średnia.** Kod nie przenosi się, a ścieżkę decode mamy lepszą. Wartościowe są trzy idee: PDL jako „wczesny start + prefetch wag + czekanie na flagę” (P1, możliwe 5–11% dla LFM, pod warunkiem że flaga any-order przetrwa przechwytywanie grafu), sprawdzanie protokołów synchronizacji na hoście (P2) i dzielenie pętli FA wg maski (P3, ~1–2% prefillu).
