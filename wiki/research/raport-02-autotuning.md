---
typ: research
tags: [research, autotuning, agenci]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/02-autotuning-i-agenci-kerneli.md:12-59
status: aktualne
---
# Raport 02: autotuning i agenci kerneli

**Duże „przed → po” robi praca wykonana raz w labie, nie strojenie u użytkownika; agenci kerneli działają tylko z mocną bramką i zostają w labie.**

- U nas 59 → 92 → 109 t/s na Qwenie dały kernele, MTP i draft head; Kernel Tuner na gotowych kernelach ggml to szacunkowo 1–2% kroku.
- Konfiguracja daje skoki tylko przy złym starcie (jedna warstwa mniej na GPU: tg 131.7 → 71.8 t/s; nasz BACO: 4.4 zamiast 92 t/s); ponad dobry default typowo 0–15%.
- Agenci: METR średnio 1.81× przy ~$20/zadanie, Kevin-32B 1.41×, ale uczciwy pomiar KernelBench L1 to mediana 1.0001×, a Sakana spadła z 3.13× do 1.49× po usunięciu reward hackingu.
- Pomiar konsumencki to główne ryzyko: ten sam SKU różni się średnio o 8% (maks. 22%), laptop na baterii 98.5 zamiast 163.1 t/s.
Rekomendacja: (a) tuning DB w chmurze per (arch, model, quant, build), (b) lokalna kalibracja 1–5 min, (c) opcjonalny „deep tune” na noc z prekompilowanych wariantów, (d) agenci tylko w labie.

## Powiązane
- [[research/_hub|research]]
- [[raport-01-konkurencja]]
- [[raport-07-metody]]
- [[metr-sakana]]
- [[pomiar-abba]]
