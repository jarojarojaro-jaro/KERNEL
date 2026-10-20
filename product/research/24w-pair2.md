# 24w: PAIR2 (para MMVQ dla mieszanych typów) na topce

## Werdykt

**ODRZUCONE (pomiar 2026-10-20 rano).** Bramka md5 przeszła (plain c4708318, MTP 6f14e814 przy `GGML_HIP_MMVQ_PAIR2=1`), ale czat T=1 ABBA zyskał tylko +0.4% (115.1 → 115.6 t/s; ms/krok 27.28–27.49 → 27.18–27.35). To poniżej progu „wyraźna wygrana albo nic”, więc nic nie instalujemy. Gałąź `pair2-topka` zostaje jako zapis wyniku.

(Pierwotnie: kolejkę nocną anulowano przed startem, bo użytkownik zakazał testów na XTX tej nocy; pomiar zrobiono rano, kolejka `morning.jobs` 13:55–14:04 UTC.)

## Stan

- Gałąź `pair2-topka` w worktree `~/wt/pair2` (od topki 9056cea22) ma trzy commity:
  - `7555f1d21`: cherry-pick RPB 76f0dfd33. Potrzebny, bo PAIR2 zależy od parametru szablonu `rows`.
  - `d7f1b7d37`: cherry-pick PAIR2 7b446922a.
  - `5ac5a69b3`: usuwa runtime'owy dispatch RPB. Nie ma instancji rows=1/2/4, więc build jest szybki, a domyślna ścieżka to rows=0, czyli wiersze z tabeli. Pomocnicze `mmvq_multi_rows*` zostały w kodzie jako martwe.
- Build: `rbuild --prefix ~/qwen-opt/pair2/inst ~/wt/pair2 llama-server` dał OK ze snapshotu ff2a8aad6 (stan identyczny z 5ac5a69b3). Binarka jest w `~/qwen-opt/pair2/inst/bin`, a string `PAIR2` jest obecny w `libggml-hip.so`.
- Skrypty w `~/qwen-opt/pair2/`:
  - `p2_md5.sh`: greedy md5 przez `fusion/greedy.sh`. Env topki: PM4 WA=2+GUARD, SVM=0, GPU_VERIFY=1, LOOKUP=3 W16, COUPLED=1, YIELD_FAST=2, MIN_DISPATCH=16, LAZY_EXEC=1. Port 18841.
    - Oczekiwane md5: plain c4708318, MTP 6f14e814.
    - Gdy wszystko się zgadza, tworzy `/tmp/pair2-gate/PASS`. Przy niezgodności usuwa ten plik.
  - `p2_arm.sh`: `gpuverify/gv_arm.sh` w trybie sweep, T=1, SEEDS 1,2,3, ten sam env, port 18842. Logi idą do `~/qwen-opt/pair2/logs`. Bez PASS skrypt się pomija.
- Joby: `~/qwen-opt/queue/p2.jobs`, kolejno md5, A, B, B2, A2 (ABBA), każdy z limitem 600 s.

## Tabela (2026-10-20, 13:55–14:04 UTC; spec_sweep T=1, seedy 1–3, env topki, ABBA: A B B2 A2)

Źródło: `~/qwen-opt/lookup/ab_summary.py ~/qwen-opt/pair2/logs --prefix p2-`; logi `~/qwen-opt/queue/logs/p2-*.log`; bramka `p2-md5.log` = `MD5 OK`.

| prompt | A + A2: t/s, ms/step | B + B2 (`GGML_HIP_MMVQ_PAIR2=1`): t/s, ms/step | tok/step |
|---|---|---|---|
| en-chat | 94.8, 27.28 | 95.1, 27.18 | 2.59 |
| en-code | 120.6, 27.49 | 121.2, 27.34 | 3.31 |
| en-tech | 120.7, 27.39 | 121.3, 27.24 | 3.31 |
| pl-kod | 137.8, 27.31 | 138.2, 27.21 | 3.76 |
| pl-proza | 96.2, 27.36 | 96.5, 27.26 | 2.63 |
| pl-tech | 120.4, 27.45 | 120.9, 27.35 | 3.31 |
| **średnio** | **115.1** | **115.6 (+0.4%)** | bez zmian |

Szacunek 0.3–0.5 ms/krok się nie potwierdził: zmierzono ~0.1 ms/krok.

## Kroki rano

1. `~/qwen-opt/queue/run-jobs.sh ~/qwen-opt/queue/p2.jobs`. Logi pojawią się w `~/qwen-opt/queue/logs/p2-*.log`.
2. Sprawdzić bramkę: `p2-md5.log` musi skończyć się linią `MD5 OK`. Jeśli jest MISMATCH, ideę zabić.
3. Podsumować A/B: `~/qwen-opt/lookup/ab_summary.py ~/qwen-opt/pair2/logs --prefix p2-`.
4. Adopcja tylko wtedy, gdy ms/step ramion B jest wyraźnie niższe niż A (oczekiwane 0.3–0.5 ms/step `[SZACUNEK]`, 3 seedy na ramię, ABBA). Wtedy instalacja wygląda tak:
   - `git -C ~/wt/topka merge pair2-topka` (albo cherry-pick 3 commitów).
   - `rbuild` topki do jej prefiksu, jak przy poprzednich instalacjach.
   - Dopisać `GGML_HIP_MMVQ_PAIR2=1` do env w `run-topka.sh`.
   - `tools/topka-restart.sh`.
   - Na koniec powtórzyć greedy md5 na zainstalowanej topce.

## Do bazy wiedzy

- PAIR2 przenosi się na topkę tylko razem z commitem RPB, bo zależy od parametru `rows` w `mul_mat_vec_q_body`. Instancje RPB można wyciąć, usuwając runtime'owy switch wierszy w `launch_multi`.
- Świeży katalog `build-hip` na farmie (pierwsza kompilacja mmvq.cu bez ccache) trwał ponad 50 min. `rbuild` z limitem 3000 s nie zdążył zwrócić wyniku, a kolejne wywołanie zakończyło się po 760 s. Pierwszy build nowego worktree trzeba puszczać bez limitu czasu.
