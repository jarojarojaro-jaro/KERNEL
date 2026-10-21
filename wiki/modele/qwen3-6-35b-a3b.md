---
typ: model
tags: [modele, moe, qwen]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/33-modele-na-karty.md:19-23; ~/KERNEL/product/research/35-xtx-eksperymenty-z-researchu.md:21
status: do-sprawdzenia
---
# Qwen3.6-35B-A3B (MoE 35B/3B)

**Wybór raportu 33 dla kart 10–16 GB przy ctx ≥ 131k: eksperci częściowo w RAM (`--n-cpu-moe`), KV q4_0; szacunki fitcalc, niezmierzone u nas (2026-10-20).**

- 3080 10 GB: UD-IQ4_XS 18.2 GB, ncmoe 28, 64/55/47 t/s przy 0/64k/131k `[SZACUNEK]`.
- 5060 Ti: UD-Q3_K_XL 17.2 GB, ncmoe 8, 95/66/50 `[SZACUNEK]`; LM mediana 115.9 t/s.
- Bramka jakości E7 (KLD do BF16) w toku w raporcie 35.

## Powiązane
- [[modele/_hub|modele]]
- [[raport-33-modele-na-karty]]
- [[raport-plan-nv-v2]]
- [[qwen3-8-27b]]
