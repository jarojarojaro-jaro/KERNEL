---
typ: research
tags: [research, mmvq, pasmo, sufit]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/24r-mmvq-pasmo.md:7-14,72-76
status: aktualne
---
# Raport 24r: pasmo MMVQ weryfikacji n=5 – sufit 926 GB/s

**Zmierzony sufit odczytu XTX to 926 GB/s (96.5% z 960); weryfikacja n=5 czyta 16.15 GB w 21.2 ms = 762 GB/s (82% sufitu), a strata to ~7–9 µs stałego kosztu na każde z 340 uruchomień MMVQ (~2.4 ms/krok); RPB=1 −3.0% – kill (2026-10-20).**

- Pasmo asymptotyczne z dopasowania 837–873 GB/s (90–94% sufitu) (`24r:9`).
- Małe uruchomienia (k,v 1024×5120) osiągają tylko 40% sufitu (`24r:30`).
- RPB=1: bitowo identyczny, spec_sweep 27.98 → 28.80 ms/krok (`24r:10-13`) – reużycie aktywacji w bloku 4 wierszy jest warte więcej niż rampa siatki.
- PAIR2 (para MMVQ dla mieszanych typów, −40 uruchomień/krok, szac. 0.3–0.5 ms) zakodowany, niezmierzony (`24r:14`).
- Analiza sufitu przed implementacją: [[lekcja-wyrazna-wygrana-albo-nic]], [[lekcja-sufit-wzorca]].

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[raport-24n-mmvq-n5]]
- [[sufit-pasma-i-mapa-czasu]]
- [[lekcja-sufit-wzorca]]
- [[lekcja-wyrazna-wygrana-albo-nic]]
