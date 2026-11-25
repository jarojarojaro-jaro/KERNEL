---
typ: lekcja
tags: [lekcje, proces, optymalizacja]
aktualizacja: 2026-11-25
zrodlo: JARO 2026-11-25 04:26 („idzie nam jak krew z nosa, trzeba wejść na level wyżej”); [[metoda-nib-level-up]]; noc Bonsai 2026-11-24/25
status: aktualne
---
# Lekcja: przegrywamy procesem, nie wiedzą o kernelach

**Jedna osoba z agentem zrobiła Nib (silnik pod Inkling na XTX, szybszy od naszej Mai przy T=0,7: 130–151 vs 112,5 t/s) w kilka dni, bo każdy wariant mierzy w 30-sekundowej pętli build → test → zegar całego kroku; my na Bonsai potrzebowaliśmy 13 rund i ~5 h, a większość czasu zjadły buildy 4–15 min, kolejka, ręczne składanie jobów i mikrobenchmarki.**

- Co: mamy playbook i ~70 łatek, ale pętla jest powolna i ręczna (skrypty składane na nowo, łatki trzech agentów scalane ręcznie, wynik z mikrobenchu brany na serio).
- Dlaczego: ogólny fork (długi build, port architektury), brak jednej komendy perf, brak księgi µs/token, brak oracle w silniku.
- Reguła: przed optymalizacją nowego modelu najpierw narzędzie `perf` i księga czasu; wariant w runtime; decyzja tylko z e2e; czas pomysł → liczba mierzony i raportowany.

## Powiązane
- [[metoda-nib-level-up]]
- [[playbook-optymalizacji]]
