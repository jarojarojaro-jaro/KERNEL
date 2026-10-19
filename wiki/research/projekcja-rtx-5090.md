---
typ: research
tags: [research, nvidia, rtx-5090, szacunek]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21b-gpu-perf-zasoby.md:156-166
status: do-sprawdzenia
---
# Projekcja RTX 5090: narzut kerneli waży tam najwięcej

**Stały narzut ~1.46 ms/token zmierzony dla LFM Q4_K_M na 5060 Ti (4.81 ms/token, podłoga ~3.35 ms przy 448 GB/s) przeniesiony na 5090 (1.792 TB/s, podłoga 0.84 ms) daje tylko 435–571 t/s, czyli 37–48% pasma – narzut to tam 40–63% czasu tokenu (`[SZACUNEK]`, raport 21b, 2026-10-19).**

Qwen UD-Q4_K_XL plain: podłoga 16.48 / 1.792 = 9.20 ms; narzut z 3090 5.28 ms → 69–76 t/s. Wniosek: techniki przeciw przerwom między kernelami (PDL, prefetch przed czekaniem, trwały blok MoE) są na 5090 warte ~2× więcej niż na kartach, które mierzyliśmy; nikt u nas 5090 nie mierzył (E2 z 21b, ~$1–2, decyzja użytkownika).

## Powiązane
- [[research/_hub|research]]
- [[karty-nvidia-parametry]]
- [[pdl-mmvq-trigger]]
- [[nvidia-wyniki-2026-10-16]]
