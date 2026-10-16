---
typ: metoda
tags: [metody, poprawnosc, bramka]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:64-70,227-228,262-265; ~/KERNEL/qwen-opt/NOTES.md:357,377; ~/KERNEL/qwen-opt/STATUS-NEXT.md:15; ~/KERNEL/qwen-opt/research/qwen-round5.md:10-16,26-28; ~/KERNEL/product/research/09-chmura-3090.md:74-85; ~/KERNEL/product/research/09-chmura-3060.md:111-127; ~/KERNEL/product/research/15c-nowe-silniki.md:147-149,213,287; ~/KERNEL/product/research/14-nemotron-3090.md:233-258
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

Ważne (kampania NVIDIA, 2026-10-16): baza to zawsze **poprzedni build forka**, nie upstream. Fork różni się od upstreamu w greedy przez łatki bez przełącznika (MMVQ multi-kolumna 0001/0002, prolog GDN 0013); dlatego względem upstreamu stosujemy bramkę KLD (na RTX 3060 fork na poziomie szumu), a nie md5.

Uzupełnienia z raportu 15c: (1) metryka „α kroków zaokrąglenia względem kernela domyślnego” `sqrt(Σ(c−d)²/Σ(w²/12))` (Magnitude `comparison.rs:16-19`) jako uzupełnienie referencji FP64 dla niebitowych łatek; (2) świadek subnormalny dla dekodu 4-bit: x = 2^-126 przy pre-scalingu daje 0x0080 → 0x0000 (TensorFold `e9bf19d9`).

Przykład odrzucenia: pierwszy GDN fast (58e578967) dał plain `0b7b073b` zamiast `c4708318`: inna kontrakcja FMA (94 vs 83 FMA w ISA), commit wycofany.

Przykład z KLD (2026-10-16): Nemotron `TOPK_MOE_NP2` KLD 0.00214 vs szum upstreamu ub256 0.00225 (PASS); z `NP2=0` logity bit w bit równe upstreamowi (PPL 5.921825) ([[2026-10-16-nemotron-3090]]).

## Powiązane
- [[metody/_hub|Metody]]
- [[bramka-kld-kanarki]]: gdy numeryka się zmienia
- [[emulator-isa]]: dowód bitowości offline
- [[greedy-check]]
- [[determinizm-fma]]
- [[lekcja-md5-wzgledem-upstreamu]]
