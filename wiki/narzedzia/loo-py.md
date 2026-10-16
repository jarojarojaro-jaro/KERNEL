---
typ: narzedzie
tags: [narzedzia, loo, latki]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/tools/loo.py:1-12; ~/wt/tools6/REPORT.md:14-25; git -C ~/llama-master log -1 4db68c6ab
status: aktualne
---
# loo.py (leave-one-out łatek)

**Narzędzie leave-one-out serii `amd-opt`: plan (CPU, git), runner GPU, buildy z revertami i raport ze sparowanym 95% CI.**

Komendy: `plan` → `loo-plan.json/md`, `run [--dry-run|--fake]` → `loo-results.jsonl` (wznawialny), `builds` → `loo-builds.sh`, `report` → `loo-report.md`. Zasady GPU: każdy blok pod `flock /tmp/gpu.lock flock /tmp/quiet.lock`, odmowa startu, gdy działa serwer użytkownika na porcie 8080, blok ≤ 5 min, potem 45 s przerwy, porty 18433–18499. Klasyfikacja 65 łatek (2026-10-15): 27 przełączników env, 2 CLI, 22 tylko build (8 revertuje się czysto, 14 z konfliktem), 14 nie-wydajnościowych. Na GPU jeszcze nie uruchomione w tamtym raporcie.

## Powiązane
- [[narzedzia/_hub|narzedzia]]
- [[kld-canary]]
- [[kt-harness]]
- [[loo]]
- [[tools6]]
