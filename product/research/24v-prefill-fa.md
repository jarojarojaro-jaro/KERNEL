# 24v — FA D=256 w prefillu Qwena: udział i usunięcie spilli (`GGML_HIP_FA_D256_CFG`)

Gałąź `prefill-fa` (`~/wt/prefillfa`, z `topka` f2217bac7), commit ade92ab69 (+ ten raport). Narzędzia: `~/wt/prefillfa-tools/` (`fa_prof.sh`, `fa_sum.py`, `isa_s.sh`, `pfa_gate.sh`, `pfa_md5.sh`, `pfa_bench.sh`, `pfa_lcb.sh`, pliki `p1..p4.jobs`). Przełącznik `GGML_HIP_FA_D256_CFG`, domyślnie 0 (bez zmian).

## Werdykt

**Spille usunięte, wynik bitowo identyczny, prefill przy głębokim kontekście +0,4–0,8%. NIE adoptujemy, bo zysk jest poniżej progu „wyraźnej wygranej” z reguły użytkownika. FA to tylko 2–24% prefillu, więc sufit jest mały.** Przełącznik zostaje w gałęzi `prefill-fa` (domyślnie 0). md5 z wyłączonym przełącznikiem nie było uruchamiane (decyzja Main: nie adoptujemy, job pominięty).

- Sufit: FA `<256,256,32,2>` zajmuje **2,2%** czasu kerneli w pp4096, **13%** przy wypełnianiu 32k i **24%** w pp512@d32k. W TTFT przy 29,5k sufit to więc ~13%.
- Przyczyna spilli: scheduler wyciąga przed pętlę wszystkie ładowania kafli V (transpozycja z LDS, 16 VGPR na kafel) dla całego kawałka DV. Wymaga to >256 VGPR i spilluje wewnątrz pętli KV. Jeden `__builtin_amdgcn_sched_barrier(0)` po każdym WMMA w pętli V daje **256 VGPR / 512 B scratch → 232 VGPR / 0 B**. Kolejność operacji jest ta sama, wyniki są bitowo identyczne.
- Zysk: pp512@d32k **+0,84%**, pp16384 **+0,40%**, TTFT 29,5k **+0,5%**. Na pp512/pp4096 przy głębokości 0 bez różnic (szum). Z udziału 24% wynika, że sam kernel FA przyspiesza o ~3,5% `[INFERENCE]`. Spille nie były więc głównym kosztem: kernel nadal osiąga ~50 TFLOPS (40% szczytu WMMA).

## Profil (rocprofv3, topka zainstalowana, KV q4_0, ub 512, `p1`)

| przebieg | czas kerneli | MMQ | FA `<256,256,32,2>` | GDN | konwersja KV→f16 |
|---|---|---|---|---|---|
| pp4096 (1117 t/s) | 7,18 s | 81,3% | **2,2%** (156 ms) | 4,0% | 1,2% |
| pp512 @ d32768, całość (wypełnienie 32k + test) | 33,3 s | 72,1% | **13,1%** (4,35 s) | 3,5% | 1,2% |
| pp512 @ d32768, ostatni ubatch | 547 ms | 63,0% | **24,0%** (131 ms, 16 wywołań = 8,2 ms/warstwę) | 3,0% | 1,3% |

Kernel FA w profilu: VGPR 256, scratch 512 B, wg 32×8. Na kolejnych ubatchach wypełniania udział FA rośnie od 1% do 24%.

## ISA (gfx1100, `isa_s.sh`, `isa_kstat.py`)

| wariant | VGPR | scratch | fale (kompilator) | instrukcje | `s_waitcnt` | LDS |
|---|---|---|---|---|---|---|
| topka (=0) | 256 | 512 B | 5 | 19156 | 1543 | 2192 |
| E1 `sched_barrier` po każdym WMMA V (=1) | **232** | **0** | 6 | 18515 | 1412 | 2192 |
| E2 `sched_barrier` co 32 kolumny V (=2) | 248 | 0 | 5 | 18403 | 1338 | 2192 |
| E3 `sched_barrier` co kawałek DV (2×128) | 256 | 308 B | 5 | 18929 | 1579 | 2192 |

Wariant `=0` ma po zmianie ISA identyczne z topką (te same statystyki), bo parametr szablonu ma domyślnie 0. LFM (head dim 64) używa innej instancji, której ta zmiana nie dotyka.

## Poprawność (`p2`)

- `test-backend-ops -o FLASH_ATTN_EXT -p hsk=256`: cfg 1 i cfg 2 **173/173**. W logu widać, że wariant był aktywny.
- Bitowość: serwer, prompt 4940 tokenów (10 ubatchy po 512, rosnąca głębokość) + prompt krótki, T=0, 24 tokeny, top-5 logprobs. md5 JSON-a **4a5d4252** dla cfg 0, 1 i 2 → identyczne. Bramka KLD nie jest potrzebna.
- md5 z wyłączonym przełącznikiem (plain c4708318 / MTP 6f14e814 / LFM 894e56e4): **nie uruchomione**, bo zmiana nie jest adoptowana. Job jest gotowy w `p4.jobs`, gdyby gałąź wracała.

## Pomiary ABBA (`p2`, `p3`; llama-bench `GGML_HIP_PM4=0`, TTFT w pełnym środowisku topki)

| test | cfg 0 (A, A) | cfg 1 (B, B) | Δ |
|---|---|---|---|
| pp512 @ d32768 | 863,8 / 861,1 → **862,5** | 870,9 / 868,5 → **869,7** | **+0,84%** |
| pp16384 | 1061,9 / 1061,8 → **1061,9** | 1066,2 / 1066,1 → **1066,1** | **+0,40%** |
| TTFT 29,5k (`long_ctx_bench`, 29510 tok.) | 958,3 / 952,5 t/s (30,8 / 31,0 s) | 961,1 / 959,2 t/s (30,7 / 30,8 s) | **+0,5%** |
| pp4096 (−r 3) | 1123,4 / 1120,3 | 1122,6 / 1122,1 (cfg 2: 1122,7 / 1122,4) | 0 (szum) |
| pp512 (−r 5) | 1096,6 / 1097,1 | 1091,1 / 1099,6 (cfg 2: 1098,1 / 1096,7) | 0 (sd ~95) |

W przebiegach TTFT akceptacja draftów różniła się między dwoma przebiegami tego samego cfg 1 (0,534 vs 0,575; cfg 0: 0,542 / 0,542). To niedeterminizm ścieżki dekodowania (lookup/MTP), a nie prefillu, bo prefill jest bitowo identyczny. Prędkości dekodowania nie porównuję.

## Działania

1. Nie adoptujemy (zysk +0,4–0,8% poniżej progu). Gdyby FA wróciło jako cel (np. prefill >64k, gdzie udział FA rośnie powyżej 24%), najpierw trzeba uruchomić `p4.jobs` (md5 z wyłączonym przełącznikiem). Potem `GGML_HIP_FA_D256_CFG=1` w `run-topka.sh` po przebudowie z `prefill-fa`.
2. Odrzucone/niezbadane w limicie czasu: zmiana `nbatch_fa`/`nthreads` (zmienia kolejność softmaksu i podział KV między warpy, więc nie jest bitowa; poprzednio `nbatch_fa=32` dawało 192 B scratch). Jedyna większa rezerwa to przepisanie ładowania V (2192 operacji LDS na iterację, transpozycja przez `ds_read_b32` + perm). FA to tylko 13% TTFT@29,5k, więc pełny zysk byłby i tak ograniczony.
3. Wynik negatywny dla depth 0: przy pp512/pp4096 bez głębokości FA jest za mały (≤2,2%), żeby zmiana kernela FA była widoczna. Prefill do ~8k dominuje MMQ (72–81%).

## Do bazy wiedzy

- Udział FA D=256 w prefillu Qwena na XTX (KV q4_0, ub 512): pp4096 2,2%, wypełnienie 32k 13%, pp512@d32k 24% (8,2 ms na warstwę atencji). Prefill dominuje MMQ (63–81%).
- Spill `flash_attn_ext_f16<256,256,32,2>` (256 VGPR, 512 B scratch) pochodzi z hoistingu ładowań kafli V (transpozycja z LDS) przez scheduler, a nie z samego akumulatora VKQ. `__builtin_amdgcn_sched_barrier(0)` po każdym WMMA w pętli V daje 232 VGPR i 0 spilli bez zmiany kolejności operacji, więc wynik jest bitowo identyczny. Bariera co kawałek DV nie wystarcza (308 B).
- Zysk z usunięcia spilli jest mały: +0,84% pp512@d32k, +0,4% pp16384, +0,5% TTFT 29,5k, czyli ~3,5% kernela FA. Spill w tym kernelu nie był wąskim gardłem; kernel nadal osiąga ~50 TFLOPS.
- Bitowość wariantów FA bez GPU-referencji: md5 odpowiedzi `/completion` z `n_probs` przy długim prompcie (≥ kilka ubatchy) wykrywa każdą zmianę w prefillu. Krótkie prompty `greedy.sh` nie uruchamiają kernela ncols1=32.
- Konfiguracje bitowo neutralne w MMA FA: `nbatch_K2`, `nbatch_V2`, `nbatch_combine`, `Q_in_reg`, `nstages`, occupancy oraz bariery schedulera. Zmieniają wynik: `nbatch_fa`, `nthreads` (np), `ncols1/ncols2`, a także wszystko, co zmienia `max_blocks_per_sm` z API occupancy (podział stream-k).
