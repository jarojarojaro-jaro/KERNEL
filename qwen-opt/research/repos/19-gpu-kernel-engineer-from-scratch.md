# 19 — vukrosic/gpu-kernel-engineer-from-scratch

Repo: https://github.com/vukrosic/gpu-kernel-engineer-from-scratch (HEAD `ba738db`, 2026-05-07). Wideo: https://youtu.be/F5v_7OCwKHs

## 1. Co to jest

Kurs na 48 tygodni („12-month CUDA, Triton, and AI systems course”, `README.md:1-4`) dla osób, które znają Pythona, ale nie znają kerneli GPU (`README.md:39-44`). Zawartość:
- 48 lekcji w `weeks/` (ok. 15.7 tys. linii markdownu, w większości opisy pojęć);
- 5 zabawkowych kerneli CUDA w `cuda/` (vector_add, reduce_sum, softmax, layernorm, naive_matmul, po 65–110 linii);
- 5 kerneli Tritona w `triton_kernels/`;
- puste szablony w `results/`: każdy plik to tylko nagłówki „Summarize…”/„Record…”, np. `results/benchmark-dashboard.md:1-20`, `results/week-12-warp-level-reductions.md`.

Stan repo:
- **Brak jakichkolwiek pomiarów** i brak licencji (GitHub API: `license: null`). 73 gwiazdki, 26 forków.
- Utworzone 2026-05-01, ostatni push 2026-05-07, potem martwe.
- README odsyła do katalogów, których nie ma: `course/`, `FINISH_PLAN.md`, `creator/`, `bonus/` (`README.md:18-20, 192, 204-206`).
- Sprzęt: tylko ogólnie „CUDA GPU”. Ani słowa o AMD, HIP ani wave64.
- Testy (`tests/test_gpu_tracks.py`) sprawdzają tylko referencje NumPy i to, czy da się zaimportować moduły bez GPU.

## 2. Kluczowe techniki (z dowodami)

Wszystko to podstawy, które już stosujemy w ostrzejszej formie. Nie ma żadnej liczby do zacytowania: repo nie podaje własnych pomiarów, a cudzych też nie przytacza.

| # | Temat | Dowód | Poziom |
|---|---|---|---|
| T1 | Redukcja w bloku przez shared memory, drzewo `stride/=2` z `__syncthreads` na każdym kroku | `cuda/reduce_sum.cu:32`, `cuda/softmax.cu:19-38`, `cuda/layernorm.cu:18` | podręcznikowy wariant (Harris, krok ~3), bez warp-shuffle |
| T2 | Redukcja wielopoziomowa: osobne uruchomienie na każdy poziom, `cudaDeviceSynchronize` po każdym | `cuda/reduce_sum.cu:65-71` | antywzorzec przy kosztach uruchomień |
| T3 | Warp-reduce `__shfl_down_sync(0xffffffff, v, 16..1)`, `lane = threadIdx.x % 32` | `weeks/week-12-warp-level-reductions.md:221-227, 250, 303-305` | zakłada warp 32 |
| T4 | Softmax/LayerNorm wierszowe: 3 przejścia po globalnym wejściu (max, sum, zapis), `expf` liczone 2× | `cuda/softmax.cu:52-63`, `cuda/layernorm.cu:39-57` | wersja naiwna, sam autor pisze, że „prawdziwe kernele używają shuffle, wektorowych odczytów…” (`weeks/week-18-fused-row-wise-softmax.md:206-209`) |
| T5 | Triton: cały wiersz w jednym programie, `cols ≤ 1024`, `num_warps=4` | `triton_kernels/softmax.py:26-54`, `triton_kernels/layernorm.py:26-54` | starter |
| T6 | Atomiki: prywatyzacja histogramu (najpierw lokalnie, potem globalnie) | `weeks/week-14-atomics-and-contention.md:240-271` | koncepcja bez kodu |
| T7 | Obłożenie kontra rejestry/LDS/kafel, „bigger is not always better” | `weeks/week-24-occupancy-registers-and-tile-size.md:34-130, 190` | koncepcja |
| T8 | Pokrętła Tritona: BLOCK_M/N/K, num_warps, num_stages, autotune | `weeks/week-30-triton-matmul-performance-knobs.md:19-116`; `triton_kernels/matmul.py` (64×64×16, fp32) | koncepcja |
| T9 | Fuzja residual+norm, „nie wypisuj tmp do pamięci globalnej” | `weeks/week-38-residual-and-norm-fusion.md:84-160` | koncepcja |
| T10 | Online softmax (m, l, o) i kafle FlashAttention | `weeks/week-42-flashattention-concepts.md:63-110` | opis, bez kernela i bez split-K/combine |
| T11 | KV cache, decode jednego tokena, „wąskim gardłem jest czytanie rosnącej historii” | `weeks/week-43-kv-cache.md:77-160` | referencja w PyTorch, bez GQA, kwantyzacji i stronicowania |
| T12 | Higiena pomiaru: synchronizacja, eventy, rozgrzewka, mediana, efekty cache | `weeks/week-07-timing-harness-and-benchmarking.md:22-177` | podstawy |

Tematów kwantyzowanego matmul, int8/dp4a, tensor cores/MMA, CUDA graphs, kerneli trwałych, split-K, GQA i decode-attention w repo nie ma. Grep po `weeks/` znajduje jedynie wzmianki („Real kernels add… tensor cores”, `weeks/week-22-tiled-matmul.md:203`; „Is launch overhead dominating?”, `weeks/week-32-profiling-gpu-kernels.md:111`).

## 3. Przeniesienie na AMD/HIP/RDNA3

- **T1/T4 (redukcje w LDS):** przenoszą się 1:1, ale na RDNA3 robimy to lepiej. Redukcje mamy na DPP/butterfly (rms_norm 5.87 → 4.51 µs, argmax 16.8 → 4.3 µs; `NOTES.md:261-262`). Drzewo z `__syncthreads` na każdym kroku to krok wstecz.
- **T2 (wielopoziomowa redukcja z synchronizacją hosta):** nie przenosić. Mamy zmierzone, że granica kernela w grafie HIP kosztuje ~2.53 µs, a ogon „ostatni blok” ~1 µs (`research/lfm-decode-round2.md:23-41`). Właściwy wariant to ticket / last-block, który już stosujemy (0053 NORM_ROUTER, 0054 INPROJ_CONV).
- **T3 (shuffle):** na HIP `__shfl_down_sync` działa, tylko maska jest 64-bitowa. Kod z `lane = threadIdx.x % 32` i stałymi offsetami 16..1 jest poprawny tylko przy wave32. Przy kompilacji wave64 (np. gdy `waves_per_eu` albo wybór kompilatora wymusi wave64) policzy źle po cichu. Odpowiedniki na RDNA3: `__builtin_amdgcn_mov_dpp` / `ds_swizzle` / `permlanex16`. Już ich używamy.
- **T5/T8 (Triton):** Triton na ROCm istnieje, ale nasz stos to ggml-cuda/HIP. Wiedza o pokrętłach (num_warps/stages) odpowiada naszemu strojeniu `waves_per_eu`/RPB/NI, które zrobiliśmy na pomiarach (`NOTES.md:103, 241-256`).
- **T6–T12:** czysta koncepcja, nic do przeniesienia ponad to, co już mamy (fuzje A3–A6, kvq FA, grafy HIP, A/B z przeplotem + hash logitów).

## 4. Pomysły dla nas

Repo nie daje **żadnego nowego eksperymentu**. Każdy temat z kursu, który dotyka naszych wąskich gardeł, mamy już zrobiony albo zapisany w backlogu z własnymi szacunkami. Dla porządku mapowanie:

| Temat kursu | Nasz stan | Co zostało (z naszych notatek, nie z repo) |
|---|---|---|
| T9 fuzja residual+norm | A3 epilog residual, 0051 MoE down+reduce+res, A6 producenci q8_1 | down+reduce+res liczące attn_norm następnej warstwy jako ogon ticketu: −40 uruchomień, ~0.12 ms/token (`lfm-decode-round2.md:105-106`) |
| T10/T11 FA/KV decode | kvq FA (q4_0, wszystkie głowy Q grupy GQA w jednym przejściu) | instancja q8_0 kvq dla LFM: ~−1.1 ms/token przy 98k (`lfm-decode-round2.md:95-101`) |
| T2/T6 atomiki, redukcja dwupoziomowa | ticket / last-block w 0053/0054 | gate+up zapisujące q8_1 dla down przez 192 tickety grup, ~0.1 ms/token (`lfm-decode-round2.md:107-108`) |
| T12 pomiar | interleaved A/B, rocprofv3 w modelu, hash logitów, mikrobench „na zimno” | — |

Jeden wniosek, który wynika z krytyki T9, a nie z samego repo:
- `[WNIOSEK]` W decode fuzje residual/norm nie oszczędzają pasma. Wektor residual to 2048×4 B = 8 KB (LFM) albo 5120×4 B = 20 KB (Qwen) na token, a w strumieniu residual i tak trzeba go zapisać. Cały zysk z takich fuzji to usunięta granica uruchomienia (~2.5 µs) plus latencja małego kernela.
- Przy priorytetyzacji backlogu fuzji liczyć więc wyłącznie **usunięte granice × 2.5 µs + czas usuniętego kernela**, a nie bajty. Dokładnie tak już liczymy szacunki w `lfm-decode-round2.md:103-112`, więc to tylko potwierdzenie.

## 5. Krytyka

- **Brak treści merytorycznej powyżej poziomu wstępnego.** Kurs kończy się na koncepcjach FlashAttention i KV cache. Nie ma kwantyzacji, tensor cores, MMA/WMMA ani narzutu uruchomień poza jednym zdaniem.
- **Wyniki to puste szablony**, mimo zapowiedzi „benchmark tables and charts” (`README.md:200`). Nie da się sprawdzić żadnej tezy wydajnościowej, bo żadnej nie ma.
- **Kernele CUDA są naiwne**, co autor przyznaje (`week-18:206-209`, `week-22:203`):
  - 3 odczyty wiersza i podwójne `expf` (`cuda/softmax.cu:52-63`);
  - redukcja wymaga, by `blockDim` było potęgą 2 (`stride = blockDim.x/2`), i tego nie sprawdza;
  - `reduce_sum` synchronizuje hosta na każdym poziomie (`cuda/reduce_sum.cu:65-71`).
- **Week 38 upraszcza fuzję residual+norm.** Twierdzi, że ścieżka złączona nie zapisuje `tmp` (`week-38:149-160`). W prawdziwym transformerze `x + residual` jest strumieniem residual i musi trafić do pamięci, bo następna warstwa doda do niego swój wynik. Złączony kernel zapisuje go równolegle z wyjściem normy. Oszczędza tylko ponowny odczyt i granicę uruchomienia.
- **Pułapka przy przenoszeniu na HIP.** Week 12 zakłada sztywno warp 32 (`week-12:250, 303-305`), a o różnicy z wave64 na AMD nic nie mówi.
- **Repo jest niedokończone.** README odsyła do nieistniejących katalogów i nie ma licencji. Aktywność skończyła się po 6 dniach.

## 6. Werdykt

**Brak.** To niedokończony kurs wstępny CUDA/Triton bez pomiarów i bez treści o kwantyzowanym matmul, decode-attention czy kosztach uruchomień. Wszystko, co porusza, mamy już zrobione na RDNA3 lepiej i z pomiarami.
