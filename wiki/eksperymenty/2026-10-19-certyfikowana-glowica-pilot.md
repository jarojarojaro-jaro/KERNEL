---
typ: eksperyment
tags: [eksperymenty, lm-head, wyniki-negatywne]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/18-nastepna-fala.md:453-486; ~/qwen-opt/mtp-train/data/ext_p1/{h.f16,top.bin,meta.txt}
status: aktualne
---
# 2026-10-19: pilot certyfikowanej głowicy LM na Qwenie (CPU) – KILL

**Certyfikat górnej granicy logitów z bazy PCA stanów (metoda knlp) nie odcina na Qwen3.8-27B prawie niczego: przy r = 1843 (0.36·d, jak knlp) baza łapie 87.3% energii h, ρ/‖h‖ = 0.39, a certyfikat top-1 otwiera 97.5% bloków przy N=1 i 98.3% przy N=5 (73 138 prawdziwych stanów).**

| r | energia h | ρ/‖h‖ | top-1 N=1 / N=5 | top-20 N=1 / N=5 | cień int8 / int4 |
|---|---|---|---|---|---|
| 512 | 64.6% | 0.607 | 99.9% / 100% | 100% / 100% | 12.2% / 6.1% |
| 1843 | 87.3% | 0.394 | 97.5% / 98.3% | 99.2% / 99.9% | 43.9% / 21.9% |
| 3584 | 97.1% | 0.220 | 35.3% / 65.7% | 97.5% / 98.3% | 85.3% / 42.7% |

Walidacja: h·W odtwarza zapisane log-proby top-32 z medianą maks. błędu 0.28 logitu, top-1 = następny token 90.6%. Najlepszy punkt (r = 3584, top-1, N=1) czyta 85% + 35% = 120% bajtów głowicy. Cień liczony względem Q6_K jest 2.4× droższy niż u knlp (bf16). Dla LFM (głowica 12% bajtów) pozostaje tania bramka CPU (kill: > 45% bajtów głowicy dla top-1, N=1). Skrypty jednorazowe w `/tmp`, nie zachowane.

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[knlp-lm-head]]
- [[lekcja-lm-head-bottleneck]]
- [[wyniki-negatywne]]
