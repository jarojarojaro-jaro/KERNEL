---
typ: metoda
tags: [metody, moe, spekulacja, lfm]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/18-nastepna-fala.md:175-198
status: do-sprawdzenia
---
# Model kosztu weryfikacji MoE (LFM2.5)

**Weryfikacja N tokenów w MoE czyta sumę ekspertów wszystkich N tokenów: przy niezależnym routingu u(N) = 64·(1 − (60/64)^N) ekspertów na warstwę, B(N) = 0.761 + 0.254·u(N) GB, T(N) ≈ 1.45 ms + B(N)/0.9 GB/ms; kalibracja T(1) = 3.42 ms vs zmierzone 3.40 (raport 18, 2026-10-19, `[SZACUNEK]`).**

| N | 1 | 2 | 3 | 4 | 5 | 8 | 16 |
|---|---|---|---|---|---|---|---|
| u(N) | 4.0 | 7.8 | 11.3 | 14.6 | 17.7 | 25.8 | 41.2 |
| B(N) GB | 1.78 | 2.73 | 3.62 | 4.46 | 5.24 | 7.32 | 11.23 |
| T(N) ms | 3.42 | 4.48 | 5.47 | 6.41 | 7.28 | 9.58 | 13.93 |

Wnioski: tani drafter albo lookup opłaca się od α ≈ 0.4; LFM2.5-2.6B jako drafter nie (1.5 GB/token); self-spec z top-1 ekspertem czyta 57% bajtów celu – wynik ujemny. Potwierdzenie: pomiar G1 `llama-bench -p 1,2,3,4,5,8,16 -n 0 -d 0,32768` (bramki: T(8) ≤ 13.6 ms, T(3) ≤ 6.8 ms). Literatura: „expert scattering”, EcoSpec ×1.62 (arXiv 2607.12696), MoESD (2505.19645).

## Powiązane
- [[metody/_hub|Metody]]
- [[koszt-szerokosci-weryfikacji]]
- [[lfm2-5-24b-a2b]]
- [[raport-18-nastepna-fala]]
