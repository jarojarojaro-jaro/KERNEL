---
typ: firma
tags: [ludzie-firmy, modele, kwanty]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/10-post-training.md:329-331,540-541; ~/KERNEL/product/research/09-chmura-3060.md:30-39,102
status: aktualne
---
# PrismML

**Autor Ternary Bonsai 2 27B (Qwen3.8-27B w trytach, Apache-2.0) i forka llama.cpp z formatami PQ2_0/PTQ1_0.**

Bonsai: 1.76 bpw, 5.93 GB, 98.2% średniej FP16 na 20 benchmarkach (whitepaper); metoda treningu nieujawniona. Testujemy go na RTX 3060 razem z Saluki (decyzja „tylko na 3060”).

Na RTX 3060 (2026-10-16) ich fork z PTQ1_0 był najszybszy (44.75 t/s); typy PQ2_0/PTQ1_0 (ggml 142/143) są prywatne dla forka, ale PQ2_0 przepakowuje się bez strat do upstreamowego Q2_0.

## Powiązane
- [[ludzie-firmy/_hub|ludzie-firmy]]
- [[conway-research]]
- [[qwen-alibaba]]
- [[prism-llama-cpp]]
- [[bonsai]]
- [[raport-09-chmura-3060]]
