---
typ: narzedzie
tags: [narzedzia, chmura, vast]
aktualizacja: 2026-10-16
zrodlo: ~/qwen-opt/cloud/{find,up,push,bootstrap,bench,collect,down,watchdog,env,lib}.sh:1-4
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

## Powiązane
- [[narzedzia/_hub|narzedzia]]
- [[samp-ab]]
- [[greedy-check]]
- [[harness-chmurowy]]
- [[lekcja-vast-cli-klucz]]
