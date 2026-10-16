---
typ: metoda
tags: [metody, profilowanie, roofline]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:191-205,216; ~/KERNEL/qwen-opt/NOTES.md:54-57,104-105,247-248,338,340
status: aktualne
---
# Sufit pasma i mapa czasu kroku

**Zanim cokolwiek zmienimy, liczymy, ile bajtów musi przeczytać krok (sufit pasma) i gdzie naprawdę idzie czas (profil rocprofv3 w modelu).**

1. **Sufit.** Qwen: `mul_mat_vec_q` czyta wagi z ~81–88% z 960 GB/s. LFM2.5: ~1.8 GB na token, czyli próg ~1.9 ms (~500 t/s). Bajty liczymy na przebieg modelu × tok/krok, nie na token (błąd „112% peaku”).
2. **Mapa czasu** (`prof_serve.sh`, `trace_breakdown.py`): kernele na token, µs na wywołanie, GB/s per miejsce wywołania, suma przerw. Przykład LFM (fork, 2026-10-14): ~721 kerneli/token, mul_mat_vec_q 71% (~680 GB/s), mediana przerwy ~3.1 µs, 5.05 ms/token = ~3.8 ms pracy + ~1.3 ms przerw/host.
3. **Kubełki strat:** pasmo (zły GB/s), narzut uruchomień (Qwen ~1900–2100 kerneli × ~3.2 µs ≈ 16%), host (sampler, maski, rollback).
4. **Decyzje z profilu w modelu, nie z mikrobencha:** mikrobench `mmvq-bench` mylił się co do Q6_K i GLC|DLC (w modelu był zysk).

## Powiązane
- [[metody/_hub|Metody]]
- [[mikrobench-granicy-kernela]]
- [[ablacja]]
- [[rocprof]]
- [[mmvq-multikolumnowe]]
