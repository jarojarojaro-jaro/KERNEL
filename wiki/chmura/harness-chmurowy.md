---
typ: chmura
tags: [chmura, harness, vast]
aktualizacja: 2026-10-16
zrodlo: ~/qwen-opt/cloud/{find,up,push,bootstrap,bench,collect,down,watchdog,env,lib}.sh (nagłówki); ~/qwen-opt/cloud/PLAN-TESTOW.md:7-49,51-71
status: aktualne
---
# Harness chmurowy (~/qwen-opt/cloud)

**Zestaw skryptów, który wynajmuje kartę na Vast, buduje upstream i nasz fork, mierzy poprawność i prędkość według stałego protokołu i niszczy instancję; każdy skrypt domyślnie tylko wypisuje komendy, wydaje pieniądze dopiero z `--go`.**

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

## Powiązane
- [[chmura/_hub|Chmura]]
- [[vast-ai]]
- [[2026-10-16-kampania-nvidia]]
- [[cuda-stos]]
- proces-klucze-poza-repo
