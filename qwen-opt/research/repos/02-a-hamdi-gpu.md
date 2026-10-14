# 02 — a-hamdi/GPU („GPU 100 days Learning Journey”)

Źródło: https://github.com/a-hamdi/GPU, HEAD `a9b0a17c` (2025-04-27). Klon płytki, nic nie było budowane ani uruchamiane. Ścieżki `plik:linia` są względem korzenia repo.

## 1. Co to jest

Dziennik nauki: 100 dni, po jednym małym kernelu dziennie, według książki PMPP (`README.md:1-11`). Są tam ćwiczenia CUDA (głównie Colab T4, `day 29/README.md`), kilka plików Triton (dni 38–43, 58–61) i garść portów HIP testowanych na **MI250 / gfx90a** (`README.md:596`, `day 32/CMakeLists.txt:31`, `day 32/benchmark_results.txt:4`). Licencja MIT, 632 gwiazdki, 79 forków. Repo powstało 2025-01-21, ostatni push 2025-04-27 i od tamtej pory nie jest rozwijane. Nie ma tu kerneli kwantyzowanych, MMVQ, WMMA/MMA, kerneli decode ani pomiarów LLM. Wszystkie kernele to FP32 skalarne, poziom „rozdział PMPP”.

## 2. Kluczowe techniki (to, co w ogóle jest)

| Technika | Dowód | Liczby (czyje) |
|---|---|---|
| CUDA Graph z 4 elementwise kernelami, 10 000 uruchomień | `day 29/Cuda_graphs.cu:139-151` | „220 ms bez grafu vs 89.9 ms z grafem” (`day 29/README.md`, autor, T4). Daje to ~5.5 → ~2.25 µs na kernel |
| SGEMM FP32 z tilingiem w rejestrach (HIP), kopia „kernel 3” z artykułu seb-v | `day 32/kernel3_registers.cpp:5-149`, `README.md:639` | 18.6 TFLOPS przy N=4096 vs rocBLAS 34.3 (`benchmark_results.txt:12`, autor, MI250X) |
| Winograd/Strassen, CSR/COO/BSR SpMM (HIP) | `day 33/*.cpp` | „Winograd 52.4 TFLOPS przy N=512” (`README.md:665`, autor) — niewiarygodne, patrz §5 |
| Flash attention forward (FA1, FP32, wątek na wiersz) w CUDA i HIP | `day 10/…`, `day 30/flash_attention_forward.cpp:7-80` | brak pomiarów; test seq=64 (`:166`) |
| RMSNorm jako 2 kernele (redukcja drzewem w shared + osobna normalizacja) | `day 93/RMS_Normalization.cu:6-54` | brak |
| Elementwise „optim”: pętla grid-stride, 2× `float4`, `__ldg`, `__launch_bounds__(1024,4)` | `day 97/elu_optim.cu:10-54`, `day 100/Kullback-Leibler.cu:6-25` | brak |
| „FP8 na Tensor Cores” | `day 50/fp32_fp16_fp8_t4.cu:9-19,52-61` | brak sensownych (patrz §5) |
| Redukcja warp `__shfl_down_sync` od offsetu 16 | `day 15/flash_attention_backprop/helper.cu:6-8` | — |

Jedyna rzecz dla nas wartościowa to **odnośnik** w `README.md:639` do artykułu seb-v „Optimizing Matrix Multiplication on RDNA3: 50 TFlops and 60% Faster Than rocBLAS” (https://seb-v.github.io/optimization/update/2025/01/20/Fast-GPU-Matrix-multiplication.html). Ten artykuł jest pisany **na RX 7900 XTX** (FP32 SGEMM 4096², pomiary autora artykułu, Windows):
- rocBLAS 4.49 ms (30.5 TFLOPS).
- Kernel 3 (tiling w rejestrach) 6.03 ms.
- Kernel 4 (double buffer GMEM) 5.38 ms.
- Kernel 5 (padding LDS `As[BK][BM+4]` przeciw konfliktom banków, kafel wątku 16×8) 4.10 ms.
- Kernel 6 (ręczny rozkład VGPR na banki pod `v_dual_fmac_f32`, kod ISA ładowany przez Module API) 3.64 ms.
- Kernel 7 (rozwinięcie pętli w ISA) 3.33 ms.
- Kernel 8 (globalne loady wsadowo) **2.80 ms, 49 TFLOPS**.

Fakty sprzętowe z artykułu, cytowane przez niego z RDNA3 ISA guide:
- LDS ma 64 banki DWORD, podzielone na 2 × 32 (każda połowa obsługuje parę SIMD32).
- Są 4 banki VGPR (numer banku = `reg % 4`), każdy z cache o 3 portach odczytu.
- Dla `v_dual_*`: SRC0X i SRC0Y muszą być w różnych bankach, SRC1X i SRC1Y też, a DST jeden parzysty i jeden nieparzysty.
- Sztucznie VALU-bound pętla z samymi `v_dual_fmac` nie przekroczyła **75% VALU utilization**; dopiero ręczny rozkład banków dał 76–80%.

## 3. Przeniesienie na AMD/HIP/RDNA3

- **CUDA Graph (dzień 29):** nic nowego. Graf HIP już mamy, a koszt granicy kernela (~2.53 µs) zmierzyliśmy dokładniej (`research/lfm-decode-round2.md` §1). Ich ~2.25 µs/kernel na T4 to ten sam rząd wielkości.
- **SGEMM z tilingiem w rejestrach:** jako kod się nie przenosi. To FP32 bez WMMA, a nasz prefill to MMQ iu8 WMMA. Kod zakłada fale 32-wątkowe (`kernel3_registers.cpp:17,26`, „wave tile” 8×4 lane), więc pasuje do RDNA3 wave32. Na gfx90a, gdzie autor go uruchamiał (wave64), podział na „fale” jest fikcyjny. Wynik jest wtedy poprawny, ale wydajność przypadkowa.
- **Lekcje z artykułu seb-v (nie z repo)** są natywnie RDNA3:
  - Padding LDS i wsadowe loady globalne przenoszą się wprost na kafle MMQ/FA prefillu. „Loady przed obliczeniami” są już w planie ze Straty (#2017).
  - Dual-issue VALU (`v_dual_*`) działa tylko w wave32 i tylko dla podzbioru opcodów (fmac/mul/add f32, mov, cndmask, kilka int). Ma znaczenie wyłącznie w kodzie ograniczonym VALU: dekwantyzacja w MMQ, softmax/rescale w FA, rekurencja GDN w prefillu. MMVQ decode jest ograniczony pamięcią i tu nie zyska. `[WNIOSEK]`
  - Ręczny ISA przez `hipModuleLoad` jest technicznie możliwy w HIP, ale nie da się go utrzymać w forku llama.cpp z 54 łatkami.
- **FA, RMSNorm, elementwise, „FP8”:** wszystko gorsze od tego, co już mamy (kvq FA z WMMA, norma z redukcją DPP i zapisem q8_1, fuzje A6). `__ldg` na AMD nic nie daje (zwykły load). 7900 XTX nie ma FP8.
- **`__shfl_down_sync(0xffffffff, …)` od 16** (`helper.cu:7`): działa tylko przy warpSize 32. Na RDNA3 w wave32 OK, w wave64 cicho błędne. Nas to nie dotyczy, bo ggml-cuda używa `WARP_SIZE`.

## 4. Pomysły dla nas

Repo samo nie daje żadnego pomysłu. Poniższe wynikają z artykułu, do którego prowadzi, i są małe.

1. **Statyczny audyt ISA gorących kerneli VALU/LDS-bound: MMQ prefill (Q4_K/Q5_K/IQ4_XS), `fattn-kvq` prefill/decode, GDN.**
   - Co: zbudować z `-save-temps` (albo `llvm-objdump -d` na code object) i w pętli wewnętrznej policzyć: udział `v_dual_*` wśród VALU, rozmieszczenie `s_waitcnt vmcnt/lgkmcnt` (czy loady globalne są wsadowe, czy przeplatane z waitami), `ds_load_b128` vs b32/b64, liczbę VGPR i obłożenie.
   - Zysk: sam audyt 0, ale wskaże, czy MMQ (~50 z ~123 TFLOPS) jest ograniczony dekwantyzacją w VALU, LDS czy pamięcią. `[SZACUNEK]` Jeśli dekwantyzacja to w większości pojedyncze VALU bez dual-issue, przestawienie kodu na pary niezależnych operacji f32/int może dać 3–8% czasu MMQ.
   - Koszt: kilka godzin, bez GPU (wystarczy build). Ryzyko: brak.
   - Pomiar: rocprofv3, czasy kerneli MMQ w `llama-bench -p 4096`, A/B przeplatane.
2. **Konflikty banków LDS w kaflach `fattn-kvq` i MMQ.**
   - Co: sprawdzić stride kafli K/V (q4_0 → f16) i kafli MMQ względem 64 banków LDS (2 × 32 na parę SIMD). Tam, gdzie wave zapisuje kolumnę (transpozycja przy zapisie do LDS), dodać padding +4 DWORD (u seb-v część skoku 5.38 → 4.10 ms).
   - Zysk: `[SZACUNEK]` 0–5% czasu danego kernela, czyli ułamek procenta e2e w decode i 1–3% prefillu.
   - Koszt: niski. Ryzyko: VGPR/LDS budżet obłożenia; bitowo bez zmian (sam layout).
   - Pomiar: rocprofv3, a jeśli działa na gfx1100 — liczniki `SQ_LDS_BANK_CONFLICT`. U nas PMC zwracają 0 (`NOTES.md:256`), więc najpierw trzeba to naprawić.
3. **Narzędzie zamiast kodu: instruction-level timing.**
   - Co: seb-v diagnozował wszystko w RGP (stall na `s_waitcnt`, VALU utilization per instrukcja). Sprawdzić, czy na Linuksie z ROCm 10.0 działa `rocprofv3 --att` (thread trace) dla gfx1100 albo RGP dla HIP. `[WNIOSEK — do sprawdzenia, w tej sesji nie weryfikowane]`
   - Zysk: pośredni, ale duży. Nasze decyzje opierają się dziś na czasach kerneli bez liczników (PMC = 0), a „gdzie stoi wave” to brakująca informacja dla MMQ, FA i GDN.
   - Koszt: 1–2 h prób. Ryzyko: brak.
4. **Outside the box (raczej odrzucić): ręczny ISA dla jednego kernela.** U seb-v K5 → K8 dało +46% w ISA, czego kompilator nie chciał wygenerować. Dla nas jedynym kandydatem byłaby pętla MMQ prefillu. Utrzymanie `.s` przy każdym rebase upstreamu i każdej zmianie typu kwantyzacji jest nierealne. Sensowne użycie: jednorazowy eksperyment diagnostyczny (ręcznie poprawiony ISA mówi, ile realnie jest do wzięcia), a potem próba wymuszenia tego samego z C++ (kolejność, `__builtin_amdgcn_sched_group_barrier`, `amdgpu_waves_per_eu`).

Repo nie wnosi niczego nowego do otwartych wąskich gardeł decode (koszt uruchomień MoE, pasmo MMVQ 1/5 kolumn, FA q8_0 przy długim kontekście).

## 5. Krytyka

- **Pomiary SGEMM na AMD są błędne metodologicznie.** Każdy kernel mierzony jest raz, na zimno, `chrono` wokół jednego uruchomienia (`day 32/benchmark_sgemm.cpp:104-110,114-129`). „rocBLAS 41 GFLOPS / 52 ms przy N=1024” i „custom 49× szybszy” (`benchmark_results.txt:10,45`, `README.md:625`) to koszt inicjalizacji rocBLAS (ładowanie code objects Tensile), a nie GEMM.
- **Weryfikacja poprawności nic nie sprawdza.** Dane są row-major, a `rocblas_sgemm` dostaje je jako column-major bez transpozycji (`benchmark_sgemm.cpp:115-121`), więc liczy B·A zamiast A·B. Stąd „Max Diff” 79–260 (`benchmark_results.txt:10-13`), które autor zignorował. Kernel przy `beta=0` czyta też niezainicjalizowane `c` (`kernel3_registers.cpp:144`, `0·NaN = NaN`).
- **„Winograd 52 TFLOPS przy N=512” i „rocBLAS 0.75 GFLOPS przy N=256”** (`README.md:659-665`) to ten sam błąd: jeden zimny pomiar eventami (`day 33/main.cpp:36-66`), bez sprawdzania błędów po launchu (`day 33/winograd.cpp:237-246`). Do tego sam autor przyznaje „accuracy challenges” (`README.md:682`). 52 TFLOPS FP32 na jednym GCD MI250 jest powyżej szczytu wektorowego FP32 (~24 TFLOPS/GCD). `[WNIOSEK]`
- **„FP8 on Tensor Cores”** (`README.md:773`) to w rzeczywistości afiniczna kwantyzacja do `uint8` w skalarnej pętli, bez żadnego MMA (`fp32_fp16_fp8_t4.cu:13-19,52-61`). `mma.h` jest dołączone, ale nieużywane.
- **„Fused linear + softmax”** (`day 74/fused_linear_softmax.cu:52-53`) to dwa osobne kernele.
- **Opis `elu_optim`** obiecuje `__half2` i `__exp2f` (`day 97/elu_optim.cu:1`, `README.md:1005`), a kod używa tylko `float4` i `expm1f`. Makro `EXP2f` jest nieużyte (`:6-7`).
- **FA forward w HIP dodaje `eps` do każdego składnika iloczynu P·V i do wykładnika** (`day 30/flash_attention_forward.cpp:72,76`), co jest systematycznym błędem numerycznym. Do tego wątek na wiersz, FP32, bez WMMA.
- **RMSNorm** robi `cudaMalloc`/`cudaFree` przy każdym wywołaniu i używa 2 kerneli (`day 93/RMS_Normalization.cu:49-56`). To dokładnie to, co u nas usuwaliśmy fuzjami.
- Ogólnie: materiał edukacyjny, popularność wynika z formatu „100 days”, a nie z jakości. Nic nie jest aktualne dla RDNA3 + kwantyzowanego LLM decode.

## 6. Werdykt

**Niska** — repo to dziennik nauki z naiwnymi kernelami FP32 i błędnymi benchmarkami; jedyną użyteczną rzeczą jest odnośnik do artykułu seb-v o SGEMM na 7900 XTX (dual-issue/banki VGPR, banki LDS, wsadowe loady), z którego warto wziąć audyt ISA kerneli MMQ/FA prefillu.
