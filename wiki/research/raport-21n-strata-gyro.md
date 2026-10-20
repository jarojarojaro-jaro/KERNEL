---
typ: research
tags: [research, strata, moe, konkurencja]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/21n-strata-020-gyro.md:7-11,15,46-54,88,96-109
status: aktualne
---
# Raport 21n: Strata 0.2.0-beta i Gyro-S (Qwen3.8-Flash-Next) na XTX

**Strata 0.2.0 to w 55% aplikacja, silnik ma tylko 6% zmian i nic nowego dla gfx1100; Gyro-S (1.708 bpw eksperci) to plik dla progu 32 GB, nie dla naszej maszyny – nie testujemy teraz (2026-10-19).**

- Gyro-S: plik 58.48 GB, eksperci 24.02 GiB, tabela PLE 26.82 GiB na SSD; wszystkie 512 × 48 ekspertów (`21n:46-51`).
- Szacunek XTX: Gyro-S ~51–79 t/s bez MTP, IQ3_S ~43–65 t/s [INFERENCE] (`21n:88`); nasz 27B robi 100 t/s czat i 170 t/s code-edit (`21n:8`).
- „Nie mieści się” było nieaktualne: IQ3_S potrzebuje ~50 GB RAM + VRAM (`21n:9`).
- Do przejęcia: krzywa trafień cache ekspertów H(f) = 1 − (1 − f)³, wątki = rdzenie fizyczne, rozgrzewka BLAS, odpowiednik `strata connect` (`21n:103-107`).
- Kill dla powrotu: sweep T=1 < 50 t/s albo pass rate < 27B (`21n:99`).

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[strata]]
- [[raport-21g-nowe-silniki]]
- [[qwen3-8-27b]]
