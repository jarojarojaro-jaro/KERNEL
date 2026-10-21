---
typ: research
tags: [research, konkurencja, benchmarki]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/32f-ninfer-tqllm-dflash2.md:1-22
status: aktualne
---
# Raport 32f: NInfer, tqLLM, DFlash2 – porównywalność rekordów

**Rekordy LocalMaxxing są fizycznie wiarygodne, ale nieporównywalne: T=0 na telegraficznym `reasoning-v1`; w ich warunkach topka dałaby ~82 t/s (5060 Ti), ~125 (3090), ~147 (XTX) `[INFERENCE]` (2026-10-20).**

- Luka do tqLLM ×1.9 (5060 Ti) i ×2.2 (3090); część to mniej bajtów przy gorszym KLD (TQ_S 0.055 vs UD-Q4_K_XL 0.012).

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-20-21]]
- [[tqllm]]
- [[ninfer]]
