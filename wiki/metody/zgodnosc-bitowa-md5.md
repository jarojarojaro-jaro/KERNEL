---
typ: metoda
tags: [metody, poprawnosc, bramka]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:64-70,227-228,262-265; ~/KERNEL/qwen-opt/NOTES.md:357,377; ~/KERNEL/qwen-opt/STATUS-NEXT.md:15; ~/KERNEL/qwen-opt/research/qwen-round5.md:10-16,26-28
status: aktualne
---
# Zgodność bitowa (greedy md5, hash logitów)

**Zmiana „bitowo identyczna” musi dać ten sam tekst greedy (md5) na świeżym serwerze i te same logity co baza w tym samym trybie.**

Elementy bramki (raport 07 §2.2.2):
- greedy md5 tekstu, plain i MTP, oba modele, **zawsze na świeżym serwerze**: llama.cpp nie jest deterministyczny w obrębie jednego serwera (2. wywołanie rozjeżdża się po ~270 znakach, upstream e60eff95f też; NOTES 2026-10-14);
- hash FNV pełnych logitów 64 kroków przy głębokości 0 i 3000;
- dla prefillu: logity 2048 tokenów;
- `test-backend-ops` dla zmienionych opów.

Bazy po instalacji 2026-10-15: Qwen plain `c4708318…`, MTP `6f14e814…`, LFM `894e56e4…` (STATUS-NEXT).

Porównujemy MTP z bazą MTP, nie z plain: weryfikacja batcha zmienia numerykę (MTP rozjeżdża się z plain po 129 znakach, DFlash po 229; qwen-round5). Klasy z raportu 07: BIT 45 łatek, SAME-TOK 6 (sampler), DIST 3 (zmienia tylko drafty).

Przykład odrzucenia: pierwszy GDN fast (58e578967) dał plain `0b7b073b` zamiast `c4708318`: inna kontrakcja FMA (94 vs 83 FMA w ISA), commit wycofany.

## Powiązane
- [[metody/_hub|Metody]]
- [[bramka-kld-kanarki]]: gdy numeryka się zmienia
- [[emulator-isa]]: dowód bitowości offline
- [[greedy-check]]
- [[determinizm-fma]]
