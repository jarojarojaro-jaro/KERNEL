# 23 — ekondis/mixbench: co zmierzy na gfx1100 i jak tym skalibrować nasz roofline

Źródła przejrzane 2026-10-14: `master` = `a8cab0c` (2026-08-04), gałęzie `hip-fix-cmakelists` (`e6391c3`, PR #65, otwarty), `hip-refactor` (2023, starsza niż master), `gh-pages`. Przeczytałem też wszystkie 65 issue/PR z listy i istotne wątki (#41, #46, #48, #31, #17). Klon był w `/tmp/repos`, już go usunąłem. **Niczego nie uruchamiałem ani nie kompilowałem.** Wszystkie liczby dla gfx1100 poniżej to `[SZACUNEK]` albo `[WNIOSEK]`. Mierzone liczby z repo pochodzą z cudzych kart (MI210, RTX 2070).

## 1. Co to jest

Mikrobenchmark „mixed operational intensity”. Jeden kernel czyta bufor, a na każdym elemencie wykonuje łańcuch `ci` FMA. `ci` przechodzi przez 33 wartości od 0 do 512, więc wynik to krzywa GB/s i GFLOPS w funkcji flop/B, czyli empiryczny roofline z „kolanem”. Implementacje: CUDA, HIP, OpenCL, SYCL i CPU. Licencja GPL-2.0, 467★. Repo jest utrzymywane, ale zmiany są drobne: ostatni commit 2026-08 dotyczy wyboru GPU w CUDA, a PR #65 modernizuje CMake dla HIP. Dla RDNA3/7900 XTX **nie ma żadnych opublikowanych wyników**:
- w README jest tylko RTX 2070 (`README.md:40-98`), a w README HIP tylko MI210 (`mixbench-hip/README.md:21-74`, pomiar z issue #48);
- `gh-pages` ma 2 obrazki (gtx480, rtx2070);
- autor uznał wyniki trzymane w repo za przestarzałe (#31);
- wyszukiwanie w sieci („mixbench” + 7900 XTX/RDNA3/gfx1100/W7900) nic nie dało.

## 2. Kluczowe techniki (z dowodami)

**T1. Kernel** (`mixbench-hip/mix_kernels_hip.cpp:55-82`)
- Wątek ładuje 8 elementów (`ELEMENTS_PER_THREAD`, `:26`) z krokiem `blockSize`, czyli 8 skoalescowanych odczytów na blok o 256 wątkach (`:60-61,67`).
- Na każdym elemencie liczy zależny łańcuch `t = t*t + seed` (`:69-71`). Daje to 8 niezależnych łańcuchów na wątek.
- Na końcu jest redukcja `mad` i zapis „martwy”, który nigdy się nie wykonuje (`:80-81`). Zapis tylko blokuje DCE, więc test mierzy **wyłącznie odczyt**.

**T2. Oś intensywności** (`:115-124,256-288`)
- Liczba operacji: `8·G + 16·ci·G`, gdzie G to liczba wątków. Liczba bajtów: `size·sizeof(T)`.
- Dla float wychodzi flop/B = (1+2·ci)/4.
- Typy:
  - `float`,
  - `float2` („Packed SP”),
  - `double`,
  - `half2` (`__hfma2`, `:40-43`),
  - `int`: `a*b+c` na 32 bitach (`:171-178`).

**T3. Pomiar czasu**
- `hipExtLaunchKernelGGL` z eventami start/stop w pakiecie dyspozycji (`:132-138`, wprowadzone w #21). Mierzony jest czas na GPU, bez narzutu hosta.
- `benchmark<3>`: pierwszy pomiar jest odrzucany, z dwóch pozostałych bierze się **minimum** (`include/common.h:6-15`).
- Rozgrzewka to jeden krótki kernel `short` na 1/128 bufora (`:99-113`).

**T4. Rozmiar**
- `VECTOR_SIZE = 32M` elementów double, czyli bufor 256 MB, zakodowany na sztywno (`main-hip.cpp:15,25`).
- Kernele `float`, `half2` i `int` czytają 128 MB, a `float2` i `double` 256 MB.
- Każdy pomiar czyta **ten sam** bufor.

**T5. Nagłówek „theoretical” nie jest pomiarem**
- Jest wyliczany z `hipDeviceProp` (`lhiputil.h:24-52,82-87`).
- `_ConvertSMVer2Cores` zakłada 64 SP/CU tylko przy `__HIP_PLATFORM_HCC__`. W nagłówkach ROCm 10 tego makra już nie ma (grep `/opt/rocm/core-10.0/include/hip` znajduje tylko `hipBlockIdx_x`/`hipThreadIdx_x`, `amd_hip_runtime.h:344-350`). Dla major=11 wpadnie więc `default: 128`.
- Pole „Memory bandwidth” bierze się z `memoryClockRate`. Oba pola nagłówka trzeba ignorować `[WNIOSEK]`.

**T6. Czego mixbench nie mierzy**
- Brak WMMA/tensor cores. Issue #41 zamknięto odpowiedzią „most modern GPUs do not require explicit vectorization”, czyli bez zrozumienia, o co chodziło.
- Brak dp4a: `int` to `v_mul_lo_u32` + add, a nie `v_dot4_i32_iu8`.
- Brak wariantu LDS/L2 (#17).
- W HIP nie ma „thread fusion” (`:227`: 1), w przeciwieństwie do CUDA (`FUSION_DEGREE 4`, `mix_kernels_cuda.cu:15`).

**T7. Pułapka kompilatora** (#46, Adreno): spadek o rząd wielkości powyżej pewnego `ci`, prawdopodobnie przez spill przy pełnym rozwinięciu pętli. Autor zaleca `#pragma unroll N`. U nas przy ci=512 jest 8×512 FMA w pełni rozwiniętych, więc przed zaufaniem prawym kolumnom trzeba sprawdzić ISA pod kątem scratch/spill.

**T8. Metoda z publikacji** (`README.md:110-120`, JPDC 2017). Krzywe z mixbench plus liczniki sprzętowe (transakcje DRAM, instrukcje) dają „quantitative roofline”: przewidywany czas kernela i jego odległość od dachu. Repo zawiera tylko część z mikrobenchmarkiem.

**Pomiary w repo (cudze):**
- MI210 (HIP): SP ~1400 GB/s przy ci=0 z teoretycznych 1638 (85%). Kolano SP około 12–14 flop/B, potem plateau ~20–24 TFLOPS. Packed SP i HP ~40 TFLOPS przy ci=512 (`mixbench-hip/README.md:42-74`).
- RTX 2070: 418–424 z 448 GB/s, czyli ~94% (`README.md:66-98`).

## 3. Przeniesienie na gfx1100: co dokładnie zmierzy binarka HIP

Kod jest już w HIP, więc przenosić nie trzeba. Trzeba za to wiedzieć, w jakie instrukcje gfx11 zamienią się kolumny, bo od tego zależy interpretacja wyników.

| kolumna | instrukcja na gfx11 `[WNIOSEK]` | teoria @2.5 GHz, 96 CU | czy przydatne dla nas |
|---|---|---|---|
| SP `float` | `v_fma_f32` (VOP3). Dodajnik `seed` ≠ cel, więc to **nie** jest forma `v_dual_fmac_f32`. VOPD ma tylko FMAC/FMAAK/FMAMK, MUL, ADD, SUB, MIN/MAX, MOV, CNDMASK, DOT2ACC_F32_F16/BF16, ADD_NC_U32, LSHLREV, AND (lista ISA, np. `azhirnov/cpu-gpu-arch gpu/AMD-RDNA3.md:102-122`) | 30.7 TF przy pojedynczym issue (128 flop/clk/CU), 61.4 TF tylko z VOPD | tak: efektywny zegar pod obciążeniem, kolano BW |
| Packed SP `float2` | gfx11 nie ma `v_pk_fma_f32`, więc wychodzą 2× `v_fma_f32` (więcej ILP, ten sam brak VOPD) | jw. | słabo: różni się od `float` też rozmiarem (256 vs 128 MB) |
| HP `half2` | `v_pk_fma_f16`; pakowane f16 **nie** wchodzi w VOPD (Chips and Cheese, RDNA3 microbenchmarking) | 61.4 TF | tak: matematyka half2 w FA vec |
| DP | FP64 ~1/32 | ~1 TF | nie |
| INT | `v_mul_lo_u32` (wolne) + add | dużo poniżej FP32 | nie, to nie dp4a/iu8 |
| ci=0, GB/s | `global_load_b32`/`b64`, sam odczyt | 960 GB/s (20 Gbps × 384 bit) | **tak**, ale tylko jako dach dla dużego strumienia |

Wnioski z tabeli:
- **Kolumna SP pokaże zapewne ~połowę marketingowych 61.4 TF.** To skutek formy instrukcji, a nie limit sprzętu. Chips and Cheese widział mało VOPD przy FMA nawet w teście zaprojektowanym pod dual-issue ([artykuł](https://chipsandcheese.com/p/microbenchmarking-amds-rdna-3-graphics-architecture)). Rozstrzyga to `-save-temps` i grep `v_dual_` w ISA, bez GPU.
- **Kolano SP** wypada przy ~32 flop/B (30.7 TF / 0.96 TB/s), czyli ci≈64 dla `float`. W jednostkach przydatnych dla nas: ~0.5 instrukcji VALU (na falę) na bajt DRAM na CU, bo 2 issue/clk/CU wobec ~4 B/clk/CU przy 2.5 GHz `[SZACUNEK]`.
- **Infinity Cache (96 MB).** Kernel `float` czyta 128 MB wielokrotnie, a `float2` 256 MB. Przy MALL 96 MB liczba GB/s dla `float` może być zawyżona częściowymi trafieniami, zależnie od polityki wymiany. Kolumn `float` i `float2` przy ci=0 nie da się więc porównać 1:1 (inny working set i inna szerokość odczytu) `[WNIOSEK]`.
- **Zegar.** Rozgrzewka jest krótka (T3), a ci=0 to pierwszy wiersz. Wiersz GB/s jest więc najbardziej narażony na niedogrzane DPM (sclk/mclk) po bezczynności. Por. runtime PM/BACO w `NOTES.md:122-126` i „rampa zegara” w `research/tensorfold/README.md:137`.

Czego się nie przeniesie: mixbench nie mierzy dachu, który ogranicza prefill (WMMA iu8/f16) ani dekodowanie (dp4a + rozpakowanie + odczyt ~2–50 MB na wywołanie przy zimnym MALL). Jego dach BW dotyczy jednego dużego, ciepłego strumienia.

## 4. Pomysły dla nas

Nasze liczby, które chcemy skalibrować:
- MMVQ: gate+up 17.3 MB, 24.2 µs, 715 GB/s; in_proj 8.65 MB, 12.9 µs, 673 GB/s; **głowica 205 MiB, 239 µs, 902 GB/s** (`research/lfm-decode.md:162-164`);
- microbench Qwen 5120×17408: 1 kolumna 742–779 GB/s, 4–8 kolumn 545–713 GB/s (`NOTES.md:67-76`);
- prefill ~50 TFLOPS z „~123”.

Głowica osiąga już 902 GB/s, więc **dach dla dużego strumienia znamy: ≥ 902**. Brakuje dachu **dla rozmiaru pojedynczego wywołania**. To jest główna wartość, jaką da się wycisnąć z mixbench.

**E1 (główny). Krzywa „idealny odczyt vs bajty na wywołanie” z rotacją powyżej MALL: decyzja, czy dalej pracować nad pasmem MMVQ.**
- Co zmienić: łatka do *kopii* mixbench (nie do naszego drzewa). Szkic w planie pomiaru poniżej:
  - rozmiar z env;
  - rotacja slotów po puli 2 GiB, żeby każde wywołanie było zimne, jak wagi w dekodowaniu;
  - typ `float4`, czyli odczyty 16 B/lane jak nasze MMVQ („4 kolejne inty”, `NOTES.md:63`);
  - R wywołań jedno po drugim.
- Wynik: t(bytes) = t0 + bytes/B∞ dla rozmiarów 1, 2, 2.9, 4, 8.65, 17.3, 50, 100 i 205 MB. Z tego idealny czas każdej klasy MMVQ i luka:
  - LFM: przy t0≈2 µs i B∞≈930 GB/s gate+up miałoby ~20.6 µs wobec 24.2, czyli −3.6 µs × 38 ≈ **0.14 ms/token (~3%)**. in_proj: 11.3 wobec 12.9 µs, ×30 ≈ 0.05 ms `[SZACUNEK]`;
  - Qwen: kształt 50 MB przy 5 kolumnach ~690–700 GB/s, wobec idealnych ~900 daje ~20–25% luki w części MMVQ kroku `[SZACUNEK]`.
- Decyzja: jeśli idealny kernel przy 17 MB też dobija tylko ~720 GB/s, to MMVQ jest przy praktycznym dachu, a wysiłek idzie w liczbę kerneli (LFM jest launch-bound). Jeśli osiąga ≥ 880, dalsza praca nad MMVQ (bajty w locie, ogon siatki) ma pokrycie.
- Koszt: ~1 h (łatka ~40 linii + pomiar < 1 min GPU). Ryzyko: niskie. Jedyna pułapka to porównanie jabłek z jabłkami: czasy liczyć z rocprofv3 tak samo jak `kernel_bw.py`, a nie z eventów mixbench.

**E2. Efektywny zegar przy 285 W, czyli rekalibracja „50 z ~123 TFLOPS” w prefillu.**
- f_eff = GFLOPS_SP(ci=512) / (96·128) [GHz]. Warunek: E3 pokaże brak VOPD. Kontrola krzyżowa przez `half2`: f_eff = GFLOPS_HP / (96·256).
- Sufit WMMA f16/iu8 ≈ 96·512·f_eff, bo 122.8 TF / (96 · 2.5 GHz) = 512 flop/clk/CU `[WNIOSEK z danych AMD]`.
- Przykład: przy f_eff ≈ 2.2 GHz sufit to ~108 TF, a prefill = 46% zamiast 41%.
- Zastrzeżenie: WMMA ma inny pobór mocy niż FMA VALU. Przydatniejszy i tańszy jest **odczyt sclk/mocy w czasie prawdziwego prefillu** (`pp_dpm_sclk`, `amd-smi metric -p`, jak w `NOTES.md:116`). mixbench daje tylko punkt odniesienia dla VALU.
- Zysk: zero bezpośredniego przyspieszenia, ale lepsza ocena, ile realnie zostało w MMQ.

**E3. ISA bez GPU: VOPD i wave64.**
- Kompilacja z `-save-temps`, potem `grep -c v_dual_` i sprawdzenie scratch/spill przy ci=512 (T7).
- Drugi build z `-mwavefrontsize64`: wave64 może wykonać operację „dual-issue” w jednym cyklu bez parowania przez kompilator (Chips and Cheese; `azhirnov ... AMD-RDNA3.md:68,94-97`).
- Jeśli SP wave64 ≫ SP wave32 na GPU (E2), daje to argument za sprawdzeniem wave64 tylko w **małych kernelach FP32-ciężkich** (rms_norm, softmax w FA, część GDN), a nie w MMVQ, gdzie dp4a i bfe/shift i tak nie wchodzą w VOPD.
- Uwaga: hipEngine nie widział zysku z wave64 na gfx1100 (`hipEngine docs/ROOFLINE.md:1158-1159`). Priorytet niski.

**E4. Bajty w locie na falę.**
- Sweep `ELEMENTS_PER_THREAD` ∈ {1,2,4,8,16} × `float`/`float4` przy 8.65 i 17.3 MB, z rotacją.
- Pokaże, ile odczytów 16 B na lane trzeba mieć w locie, żeby dobić ~90% B∞ na gfx1100. To bezpośrednio dotyczy in_proj (466–475 GB/s, „low bytes in flight per wave”, `lfm-decode.md:53,128`).
- **Uwaga na wynik negatywny:** „n=1 K loop in unrolled chunks of 4/2” nie dał zysku (`lfm-decode.md:143-144`). E4 nie jest ponowną próbą, tylko pomiarem, który ma wyjaśnić, czy limitem było MLP, czy obłożenie/siatka. Wracać do kernela tylko wtedy, gdy E4 pokaże wyraźny próg.

**E5 (outside the box). „Quantitative roofline” z rocprofv3 dla każdego kernela w trace.**
- Metoda z publikacji (T8) przeniesiona na nasz trace. Dla każdego kernela: FETCH_SIZE (bajty), SQ_INSTS_VALU i SQ_WAVES (rocprofv3 `--pmc`), czas.
- Klasyfikacja:
  - VALU/B względem kolana z mixbench (~0.5 instr. fali/B, E2/E3);
  - bajty względem krzywej t0 + b/B∞ z E1.
- Wynik: automatyczny ranking luki w µs/token dla każdej klasy kernela (rozszerzenie `kernel_bw.py`).
- Mój szacunek dla MMVQ przy 5 kolumnach: ~0.07–0.1 instr. VALU fali/B, czyli 15–20% kolana. MMVQ nie jest więc ograniczony przez ALU, a luka to latencja/MLP/ogon `[SZACUNEK]`. Licznik to potwierdzi albo obali w jednym przebiegu.
- Koszt: średni (skrypt + jeden profil z licznikami). Ryzyko: liczniki gfx11 bywają niedostępne lub multipleksowane; wtedy kilka przebiegów.

**E6. Pasmo MALL.** Rozmiar < 96 MB bez rotacji (np. 32 MB `float4`) daje empiryczne pasmo MALL na gfx1100 (Chips and Cheese: ~2.3 TB/s). Przydatne do wyceny pomysłów z ponownymi odczytami z L2/MALL, np. FA q8_0 czytające K/V 4× (`lfm-decode-round2.md:88-91`). Priorytet niski.

### Plan pomiaru (proponowany, NIE wykonany; wymaga GPU, tylko przez nasze blokady)

Zasady:
- build pod `/tmp/quiet.lock`;
- pomiar pod `flock -o /tmp/gpu.lock` + `/tmp/quiet.lock`;
- przed startem sprawdzić `/sys/class/kfd/kfd/proc/` (whitelist gpu-keepawake) i `gpu_busy_percent` (`repos/14-auto-gpu-kernel.md:78`);
- żaden serwer llama nie może trzymać VRAM.

```bash
# 0) źródła (CPU)
git clone --depth 1 https://github.com/ekondis/mixbench /tmp/mixbench && cd /tmp/mixbench/mixbench-hip
echo '#define VERSION_INFO "a8cab0c"' > version_info.h        # zamiast CMake (find_package(HIP) jest stary, PR #65)
# 1) build stock: wave32 i wave64, z ISA (CPU, pod quiet.lock)
for w in 32 64; do
  flock -o /tmp/quiet.lock nice -n 10 /opt/rocm/core-10.0/bin/hipcc --offload-arch=gfx1100 -O3 -std=c++17 \
    -I../include -I. $([ $w = 64 ] && echo -mwavefrontsize64) -save-temps=obj -o mixbench-hip-w$w \
    main-hip.cpp mix_kernels_hip.cpp
done
grep -c 'v_dual_' *gfx1100*.s; grep -E 'scratch|private_segment' *gfx1100*.s | head   # E3, bez GPU
# 2) E2: stock, 20 powtórzeń dla ustalonego zegara + log zegarów/mocy (GPU ~40 s)
flock -o /tmp/gpu.lock flock -o /tmp/quiet.lock bash -c '
  (while :; do date +%s.%N; grep "\*" /sys/class/drm/card0/device/pp_dpm_sclk /sys/class/drm/card0/device/pp_dpm_mclk;
     amd-smi metric -p; sleep 0.2; done) > clk.log 2>&1 & L=$!
  ./mixbench-hip-w32 > warm.txt                              # rozgrzewka, wynik odrzucony
  for i in $(seq 20); do ./mixbench-hip-w32; done > w32.txt
  for i in $(seq 20); do ./mixbench-hip-w64; done > w64.txt
  kill $L'
```
Analiza E2: mediana z 20 przebiegów dla każdego wiersza, a nie minimum (minimum z N zawyża wynik, `repos/06-kernelagent.md:130`). f_eff z SP i HP przy ci=512, porównany z logiem sclk. Kolano = pierwsze `ci`, przy którym GB/s spada > 5% poniżej plateau.

E1/E4/E6 wymagają łatki do kopii mixbench (`mix_kernels_hip.cpp`, `main-hip.cpp`; szkic):
1. `size` z env `MIXBENCH_ELEMS` zamiast `VECTOR_SIZE` (`main-hip.cpp:15`); `int` w `init_vector` zamienić na `size_t`.
2. Alokacja puli `max(size*16, MIXBENCH_POOL)` (domyślnie 2 GiB). Slot = `align_up(size*sizeof(T), 2 MiB)`. Każde wywołanie bierze kolejny slot cyklicznie. Pula ≥ 8 slotów i ≫ 96 MB, więc wywołania są zimne.
3. Instancja `float4`: kopia bloku `float2` (`:141-149`) z `4*computations`, `sizeof(float4)` i `float4{1.0f}`. Pula musi mieć ≥ `size*16` B, bo obecny bufor `size*8` byłby za mały.
4. `MIXBENCH_CI` = lista `ci` (tu „0”), `MIXBENCH_RUNS` = R wywołań jedno po drugim **bez synchronizacji między nimi**, jak węzły grafu. Do tego wypisanie mediany.
5. `ELEMENTS_PER_THREAD` z `-D` (dla E4). `#define` w `:26` dostaje `#ifndef`.

```bash
# E1: zimne wywołania, odczyt 16 B/lane, czasy z rocprofv3 jak w kernel_bw.py (GPU < 2 min łącznie)
for MB in 1 2 2.9 4 8.65 17.3 50 100 205; do
  E=$(python3 -c "print(int($MB*1e6/16)//2048*2048)")
  flock -o /tmp/gpu.lock flock -o /tmp/quiet.lock env MIXBENCH_ELEMS=$E MIXBENCH_POOL=$((2<<30)) MIXBENCH_CI=0 \
    MIXBENCH_RUNS=50 rocprofv3 --kernel-trace --stats -d e1_$MB -- ./mixbench-hip-rot
done
# E4: to samo dla 8.65 i 17.3 MB, binarki -DELEMENTS_PER_THREAD={1,2,4,8,16}
# E6: MB w {16,32,64} z MIXBENCH_POOL=0 (bez rotacji: ciepły MALL)
```
Raport: tabela MB → µs (mediana) → GB/s, dopasowanie t0 i B∞, a potem kolumna „idealny czas / zmierzony” dla klas MMVQ z `lfm-decode.md:162-164` i shape'ów z `NOTES.md:67-76`.

## 5. Krytyka

- Dla nas to **nie jest roofline kerneli skwantyzowanych**: nie ma WMMA, dp4a ani LDS, a `int` to 32-bitowe mnożenie. Nie skalibruje bezpośrednio sufitu prefillu ani obliczeniowej części MMVQ.
- Wiersz GB/s to jeden duży, powtarzany strumień 128/256 MB, częściowo w zasięgu 96 MB MALL. Nasze dekodowanie to dziesiątki zimnych wywołań po 2–50 MB z ogonem siatki. Bez rotacji i sweepu rozmiaru (E1) liczba „~9xx GB/s” niczego nie rozstrzyga. Dach ≥ 902 GB/s i tak już mamy z głowicy LFM.
- Minimum z 2 pomiarów, krótka rozgrzewka i ci=0 jako pierwszy wiersz to słaba statystyka i ryzyko niedogrzanego DPM.
- Nagłówek „theoretical” (SP/CU, BW) jest wyliczany z właściwości, nie mierzony. Na ROCm 10 SP/CU wyjdzie 128 przez nieobecne `__HIP_PLATFORM_HCC__` (`lhiputil.h:25-37`).
- Kolumna SP najpewniej nie pokaże dual-issue, bo forma FMA nie pasuje do VOPD. Kto weźmie ją za „peak FP32 7900 XTX”, zaniży sufit 2×. Odwrotnie: marketingowe 61.4 TF nie są osiągalne dla zwykłego `fma(a,b,c)` w wave32.
- Odpowiedź autora w #41 (tensor cores = „explicit vectorization”) pokazuje, że projekt nie celuje w ML.
- Nasz `mmvq-bench` już rotuje wagi > 96 MB (`NOTES.md:33`, `mmvq_bench.cpp:3-5,29-30`). mixbench dokłada tylko odniesienie „idealnego czytnika” przy tych samych bajtach na wywołanie i kolano VALU/B.
- Uwaga na wtórne źródła: `hipEngine docs/ROOFLINE.md:118` podaje dla 7900 XTX GDDR6 „24 Gbps”. Karta ma 20 Gbps × 384 bit = 960 GB/s `[WNIOSEK z danych AMD]`. Ich tabela przepustowości cache to zapożyczenie z Chips and Cheese, nie ich pomiary.

## 6. Werdykt

**Średnia.** Technik do przeniesienia mixbench nie zawiera. Jako tanie narzędzie kalibracyjne (minuty GPU) daje jednak dwa brakujące punkty: dach odczytu w funkcji bajtów na wywołanie przy zimnym MALL (E1) oraz efektywny zegar i kolano VALU/B przy 285 W (E2/E3). Pierwszy rozstrzyga, czy dalsza praca nad pasmem MMVQ ma sens, czy zostaje tylko redukcja liczby kerneli. Wymaga łatki do kopii repo i pomiaru przez `/tmp/gpu.lock` + `/tmp/quiet.lock`.
