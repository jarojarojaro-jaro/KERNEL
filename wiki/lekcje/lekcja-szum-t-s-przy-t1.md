---
typ: lekcja
tags: [lekcje, pomiar]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:271; ~/KERNEL/qwen-opt/NOTES.md:168
status: aktualne
---
# Szum t/s przy T=1

**Przy T=1 t/s zależy od wylosowanego tekstu bardziej niż od kernela; metryka to ms/krok, kilka seedów i przeplatanie.**

Tryb awarii #10. Przy spekulacji liczba tokenów na krok zależy od treści, więc t/s skacze między przebiegami. Rozwiązanie: mierzyć ms/krok (koszt kroku weryfikacji), stałe seedy, zestaw 6 promptów × 3 seedy, przeplatane A/B.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-jeden-prompt]]
- [[lekcja-losowe-spowolnienia]]
- [[ms-na-krok]]
- [[pomiar-abba]]
