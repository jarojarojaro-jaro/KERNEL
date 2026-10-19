---
typ: narzedzie
tags: [narzedzia, benchmarki, agenci]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21f-inferencex.md:33-78,175-209
status: aktualne
---
# AgentX harness (SemiAnalysis, AIPerf)

**`agentx-harness==1.0.11` (na AIPerf NVIDIA, wrapper `python3 -m infx.bench agentic`) odtwarza 393 sesje Claude Code z zachowanymi długościami, hashami bloków 64 tokenów, drzewem subagentów i przerwami na narzędzia, ale z syntetyczną treścią; c = liczba żywych drzew sesji, punkt ≥ 900 s (oficjalnie 1 h) na świeżym serwerze (raport 21f, 2026-10-19).**

- „P90 interactivity” = `1 / p90(średnie ITL na zapytanie)` (`request_metrics.py:65-84`); throughput liczy tokeny wejścia z cache.
- Spekulacja z wymuszoną długością akceptacji (golden AL z SPEED-Bench), nie rzeczywistą.
- Korpusy HF: `semianalysisai/cc-traces-weka-062126` (do 1M) i `…-256k`.
- U nas: okazjonalny test systemowy cache/slotów przy c=1 bez spekulacji (plan §7.1 raportu); własny „PodX” z prawdziwą treścią omp jako benchmark agentowy (§7.2).

## Powiązane
- [[narzedzia/_hub|Narzędzia]]
- [[spec-sweep]]
- [[ksztalt-ruchu-agentowego]]
- [[raport-21f-inferencex]]
