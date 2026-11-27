---
typ: model
tags: [modele, moe, qwen]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/33-modele-na-karty.md:19-23; ~/KERNEL/product/research/35-xtx-eksperymenty-z-researchu.md:21
status: do-sprawdzenia
model: qwen3-6-35b-a3b
rozmiar: 35B-A3B
kwant: UD-Q3_K_XL
karty: rtx-5060-ti
wynik: qwen3-6-35b-a3b | rtx-5060-ti | 115.9 t/s | dekod mediana; LM | 2026-10-20
---
# Qwen3.6-35B-A3B (MoE 35B/3B)

**Wybór raportu 33 dla kart 10–16 GB przy ctx ≥ 131k: eksperci częściowo w RAM (`--n-cpu-moe`), KV q4_0; szacunki fitcalc, niezmierzone u nas (2026-10-20).**

- 3080 10 GB: UD-IQ4_XS 18.2 GB, ncmoe 28, 64/55/47 t/s przy 0/64k/131k `[SZACUNEK]`.
- 5060 Ti: UD-Q3_K_XL 17.2 GB, ncmoe 8, 95/66/50 `[SZACUNEK]`; LM mediana 115.9 t/s.
- Bramka jakości E7 (KLD do BF16) w toku w raporcie 35.

<!-- TABELE:START -->
## Wyniki z notatek (1)

Najlepszy wynik na metrykę z pól `wynik` notatek testów (tools/tabele.py, 2026-11-28); pełna tabela: [[najlepsze-wyniki]].

| karta | metryka | najlepszy | warunki | data | źródło |
|---|---|---|---|---|---|
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | dekod mediana | **115.9 t/s** | LM | 2026-10-20 | [[qwen3-6-35b-a3b]] |
<!-- TABELE:END -->

## Powiązane
- [[modele/_hub|modele]]
- [[raport-33-modele-na-karty]]
- [[raport-plan-nv-v2]]
- [[qwen3-8-27b]]
