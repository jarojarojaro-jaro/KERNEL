---
typ: metoda
tags: [metody, pomiar, statystyka]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:230-233,271,278; ~/KERNEL/product/research/02-autotuning-i-agenci-kerneli.md:47-52,283-298; ~/KERNEL/qwen-opt/NOTES.md:166-168,359; ~/KERNEL/product/research/15c-nowe-silniki.md:249; ~/KERNEL/product/research/15f-agentowa-nauka.md:178-182
status: aktualne
---
# Pomiar: przeplatane A/B (ABBA) na ms/krok

**Porównania robimy w jednej binarce, przeplatając warianty (ABBA), na metryce ms/krok, z kilkoma seedami i promptami; pojedynczy przebieg nic nie dowodzi.**

- **Metryka ms/krok, nie t/s.** Przy T=1 t/s zależy bardziej od wylosowanego tekstu (tok/krok) niż od kernela; ms/krok jest wiarygodne (NOTES 2026-10-12, Vulkan MMVQ: „powtarzalne co do 0.3 ms”).
- **Zestaw:** `spec_sweep` 6 promptów PL/EN × 3 seedy, T=1; llama-bench `-r 5` × 3 rundy albo 2 rundy spec_sweep.
- **ABBA zamiast ABAB:** przy limicie mocy B startuje na rozgrzanej karcie (raport 02).
- **Wiele procesów:** losowe spowolnienia per proces (gate+up 24.3 → 27.2 µs w 4/8 profili, także na buildzie bez zmian; NOTES).
- **Statystyka:** `loo.py` liczy sparowany 95% CI (t Studenta) i flagi NEUTRAL / REMOVAL FASTER.

Skala szumu z literatury (raport 02): ten sam config 12× jednego dnia: +17.3…+26.7%; ten sam SKU GPU: średnio 8%, maks. 22%; laptop na baterii 163.1 → 98.5 t/s. Stąd rekomendacja dla produktu: test A/A, przedziały ufności, zysk tylko przy |Δ| > 2σ.

Uzupełnienia (2026-10-16):
- Dwie klasy obciążenia zawsze osobno: nowe pisanie (spec_sweep PL/EN, T=1) i kopiowanie/edycje; T=0 i T=1 osobno – benchmarki konkurencji wygrywają doborem promptu (tqLLM: 273 t/s na LocalMaxxing vs 131–155 t/s na WikiText; raport 15c).
- Próg z A/A (raport 15f): para przebiegów z tym samym labelem w jednej sesji różni się o 0.09% ms/krok (mediana z 15 par); minimalny wykrywalny efekt przy 2–3 rundach ABBA ~0.2–0.3% `[INFERENCE]`. Wybory konfiguracji na 6 promptach wymagają zestawu odłożonego ([[zestaw-odlozony]]).

## Powiązane
- [[metody/_hub|Metody]]
- [[ms-na-krok]]
- [[loo]]
- [[spec-sweep]]
- [[raport-02-autotuning]]
- [[lekcja-benchmark-kopia]]
