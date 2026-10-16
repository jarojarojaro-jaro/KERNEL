---
typ: lekcja
tags: [lekcje, mtp, vram, nvidia]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/09-chmura-5060ti.md:19,28,89,127,196; ~/KERNEL/product/research/14-nemotron-3090.md:52-55,198
status: aktualne
---
# Pułapka upstream: -fit on ze spekulacją (MTP na 16 GB, DFlash na 24 GB)

**Upstreamowe `-fit on` źle liczy pamięć spekulacji. Na RTX 5060 Ti 16 GB upstreamowy serwer z `-fit on` i MTP dawał 7.7 t/s, wolniej niż bez spekulacji, bo `-fit` przy ciasnym VRAM zostawiał część pracy MTP na CPU; `-fit off -ngl 99 -t 8` dało 31.8 t/s na tym samym prompcie.**

Objawy (2026-10-16): serwer 760% CPU, GPU 0–14%. Test jednego promptu: `-fit on -t 32` 6.3, `-t 8` 14.0, `-fit off -ngl 99 -t 8` 31.8 t/s; `--backend-sampling` nie pomaga (14.5). Nasz fork z `-fit on` nie miał problemu (45.5). Na 3090 (24 GB) tego nie widać.
Ta sama klasa błędu z drafterem DFlash (Nemotron 3.5 Bolt na RTX 3090 24 GB, 2026-10-16): `-fit on` nie umie zmierzyć draftera („failed to measure the memory of the extra model, fitting without it”), więc dało 67 t/s przy `-c 65536` wobec 95 t/s przy pełnym offloadzie.

Reguły: przy MTP lub osobnym drafterze na kartach 16 GB nie używać `-fit on`, tylko pełny offload i jawne `-t`; pierwszą serię sweepów z tą konfiguracją odrzuciliśmy jako niereprezentatywną. Dla produktu: estymator pamięci musi uwzględniać bufory MTP, a kalibracja powinna wykrywać „GPU bezczynne przy pełnym obciążeniu CPU”.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-limit-cpu-kontenera]]
- [[lekcja-md5-wzgledem-upstreamu]]
- [[rtx-5060-ti]]
- [[glowica-mtp]]
- [[raport-14-nemotron-3090]]
