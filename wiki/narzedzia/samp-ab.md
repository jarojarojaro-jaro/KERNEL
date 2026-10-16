---
typ: narzedzie
tags: [narzedzia, sampler, ab]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/samp_ab.py:1-25; ~/KERNEL/qwen-opt/NOTES.md:384
status: aktualne
---
# samp_ab.py (A/B samplera)

**Skrypt A/B szybkich ścieżek samplera: wysyła do działającego llama-server zapytania w stylu web UI i omp, wypisuje t/s dekodu i md5 wyjścia z ustalonym seedem.**

Przypadki: `plain`, `reasoning_control`, `budget_2048`, `tools(lazy grammar)`, `logit_bias`; sampler UI: T=0.8, top_k 40, top_p 0.95, min_p 0.05, seed 11. Ten sam md5 między buildem szybkim i wolnym = te same tokeny. Użycie w rundzie samplera (0065–0069, 2026-10-15): serwer świeży, 800 tok., md5 tekstu i wywołań narzędzi fast == slow we wszystkich 5 przypadkach dla LFM i Qwen MTP. Uruchomienie: `samp_ab.py --port N`.

## Powiązane
- [[narzedzia/_hub|narzedzia]]
- [[det-probe]]
- [[greedy-check]]
- [[2026-10-15-sampler]]
- [[opt-samp]]
- [[serve-bench]]
