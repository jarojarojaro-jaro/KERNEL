# Plan pracy: RX 7900 XTX (główna karta) + RTX 5060 Ti 16 GB (pomocnicza)

Stan wiedzy: październik 2026. Źródła szczegółowe: `reports/Optymalizacja kerneli na AMD.md` i `research_notes/Optymalizacja kerneli na AMD/`.
Liczby oznaczone *(wyliczone)* to moja arytmetyka, a nie dane producenta. *(do weryfikacji)* = wiedza tła, niesprawdzona w źródłach.

## 1. RX 7900 XTX w liczbach, które mają znaczenie dla kerneli

| Parametr | Wartość | Co z tego wynika |
|---|---|---|
| Target | **gfx1100** (Navi31, RDNA3) | Kompiluj zawsze na `gfx1100`, nie na `gfx11-generic` (generic nie pozwala użyć wszystkich VGPR) |
| CU / WGP | 96 CU = 48 WGP, każde CU = 2× SIMD32 | ~96 bloków to minimum, żeby zapełnić GPU (lekcja split-K z auto-gpu-kernel) |
| Fala | natywnie **wave32**, wave64 opcjonalnie | wave32 dla GEMV/decode; wave64 testować dla kodu ograniczonego VALU (dual-issue „za darmo”) |
| Rejestry | 192 KiB/SIMD = 1536 VGPR na lane (wave32) | ≤96 VGPR → 16 fal/SIMD, 128 → 12, 256 → 6 *(wyliczone)* |
| LDS | 128 KiB na WGP (64 KiB na workgroup w praktyce, jak w Stracie) | |
| Cache | L2 6 MiB, Infinity Cache 96 MiB | IC pomaga dla KV cache przy krótkim kontekście; wagi i tak lecą z VRAM |
| VRAM | 24 GB GDDR6, 384-bit, **960 GB/s** *(do weryfikacji, standardowa wartość)* | **sufit decode** |
| Macierze | WMMA 16×16×16: FP16/BF16/INT8 ~123 TFLOPS/TOPS, INT4 ~246 *(wyliczone)* | WMMA na RDNA3 **nie jest osobnym tensor core'em** – ta sama przepustowość co VALU dual-issue; dane A/B trzeba duplikować między połówkami fali |
| Brak | FP8, FP4, sparsity | FP8/MXFP4 tylko jako oszczędność pamięci (dekwantyzacja do FP16) |
| Instrukcje decode | `v_dot4_i32_iu8` (`__builtin_amdgcn_sudot4`), `v_dot2_f32_f16`, DPP, `v_perm_b32` | rdzeń kwantyzowanego GEMV |

### Sufit generowania tokenów: tok/s ≤ 960 GB/s ÷ bajty wag czytane na token

| Model (przykład) | Rozmiar wag | Sufit teoretyczny | Realnie (~75% pasma) |
|---|---|---|---|
| Llama 2 7B Q4_0 (benchmark referencyjny) | 3,83 GB | ~250 tok/s | **zmierzone: 191 (Vulkan+FA), 170 (ROCm+FA)** |
| gęsty 14B Q4_K_M | ~9 GB | ~107 | ~80 |
| gęsty 27–32B Q4_K_M | ~17–20 GB | ~48–56 | ~36–42 |
| MoE 30B-A3B Q4_K_M | ~2 GB aktywnych/token | wysoki | MoE osiąga gorszy % pasma (56–61% na R9700) – **zmierzyć** |
| gęsty 70B Q4 | ~40 GB | nie mieści się w 24 GB | tylko z drugą kartą lub offloadem |

Dane referencyjne dla 7900 XTX (llama.cpp, Llama 2 7B Q4_0):
- Vulkan RADV: pp512 3727 → **3890** z FA, tg128 182,6 → **190,9** z FA (~76% pasma) – [#10879](https://github.com/ggml-org/llama.cpp/discussions/10879)
- ROCm: pp512 3552 → 3874 z FA, tg128 167,1 → 170,1 (~68% pasma)
- **Otwarty problem [#20934](https://github.com/ggml-org/llama.cpp/issues/20934)** (marzec 2026): na 7900 XTX ROCm generuje o 15–25% wolniej niż Vulkan, „bursty GPU utilization”, przyczyna nieznana. **To kandydat na nasz pierwszy realny wkład.**

## 2. Rola RTX 5060 Ti 16 GB

Parametry *(do weryfikacji)*: Blackwell GB206, sm_120, 16 GB GDDR7 128-bit, ~448 GB/s (czyli ~2× wolniej niż XTX przy decode), tensor core'y 5. gen. z FP8 i FP4.

Do czego się przyda:
1. **Referencja CUDA.** Większość tutoriali, paperów i kerneli (FlashAttention, Triton, konkursy) powstaje pod CUDA. Ten sam kernel w CUDA i HIP → uczymy się różnic (warp 32 vs wave32/64, tensor core vs WMMA, cp.async/TMA vs brak async copy na RDNA3).
2. **Formaty, których XTX nie ma:** FP8 i FP4 (NVFP4/MXFP4) sprzętowo – do nauki kwantyzacji niskobitowej.
3. **Więcej pamięci dla dużych modeli:** 24 + 16 = 40 GB. Backend Vulkan w llama.cpp widzi obie karty (AMD i NVIDIA) w jednym procesie i umie dzielić warstwy. Koszt: warstwy na 5060 Ti czytają się ~2× wolniej. Opłaca się tylko, gdy model nie mieści się w 24 GB. *(do przetestowania; alternatywa: osobne backendy CUDA+HIP lub `llama-rpc`)*
4. **Speculative decoding:** mały model-draft na 5060 Ti, duży model na XTX (`llama-server` ma osobne urządzenie dla draftu, `--device-draft`) *(do przetestowania)*.

**Uwaga przy pomiarach:** Vulkan widzi obie karty – przy benchmarkach Radeona izoluj go: `GGML_VK_VISIBLE_DEVICES=<indeks>` (indeks sprawdzisz w logu startowym `ggml_vulkan: Found N Vulkan devices`).

## 3. Etap 0 – baseline (zanim cokolwiek optymalizujemy)

Cel: wiedzieć, ile **Twoja** karta robi dziś, w obu backendach, i ile to procent pasma. Każdy wynik zapisujemy z: datą, commitem llama.cpp, wersją Mesa / ROCm, wersją jądra, sterownikiem.

```bash
git clone https://github.com/ggml-org/llama.cpp && cd llama.cpp

# Vulkan (RADV) – potrzebny aktualny Vulkan SDK / glslc (stary glslc = poważne regresje)
cmake -B build-vk -DGGML_VULKAN=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build-vk -j

# ROCm/HIP – tylko gfx1100
HIPCXX="$(hipconfig -l)/clang" HIP_PATH="$(hipconfig -R)" \
  cmake -B build-hip -DGGML_HIP=ON -DGPU_TARGETS=gfx1100 -DCMAKE_BUILD_TYPE=Release
cmake --build build-hip -j

# (opcjonalnie) wariant z rocWMMA flash attention – na RDNA3 raportowany jako pomocny
HIPCXX="$(hipconfig -l)/clang" HIP_PATH="$(hipconfig -R)" \
  cmake -B build-hip-wmma -DGGML_HIP=ON -DGPU_TARGETS=gfx1100 -DGGML_HIP_ROCWMMA_FATTN=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build-hip-wmma -j
```

Pomiar (ten sam model, te same parametry, 5 powtórzeń):

```bash
M=llama-2-7b.Q4_0.gguf   # do porównania ze scoreboardem
GGML_VK_VISIBLE_DEVICES=0 ./build-vk/bin/llama-bench -m $M -ngl 99 -fa 0,1 -p 512 -n 128 -r 5 -o md
./build-hip/bin/llama-bench -m $M -ngl 99 -fa 0,1 -p 512 -n 128 -r 5 -o md
ROCBLAS_USE_HIPBLASLT=1 ./build-hip/bin/llama-bench -m $M -ngl 99 -fa 1 -p 512 -n 128 -r 5 -o md
```

Potem to samo dla modeli, których faktycznie używasz (np. MoE 30B-A3B i gęsty ~27–32B), plus test długiego kontekstu (`-p 8192`, `-d 16384`).

Liczymy: **% pasma = tg × rozmiar_pliku_GB ÷ 960**. Cel referencyjny: ~76% (Vulkan) na 7B Q4_0.

Ustawienia systemu do sprawdzenia: Resizable BAR włączony, DPM na `auto` (nie `high`), aktualna Mesa (RADV), ROCm 10.x (gfx1100 jest oficjalnie wspierany – **bez** `HSA_OVERRIDE_GFX_VERSION`).

## 4. Ścieżka nauki na tej karcie

| # | Projekt | Czego uczy | Miara sukcesu |
|---|---|---|---|
| 1 | Mikrobenchmark pasma w HIP (kernel czytający duży bufor, `float4`/`dwordx4`) | realny sufit karty, coalescing, occupancy | % z 960 GB/s – to nasz prawdziwy sufit |
| 2 | Własny GEMV Q8_0, potem Q4_0 w HIP (wave32, `sudot4`, redukcja przez DPP) | sedno decode; czytanie ISA (`--save-temps`) | >75% pasma; porównanie z `mmvq` z llama.cpp |
| 3 | Ten sam GEMV w CUDA na 5060 Ti | różnice AMD vs NVIDIA | % pasma na obu kartach |
| 4 | GEMM FP16 na WMMA (`__builtin_amdgcn_wmma_f32_16x16x16_f16_w32`) | prefill, duplikacja A/B na RDNA3, LDS | % z ~123 TFLOPS; porównanie z hipBLASLt |
| 5 | Shadery Vulkan w llama.cpp: `GGML_VK_PIPELINE_STATS`, `GGML_VK_PERF_LOGGER`, sweep parametrów tile'i dla gfx1100 | jak naprawdę wygląda kernel produkcyjny | zmierzony zysk na XTX |
| 6 | Zbadać #20934 (ROCm wolniejszy od Vulkana w decode) – `rocprofv3`, porównanie czasów per kernel | profilowanie, prawdziwy problem | diagnoza / PR |
| 7 | Split-K flash-decoding w Tritonie na gfx1100 + pętla A/B w stylu auto-gpu-kernel | attention, metodologia | latencja vs FA w llama.cpp |
| 8 | Strata na XTX (gfx1100 to cel walidowany; tabele hipBLASLt dały 926 → 1687 tok/s prefill przy 131K) | rozmieszczenie danych GPU/RAM/SSD, MoE | wymaga dużo RAM – zależy od Twojego PC |

Zasady z auto-gpu-kernel obowiązują od pierwszego dnia: **tylko absolutne czasy, jedna zmiana naraz, A/B na tej samej maszynie przy różnicach <5%, logujemy też porażki.**

## 5. Otwarte pytania (do uzupełnienia)
- [ ] System: Linux (która dystrybucja / jądro / Mesa) czy Windows?
- [ ] RAM i CPU (ważne dla offloadu MoE i Straty)
- [ ] Jakich modeli używasz na co dzień?
- [ ] Wyniki Etapu 0
