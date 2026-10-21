---
typ: research
tags: [research, modele, nvidia]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/33-modele-na-karty.md:15-27
status: aktualne
---
# Raport 33: najlepsze modele lokalne na klasę karty (ctx ≥ 131k)

**Na 10–16 GB wygrywa Qwen3.6-35B-A3B z ekspertami w RAM (`--n-cpu-moe`), na 24–32 GB Qwen3.8-27B z MTP (2026-10-20, szacunki fitcalc).**

- 3080: UD-IQ4_XS, ncmoe 28, 64/55/47 t/s przy 0/64k/131k `[SZACUNEK]`; 5060 Ti: UD-Q3_K_XL, 95/66/50.
- fitcalc v2: iSWA (Gemma 4), MLA, MoE, drafter jako osobny plik.

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-20-21]]
- [[qwen3-6-35b-a3b]]
- [[gemma-4]]
- [[raport-plan-nv-v2]]
