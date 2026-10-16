---
typ: lekcja
tags: [lekcje, pomiar, pasmo]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:273; ~/KERNEL/qwen-opt/NOTES.md:54,104
status: aktualne
---
# Błędny roofline (bajty na token zamiast na przebieg)

**„1075 GB/s, 112% peaku” wyszło z liczenia bajtów na token zamiast na przebieg modelu; poprawnie: bajty na przebieg × tokeny na krok.**

Tryb awarii #12. Przy spekulacji jeden przebieg wag obsługuje kilka tokenów, więc dzielenie bajtów przez czas tokenu zawyża pasmo ponad fizyczny sufit (960 GB/s dla 7900 XTX). Wynik > 100% peaku to zawsze błąd metodyki.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-mikrobench-klamie]]
- [[lekcja-siatka-pelna-fala]]
- [[sufit-pasma-i-mapa-czasu]]
- [[rx-7900-xtx]]
