# 10 — tile-ai/tilelang: backend AMD/RDNA3, dequant GEMV (linia BitBLAS), autotuning

Klon: `--depth 1`, HEAD `19da924` (2026-10-14). Ścieżki `plik:linia` są względem korzenia repo. Nic nie budowano ani nie uruchamiano.

## 1. Co to jest
Python DSL do kafelkowych kerneli GPU (TVM pod spodem). Generuje kod CUDA, HIP, Metal i Ascend, ma JIT i autotuner. Autorzy pochodzą z PKU/MSR, to ci sami ludzie co BitBLAS/Ladder; artykuł: https://arxiv.org/abs/2504.17577. Repo jest bardzo aktywne (~8.6k gwiazdek, wydanie v0.1.13 z 2026-08, codzienne commity), licencja MIT. Główne cele to NVIDIA (Hopper/Blackwell) i MI300X. CI dla AMD działa tylko na gfx942 (`.github/workflows/ci.yml:93`, `README.md:124`). RDNA3 (gfx11) jest obsługiwane od PR #2044 (2026-04). Poprawność potwierdzono wtedy zrzutami ekranu przykładów FA na W7900, 8060S i 9070XT. W CI nie ma żadnego runnera gfx11.

## 2. Kluczowe techniki (z dowodami)
- **RDNA3 ma WMMA, ale tylko f16→f32.**
  - `T.gemm` wybiera `rocm.wmma` dla gfx11/gfx12 (`src/rocm/op/gemm.cc:114-115`). Codegen emituje `__builtin_amdgcn_wmma_f32_16x16x16_f16_w32` z operandami v16f16 (gfx11) albo v8f16 z sufiksem `_gfx12` (`src/rocm/codegen/codegen_hip.cc:1878-1926`).
  - Emiter przyjmuje f16/bf16 i akumulator f32 (`tilelang/rocm/intrinsics/wmma_macro_generator.py:71-72`). Carver dopuszcza na RDNA wyłącznie parę (f16, f32) (`tilelang/carver/matmul_analysis.py:643`).
  - **Nie ma int8 (iu8) WMMA.** Testy int8 GEMM są na RDNA pomijane (komentarz lhl w PR #2127).
- **Układy fragmentów gfx11, sprawdzone na sprzęcie** (`tilelang/rocm/intrinsics/wmma_layout.py:25-53`):
  - A: lane t ma wiersz M=t%16, K=0..15; lanes 16–31 duplikują A/B.
  - D: wiersz M=(t/16)+2·l, kolumna N=t%16.
  - Emiter modeluje to jako `replicate=2` (`wmma_macro_generator.py:96-102`).
- **Przykład FA na RDNA** (`examples/amd/example_amd_flash_attn_fwd.py:58-72, 169-174`):
  - bloki ograniczone do 16/32×16/32, bo układ D≠A i transpozycja przez LDS psuje większe bloki;
  - `k_pack=2` jest zepsute, `num_stages=[0]`;
  - P idzie przez `P_shared` (LDS) jako most z układu D do A.
- **Async copy (bufor→LDS) tylko na CDNA gfx94+** (`src/rocm/target_utils.cc:54-61`). Na RDNA `T.Pipelined` nie ma prawdziwego nakładania transferów.
  - Buffer resource (`0x31004000` dla gfx11) jest używany tylko w ścieżce async copy (`src/tl_templates/hip/copy.h:28-32, 84-91`). Zwykłe loady globalne idą przez wskaźniki.
- **Kontrola obłożenia jest uboga.** Codegen dodaje tylko `__launch_bounds__(N)` dla N≥64 (`codegen_hip.cc:397-403`). Nie ma waves_per_eu ani GLC/DLC/SLC (grep pusty).
- **Redukcje warpu przez `__shfl_xor`** (`src/tl_templates/hip/reduce.h:174-177`), bez DPP.
- **dp4a na gfx11** → `__builtin_amdgcn_sudot4` (`src/tl_templates/hip/common.h:123-145`, PR #2127). To ta sama instrukcja `v_dot4_i32_iu8`, której używa ggml.
- **Dequant GEMV/GEMM z linii BitBLAS** (`examples/dequantize_gemm/example_dequant_gemv_fp16xint4.py:83-153`):
  - układ: wątki (reduce_thread=32, n_partition=4), 128-bitowe wektory K, dekwantyzacja w rejestrach, `tvm_thread_allreduce`;
  - szybki dequant to PTX `lop3.b32` + `sub.f16x2` z magiczną liczbą (`examples/dequantize_gemm/quantize/lop3.py:21-24`), czyli tylko NVIDIA;
  - wariant HIP istnieje wyłącznie dla MXFP4 na gfx950 (`quantize/mxfp.py:198-224`);
  - BitNet int2×int8 decode (`examples/bitnet-1.58b/kernel_benchmark/tilelang_bitnet_158_int8xint2_decode.py:109-150`) ma tę samą strukturę: warp na wiersz + dp4a. To jest MMVQ z ggml w innej składni.
- **Brak formatów GGUF/K-quant.** Grep `gguf|ggml|q4_k` daje zero trafień. Super-bloki z 6-bitowymi skalami (Q4_K/Q5_K) i siatki IQ trzeba by pisać od zera w DSL.
- **Inne przykłady:**
  - GEMV fp16 (`examples/gemv/example_gemv.py`, splitk + autotune);
  - fused MoE fp16 jako grouped GEMM dla prefillu, routing w torch (`examples/fusedmoe/example_fusedmoe_tilelang.py:92-193`);
  - GQA flash-decoding z pakowaniem głów Q w wymiar M i split-KV + combine (`examples/flash_decoding/example_gqa_decode.py:50-160`). To ta sama idea co nasz `fattn-kvq`, ale z KV f16;
  - chunked GDN (WY, port FLA) tylko pod CUDA (`examples/gdn/`, `test_example_gdn_compilation.py:282 requires_cuda`).
- **Autotuner** (`tilelang/autotuner/tuner.py`, `tilelang/profiler/bench.py`):
  - przestrzeń konfiguracji, opcjonalna weryfikacja każdej konfiguracji względem `ref_prog` z `atol` (`tuner.py:238-310`);
  - cache wyników na dysku, równoległa kompilacja na CPU, „grouped compile”, czyli wiele konfiguracji w jednym module (`autotuner/grouped_compile.py`, PR #2159);
  - flush L2 buforem 256 MB przed każdym pomiarem (`bench.py:72, 210-214`), co jest więcej niż nasze 96 MB MALL.
  - Roller/carver to analityczny model ruchu (transakcje 32/128 B), który podpowiada kafle. Dla RDNA ma tabelę per mcpu, ale z wpisem tylko dla gfx1151 (`tilelang/carver/arch/rdna.py:34-47`); `bandwidth=[750, 12080]` to stała (`rdna.py:93`).
- **Liczby na naszej karcie (pomiar autora PR #2208, lhl):** GEMM f16 4096³ przez Roller na RX 7900 XTX daje **75.1 TFLOPS / 1.83 ms**. Autor dodaje, że to „typowo mniej niż PyTorch (hipBLASLt) i rocWMMA”. Innych liczb dla gfx1100 w repo/PR nie znalazłem.
- **Ścieżka kompilacji HIP i integracja:**
  - `hipcc -O3 -c --genco --offload-arch=<mcpu> -gline-tables-only` + remark zużycia VGPR (`tilelang/contrib/hipcc.py:77-96`);
  - kernele `extern "C" __global__` (`codegen_hip.cc:355`);
  - źródło dostępne przez `kernel.get_kernel_source()` / `export_sources()` (`tilelang/jit/kernel.py:562, 622`);
  - nagłówki `tl_templates/hip/*` dołączane w preambule (`codegen_hip.cc:426-432`); `common.h` ciągnie `rocwmma.hpp` (jest w `/opt/rocm/core-10.0/include/rocwmma`) i definiuje makra `uint`/`uchar` (`common.h:8, 22-24`).

## 3. Przeniesienie na AMD/HIP/RDNA3
| Technika | Czy się przenosi / co już mamy |
|---|---|
| WMMA f16 16×16×16 + układy gfx11 | Działa na gfx1100, ale mamy to ręcznie w `fattn-kvq.cu` (z `permlanex16` dla zduplikowanej połowy fali, `fattn-kvq.cu:20, 88`) i w K4. Brak iu8 WMMA wyklucza ścieżkę MMQ/K4 w TileLang. |
| Dequant przez magiczną liczbę (LOP3 + sub.f16x2) | Odpowiednik AMD to `v_perm_b32`/`v_and_or_b32` + `v_pk_add_f16`. **Już zrobione** w kvq: `__builtin_amdgcn_perm(0x64646464, x, sel)` i odjęcie 1152 (`~/llama-master/ggml/src/ggml-cuda/fattn-kvq.cu:145-147, 306`). |
| GEMV warp-na-wiersz + dp4a (BitBLAS/BitNet) | To jest MMVQ z ggml. Nasze MMVQ ma więcej: buffer loads w SGPR, GLC/DLC, waves_per_eu, DPP, multi-column. TileLang nie wyraża tych pokręteł (sekcja 2), więc wygenerowany kernel byłby co najwyżej równy upstreamowemu MMVQ. `[WNIOSEK]` |
| Pipelining/async copy | Na RDNA3 brak sprzętowego bufor→LDS, więc w TileLang to no-op. Ręcznie: loady przed obliczeniami/rejestrowy double-buffer (już w planach K5/Strata #2017). |
| Redukcje `__shfl_xor` | U nas DPP/`ds_swizzle` (K2: norm 5.87→4.51 µs, argmax 16.8→4.3 µs). TileLang jest tu w tyle. |
| GQA flash-decoding (głowy Q w M, split-KV) | Ten sam pomysł co `fattn-kvq` (q4_0). Wersja TileLang czyta f16 KV, więc dla nas nic nowego. |
| Chunked GDN (WY) | Przenośne, ale na gfx1100 udokumentowane jako strata: Strata #888 −39% e2e (rocWMMA); #2299 na gfx1151 +1.4–2.1% promptu; GDN to ~7.4% prefillu 128K (`research/strata/prefill.md:173-175`). Nasz GDN jest szeregowy (`gated_delta_net.cu:161, 377`). |
| Autotuner (ref-check per config, flush > MALL, cache) | Metodologia zgodna z naszym `mmvq-bench` (wagi > 96 MB) i weryfikacją bitową. Nic nowego. |
| Integracja wygenerowanego HIP | Technicznie prosta: osobna jednostka `.cu` tylko dla HIP z dołączonymi `tl_templates/hip` (MIT), zmiana nazw `extern "C"`, launcher na strumieniu ggml, kształty statyczne per instancja. Koszty: makra w `common.h` (osobny TU), dodatkowa zależność od rocWMMA, brak kontroli waves_per_eu/GLC, **inne bity niż ścieżki ggml** (łamie naszą politykę „bitowo identyczne”). Utrzymanie przy 54 łatkach: kod generowany, nieczytelny, regenerowany poza drzewem. |

## 4. Pomysły dla nas
1. **Pomiar sufitu f16 WMMA na kształtach prefillu (narzędzie decyzyjne, nie zmiana w kodzie).**
   - Co: w osobnym venv (torch ROCm + wheel tilelang) puścić `benchmark/matmul/benchmark_matmul.py --with_roller` i autotune `T.gemm` f16 dla M=512 (ubatch) oraz N×K Qwena: ffn up/gate 17408×5120, down 5120×17408, ssm_out/attn_out 5120×6144, qkv. Porównać z rocprof MMQ (~50 TFLOPS).
   - Po co: rozstrzyga, czy warto robić F16-WMMA z dekwantyzacją w LDS (Strata #2020) zamiast MMQ iu8. Na gfx1100 f16 i iu8 mają ten sam szczyt, więc różnicę robi tylko koszt dekwantyzacji i LDS. Jeśli sam rdzeń f16 przy M=512 nie przekracza ~60 TFLOPS, wersja z dekwantyzacją nie pobije MMQ i #2020 można odłożyć. `[SZACUNEK]` Punkt odniesienia: 75 TFLOPS przy 4096³ (lhl, PR #2208); przy M=512 spodziewam się mniej.
   - Zysk bezpośredni: 0. Pośredni: unika się 1–3 dni pracy w złą stronę.
   - Koszt: ~0.5 dnia. Ryzyko: wheel budowany pod ROCm 7.x może nie wstać na ROCm 10.0 (runtime/tvm-ffi); kernel kompiluje lokalny hipcc, więc szanse są realne. `[WNIOSEK]`
   - Wymaga GPU (nie ja, decyzja Main). Wynik niczego nie zmienia w modelu, służy tylko do decyzji.
   - Uwaga: osobny wynik negatywny „dequant + hipBLAS dla wszystkich typów: −15%” (NOTES:324) już zamyka ścieżkę f16 *bez fuzji*.
2. **Instancja q8_0 w `fattn-kvq` (otwarte z `lfm-decode-round2.md` §4) z trikiem magicznej liczby dla int8.**
   - Co: dla q8_0 bajt b (int8) → `0x6400 | (b ^ 0x80)` przez `__builtin_amdgcn_perm` + `v_pk_add_f16(-1152)`. Wynik jest dokładny (1024 + b + 128 − 1152 = b), tak jak istniejące 1152 dla q4_0 (`fattn-kvq.cu:145`). Linia BitBLAS (`lop3.py:21-24`) potwierdza, że to najtańsza konwersja int→f16 (2 instrukcje na 2 wartości).
   - Zysk: przy 98k kontekstu −1.1 ms/token na LFM (+19% t/s), szacunek własny z round2. Ten trik tylko utrzymuje dekwantyzację K poza ścieżką krytyczną. `[SZACUNEK]`
   - Koszt: 0.5–1 dnia. Ryzyko: numeryka inna niż `flash_attn_ext_vec` (nie bitowo). Pomiar: `llama-bench -d 98304`, `test-backend-ops FLASH_ATTN_EXT`.
   - To nie jest pomysł z TileLang, tylko potwierdzenie techniki. TileLang nie pomoże tego napisać lepiej niż ręcznie.
3. **Outside the box: „grouped compile” jako sposób na szybsze sweepy makr.**
   - TileLang kompiluje wiele konfiguracji do jednego modułu i wybiera kernel w runtime (PR #2159). Nasz `e2e_exp.sh` przebudowuje cały llama.cpp na wariant.
   - Dla przyszłych sweepów (np. RPB/NI/waves_per_eu w MMVQ, kafle MMQ) lepiej zinstancjonować N wariantów szablonu w jednym buildzie i wybierać je zmienną `GGML_HIP_*_VARIANT=k` przy starcie. Jeden build zamiast N.
   - Zysk: czas iteracji, nie t/s. Koszt: niski. Ryzyko: rozrost binarki (tylko w gałęzi eksperymentalnej).
4. **Nie robić:**
   - generowania MMVQ/MoE decode przez TileLang: brak K-quantów, brak naszych pokręteł RDNA3, a LFM jest ograniczony liczbą uruchomień kerneli (416 × ~2.5 µs), czego generator pojedynczych kerneli nie rusza;
   - FA prefill przez TileLang: bloki 32×32 na RDNA wobec naszych 49–52 TFLOPS;
   - chunked GDN z `examples/gdn`: wynik negatywny na gfx1100 (Strata #888, #2299).

## 5. Krytyka
- „Supported” dla RDNA w README (`README.md:124`) jest na wyrost:
  - CI tylko na gfx942;
  - walidacja gfx11 to zrzuty ekranu przykładów;
  - otwarta lista kandydatów na błędy HIP, w tym ciche gubienie kolumn wyjścia WMMA przy `N/n_warp` niepodzielnym przez 16 (issue #2645, B1).
- WMMA na RDNA tylko f16. Ścieżka bf16 dla gfx11 jest prawdopodobnie zepsuta w codegenie: rzutowanie operandów zawsze na wektory `__fp16` (`codegen_hip.cc:1884-1913`), a builtin bf16 na gfx11 przyjmuje v16i16. Carver i tak dopuszcza tylko f16. `[WNIOSEK]`
- Przykład FA na RDNA to tryb „żeby działało”: 32×32, bez k_pack=2, bez pipeliningu. Nie ma liczb.
- Wykresy wydajności w README (GEMM na 4090/A100/H100/MI300X, dequant GEMV na A100) nic nie mówią o RDNA3. Jedyna liczba dla 7900 XTX (75 TFLOPS, 4096³) pochodzi od kontrybutora i według niego jest poniżej hipBLASLt.
- Szybki dequant BitBLAS to wstawki PTX. Na AMD zostaje wolna ścieżka skalarna (`_tir_packed_int_to_int_convert`) albo własny kod HIP.
- Narzut środowiska: TVM, Python, torch ROCm i JIT przy każdym nowym kształcie. Dla llama.cpp przydatne wyłącznie offline (eksport źródła).

## 6. Werdykt
**Niska.** Backend RDNA3 to niedojrzałe f16-WMMA bez iu8, bez async copy i bez pokręteł, które dały nam zyski (buffer loads/GLC/DLC, waves_per_eu, DPP). Nie zna formatów GGUF. Jego kernele GEMV/MoE/FA to podręcznikowe wersje tego, co mamy już ręcznie strojone. Jedyny realny użytek to offline pomiar sufitu f16 WMMA dla decyzji o ścieżce prefillu.
