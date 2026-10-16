---
typ: metoda
tags: [metody, profilowanie, launch-overhead]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:358,373; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:206-214
status: aktualne
---
# Mikrobenchmark granicy kernela

**Zanim zainwestujemy w fuzje albo nowy sposób wysyłania pracy, mierzymy, ile kosztuje sama granica między kernelami na danym stosie.**

Pomiary na RX 7900 XTX (ROCm 10.0, 2026-10-14):

| ścieżka | koszt granicy | źródło |
|---|---|---|
| graf HIP (także pusty kernel) | ~2.53 µs (runda 2), 2.75 µs (runda 4) | NOTES:358, 373 |
| każdy wariant AQL (własna kolejka ROCr, dowolny fence, kernargi w VRAM, bez bitu bariery) | ≥ 2.08 µs | NOTES:373 |
| bufor poleceń PM4 (jeden pakiet vendor, dispatche z wait + inwalidacją cache, kernargi w VRAM) | 0.46–0.86 µs (+1 µs z kernargami w pamięci hosta) | NOTES:373 |
| bariera siatki w kernelu trwałym | 0.5–0.8 µs | NOTES:358 |
| łańcuch dużych faz w jednym kernelu z czekającymi blokami | 8–11 µs/faza (odpada) | NOTES:358 |

`hipExtAnyOrderLaunch` jest ignorowany przy przechwytywaniu strumienia. Ten pomiar uzasadnił łatkę 0060 (replay PM4): LFM 3.887 → 3.424 ms/token.

## Powiązane
- [[metody/_hub|Metody]]
- [[sufit-pasma-i-mapa-czasu]]
- [[pm4-replay]]
- [[pm4]]
- [[playbook-optymalizacji]]
