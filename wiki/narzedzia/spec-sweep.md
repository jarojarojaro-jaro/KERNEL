---
typ: narzedzie
tags: [narzedzia, pomiar, spekulacja]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/spec_sweep.sh:1-8; ~/KERNEL/qwen-opt/spec_sweep.py:1-6; ~/KERNEL/qwen-opt/sweep_summary.py:1-4; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:242,301; ~/KERNEL/qwen-opt/NOTES.md:160
status: aktualne
---
# spec_sweep — główny pomiar t/s i ms/krok

**Standardowy benchmark projektu: restartuje serwer dla każdej konfiguracji i mierzy t/s, ms/krok, tokeny na krok i akceptację draftu na stałym zestawie promptów PL/EN.**

- `spec_sweep.sh "KONFIG1" "KONFIG2" …` (np. `"DRAFT_N=5 P_MIN="`, `RUN_ARGS="qwen dflash"`): restart `run-llm.sh` per konfiguracja, log mocy i temperatur do `logs/sweep-gpu.csv`, serwer dobijany SIGKILL po 15 s (lekcja z wiszącego serwera DFlash).
- `spec_sweep.py --label NAME [--port] [--tokens 400] [--temps 1.0] [--seeds 1,2]`: pomiar na działającym serwerze; zestaw 6 promptów (PL proza/tech/kod, EN chat/tech/kod).
- Wyniki: `spec_sweep.jsonl` (raport 07: 182 konfiguracje, 2026-10-10…14, mediana 2.15 min na konfigurację, łącznie 6.8 h GPU); podsumowanie `sweep_summary.py [N]`.
- Standard projektu: 6 promptów × 3 seedy, T=1, metryka ms/krok; ten sam skrypt jest w harnessie chmurowym (etap „sweep”).

## Powiązane
- [[narzedzia/_hub|Narzędzia]]
- [[pomiar-abba]]
- [[ms-na-krok]]
- [[run-llm-sh]]
- [[harness-chmurowy]]
