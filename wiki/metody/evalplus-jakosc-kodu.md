---
typ: metoda
tags: [metody, jakosc, evalplus, poprawnosc]
aktualizacja: 2026-11-09
zrodlo: ~/KERNEL/qwen-opt/evalplus/jakosc-mini.sh; ~/KERNEL/qwen-opt/evalplus/gen.py; ~/KERNEL/qwen-opt/evalplus/sandbox_eval.py; ~/KERNEL/qwen-opt/evalplus/report.py; https://github.com/evalplus/evalplus
status: aktualne
---
# jakość-mini: bramka jakości kodu EvalPlus

**Jedna komenda mierzy greedy pass@1 modelu z profilu `run-topka.sh` na HumanEval+ (164) i MBPP+ (378); generacja na GPU przez kolejkę, wykonanie niezaufanego kodu na CPU w piaskownicy Landlock.**

Użycie (`~/qwen-opt/evalplus/`, evalplus 0.3.1 w `.venv`):
```
./jakosc-mini.sh --model uncensored --port 8097 --effort low [--tag NAZWA] all
```
`all` = `submit` (zapisuje `runs/<tag>/gate.jobs`: `gen` + `restore`, przez `queue/run-jobs.sh`) → `eval` → `report`. Zmienne `run-llm.sh` (CTX, DRAFT_N, ROCM_DIR…) przechodzą z otoczenia, więc kandydat (Astra-Stop, kwant, przepis) to inny `ROCM_DIR`/model i inny `--tag`.

- **gen**: serwer produkcyjny na własnym porcie (`PORT`, `EFFORT` → `--reasoning-effort`), pętla `evalplus.codegen` z dekoderem OpenAI evalplus (ten sam prompt systemowy i prefiks instrukcji, `sanitize`), T=0, n=1; bez 100-sekundowego alarmu evalplus (myślenie bywa dłuższe), `max_tokens` 32768; statystyki per odpowiedź (`timings` llama-server) w `*.stats.jsonl`. Stop: jeden SIGTERM, 60 s, SIGKILL.
- **restore**: `run-topka.sh uncensored` na :8080, sprawdza `/health`, n_ctx 262144, binarkę `~/llama-topka/bin/llama-server`.
- **eval** (piaskownica): na hoście nie ma bubblewrap/firejail, `unshare -n` blokuje AppArmor, `systemd --user` nie egzekwuje `IPAddressDeny`. Dlatego Landlock ABI 4 (zakaz TCP connect/bind, zapis tylko w katalogu runu, `/dev/shm`, `/dev/null`) + blokada `socket` w Pythonie + `reliability_guard` evalplus, w `systemd-run --user --scope MemoryMax=4G CPUQuota=200%`, `nice 19`, nigdy root. Test 2026-11-09: rozwiązania kanoniczne 163/164 (164. to celowo złośliwa próbka), `curl` pod Landlockiem rc 7, zapis do `~` odrzucony.
- **report**: `summary.{md,json}`: pass@1 base/plus, tokeny/odpowiedź, ucięte, wall, t/s. Prędkość na prawdziwych zadaniach: `/usr/bin/python3 ~/qwen-opt/speed_real.py runs/<tag> --md runs/<tag>/speed.md`; narzut na żądanie: `overhead.py runs/<tag>`.
- Kopia skryptów i podsumowań (bez surowych generacji): [qwen-opt/evalplus](../../qwen-opt/evalplus/jakosc-mini.sh).

Pierwszy pomiar: [[2026-11-09-evalplus-qwen-uncensored]] (topka-q70 `3191b25f4`).

## Powiązane
- [[metody/_hub|Metody]]
- [[bramka-kld-kanarki]]: bramka numeryki (KLD), ta mierzy wynik zadania
- [[zgodnosc-bitowa-md5]]
- [[modele/qwen3-8-27b-uncensored|Qwen3.8-27B-Uncensored]]
