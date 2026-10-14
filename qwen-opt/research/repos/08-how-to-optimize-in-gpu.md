# 08 — Liu-xiandong/How_to_optimize_in_GPU

Źródło: https://github.com/Liu-xiandong/How_to_optimize_in_GPU, HEAD `5d2def3e` (2023-07-29). Klon płytki, nic nie było budowane ani uruchamiane. Ścieżki `plik:linia` są względem korzenia repo. Teksty autora są też w kolumnie Zhihu „深入浅出GPU优化” (https://www.zhihu.com/column/c_1437330196193640448, np. GEMM (三): https://zhuanlan.zhihu.com/p/481600052). Artykułów nie czytałem poza wynikami wyszukiwania; w repo jest pełny tekst tylko o reduce (`reduce/README.md`).

## 1. Co to jest

Seria dydaktyczna „drabin optymalizacji” w CUDA dla **V100 (sm_70)**. Obejmuje elementwise, reduce (v0–v7), sgemv (3 warianty według N), sgemm FP32 (v1, v3 + strojenie SASS przez CuAssembler), SpMV/SpMM CSR (`README.md:1-38`). Licencja Apache 2.0. Ostatni commit 2023-07, repo nie jest rozwijane. README dla elementwise/sgemv/sgemm to „# TODO”. Wszystkie liczby to pomiary autora (nsight lub cudaEvent, V100, 900 GB/s). Nie ma kwantyzacji, MMA/tensor cores, kerneli LLM ani AMD.

## 2. Kluczowe techniki (z dowodami)

| Krok | Dowód | Liczby (autor, V100) |
|---|---|---|
| Elementwise: `float` → `float2` → `float4` | `elementwise/elementwise_add.cu:11-12,31-43` | 827 → 838 → 844 GB/s (91.9 → 93.8%), `README.md:9-13`; N = 32M float, 128 MiB/tablicę |
| Reduce v0 → v1: brak dywergencji (`index = 2*s*tid`) | `reduce/README.md:85-130` | 159 → 253 GB/s |
| v2: odwrócona pętla stride (bez konfliktów banków) | `reduce/README.md:130+` | 322 GB/s |
| **v3: dodawanie przy ładowaniu (2 elementy/wątek, połowa bloków)** | `reduce/reduce_v3_add_during_load.cu:46-47` | **600 GB/s (1.86×, największy skok)** |
| v4: rozwinięta ostatnia warpa bez `__syncthreads` (`volatile` LDS) | `reduce/reduce_v4_unroll_last_warp.cu:11,44` | 756 GB/s |
| v5: pełne rozwinięcie (template blockSize) | `reduce_v5_completely_unroll.cu` | 768 GB/s (1.01×) |
| v6: stała liczba bloków (1024), NUM_PER_THREAD=128 rozwinięte | `reduce/reduce_v6_multi_add.cu:32,77-79`; „2048 bloków lepsze niż 512/1024/4096” `reduce/README.md:419` | 768 GB/s (1.00×) |
| v7: `__shfl_down_sync` zamiast LDS w warpie, LDS tylko na sumy warp | `reduce/reduce_v7_shuffle.cu:12-18,39-46` | 770 GB/s (1.00×); tabela `reduce/README.md:478-485` |
| Sgemv N=32: warp na wiersz, lane = kolumna | `sgemv/Sgemv_v0.cu:35-64` | 10.3 µs vs cuBLAS 8.4 µs (M=16384), `README.md:27` |
| Sgemv N≥128: warp na wiersz, `float4` na lane | `sgemv/Sgemv_v1.cu` (diff do v0: `kIteration=(N/32)/4`, float4 A i x) | 14.3 µs vs 15.8 µs cuBLAS, `README.md:28` |
| **Sgemv N≤16: kilka wierszy na warp (pod-warp 16 lane / wiersz)** | `sgemv/Sgemv_v2.cu` (`ROW_PER_WARP`, `warpReduceSum<kWarp_size>`) | 6.9 µs vs 7.6 µs, `README.md:29` |
| SpMV CSR: wektor 2/4/8/16/32 lane na wiersz dobierany średnią nnz/wiersz | `spmv/spmv.cu:158-187,276-321` | brak liczb w repo |
| Sgemm v3: kafel 128×128×8, 8×8 na wątek, A transponowane w LDS, **podwójny bufor LDS + prefetch global→rejestry następnego kafla, 1 `__syncthreads` na kafel**, podwójny bufor fragmentów w rejestrach | `sgemm/sgemm_v3.cu:58-75,138-200` (komentarz „use double buffer, only need one sync” `:196-197`) | 96.8% cuBLAS, 93.6% szczytu FP32 przy 4096³ (`README.md:35`); wykres `figure/sgemm.png`: 1024–1280 tylko 63–78% cuBLAS |
| Sgemm v1 → v3: rozkład fragmentu wątku na 4 pod-kafle 4×4 co 64 (`a_tile_index`, `b_tile_index`) przeciw konfliktom LDS.128 | `sgemm/sgemm_v3.cu:97-100,127-132` | brak osobnej liczby |
| SASS: remapowanie rejestrów i flagi `.reuse` (CuAssembler) | `sgemm/asm/*.cuasm` (333 → 345 flag `.reuse`) | brak liczby w repo |

## 3. Przeniesienie na AMD/HIP/RDNA3

- **Vectorized loads (`float4`)** → `global_load_dwordx4` / `buffer_load_dwordx4`. Fork już to ma w MMVQ (4 kolejne inty na wątek, buffer resource, K1). W małych kernelach (2048 floatów = 8 KB) to nic nie da: czas to latencja, nie instrukcje. Przy 960 GB/s 16 KB wejścia to ~17 ns z 2.7 µs.
- **Shuffle (v7)** → DPP (`row_shr`, `row_bcast`, `v_permlanex16`) / `ds_swizzle`. Już jest `warp_reduce_sum_dpp` (`ggml-cuda/norm.cu:253,258`).
- **Ostatnia warpa bez synchronizacji (v4)**: na AMD fala jest zawsze w lockstepie, więc trik działa „naturalnie”. DPP i tak jest lepsze niż LDS z `volatile`. Nic do przeniesienia.
- **Dywergencja, konflikty banków (v1, v2)**: to lekcje dla redukcji drzewem w LDS, której już nie używamy (DPP). Organizacja banków LDS na RDNA3 jest inna (64 banki DWORD w 2 połowach po 32, za raportem 02/seb-v). Wniosek z v2 o „stride od góry” przenosi się jakościowo, liczby nie.
- **Więcej pracy na wątek, mniej wątków/bloków (v3, v6)**: przenosi się wprost i to jest jedyna lekcja z drabiny reduce, która ma znaczenie w reżimie latencji (mniej fal do rozdysponowania, tańsza bariera). Patrz P2.
- **Pętla grid-stride przy stałej siatce (v6)**: przenosi się 1:1. Ważny dowód pośredni: u autora stała siatka (1024–2048 bloków, każdy ~16K elementów) nie traci pasma wobec siatki „blok na kawałek” (768.1 vs 767.6 GB/s, `reduce/README.md:483-484`). Pomiar dotyczy 128 MiB, nie naszych 1–17 MB. Patrz P3.
- **Sgemv, kilka wierszy na warpę (v2) i SpMV z wektorem dobieranym do długości wiersza**: odpowiednik to „lane'y na wiersz” w MMVQ. Fork to sprawdzał: 2 wiersze na blok przyjęte (0052), 4 wiersze na falę i 4 wiersze na blok negatywne (`research/lfm-decode.md:141-144`, `NOTES.md:351`). Repo nie mówi nic o przypadku odwrotnym (mało wierszy, długi K: router 64×2048, alpha/beta 48 wierszy), a ten dla nas zostaje. Patrz P4.
- **Sgemm v3 (podwójny bufor LDS + staging w rejestrach)**: na RDNA3 nie ma `cp.async`/TMA, więc staging global→VGPR→`ds_write` po obliczeniach jest **jedynym** sposobem nakładania loadów na obliczenia w obrębie bloku. Przenosi się na MMQ prefillu (WMMA iu8 zamiast FFMA). Koszt to VGPR i LDS ×2. Patrz P1.
- **SASS `.reuse` / remapowanie rejestrów**: odpowiednik na RDNA3 to banki VGPR (`reg % 4`) i dual-issue `v_dual_*` (raport 02). Wymaga ręcznego ISA, nie do utrzymania w forku. Nie przenosimy.
- **Top-k**: w repo nic nie ma.

## 4. Pomysły dla nas

Większość drabiny jest już w forku (DPP, szerokie loady, mniej bloków, „ostatni blok” zamiast drugiego kernela redukcji). Zostały cztery eksperymenty, od najbardziej obiecującego.

**P1. MMQ prefill: podwójny bufor LDS ze stagingiem w rejestrach, 1 bariera na iterację K (wzór `sgemm_v3.cu:138-200`)**
- Stan: `mul_mat_q_process_tile` (`ggml-cuda/mmq.cuh:909-942`) ma jeden bufor LDS i **4 `__syncthreads` na iterację** kb0: load_tiles + pierwsza połowa y, sync, vec_dot, sync, druga połowa y, sync, vec_dot, sync. Latencję globalnych loadów chowa tylko obłożenie innymi blokami.
- Zmiana (RDNA3, najpierw Q4_K/Q5_K/Q6_K):
  1. Rozdzielić `load_tiles` na „global→VGPR (surowe bloki kwantów + y)” i „VGPR→LDS (z rozpakowaniem)”.
  2. Wydać loady kb0+1 przed `vec_dot` kb0, zapisać je do drugiego bufora LDS po obliczeniach.
  3. Jedna bariera na iterację.
- Tańszy pierwszy krok: cały `tile_y` naraz (2× LDS na y), czyli 2 bariery zamiast 4.
- Związek z innymi raportami: to konkretna postać punktu 8(a) z `research/strata/README.md:170,211` („loady przed obliczeniami”, Strata #2017: −9.7% czasu kernela; głębszy prefetch 232→248 VGPR oddał wszystko). Pułapka #1180: brak bariery po double-buffered LDS.
- Zysk `[SZACUNEK]`: 5–12% czasu MMQ, czyli +3–8% prefill (MMQ to większość prefillu przy krótkim kontekście). Uzasadnienie: Strata −9.7% dla samych loadów przed obliczeniami, tu dodatkowo mniej barier.
- Koszt: 3–5 dni (load_tiles per typ). Ryzyko: VGPR (WMMA akumulatory + staging) obniża obłożenie, LDS ×2 może nie zmieścić się w obecnym kaflu. Wynik bitowo identyczny, bo kolejność sumowania jest ta sama.
- Pomiar: `test-backend-ops perf -o MUL_MAT` na kształtach Qwena (łatka 0044), rocprofv3 czasu `mul_mat_q`, llama-bench pp4096 przy d0 i d32k. Sprawdzić VGPR/LDS w `--save-temps` lub objdump.

**P2. rms_norm*mul(+q8_1) na 2048/5120 kolumn: 256 wątków zamiast 1024, bitowo (lekcja v3/v6)**
- Stan: `rms_norm_mul_f32_unrolled<NV>` uruchamia 1024 wątki (32 fale na jednym WGP) dla wiersza 2048 (NV=2), z barierą między 32 falami (`ggml-cuda/norm.cu:193-283`). Trywialny kernel q8_1 trwa 1.28 µs, rms_norm 2.71 µs (`research/lfm-decode-round2.md:55,57`).
- Zmiana: mapowanie „wirtualnych warp” takie jak w już istniejącym `norm_router_topk_f32` (`ggml-cuda/topk-moe.cu:345-395`). Fala fizyczna liczy `nsum` = 4 wirtualne warpy: te same pary `fmaf`, 4 przeplecione redukcje DPP (ILP), te same sumy do LDS. Daje to identyczne bity przy 8 falach zamiast 32.
- Zysk `[SZACUNEK]`: 0.2–0.5 µs/wywołanie, czyli LFM 43 wywołania ≈ 10–20 µs/token (0.3–0.5%), Qwen podobnie na ~130 normach (<0.3%). Mały, ale tani.
- Koszt: pół dnia. Ryzyko: niskie (wzór już działa w forku, bitowość sprawdzona logit-hashem).
- Pomiar: rocprofv3 µs/wywołanie, `lh.sh` (hash logitów 64 kroków).
- Uwaga: większą dźwignią jest usunięcie tego kernela jako „ogona biletowego” poprzedniego (`lfm-decode-round2.md:105-106`, ~0.12 ms). P2 ma sens tylko dla norm, których nie da się wchłonąć.

**P3. Bramka do kernela trwałego: MMVQ n=1 w pętli grid-stride przy stałej siatce (lekcja v6)**
- Kontekst: zmierzono 2.53 µs na granicę kernela vs 0.5–0.8 µs na barierę siatki w kernelu trwałym (16–192 bloki). Łańcuch dużych faz z czekającymi blokami przegrywa (`lfm-decode-round2.md:23-41`). Brakujący element to MMVQ, który osiąga pasmo przy **małej stałej siatce** (≤192 bloki × 256), bo tylko taka siatka ma tanią barierę.
- Eksperyment bramkowy (tani, bez fuzji): wariant `mul_mat_vec_q` n=1 z siatką 96/192 bloków, który pętlą grid-stride przechodzi po wierszach (z obecnym kodem wątku i rozwinięciem loadów). Mierzyć GB/s na kształtach LFM (in_proj 6144×2048, gate+up ids, out_proj 2048×2048, k/v 512×2048) i Qwena.
- Jeśli straty ≤5%: kernel warstwy LFM (in_proj+conv → out_proj → norm+router+top-k → gate+up → down+reduce) jako jeden launch z barierami. Zysk `[SZACUNEK]` przy ~7 granicach/warstwę × 40 warstw × (2.5 − 0.7) µs ≈ 0.4–0.5 ms/token, czyli 10–12% LFM.
- Jeśli straty >10% (prawdopodobne przy 4 falach/SIMD bez dużej liczby loadów w locie `[WNIOSEK]`): temat zamknięty liczbą.
- Koszt bramki: 1 dzień. Koszt pełnej wersji: tygodnie. Ryzyko pełnej wersji: obłożenie = maksimum VGPR wszystkich faz, „slow mode” gate+up, utrzymanie.

**P4. Małe macierze o długim K: więcej fal na wiersz (odwrotność Sgemv_v2/SpMV)**
- Repo dobiera lane'y na wiersz do długości wiersza (`spmv/spmv.cu:287-321`). U nas problem jest odwrotny: k/v 512×2048 osiągają 274–317 GB/s przy 2.6 µs (`research/lfm-decode.md:47-48`). To 512 fal na 96 CU (~5 fal/CU), czyli rozbieg i ogon. 4 wiersze na blok pogorszyły małe launche (o-proj 5.3 → 6.6 µs, `lfm-decode.md:141-142`), co pasuje do tezy, że małe launche chcą *więcej* równoległości na wiersz.
- Zmiana: dla nrows < ~2048 podział K na 2 fale na wiersz (redukcja DPP + LDS jak w Q6_K, który już ma 2 fale/wiersz).
- Zysk `[SZACUNEK]`: 0.3–0.6 µs na takim launchu. LFM ~20/token ≈ 10 µs (0.25%), Qwen k/v 1024 wierszy w weryfikacji podobnie mało.
- Ryzyko: zmienia kolejność sumowania, więc nie jest bitowe (KLD). Niski priorytet; robić tylko razem z inną zmianą MMVQ.

**Czego z repo NIE robić**: wektoryzacji `float4` w bin_bcast/cpy/set_rows (czas = latencja), strojenia „liczba bloków = wielokrotność SM” dla małych kerneli, kodu ISA z ręcznymi bankami VGPR.

## 5. Krytyka

- **Hot-cache w sgemv**: A ma 1 MB (N=16) i 2 MB (N=32), mieści się w 6 MB L2 V100 i jest uruchamiane 1000× pod rząd (`sgemv/Sgemv_v0.cu:106-110`). „110% cuBLAS” to pomiar z L2, nie z DRAM. Efektywnie wychodzi 152–203 GB/s przy 7–10 µs, czyli kernel latency-bound, a nie optymalizacja pasma. Nasz mikrobench „na zimno” (>96 MB MALL) jest właściwy.
- **Niespójne liczby reduce**: README główne podaje 858 GB/s = 95.3% (`README.md:17`, wykres `figure/reduce.png`), tabela 770.3 GB/s = 85% (`reduce/README.md:485,489`). Autor sam pisze, że wyniku ~800 GB/s „nie umie odtworzyć” (`:495`). Przeliczenie tabeli: 159.2 GB/s × 804 µs ≈ 128.0e6 B, czyli użyto 128e6 zamiast 134.2e6 bajtów (−4.7%).
- **Kod ≠ opis**: README v6 opisuje pętlę `while(i<n)` grid-stride, a kod ma stałe `NUM_PER_THREAD=128` z akumulacją w `sdata[tid]` (`reduce_v6_multi_add.cu:32`). Rozwinięte sumowanie 128 elementów w jednym łańcuchu zależności nie zostawia ILP.
- **v4 `volatile` bez `__syncwarp`**: na Volta+ (independent thread scheduling) to formalnie UB (`reduce_v4_unroll_last_warp.cu:11`). Działa przypadkiem.
- **`__shfl_down_sync(0xffffffff)` wewnątrz `if(row_id < row_num)`** (`spmv/spmv.cu:171-182`, też sgemv): pełna maska przy możliwej dywergencji, UB na ogonie.
- **ComplexHalfGemv jest błędny, a test to maskuje** `[WNIOSEK z czytania kodu]`. `current_col_vec = (i*32+lane)/4` (`sgemv/ComplexHalfGemv.cu:56`) każe 4 lane'om czytać ten sam float4. Pętla pokrywa N/4 elementów 4 razy. Przy stałych danych 1+i (`:106-118`) wynik jest przypadkiem poprawny.
- **Sgemm**: flaga `ENABLE_DOUBLE_BUFFER` nie jest używana, kernel zawsze buforuje podwójnie (`sgemm_v3.cu:32,290`). Na małych rozmiarach 63–78% cuBLAS (kwantyzacja kafla 128×128 na 80 SM), czego README nie mówi. FP32 SIMT: dla nas tylko wzór pipeliningu.
- **Brak FP16/INT8/MMA, brak latency-bound małych kerneli, brak AMD**: drabina reduce jest mierzona na 128 MiB, więc cały czas w reżimie pasma. Nasze kernele (2–8 KB, 1–3 µs) są w reżimie latencji, gdzie kroki v1/v2/v4/v5/v7 nic nie zmieniają, a liczy się liczba granic kerneli i liczba rund pamięci na ścieżce krytycznej.

## 6. Werdykt

**Niska.** To solidny, ale podręcznikowy materiał z V100 mierzony w reżimie pasma, który fork już przyswoił (DPP, szerokie loady, mniej bloków, „ostatni blok”). Realnie przydatne są tylko: wzór podwójnego bufora LDS ze stagingiem w rejestrach i jedną barierą (P1, MMQ prefill), lekcja „mniej wątków, więcej pracy na wątek” (P2) oraz pośredni dowód, że stała siatka grid-stride nie traci pasma, czyli tania bramka przed kernelem trwałym (P3).
