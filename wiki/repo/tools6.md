---
typ: repo
tags: [repo, galezie, narzedzia]
aktualizacja: 2026-10-16
zrodlo: ~/wt/tools6/REPORT.md:1-25; git -C ~/llama-master log -1 4db68c6ab
status: aktualne
---
# Gałąź tools6 (LOO, kanarki KLD, Kernel Tuner)

**Gałąź `tools6` @ `4db68c6ab` (2026-10-15) dodaje tylko hak kompilacji `MMVQ_TUNE_NWARPS_N1` dla Kernel Tunera; reszta rundy to narzędzia w `~/qwen-opt/tools/`.**

Hak nie zmienia kodu kompilowanego przez build ggml (makro definiuje tylko harness), oznaczony NIEZMIERZONE i nieprzeznaczony do `amd-opt`. Narzędzia rundy: `loo.py` (klasyfikacja 65 łatek: 27 przełączników env, 2 CLI, 22 tylko build, 14 nie-wydajnościowych), kanarki bramki KLD (`kld_canary.sh`, `kld_gate.py`, `perturb_gguf.py`) i rusztowanie `kt/`. Nic nie było uruchamiane na GPU.

## Powiązane
- [[repo/_hub|repo]]
- [[galezie-rund]]
- [[loo-py]]
- [[kld-canary]]
- [[kernel-tuner]]
