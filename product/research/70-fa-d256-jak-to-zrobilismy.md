# 70 — FA D=256 w prefillu, wariant 83: jak to zrobiliśmy (post-mortem)

Data: 2026-11-09. Praca tylko na CPU (bez GPU, buildów i pobierania). Wszystkie liczby pochodzą z istniejących artefaktów. Kod: commit `32292cc0a` w `~/wt/fa-d256` (gałąź `fa-d256` na topka-q63 `c0576e3e8`), łatka `qwen-opt/patches/fa-d256/0001-…patch`. Harness i wyniki: `~/qwen-opt/fa-d256/` (`res/*.txt`, `res/md5-*.json`, `logs/`, `*.sh`, `select.py`). Notatka eksperymentu: `wiki/eksperymenty/2026-11-08-fa-d256-prefill.md`. Numery linii `fattn-mma-f16.cuh` odnoszą się do `32292cc0a`.

Oznaczenia: `[INFERENCE]` = mój wniosek albo rachunek, nie pomiar. „Kernel” = `flash_attn_ext_f16<256,256,32,2,…>` (D=256, 64 kolumny = 32 tokeny × 2 głowy Q na blok), czyli kernel prefillu Qwen3.8-27B (GQA 6) na RDNA3.

## 1. TL;DR

**Wariant 83 to ten sam algorytm FA z tą samą kolejnością działań. Różni się tylko kolejnością instrukcji i układem danych: ma bariery schedulera po każdym WMMA (KQ i V), kafel V jest transponowany przy zapisie do LDS i czytany 128-bitowymi ładowaniami, a V idzie kawałkami 64 zamiast 128 kolumn. Dzięki temu kernel nie spilluje (220 VGPR spillowanych → 0, scratch 512 B → 0) i robi mniej odczytów LDS. Wynik jest bitowo identyczny, a przy 131k kernel zajmuje 0,878× czasu.**

| Pomiar (eco 2200, Qwen3.8-27B-Uncensored Q4_K_M, KV q4_0, ub 512) | VAR 0 (produkcja) | VAR 83 | Δ | źródło |
|---|---|---|---|---|
| kernel FA q4_0, kv 131 072 (µs/wywołanie, średnia 2 przebiegów) | 37 231 | 32 674 | **0,878×** (44,3 → 50,5 TFLOPS) | `res/select.txt`, `logs/perf-*.log` |
| llama-bench pp512 @ d4096 (ABBA) | 950,9 / 950,3 t/s | 955,4 / 956,0 | **+0,5%** (sd ~21, szum) | `res/bench.txt` |
| llama-bench pp512 @ d32768 | 760,6 / 759,7 | 775,1 / 773,2 | **+1,9%** (1. para; średnia ABBA +1,8%) | `res/bench.txt` |
| llama-bench pp512 @ d131072 | 459,5 / 459,9 | 486,3 / 485,4 | **+5,8%** (1. para; średnia ABBA +5,7%) | `res/bench.txt` |
| serwer, fill 255k (254 977 tok.) | 466,3 t/s (546,8 s) | 493,4 t/s (516,8 s) | **+5,8%, −30 s** | `res/fill.txt` |
| serwer, prefill 32k (long_md5) | 849,8 | 860,8 | +1,3% | `res/long_md5.txt` |
| spec_sweep T=1, seedy 1–3 | 119,2 t/s, 26,92 ms/krok | 119,2 t/s, 26,91 ms/krok | 0% | `logs/{A,B}/spec_sweep.txt` |
| md5 greedy 12k / 32k / 255k | 816334e4 / e460e3b6 / 31b6525a | to samo | bitowo = | `res/md5.txt`, `long_md5.txt`, `fill.txt` |
| szczyt VRAM przy fillu 255k | 23 446 MiB | 23 414 MiB | −32 MiB | `res/fill.txt` |

Dlaczego to zadziałało, w trzech zdaniach:
1. **Zmierzyliśmy tam, gdzie boli.** Udział FA w czasie ubatcha rośnie liniowo z głębokością: ~4% przy 4k, ~24% przy 32k, ~56% przy 128k (model z profilu 24v). Ten sam −12% kernela daje więc +0,5% przy 4k i +5,8% przy 128k. Raport 24v odrzucił bariery, bo mierzył przy ≤32k.
2. **Przeszukaliśmy kombinacje, a nie pojedyncze pokrętła.** `nbatch_V2=32` sam nic nie daje (67: −5,0% wobec −6,1% samych barier). Za to usuwa 48 spilli, które tworzy transpozycja V (19 → 83). Przegląd po jednym parametrze by go odrzucił.
3. **Bramka bitowa zamiast KLD.** Do kandydatów dopuszczaliśmy tylko zmiany bitowe z konstrukcji, potwierdzone `test-backend-ops` i md5. Dlatego wystarczyły 62 minuty jednego joba GPU, bez kampanii KLD.

## 2. Oś czasu pomysłu

| Data | Zdarzenie | Co nam dało |
|---|---|---|
| 2026-10-14 | Łatka **0042** (`cf397468e`): Q w SRAM zamiast w rejestrach, K/V batch 64, „Q + K/V + mask fit the 64 KiB per block” (`fattn-mma-f16.cuh:164-166`); 0043 przywraca kolejność chunków K (KLD 0,0135 → 0) | Kernel 40,2 → 49,0 TFLOPS, FA przy 32k 4,36 → 3,42 s ([[prefill-mmq-fa]]). To połowa tego, co 3 tygodnie później zrobił upstream #31746 |
| 2026-10-20 | Raport **24v** (`product/research/24v-prefill-fa.md`) | Profil: FA = **2,2%** pp4096, **13%** wypełnienia 32k, **24%** ostatniego ubatcha przy d32k (131 ms z 547 ms). Przyczyna spilli: scheduler wyciąga przed pętlę ładowania kafli V (transpozycja z LDS). `sched_barrier(0)` po każdym WMMA V: 256 VGPR / 512 B → 232 / 0 B, bitowo =, pp512@d32k **+0,84%**. **Odrzucone** (próg wyraźnej wygranej). W wnioskach: „jedyna większa rezerwa to przepisanie ładowania V (2192 operacji LDS na iterację, `ds_read_b32` + perm)” oraz lista parametrów bitowo neutralnych: `nbatch_K2/V2`, `nbatch_combine`, `Q_in_reg`, `nstages`, occupancy, bariery |
| 2026-11-05 | Upstream PR **#31746** „hip: tune D256 MMA FlashAttention on RDNA3” (ravel7524, W7800 = gfx1100, head `2ae66a338`) | Q z LDS, `nbatch_fa` 64 → 32, `nbatch_K2/V2` 128, bariery WMMA. Operator GQA 6: **0,695×** (ROCm 10.1) / 0,783× (7.2.4) względem mastera. Zewnętrzny dowód, że ten kernel na naszej architekturze i kształcie ma 20–30% zapasu |
| 2026-11-06 | ctx 262k w produkcji | Prefill 255k = **465 t/s (548 s)**. To nowy „pain point”: użytkownik czeka 9 minut |
| 2026-11-07 | Runda researchu **68** | **68a §1 pkt 2, §4.1**: pakiet FA (bariery 24v + config #31746 + `exp2f`). Z modelu 24v FA ≈ **53%** wypełnienia 255k, szacunek +5…13%. **68c §1 pkt 2, tabela poz. 1–2**: najpierw przegląd bitowo neutralnych parametrów z 24v (+5…11%), potem V/K w układzie WMMA przy konwersji q4_0→f16 (+8…16%), bo „usuwa transpozycję V przez LDS, którą 24v wskazał jako jedyną większą rezerwę”. **68d §1 pkt 1, §5 poz. 1**: #31746 to najcenniejsze znalezisko. Mamy już Q w SRAM, więc zostaje ~0,85× FA, +5…9%. Zmiana `nbatch_fa` przestawia softmax, więc bramką jest KLD. **68-SYNTEZA poz. 2**: prefill FA D256, oczekiwane +5…22% |
| 2026-11-07 23:xx | Agent **XtxFaPrefill** (Main przekazuje 68c i 68d przez IRC) | Projekt: jedna binarka, 8 bitów w masce `GGML_HIP_FA_D256_VAR`, 15 skompilowanych masek. Pomysł 68c poz. 2 („V w układzie WMMA”) zrealizowany taniej: transpozycja przy zapisie global → LDS wewnątrz kernela FA (bit 16), a nie w kernelu konwersji. Nie wiąże konwersji z FA i działa też dla f16 KV. Dodany bit 128 (natywne q4_0, idea #31802 / 68a 4.3) |
| 2026-11-09 01:41 | Pierwszy job `fa-d256.jobs` | Build 419 s OK. Bramka: `test-backend-ops` rc=127 (brak `libhipblas.so.3` w RUNPATH), wszystkie warianty FAIL. Reszta kroków „rc=0” w 8 minut, nic nie zmierzone (§4.8) |
| 2026-11-09 01:56–02:58 | `fa-d256-rerun.jobs` (XtxRunner), 62 min | Bramka 256 s, micro 764 s, md5 295 s, select, ABBA 1035 s, ramiona 668 + 639 s → **BEST 83, PASS** |

### Jak powstała hipoteza

Hipoteza złożyła się z trzech osobnych faktów. Żaden z nich sam nie wystarczał:

1. **Prawo Amdahla z głębokością.** Koszt FA na ubatch jest proporcjonalny do głębokości d, a reszta ubatcha (MMQ ~63–81%, GDN, normy) jest stała. 24v zmierzył udział przy d32k (24%). 68a/68c ekstrapolowały liniowo do 255k (~53–54%). Ta sama poprawka kernela, która przy 32k dawała +0,84%, przy 128k+ musi więc dać 2–3× więcej. Odrzucenie w 24v było dobre dla reżimu ≤32k, ale nie dla nowego pain pointu.
2. **Znane, nazwane rezerwy w samym kernelu** (24v): spille z hoistingu ładowań V (lek: bariery) i 2192 operacje LDS na iterację przy transpozycji V (lek: inny układ V).
3. **Zewnętrzny dowód zapasu** (#31746): ktoś na gfx1100 i dokładnie naszym GQA 6 uzyskał 0,70–0,78× czasu operatora tymi samymi typami zmian.

Hipoteza robocza brzmiała tak: „bitowo neutralne pokrętła z 24v + transpozycja V + elementy #31746, przeszukane kombinatorycznie, dadzą FA −10…25% przy 131k, czyli +5…13% fillu 255k”. Sfalsyfikowana została jedna jej część, config #31746 (§3.6). Zysk dała własna rezerwa z 24v (transpozycja V) razem z budżetem rejestrów (`nbatch_V2=32`) i barierami.

## 3. Czym dokładnie jest wariant 83

### 3.1 Maska bitowa (`fattn-mma-f16.cuh:236-257`)

83 = 64 + 16 + 2 + 1 = `FATTN_FV_V2_32 | FATTN_FV_VT | FATTN_FV_FENCE_KQ | FATTN_FV_FENCE_V`.

| bit | nazwa | co zmienia w kernelu | kod | bitowo? | w 83 |
|---|---|---|---|---|---|
| 1 | `FENCE_V` | `__builtin_amdgcn_sched_barrier(0)` po każdym WMMA w pętli VKQ: scheduler nie wyciąga ładowań operandów kolejnych WMMA ponad bieżący (wzór 24v) | makro `:259-264`, użycie `:1230` | tak (te same instrukcje arytmetyczne w tej samej kolejności) | **tak** |
| 2 | `FENCE_KQ` | to samo po każdym WMMA w pętli KQ (wzór #31746) | `:876` | tak | **tak** |
| 4 | `PR31746` | config #31746: `nbatch_fa` 32, `nbatch_K2/V2` 128 | `:269-272` | **nie**: softmax liczony co 32 wiersze KV, inna kolejność | nie |
| 8 | `EXP2` | `exp2f(x·log2 e)` zamiast `expf(x)` | `:1059, :1073` | **nie** | nie |
| 16 | `VT` | kafel V zapisywany do LDS **transponowany** już przy ładowaniu z VRAM (`flash_attn_ext_f16_load_tile_Vt`, `:538-566`). Każdy element dwóch kolejnych wierszy KV trafia jako para half2 do wiersza „kolumna V d”, segmenty 16 B z XOR-swizzlem po d (`fattn_vt_seg`, `:530-536`) bez konfliktów banków. Operand A dla WMMA V jest czytany **czterema 128-bitowymi ładowaniami** (`:1209-1219`) zamiast `load_ldmatrix_trans_swizzled` (16 transponujących ładowań 32-bit + perm, `:1221`) | `:530-566, 1180-1191, 1209-1222` | tak (wartości tylko przenoszone) | **tak** |
| 32 | `K2_32` | `nbatch_K2` 64 → 32 (K w 4 zamiast 2 kawałkach na D) | `:271` | tak | nie |
| 64 | `V2_32` | `nbatch_V2` 64 → 32: V w 4 kawałkach po 64 kolumny zamiast 2 po 128 (pętla `:1172`, `__syncthreads` `:1195`). W każdym kawałku jest połowa kafli A „w locie” | `:272` | tak | **tak** |
| 128 | `KQ4` | K/V czytane jako q4_0 i dekwantowane w drodze do LDS, bez kopii f16 całego KV (`:606-637`, `:568-604` dla VT) | `:819-826, 1180-1188, 2236-2238, 2339` | z konstrukcji „tak”, ale **md5 ≠** (§3.6) | nie |

Pozostałe elementy configu przy `fv ≠ 0` (`:266-275`) są takie same jak w domyślnym wierszu RDNA3 (`:166`): 256 wątków, occupancy 2, `nbatch_fa` 64, `nbatch_combine` 64, 1 etap, Q w SRAM. Przełącznik działa tylko dla `DKQ = DV = 256`, `ncols1 = 32`, `ncols2 = 2`, bez softcapu i przy `GGML_CUDA_CC_IS_RDNA3(cc)`, czyli **także RDNA3.5** (`:2213-2240`; `common.cuh:90-92`). Nieznana maska przechodzi na 0 z ostrzeżeniem. Lista skompilowanych masek: X-makro `GGML_CUDA_FATTN_MMA_D256_VARIANTS` (`:257`), wybór instancji `switch (fv)` (`:2310-2317`). Limit LDS ustawiany jest osobno dla każdego `fv` (`:2320-2324`). W `test-backend-ops.cpp:13267` dodany kształt kv 131 072.

### 3.2 Co 83 robi w jednej iteracji KV (64 wiersze)

1. K: ładowanie 2 kawałków po 64 half2 do LDS, KQ przez WMMA z **barierą po każdym WMMA** (bit 2). Bez niej scheduler wyciąga ładowania K_A kolejnych kafli ponad WMMA i podnosi presję rejestrów.
2. Softmax online: bez zmian (`expf`, te same 64 wiersze, ta sama kolejność).
3. V: **4 kawałki po 64 kolumny** (bit 64). Każdy kawałek: 64 wiersze KV × 64 kolumny V są czytane z VRAM 16-bajtowymi porcjami i od razu zapisywane do LDS w układzie V^T (bit 16). Potem `__syncthreads`, a każdy warp czyta swój operand A dwoma wierszami po 2 × 16 B i wykonuje WMMA z **barierą po każdym** (bit 1).
4. LDS na blok jest bez zmian: Q 33 792 B + KV 16 384 B + maska 4 608 B = **54 784 B** (wzór hosta `:2261-2271`; kafel V^T przy `nbatch_V2=32` zajmuje 8 KiB i mieści się w tym samym slocie) `[INFERENCE: rachunek ze wzoru, isa.txt pokazuje lds=0, bo LDS jest dynamiczny]`.

### 3.3 Izolowane efekty (micro: średnia 2 przebiegów S + odwrócone S; ISA: `res/isa.txt`)

Czas kernela względem VAR 0. Ujemny = szybciej. Kolumny q4_0 to kształt produkcyjny, f16 to KV jako widok (`kv_view=1`).

| VAR | bity | VGPR | spill VGPR | scratch B | q4_0 8k | q4_0 32k | **q4_0 131k** | f16 8k | f16 32k | f16 131k | md5 12k |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | — | 256 | 220 | 512 | 0 | 0 | 0 | 0 | 0 | 0 | 816334e4 |
| 1 | FV | 232 | 0 | 0 | −7,2% | −4,0% | −5,4% | −2,8% | −2,2% | +9,9% | = |
| 2 | FKQ | 256 | 194 | 456 | −6,4% | −1,8% | −1,7% | −0,2% | −4,6% | +0,5% | = |
| 3 | FV+FKQ | 248 | 0 | 0 | −10,0% | −5,9% | −6,1% | −7,7% | −7,5% | −2,2% | = |
| 16 | VT | 256 | 199 | 444 | −6,1% | +3,1% | +1,5% | −4,9% | +7,5% | +21,0% | = |
| 19 | F+VT | 256 | **48** | 136 | −17,1% | −7,8% | −8,6% | −15,0% | −4,6% | +5,0% | = |
| 35 | F+K2_32 | 252 | 0 | 0 | −8,2% | −3,2% | −4,9% | −5,2% | −3,5% | +6,8% | = |
| 51 | F+VT+K2_32 | 256 | 44 | 128 | −15,1% | −8,4% | −8,9% | −8,2% | −5,8% | +5,9% | = |
| 67 | F+V2_32 | 254 | 0 | 0 | −8,1% | −4,2% | −5,0% | −4,0% | −3,9% | +5,7% | = |
| **83** | **F+VT+V2_32** | **251** | **0** | **0** | **−17,3%** | **−11,3%** | **−12,2%** | −16,0% | −9,6% | **+2,4%** | **=** |
| 7 | F+PR | 226 | 0 | 0 | −8,6% | −4,1% | −3,6% | −5,6% | −5,0% | −0,6% | ≠ (0c32617a) |
| 11 | F+EXP2 | 232 | 0 | 0 | −12,1% | −8,3% | −9,0% | −8,9% | −9,9% | −4,5% | nie mierzone |
| 15 | F+PR+EXP2 | 211 | 0 | 0 | −8,3% | −4,0% | −3,5% | −4,2% | −5,2% | −1,5% | ≠ (078b0415) |
| 23 | F+PR+VT | 235 | 0 | 0 | +4,3% | +8,6% | +8,6% | +7,8% | +10,4% | +12,2% | nie mierzone |
| 131 | F+KQ4 | 243 | 0 | 0 | −10,5% | −6,4% | −4,2% | −4,5% | +0,7% | −2,2% | ≠ (e9dcdd80) |
| 147 | F+VT+KQ4 | 256 | 45 | 144 | −9,1% | −1,9% | +5,9% | −9,6% | +6,7% | +5,0% | ≠ (e9dcdd80) |

(F = bity 1+2. Kolumna „md5 12k”: `=` oznacza 816334e4 = VAR 0 = produkcja. Rozrzut między przebiegami tego samego wariantu przy 131k q4_0 to ≤0,2% (`micro.txt`, np. 83: 32 668,7 / 32 679,2 µs).)

### 3.4 Dlaczego wygrywa kombinacja

- **Spille to stały podatek od każdej iteracji KV.** VAR 0 ma 256 VGPR (sufit architektury dla jednej fali) i 220 VGPR spillowanych do 512 B scratchu na wątek. Spill i reload siedzą w pętli po KV, więc ich koszt rośnie z głębokością. Same bariery (3) zerują spille: −6,1% przy 131k. To efekt 24v, tylko zmierzony głębiej (24v przy d32k: ~−3,5% kernela; tu −5,9%).
- **VT zmniejsza liczbę instrukcji LDS po stronie V,** ale podnosi presję rejestrów. Jeden operand A to 4 ładowania `b128` zamiast 16 transponujących `b32` + perm (komentarz bitu 16, `:242-243`). 24v policzył 2192 operacje LDS na iterację w VAR 0. Szerokie ładowania trzymają jednak więcej rejestrów naraz: sam VT (16) ma 199 spilli, a VT z barierami (19) ma ich jeszcze 48 i 136 B scratchu. Przy 8k VT już wygrywa (−17,1%), ale przy 131k resztkowe spille zjadają zysk (−8,6%).
- **`nbatch_V2=32` to budżet rejestrów dla VT.** Połowa kolumn V na kawałek oznacza połowę kafli A i akumulatorów „w locie” między `__syncthreads`. 19 → 83: spille 48 → 0, VGPR 251. Sam V2_32 (67) jest gorszy od samych barier (−5,0% vs −6,1%), bo dokłada 2 bariery `__syncthreads` na iterację bez niczego do zyskania. Dopiero z VT zamienia się w −12,2%. `K2_32` (51) tej roli nie spełnia: presja jest w pętli V, nie K, i zostaje 44 spilli.
- **Occupancy się nie zmienia.** LDS 54 784 B na blok oznacza 2 bloki na WGP, czyli 4 fale na SIMD. Rejestry pozwalałyby na 6 (1536/256) `[INFERENCE: limity gfx11 wave32]`, więc zarówno VAR 0, jak i 83 są ograniczone przez LDS, nie przez VGPR. Zysk nie bierze się z większej liczby fal. Bierze się z (a) braku ruchu do scratchu w pętli, (b) mniejszej liczby instrukcji LDS i oczekiwań `s_waitcnt` na nie `[INFERENCE dla (b): isa.sh zbiera tylko metadane zasobów, liczby instrukcji dla 83 nie mamy]`.
- **Bilans pamięć/obliczenia.** Kernel prefillu jest ograniczony obliczeniami i wydawaniem instrukcji, nie pasmem DRAM. Każdy wiersz K/V używa 64 kolumn bloku, a ten sam KV czyta 48 bloków na głowę KV (512 tokenów × 6 głów / 64). Przy 131k q4_0 VAR 0 robi **44,3 TFLOPS**, a 83 **50,5 TFLOPS** (1,65 TFLOP na wywołanie, `logs/perf-1-0.log`, `perf-14-83.log`), czyli ~40% → ~47% szczytu WMMA f16 przy 2200 MHz `[INFERENCE: szczyt ~108 TFLOPS przy eco]`. Każda zaoszczędzona instrukcja LDS albo reload ze scratchu skraca ścieżkę krytyczną.

### 3.5 Dlaczego zysk rośnie z kontekstem, a krótkie prompty mają ~0

Model z 24v: ostatni ubatch przy d32k = 547 ms, z czego FA 131 ms, reszta 416 ms (stała). FA rośnie liniowo z głębokością.

| głębokość | FA na ubatch `[INFERENCE]` | udział FA | stosunek kernela 83 (micro q4_0) | przewidziane e2e | zmierzone (llama-bench) | udział wynikający z pomiaru |
|---|---|---|---|---|---|---|
| 4k | 17 ms | 4,0% | 0,827 (8k) | +0,7% | +0,5% | ~3% |
| 32k | 132 ms | 24,1% | 0,887 | +2,8% | +1,9% | ~17% |
| 128k | 525 ms | 55,8% | 0,878 | +7,3% | +5,8% | ~45% |
| fill 255k (średnio ~128k) | — | ~53% (68a) | 0,878 | ~+7% | **+5,8% (−30 s)** | ~45% |

Model trafia kierunek i nachylenie. Zmierzony zysk to ~70–80% przewidzianego, bo profil 24v był robiony przy zegarach stock, a nie eco, a mikrobench izoluje kernel od cache'u reszty kroku ([[lekcja-mikrobench-klamie]]) `[INFERENCE]`. Przy pp ≤4k MMQ to 72–81% prefillu, a FA 2,2% (24v). Żadna zmiana FA nie przekroczy tam szumu: d4k ma sd ~21 t/s przy różnicy 5 t/s. Dla tur agenta (kilka tysięcy nowych tokenów na kontekście 100k+ z cache'em promptu) liczy się kolumna „128k”, czyli TTFT ~−5% `[INFERENCE]`.

Decode jest nietknięty, bo weryfikacja i krok draftu idą przez `kvq`, a nie przez ten kernel. Catch-up draftu MTP to ścieżka bez atencji. Stąd spec_sweep 119,2 = 119,2.

### 3.6 Co nie zadziałało albo zaskoczyło

- **Config #31746 na naszej bazie nie pomaga.** 7 (bariery + config PR): −3,6% vs 3 (same bariery) −6,1%. 23 (z VT): **+8,6%**. Do tego config nie jest bitowy. Duża część zysku #31746 (0,695×) pochodziła z przeniesienia Q do SRAM. My mieliśmy to od 14.10 (0042), więc z PR-a przeniósł się pomysł barier, a nie jego config.
- **`exp2f` daje ~3 pkt kernela** (11: −9,0% vs 3: −6,1% przy 131k), ale jest stratny. Kombinacji 83 + 8 = 91 nie skompilowano. To kandydat tylko z bramką KLD (§5).
- **„Bitowo z konstrukcji” to nie dowód.** 131 i 147 (natywne q4_0) przechodzą `test-backend-ops` 173/173 (tolerancja NMSE), ale md5 wychodzi e9dcdd80 ≠ 816334e4. Komentarz w kodzie (`:245`, `:606-608`) twierdzi, że kafel jest bitowo taki sam jak po konwersji. Przyczyny nie zbadano `[INFERENCE: inna ścieżka niż `dequantize_q4_0` z `dequantize.cuh:46-58` albo obsługa ogona KV]`. Tę lukę złapała bramka md5, a nie `test-backend-ops`.
- **f16 KV przy 131k: 83 jest wolniejszy (+2,4%)**, choć przy 8k/32k wygrywa (−16,0% / −9,6%). Odczyty są stabilne (4 próbki 39 116–39 201 µs vs 38 202–38 361). W teście f16 K/V to widok większego tensora (`kv_view=1`), a q4_0 jest konwertowane do ciągłej kopii f16 `[INFERENCE: wzorzec 16-bajtowych odczytów VT po dwóch wierszach gorzej znosi rozstrzelone wiersze widoku przy 512 MiB KV]`. Produkcja (cel i draft) ma KV q4_0, więc to nie dotyczy dzisiejszego wdrożenia. Domyślne włączenie dla f16 KV wymaga osobnego pomiaru (§6).

## 4. Metoda, która to umożliwiła

Cały pipeline to jeden plik jobów (`fa-d256.jobs`) w kolejce GPU. Każdy krok ma własny skrypt i zapisuje wynik do `res/`. Kolejny krok czyta tylko pliki poprzedniego.

### 4.1 Jedna binarka, warianty przełączane z env
- Parametr szablonu `int fv = 0` przechodzi przez `flash_attn_ext_f16` → `_process_tile` → `_iter`. Każda decyzja to `constexpr bool` (`:768-772`), więc wariant 0 kompiluje się do **identycznego** ISA co produkcja (`res/isa-topka-test.txt` = wiersz `…,0>` w `isa.txt`: 256/220/512).
- Lista masek w jednym X-makrze (`:257`). Host czyta env raz (statyczna lambda, `:2217-2232`), nieznaną maskę loguje i zamienia na 0, wpisuje `GGML_HIP_FA_D256_VAR=<v>` do logu i wybiera instancję przez `switch`.
- Zysk: 16 wariantów to 1 build (419 s) zamiast 16, 1 ISA, a ABBA idzie na **tej samej binarce** (A = VAR 0, B = VAR 83), więc różnica nie może pochodzić z buildu.
- Koszt: 15 dodatkowych instancji jednego kernela w jednym pliku `.o` (czas kompilacji tej jednostki).

### 4.2 Bramka bitowa (dwa niezależne sita)
1. `gate.sh`: `test-backend-ops -o FLASH_ATTN_EXT -p hsk=256 -b ROCm0` dla każdego wariantu, wynik `res/tbo.txt`. PASS wymaga rc=0, 0 linii FAIL, „N/N tests passed” **i** linii `GGML_HIP_FA_D256_VAR=v` w logu (dowód, że wariant był aktywny; [[lekcja-flaga-bez-dowodu-dzialania]]). Wynik: 16/16 × 173/173.
2. `md5.sh`: czysty `llama-server` na wariant (model produkcyjny, KV q4_0, ub 512, bez spekulacji). Prompt 12 000 tokenów z zamrożonego korpusu to 24 ubatche na rosnącej głębokości, czyli dokładnie ten kernel. Do tego prompt krótki. T=0, 24 tokeny, top-5 logprobs, md5 całego JSON-a (wzór 24v). Plus **`prod`** (zainstalowane `~/llama-topka`) jako kontrola, że VAR 0 = produkcja.
3. **Kontrola pozytywna:** w logach serwera linia INFO z wariantem się nie pojawia (`var_log=0` we wszystkich `md5-srv-*.log`). Dowodem, że env dociera do kernela w serwerze, są warianty stratne 7/15/131/147 z innym md5. Bez nich równe md5 dla 83 mogłoby oznaczać „wariant nieaktywny”.

### 4.3 Wyczerpujący mikrobench (`micro.sh`)
`test-backend-ops perf -o FLASH_ATTN_EXT` na kształcie Qwena (D 256, 4 głowy KV, GQA 6, nb 512) × KV {q4_0, f16} × kv {8k, 32k, 131k}. Mierzone są tylko warianty z PASS. Kolejność to S, a potem odwrócone S, co znosi dryf termiczny i zegarowy (ABBA-like), i daje 2 próbki na komórkę. 16 wariantów × 6 kształtów × 2 przebiegi = 764 s.

### 4.4 Automatyczny wybór (`select.py`)
Kandydat musi spełnić wszystkie warunki: (a) bitowy z konstrukcji (lista `LOSSLESS`), (b) PASS w bramce, (c) md5 = VAR 0, (d) VAR 0 = produkcja. Wynik to czas q4_0 przy kv 131 072, bo fill 255k ma średnio ~128k głębokości. Próg `MIN_GAIN` = 2% kernela, bo przy udziale FA ~53% dawałoby to ~+1% e2e, a poniżej tego e2e nie ma sensu. Wynik: `83:0,878, 51:0,911, 19:0,914, 3:0,939, 1:0,946, …` → `res/BEST` = 83. Wybór jest mechaniczny, więc agent nie wybiera „ładniejszego” wariantu po fakcie.

### 4.5 llama-bench ABBA przy głębokości (`bench.sh`)
pp512 przy `-d` 4096 / 32768 / 131072, kolejność 0, B, B, 0, ta sama binarka, `GGML_HIP_PM4=0`, KV q4_0, ub 512, `taskset -c 2-5`. 1035 s. Głębokość jest kluczowa: pp512 przy d=0 pokazałby zero.

### 4.6 Ramiona produkcyjne (`arm.sh A 0`, `arm.sh B BEST`)
`run-topka.sh uncensored` przy ctx 262 144 w pełnej konfiguracji produkcyjnej (MTP, lookup, PM4 WA=2 + GUARD, eco 2200 sprawdzane w sysfs). Kolejno: long 32k greedy md5 → spec_sweep T=1 seedy 1–3 → fill 255k z **zamrożonym korpusem** (`corpus.txt` 5,2 MB, ten sam prompt w obu ramionach) + 256 tokenów decode → szczyt VRAM z próbkowania co 1 s. ~11 min na ramię.

### 4.7 Koszt całości (rerun, `queue.log`)

| krok | czas |
|---|---|
| bramka (16 wariantów) | 256 s |
| micro | 764 s |
| md5 (15 serwerów) | 295 s |
| select | <1 s |
| llama-bench ABBA | 1035 s |
| ramię A / B | 668 s / 639 s |
| **razem** | **62 min** (+ build 7 min w pierwszym jobie) |

### 4.8 Porażki po drodze i lekcje
1. **Brak `libhipblas.so.3` w RUNPATH builda.** Produkcyjne serwery startują przez `run-topka.sh`, które ustawia biblioteki, a gołe `test-backend-ops` z `build-hip/bin` padało rc=127. `gate.sh` słusznie oznaczył wszystko jako FAIL (żadnego fałszywego PASS), ale potem **cała kaskada skończyła się „rc=0” w 8 minut**: micro bez wariantów, md5 tylko `prod`, select → NONE, bench i ramiona „no BEST: skipped”. Kolejka wyglądała na zieloną. Naprawa: `export LD_LIBRARY_PATH=$BIN:/opt/rocm/core-10.0/lib` w `common.sh` i rerun bez kroku budowania (`fa-d256-rerun.jobs`). **Lekcje:** (a) przed zgłoszeniem joba uruchomić każdą binarkę harnessu na CPU (`ldd … | grep 'not found'`, `--help`); (b) krok, który nie ma czego mierzyć, ma kończyć się rc≠0 (albo runner ma oznaczać „0 s” jako podejrzane), a nie cichym `exit 0`.
2. **`cpuheavy` i kolejka GPU.** Zasada pracy kazała budować przez `cpuheavy --quiet`, ale `quiet.lock` trzymała kolejka (kvq-once, potem l1tok), więc build czekałby do rana. XtxFaPrefill zauważył, że `cpuheavy --quiet` **wewnątrz** joba czekałoby na lock trzymany przez samą kolejkę, czyli zakleszczenie. Zapytał Main i anulował swój build. Main pozwolił budować w jobie przez zwykłe `nice -n 19 taskset -c 0-3 cmake --build -j4` (`build.sh:8`). W tym samym czasie (2026-11-08 00:54) job `kvq-once2` innego agenta zakleszczył się dokładnie tak ([[lekcja-cpuheavy-w-jobie-kolejki]]). Main ogłosił regułę i przestawił kolejność biletów według wartości (fa-d256 na 2. miejsce). **Lekcja:** w jobie kolejki nigdy `cpuheavy`. Build albo przed zgłoszeniem, albo w jobie z gołym `nice`/`taskset`.
3. **Ramiona kończą się rc=1** przez pułapkę TERM przy zatrzymaniu serwera, choć wyniki są kompletne. Kosmetyka, ale myli przy czytaniu `queue.log`. `trap stop EXIT` nie powinien zmieniać kodu wyjścia.
4. **Brak widocznej linii wariantu w logu serwera** (`GGML_LOG_INFO` odfiltrowane). Ratuje to kontrola pozytywna z §4.2. Przy wdrożeniu logować na poziomie widocznym w `server.log` (§6).
5. **Poprzednie odrzucenie nie było błędem, tylko złym reżimem pomiaru.** 24v miało rację dla ≤32k. Wynik negatywny trzeba zapisywać razem z warunkami (głębokość), żeby dało się go ponownie otworzyć, gdy zmienia się pain point ([[lekcja-zysk-rosnie-z-glebokoscia]]).

## 5. Macierz reprodukowalności (ranking: oczekiwany zysk / wysiłek)

Wzorzec do powtórzenia: **(1)** profil → udział kernela w czasie w reżimie pain pointu, **(2)** config/kernel z parametrem szablonu i maską env, **(3)** ISA (VGPR/spill/scratch) na CPU, **(4)** bramka `test-backend-ops` + md5 z kontrolą pozytywną, **(5)** mikrobench S/odwrócone S na kształtach i głębokościach produkcji, **(6)** automatyczny wybór, **(7)** ABBA przy właściwej głębokości/kształcie, **(8)** ramiona produkcyjne.

| # | Cel | Oczekiwany zysk `[INFERENCE]` | Uzasadnienie | Pierwszy test (dokładnie) | Koszt | Kill |
|---|---|---|---|---|---|---|
| 1 | **Wdrożenie 83 + ta sama maska dla całej rodziny Qwen3.8-27B w Enigmie na RDNA3** (Uncensored, Saluki, Bonsai Q2_0: ta sama architektura, D 256, GQA 6, ten sam kernel) | fill 255k **+5,8%** zmierzone. Saluki/Bonsai: ten sam kernel FA, ale ich MMQ jest szybsze (2 bity), więc udział FA przy głębokości większy, a zysk raczej ≥ | kernel i kształt identyczne; zmienia się tylko typ wag (MMQ), nie FA | §6 (już zmierzone dla Uncensored); dla Saluki/Bonsai: `bench.sh` z `M=` innego modelu, 3 głębokości | 0,5 d + 20 min GPU na model | md5 ≠ VAR 0 albo d128k < +3% |
| 2 | **Sweep configu MMQ (Q4_K, Q6_K, IQ4_XS) na RDNA3** tą samą metodą | pp ≤32k **+2…4%**, fill 255k +1…2%; to jedyna dźwignia prefillu przy krótkich promptach | MMQ = 63–81% prefillu (24v). Config to dokładny odpowiednik `fattn_mma_config`: tabela per arch `mmq-config-rdna3.cuh` (`nthreads`, `occupancy`, `I`, `J`, `sram_layout`, `K_vram`, `stream_k`). Na RDNA3 `stream_k=false`, więc zmiana kafla nie zmienia kolejności sumowania po K i powinna być bitowa (do potwierdzenia md5). Pokrętła dodatkowe: `sched_barrier` w pętli WMMA, `#pragma unroll 1` (#31751), 32-bitowe offsety (RDNA-FAST `04a0e2e6`, −14…17 VGPR) | (CPU) maska `GGML_HIP_MMQ_VAR` dla Q4_K/Q6_K + `isa.sh` na `mmq-instance-q4_k.cu.o` / `q6_k` (VGPR/spill); (GPU) `test-backend-ops perf -o MUL_MAT -p 'type_a=(q4_K|q6_K)'` na kształtach Qwena przy n=512, S/odwrócone S; md5 12k jak `md5.sh`; ABBA `llama-bench -p 512,4096 -ub 512` | 1–1,5 d kod + ~1,5 h GPU | brak bitowego wariantu ≤ 0,97× na 3 najcięższych kształtach (rocprofv3 pp4096) |
| 3 | **Enigma ROCm na innych kartach AMD + autotune przy instalacji** | RDNA3 gfx1101/1102: kernel −5…15% przy 131k, prefill przy głębokości +3…6%, jeśli karta mieści taki kontekst. gfx1151: nieznane (inny bilans pasmo/compute). gfx1201: wymaga portu | gfx1101/1102 to ten sam gfx11 (VGPR, LDS 64 KB/CU, WMMA), więc ISA prawie na pewno ta sama i bariery/spille przenoszą się 1:1. Ale ranking wariantów zależy od liczby CU, zegarów i cache: na samym XTX f16 i q4_0 dały różnych zwycięzców przy 131k (3 vs 83). Upstream trzyma osobne tabele MMQ dla rdna3 / rdna3-5 / rdna4, czyli strojenie per arch jest normą. Przełącznik 83 aktywuje się już dla RDNA3.5 (`GGML_CUDA_CC_IS_RDNA3`), co dziś jest niezmierzone. RDNA4 ma inny układ operandów WMMA, więc `static_assert(T_A_VKQ::I == 32 && T_A_VKQ::ne == 16)` w VT może nie przejść | **autotune-at-install**: aplikacja uruchamia `test-backend-ops` (bramka) + `perf` 5 kandydatów bitowych × 2 kształty (q4_0 32k/131k) × 2 przebiegi (~3–4 min) i zapisuje `GGML_HIP_FA_D256_VAR` per GPU w profilu silnika. Bramka u użytkownika: tbo PASS + md5 krótkiego greedy vs VAR 0 na tej samej karcie. Pierwszy test u nas: wynajem R9700 (gfx1201, €0,471/h) albo karta testera gfx1101 | 1 d (skrypt + integracja z profilem silnika) + 1 h wynajmu | wariant 0 wygrywa na ≥2 archach → nie warto, zostaje stała tabela |
| 4 | **FA prefill dla innych kształtów** (D 256 przy innym GQA: Qwen3.6-35B-A3B `[INFERENCE: D 256, GQA 8 jak w rodzinie qwen35moe, niesprawdzone w GGUF]`, Nemotron-3.5-Bolt-E4B/Gemma-4 (D 256, GQA 4); D 64: LFM2.5-24B) | Qwen3.6-35B-A3B przy ≥128k: +3…5% (podobny udział FA). Gemma-4/E4B: ~0 (SWA 512–1024, pełna atencja tylko co 5.–6. warstwa). LFM2.5: +1…2% przy 128k (10 z 40 warstw to atencja, KV q8_0) | Przełącznik obejmuje dziś tylko instancję `<256,256,32,2>`. Inne GQA to inne `ncols2` (np. `<256,256,8,8>`), czyli osobny config i osobny sweep. **Korekta zlecenia:** LFM2.5 ma head dim **64** (24v: „LFM (head dim 64) używa innej instancji”; emb 2048 / 32 głowy), a nie 128 | (CPU) rozszerzyć warunek `:2216` na kolejne instancje + `isa.sh` dla `ncols1_8-ncols2_8` (najpierw sprawdzić spille VAR 0: bez spilli bariery nic nie dadzą); (GPU) `micro.sh` z `-p 'hsk=256,…nr23=\[8,1\]'` lub `hsk=64` | 0,5 d + 1 h GPU na kształt | VAR 0 bez spilli i VT ≥ 0,97× |
| 5 | **FA verify/decode `kvq`** | kernel −5…10% przy 199k → decode +1,5…3% przy ≥94k, ~0 przy krótkim kontekście (poniżej progu 3–5%, chyba że przy 199k+) | Profil 11-08: przy 199k FA to 30% kroku (11,3 ms), cały przyrost od 1,7k. Kernel jest **ograniczony obliczeniami** (dekwant + WMMA na kafel): nb1 658 GB/s, nb5 tylko 355 GB/s. **ONCE=1** (V dekwantowane raz dla 2 grup wierszy) oszczędza tylko dekwant V: −6,1% przy 199k, kill przy −10%. **ONCE=2** (K dzielone między fale pary, częściowe KQ przez LDS) dokłada synchronizację i ruch LDS, które kosztują więcej niż oszczędzony dekwant: +0,4…1,4%. `kvq` **ma już** transponowany kafel V w LDS, pakowany dekwant f16 z magiczną 0x6400 i `sched_barrier` (`fattn-kvq.cu:15, 174-177, 487, 536`), więc VT i bariery z 83 się nie przeniosą. Przenosi się **metoda** i dwa pokrętła: szerokość kawałka V (odpowiednik `nbatch_V2`: mniej akumulatorów VKQ w locie) oraz rozmieszczenie barier (po każdym WMMA vs na kawałek). W kombinacji z `ngroups`, `nwarps` i `__launch_bounds__(…,1)` → 2 mogłyby dać occupancy, której dziś brak `[INFERENCE]` | (CPU) ISA `flash_attn_ext_kvq<256,8,q4_0>`: VGPR/spill (ONCE=2 ma 236 VGPR i LDS 54 KB, więc druga fala na SIMD nie zmieści się bez zmian `[INFERENCE]`); maska `GGML_HIP_KVQ_VAR` (szerokość V, bariery, nwarps); (GPU) `kperf` z `~/qwen-opt/kvq-once` nb5 przy 32k/98k/196k + `fa_hash` (bitowo) | 1 d + 1 h GPU | brak wariantu ≤ 0,93× przy 196k nb5 |
| 6 | **Strona CUDA: `enigma-cuda-fork` na 3090/4090/5090** | 0…3% prefillu przy głębokości; niski priorytet | Ścieżka MMA FA na Ampere+ ma już config w stylu #31746: `(256,256,64)`: 128 wątków, `nbatch_fa` 32, K2/V2 128, 2 etapy cp.async, Q w rejestrach (`fattn-mma-f16.cuh:72`). #31746 jest czysto RDNA3. Nie istnieją tam `sched_barrier` (brak odpowiednika w NVCC) ani VT (`ldmatrix.trans` transponuje sprzętowo). Pokrętła CUDA: `nbatch_K2/V2`, `nstages`, `Q_in_reg`, occupancy, `nthreads`, `nbatch_combine`; bitowe są wszystkie poza `nbatch_fa`/`nthreads` (24v). Sens ma tylko wtedy, gdy instancja spilluje | (CPU, 10 min) `cuobjdump -res-usage` na buildzie forka dla `flash_attn_ext_f16<256,256,32,2…>` sm_86/89/120: liczba rejestrów i `STACK`/`LOCAL`. Jeśli 0 spilli → kill bez GPU. Jeśli są → maska jak w 4.1 + 1 h na wynajętej 3090 | 0,5 d + ~1 h wynajmu | 0 spilli na wszystkich sm |
| 7 | **GDN chunked prefill** | ≤ +1% | Koszt GDN nie zależy od kontekstu: 3–4% prefillu (24v, 68c pkt 6). Nawet −20% kernela to <1% e2e. Chunked GDN na WMMA nie jest bitowy (68c) | nie uruchamiać osobno; najwyżej dołożyć pokrętło do sweepu MMQ, jeśli będzie przy okazji | — | z góry poniżej progu |
| — | **Upstream: PR do llama.cpp** | 0% dla nas bezpośrednio; mniejszy koszt rebase'ów i wiarygodność Enigmy | VT + `nbatch_V2` 32 + bariery to zmiany bitowe względem bazy z Q w SRAM. #31746 (otwarty, `2ae66a338`) już przenosi Q do SRAM. Nasz dodatkowy −12% przy 131k q4_0 jest uzupełnieniem, nie konkurencją | komentarz w #31746 z tabelą §3.3 (warianty 3, 19, 67, 83) i ISA; po scaleniu #31746 osobny PR „hip: transposed V tile for D256 MMA FA on RDNA3” na bazie mastera + `test-backend-ops` + `llama-bench -d 4096,32768,131072` | 1–2 d (rebase na master, opis, odpowiedzi w review) | review wymaga zmian, które psują bitowość |

Kolejność: **1** (gotowe, czeka na OK) → **2** (największy niezagospodarowany udział w prefillu, ta sama metoda 1:1) → **3** (konieczne przed sprzedażą Enigmy na inne Radeony; autotune zamienia jednorazowy wynik w funkcję produktu) → **4** (Qwen3.6-35B-A3B) → **5** → **6** (najpierw tylko ISA na CPU) → **7** nie. Upstream równolegle, gdy #31746 się ruszy.

**Stratny dodatek do rozważenia osobno:** 83 + `EXP2` (maska 91). Na barierach `exp2f` daje ~3 pkt kernela, czyli ~+1,5% fillu 255k `[INFERENCE]`. Wymaga bramki KLD z kanarkami ([[bramka-kld-kanarki]]), nie md5. Opłaca się tylko w pakiecie z innymi zmianami stratnymi.

## 6. Przepis wdrożenia

Stan: **wykonane 2026-11-09** (wdrożenie 15:00:16 UTC, ticket 22938). Produkcja `~/llama-topka` = topka-q70 (topka-q63 `c0576e3e8` + cachesave `3152b0bfa`/`6f4ae4198` + fa-d256 `3191b25f4`, cherry-pick `32292cc0a`); backup `~/llama-topka.c0576e3e8`. Faktyczna metoda: wariant A (domyślne w launcherze, nie w kodzie): `run-topka.sh` eksportuje `GGML_HIP_FA_D256_VAR=${…:-83}` tylko dla qwen/uncensored (`fa_var_default=0` dla lfm/flint) i `LLAMA_SERVER_CACHE_HUGE=1`; binarka to pełny build `~/wt/l1-cachesave/build-hip` skopiowany jako `~/llama-topka.q70` (RUNPATH → `$ORIGIN`), ramiona na kopii, bramka md5, zamiana. Wyniki (final mode, Uncensored): long 32k md5 e460e3b6 =, fill 255k 466,3 → 492,5 t/s (+5,6%, 546,8 → 517,7 s) md5 31b6525a =, spec_sweep 119,3 t/s (bez zmian), szczyt VRAM 23 446 → 23 398 MiB, tura agenta 76–112k 13 413 → 12 029 ms (−10,3%). Wariant B (domyślne w kodzie) nadal otwarty. Notatka: `wiki/eksperymenty/2026-11-09-wdrozenie-topka-q70.md`. Poniżej przepis w brzmieniu sprzed wdrożenia.

### 6.1 Wariant A: zero zmian w kodzie (najszybszy, rekomendowany na dziś)
1. Build `~/wt/fa-d256` (`32292cc0a`) już istnieje i jest zmierzony: A/B w ramionach to ta binarka. Zainstalować go jako produkcję w jobie kolejki: `mv ~/llama-topka ~/llama-topka.c0576e3e8 && mkdir ~/llama-topka && cp -a ~/wt/fa-d256/build-hip/bin ~/llama-topka/` (tylko `bin/`, jak dotąd; `run-topka.sh` bierze `$ROCM_DIR/bin`, a ramiona B działały z `ROCM_DIR=~/wt/fa-d256/build-hip`).
2. W `~/qwen-opt/run-topka.sh` obok eksportów PM4 (`:86-88`) dodać `export GGML_HIP_FA_D256_VAR=${GGML_HIP_FA_D256_VAR:-83}` i dopisać zmienną do linii logu startowego (`:104-107`, stderr → `server.out`). Dziś to jedyne miejsce, które pokaże aktywny wariant, bo linia INFO z ggml nie trafia do logów serwera.
3. Override: `GGML_HIP_FA_D256_VAR=0 run-topka.sh uncensored` przywraca stary kernel w tej samej binarce. Wartość spoza listy daje ostrzeżenie i 0.

### 6.2 Wariant B: domyślne w kodzie (dla Enigmy i kolejnych rebase'ów)
- W `ggml_cuda_flash_attn_ext_mma_f16_case` (`:2217-2239`): brak env → `fv = 83` **tylko** gdy `GGML_CUDA_CC_IS_RDNA3_0(cc)` (gfx110x; RDNA3.5 dopiero po pomiarze) i `K->type == V->type == GGML_TYPE_Q4_0` (zmierzony typ; dla f16 KV przy 131k +2,4%). Env ustawione → zawsze wygrywa (`0` = wycofanie).
- Logować wybór raz na poziomie widocznym w `server.log` (dziś `GGML_LOG_INFO` nie trafia: `var_log=0`).
- Lista skompilowanych masek w produkcji: `X(83)` (+ 0 domyślnie). Pełna lista sweepu za opcją CMake, np. `GGML_HIP_FA_D256_SWEEP=ON`, na gałęziach badawczych. Mniej instancji = krótszy build, a numeryka bez zmian.
- Commit z opisem w manifeście łatek (`patch-manifest`) i wyłącznikiem w [[wylaczniki-env]].

### 6.3 Wycofanie
- Natychmiast: `GGML_HIP_FA_D256_VAR=0` + restart serwera (ta sama binarka, kernel bit w bit jak dziś).
- Pełne: `rm -rf ~/llama-topka && mv ~/llama-topka.c0576e3e8 ~/llama-topka`.

### 6.4 Weryfikacja (w jobie kolejki, ~45 min)
1. `LD_LIBRARY_PATH=~/llama-topka/bin:/opt/rocm/core-10.0/lib ~/llama-topka/bin/test-backend-ops -o FLASH_ATTN_EXT -p hsk=256 -b ROCm0` bez env, z `=0` i z `=83`: za każdym razem 173/173.
2. Harness md5 (`md5.sh`, z `BIN` i `PROD` w `common.sh` przestawionymi na `~/llama-topka/bin`): `=83` (wariant A) albo env pusty (wariant B) → **816334e4**; `=0` → 816334e4; kontrola pozytywna `=7` → 0c32617a. Kontrola wymaga binarki z pełną listą masek; przy produkcyjnym `X(83)` trzeba ją uruchomić na buildzie z `GGML_HIP_FA_D256_SWEEP=ON`. Uwaga: `md5.sh` wymusza `GGML_HIP_FA_D256_VAR=0` dla ramienia `prod`, więc domyślny wariant B trzeba sprawdzić osobnym ramieniem z `unset GGML_HIP_FA_D256_VAR`.
3. `bench.sh` (A = `=0`, B = domyślny): d128k ≥ +5% (oczekiwane 459,5 → ~486 t/s), d32k ≥ +1,5%.
4. Ramiona `arm.sh` (stara produkcja vs nowa): long 32k md5 **e460e3b6**, spec_sweep 119,2 ± 0,2 t/s, fill 255k ≥ 490 t/s z md5 **31b6525a**, szczyt VRAM ≤ 23 446 MiB, w logu startu (`server.out`) `GGML_HIP_FA_D256_VAR=83`.
5. LFM (`run-topka.sh lfm`): md5 greedy bez zmian. Instancja D=64 nie jest objęta przełącznikiem, więc to tylko kontrola, że binarka jest ta sama.
6. Po wdrożeniu: [[REKORDY]] (wiersz fill 255k: „w produkcji: tak”), notatka eksperymentu, `wylaczniki-env`, `log.md`.

## 7. Źródła
- Kod: `~/wt/fa-d256/ggml/src/ggml-cuda/fattn-mma-f16.cuh` @ `32292cc0a` (`:72, 164-166, 236-275, 530-637, 768-776, 876, 1059, 1073, 1172-1235, 2213-2341`); `tests/test-backend-ops.cpp:13267`; `common.cuh:82-93`; `mmq.cuh:223-247`, `mmq-config-rdna3.cuh:113-120`; `~/wt/kvq-once/ggml/src/ggml-cuda/fattn-kvq.cu:15, 174-177, 395-420, 487, 536`.
- Wyniki: `~/qwen-opt/fa-d256/res/{select,micro,isa,isa-topka-test,tbo,md5,bench,fill,long_md5}.txt`, `logs/perf-*.log`, `logs/{A,B}/spec_sweep.txt`; `~/qwen-opt/queue/logs/queue.log` (2026-11-09 01:41–02:58).
- Harness: `~/qwen-opt/fa-d256/{common,build,isa,gate,micro,md5,bench,arm}.sh`, `select.py`, `fill.py`, `long_md5.py`, `fa-d256.jobs`, `fa-d256-rerun.jobs`.
- Raporty: `24v-prefill-fa.md` (Werdykt, Profil, ISA, Działania 2, Do bazy wiedzy), `68a-rdna3-kernele.md` §1 pkt 2, §2.1, §4.1, `68c-dlugi-kontekst-gdn.md` §1 pkt 2/6 i tabela poz. 1–2, `68d-swieze-od-spolecznosci.md` §1 pkt 1, §2.3, §5 poz. 1, `68-SYNTEZA.md` poz. 2.
- Wiki: `eksperymenty/2026-11-08-fa-d256-prefill`, `eksperymenty/2026-11-08-kvq-once-profil`, `kernele/prefill-mmq-fa` (0042/0043), `lekcje/lekcja-cpuheavy-w-jobie-kolejki`, `karty/strix-halo`, `karty/rx-9070-xt`, `modele/lfm2-5-24b-a2b`.
- Upstream: [llama.cpp #31746](https://github.com/ggml-org/llama.cpp/pull/31746) (head `2ae66a338`, 2026-11-05/06), [#31751](https://github.com/ggml-org/llama.cpp/pull/31751), [#31802](https://github.com/ggml-org/llama.cpp/pull/31802) (wg 68d).
- Transkrypt agenta: `history://XtxFaPrefill` (zlecenie, IRC z 68c/68d, decyzja o buildzie w jobie, reguła `cpuheavy`).
