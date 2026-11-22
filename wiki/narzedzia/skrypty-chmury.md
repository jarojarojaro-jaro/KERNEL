---
typ: narzedzie
tags: [narzedzia, chmura, vast]
aktualizacja: 2026-11-22
zrodlo: ~/qwen-opt/cloud/{find,up,push,bootstrap,bench,collect,down,watchdog,env,lib}.sh:1-4; ~/qwen-opt/cloud/{find,up,push,bootstrap,bench,collect,down,watchdog,env,lib}.sh (nagłówki); ~/qwen-opt/cloud/PLAN-TESTOW.md:7-49,51-71; ~/KERNEL/product/research/16c-kvq-cuda.md:37,210
status: aktualne
---
# Skrypty chmury (~/qwen-opt/cloud)

**Zestaw skryptów bash do kampanii na wynajętych kartach Vast; każdy domyślnie tylko wypisuje komendy, a wykonuje je dopiero z `--go`.**

- `find.sh` – najtańsze niezawodne oferty dla modelu GPU, ranking po koszcie jednej rundy;
- `up.sh` – wynajem oferty jako instancji SSH z obrazem CUDA devel i dwoma niezależnymi timerami śmierci;
- `push.sh` – fork jako cienki git bundle na upstream `e60eff95f`, skrypty i drafty;
- `bootstrap.sh` – na instancji (`nvidia/cuda:12.8.1-devel-ubuntu24.04`): zależności, modele, buildy;
- `bench.sh` – etapy `tbo,greedy,lb,sweep`; `collect.sh` – rsync wyników do `cloud/results/<klasa>-<data>/`;
- `down.sh` – destroy (opłata za storage kończy się dopiero po destroy); `watchdog.sh` – lokalny timer;
- `env.sh` – klucze z plików z `chmod 600` (nigdy w repo); `lib.sh` – `run` drukuje zamiast wykonywać.
Opis protokołu w notatce harness chmurowy.

## Ze scalonej notatki: Harness chmurowy (~/qwen-opt/cloud)

Zestaw skryptów, który wynajmuje kartę na Vast, buduje upstream i nasz fork, mierzy poprawność i prędkość według stałego protokołu i niszczy instancję; każdy skrypt domyślnie tylko wypisuje komendy, wydaje pieniądze dopiero z `--go`.

| skrypt | gdzie | co robi |
|---|---|---|
| `find.sh <gpu> <max_$/h>` | lokalnie, bez klucza | filtruje oferty (reliability ≥ 0.98, verified, port, dysk, CUDA ≥ 12.8, ≥ 6 vCPU, ≥ 24 GB RAM, bez CN) i sortuje po koszcie rundy |
| `up.sh <offer> --hours N` | lokalnie | instancja `nvidia/cuda:12.8.1-devel-ubuntu24.04` + dwa niezależne timery zniszczenia |
| `push.sh --start` | lokalnie → instancja | bundle git forka (~0.3 MB, domyślnie `cuda-compat`), skrypty, słownik draftu; startuje bootstrap + bench |
| `bootstrap.sh` | instancja | apt, modele z HF (przypięta rewizja, sha256), 2 buildy CUDA z ccache, snapshot sprzętu |
| `bench.sh` | instancja | etapy tbo → greedy → bisect → lb → sweep (A0/A1/A2/A2s/A3) |
| `collect.sh` | lokalnie | rsync wyników do `results/<klasa>-<data>/` |
| `down.sh` | lokalnie | `vastai destroy` (stop nadal nalicza dysk) i stan konta |
| `watchdog.sh` | lokalnie | niszczy instancję po N h |

Bezpieczniki kosztów: lokalny watchdog + samozniszczenie na instancji po N h + 15 min (per-instancyjny klucz, który może tylko start/stop/destroy tej jednej maszyny); bench przestaje startować nowe przebiegi 20 min przed terminem. Klucze API są tylko w plikach na serwerze (chmod 600), wczytywane przez `env.sh`; nigdy w repo.

Na każdą kartę osobny katalog `runs/<karta>/` z kopiami skryptów dopasowanymi w trakcie kampanii (np. `scorecard.py`, `ttft.py`, `opt-switch.sh`).

Uwaga z E1 (2026-10-16): upload z domu ~155 KB/s (53 MB binarek w 5:42 min); przy iteracji lepiej wysłać bundle źródeł (355 KB) i zbudować na instancji (sm_120: 234 s przy 11 wątkach). Zobacz też [[lekcja-vast-authorized-keys]].

## Powiązane
- [[narzedzia/_hub|narzedzia]]
- [[samp-ab]]
- [[greedy-check]]
- [[narzedzia/skrypty-chmury]]
- [[lekcja-vast-cli-klucz]]
