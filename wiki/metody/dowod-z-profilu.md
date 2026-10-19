---
typ: metoda
tags: [metody, profilowanie, pomiar]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21j-flameox.md:234-247; flameox docs/adapters.md:144-181
status: aktualne
---
# Zasady uczciwego dowodu z profilu

**Każde podsumowanie trace'u/profilu musi mówić, ile pokrywa: liczba wierszy razem, zachowanych i wyciętych (z oknem w ns), liczba kolejek i strumieni, union-busy vs sum-busy (różnica > 0.1% → ostrzeżenie); pusty selektor albo 0 dopasowań to INCOMPLETE z kodem ≠ 0, a profil z `GGML_HIP_PM4` ≠ 0 jest odrzucany (P2 z raportu 21j, 2026-10-19).**

Dalej: selekcja przed obcięciem (nie „pierwsze 1000 wierszy”), tożsamość serii z device/dtype/shape/wariantem, nie mieszać zegarów (`hip_event` vs `host_monotonic`) pod jedną nazwą metryki, osobno liczone rozgrzewki (P5). Do wdrożenia w `trace_breakdown.py` i `attsum.py` ([[att-gfx1100]]); zapobiega klasie błędu „profil z PM4 = 1 albo pusty regex wygląda jak prawdziwy”.

## Powiązane
- [[metody/_hub|Metody]]
- [[rocprof]]
- [[sufit-pasma-i-mapa-czasu]]
- [[raport-21j-flameox]]
