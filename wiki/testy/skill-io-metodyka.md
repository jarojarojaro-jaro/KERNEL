---
typ: test
tags: [testy, pomiar, szum, spekulacja, skill-io]
aktualizacja: 2026-11-17
zrodlo: ~/kernel/zrodla/inference-optimisation-skill @ fda968e — references/methodology.md:1-55, SKILL.md:78-101 (zasady 1–10), README.md:130-143
status: aktualne
---
# Metodyka pomiaru wg skill-io (methodology.md + zasady SKILL.md) a nasza praktyka

**„Większość wygranych i regresji w strojeniu inferencji to błędy pomiaru” (`methodology.md:3`). Stosujemy prawie całą tę metodykę; braki to bramka igieł i flaga zapętlenia w harnessie. Ich szum ±5–10% (laptopy) to nie nasz przypadek: na XTX w eco 2200 mamy 0,02–0,33% ([[xtxbench-szybki-ab]]).**

| reguła (źródło) | treść | u nas |
|---|---|---|
| liczenie tokenów (`:7`) | z usage serwera albo tokenizera, nie z kawałków strumienia; przy MTP kawałek = kilka tokenów | tak: `spec_sweep` i harnessy biorą `timings` serwera ([[spec-sweep]]) |
| rozmiar promptu (`:8`) | tokenizerem; „32K” z losowych słów to było 58K | tak: xtxbench tnie korpus tokenizerem |
| prompt przed zegarem, unikalny (`:9`) | losowy prefiks, by nie trafić w cache | tak: `cache_prompt=false`, xtxbench `erase` |
| dekod t/s (`:10`) | (tokeny − 1) ÷ czas od pierwszego tokena | liczymy z czasu serwera (`predicted_ms`) |
| prefill (`:11`) | prompt ÷ TTFT na zimno; cache-hit raportować osobno | tak; fill 255k osobno od `pp` |
| cN (`:12`) | tokeny ÷ ściana od pierwszego startu do ostatniego końca | nie dotyczy produkcji (1 slot) |
| szum (`:16-21`) | ≥ 6 próbek, mediana, stały zestaw promptów; losowe prompty zmieniały akceptację 2,4 → 3,7 | tak: 6 promptów × seedy, mediana ([[pomiar-abba]]) |
| przeplot (`:22`) | kontrola, kandydat, kontrola; dryf 53,8 → 49,5 w godzinę | tak: A B B A, A/A kalibracja szumu |
| porównanie silników (`:23`) | bootstrap 95% CI mediana(B)/mediana(A) > 1 | **brak** (mamy Wilson tylko dla jakości) |
| odrzucać zimne pierwsze runy (`:24`) | JIT/cache (36 vs 90 t/s) | tak: rozgrzewka w harnessach |
| spekulacja (`:29-33`) | t/s = a ÷ czas kroku; wyższa akceptacja może być wolniejsza (3,26 vs 2,85, −11…14%); rozjazd greedy przy innych M to numeryka, nie błąd | tak: raportujemy tok/krok i ms/krok; [[2026-11-14-k001-wyciek-stanu-restore]] |
| długi kontekst (`:37-38`) | osobny run; **3 igły** na różnych głębokościach, odpowiedź dokładna | **tak od 2026-11-19**: 3 igły przy 130k i 222k, 3/3 ([[2026-11-19-k109-k110-k106-xtx]]) |
| zdrowie wyjścia (`:42`) | flagować pętle, błędy, bezczynne GPU; „rekord 117 t/s” był pętlą listy | **częściowo**: pętlę wykryliśmy ręcznie (MMLU-Pro 32 768 tok.) |
| pamięć (`:46-48`) | na pamięci zunifikowanej `drm-resident-*` + anon | XTX dyskretny: `mem_info_vram_used`; fdinfo w K-011 |
| profilowanie (`:52-55`) | graf wyłączony do rozbicia na kernele; czytać ISA | tak: rocprofv3 przy PM4=0, `isa.sh` |

**Zasady twarde SKILL.md** (`:78-101`):
1. Jedna zmiana na eksperyment.
2. Przeplot kontroli i przyjęcie tylko, gdy kandydat bije obie sąsiednie kontrole, a nic nie traci > 3%.
3. Stałe środowisko.
4. Jedno zadanie GPU naraz.
5. Watchdog pamięci.
6. Bramki stabilności: igły 50% i 100% kontekstu, soak, greedy-ekwiwalencja.
7. Nie zabijać serwera w trakcie batcha: „wymuszony stop w prefillu wywołał fault sterownika”.
8. Sprawdzać wyjście, nie tylko prędkość.
9. Logować porażki.
10. Sekrety.

Wszystkie mamy (kolejka, `gpu-guard`, jeden SIGTERM, [[lekcja-pm4-zamienia-fault-w-reset]]) poza bramką igieł z punktu 6.

## Ta sama metodyka na AMD i NVIDIA (2026-11-17)

| krok | AMD (ROCm) | NVIDIA (CUDA) |
|---|---|---|
| pasmo (`ceilings.md:3`) | `hipMemcpy` D2D / `rocm-bandwidth-test` | `nvbandwidth` / `cudaMemcpy` D2D |
| szczyt GEMM | `rocblas-bench` / `hipblaslt-bench` f16 i i8, 4096³ + 8192³ | `cublasLt` matmul (f16, i8), te same rozmiary |
| profil kerneli (`methodology.md:52`) | `rocprofv3` (PM4=0, potem czas taśmy) | `nsys` + `ncu` (grafy CUDA wyłączone do rozbicia) |
| stan środowiska (zasada 3) | `rocm-smi`: sclk eco 2200, temperatury, `gpu-guard` | `nvidia-smi -q -d POWER,CLOCK`: zapisać limit mocy hosta i zegary |
| pamięć | `mem_info_vram_used` | `nvidia-smi --query-compute-apps` (jak `mem.sh`) |
| przeplot | ABBA na tej samej karcie | ABBA na **tym samym hoście Vast** (hosty różnią się limitem mocy i CPU) |
| harness | `spec_sweep`, xtxbench, `bench.py` | te same skrypty (OpenAI API), bez zmian |

**Ewaluator przy pracy autonomicznej agenta** (z [[megakernel-zoo]]): odniesienie wysokiej precyzji z tolerancją kalibrowaną na zwykłej implementacji, ukryty zbiór promptów (agent zna tylko zdał/nie zdał), logity z przebiegu pomiarowego sprawdzane po fakcie, odwrócona kolejność batcha = bitowo, audyt kodu drugim agentem, naturalny tekst do pomiaru prędkości (pętle powtórzeń fałszują t/s).

**Czas optymalizacji jako metryka** (właściciel 2026-11-18, [[lekcja-czas-optymalizacji-to-metryka]]): każda kampania zapisuje znaczniki etapów (`phases.txt`), a raport podaje ścianę, czas GPU i najwolniejszy etap.

**Reguła:** liczba z NVIDIA i liczba z XTX trafiają do jednej tabeli tylko wtedy, gdy pochodzą z tego samego harnessu, panelu promptów, temperatury i głębokości draftu. Przy każdej podajemy % sufitu karty.

**Pozostałe firmy:**
- **Apple:**
  - pasmo: STREAM na GPU (Metal) albo `mlx` benchmark kopii;
  - GEMM: `mx.matmul` f16 4096³;
  - profil: Xcode Instruments / Metal System Trace;
  - pamięć: `vm_stat`, limit `iogpu.wired_limit_mb`;
  - stan: zasilanie sieciowe (`pmset -g batt`, jak `on_ac()` w `bench.py`).
- **Intel:**
  - pasmo i GEMM: `sycl` stream / oneMKL GEMM, `xpu-smi`;
  - profil: VTune / `unitrace`;
  - pamięć iGPU: `drm-resident-*` (jak `mem.sh unified`).
- **Tenstorrent:**
  - `tt-smi` (zegary, temperatura, DRAM);
  - profil: Tracy + profiler urządzenia TT-Metalium;
  - pasmo i GEMM: testy TT-NN (`ttnn.matmul`).
- Harness OpenAI (`bench.py`, `spec_sweep`) działa bez zmian wszędzie tam, gdzie jest serwer zgodny z OpenAI: llama-server, MLX-LM server, fork vLLM Tenstorrent.

## Powiązane
- [[skill-io-przeglad]]
- [[pomiar-abba]]
- [[xtxbench-szybki-ab]]
- [[spec-sweep]]
