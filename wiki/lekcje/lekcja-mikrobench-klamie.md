---
typ: lekcja
tags: [lekcje, pomiar, mmvq]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:268; ~/KERNEL/qwen-opt/NOTES.md:247; ~/KERNEL/product/research/66d-saber-engine-rdna.md:123-126
status: aktualne
---
# Mikrobench kłamie

**Mikrobenchmark dał inną decyzję niż model (Q6_K z GLC|DLC); decyzje o kernelach podejmujemy tylko na rocprofv3 w pełnym modelu.**

Tryb awarii #7 z raportu 07. Mikrobench w izolacji ma inną zawartość cache (L2, MALL 96 MB) niż kernel w środku kroku modelu, więc polityka cache (GLC/DLC) wypada w nim inaczej. Reguła z AKO4ALL: ten sam reżim pomiaru w rankingu i w werdykcie. Wynik pygpubench: czyszczenie cache odczytem bufora > L2 + MALL.

Aktualizacja 2026-11-07 (R66d): Saber stroi „IC-cold”: rotuje bufory, aż `(kopie − 1) × bajty ≥ 64 MiB` (MALL R9700), i zapisuje 2× MALL między próbkami. Sama rotacja trzech kopii dawała 925 GB/s = 1.46× szczytu DRAM, a wycofana reguła BK=64 była +30% na gorąco i −11% na zimno. Dla XTX: scrub 192 MB ([[saber-engine]]).

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-bledny-roofline]]
- [[lekcja-jeden-prompt]]
- [[mmvq-multikolumnowe]]
- [[pygpubench]]
