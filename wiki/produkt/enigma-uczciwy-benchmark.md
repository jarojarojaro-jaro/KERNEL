---
typ: produkt
tags: [produkt, enigma, benchmark, aplikacja]
aktualizacja: 2026-11-05
zrodlo: git 1af7fd2 (app/engine); ~/qwen-opt/queue/logs/enigma-xtx2.log:50,67,100; ~/qwen-opt/queue/logs/enigma-xtx3.log:32,43,61,108,125-127,141
status: aktualne
---
# Enigma: uczciwy benchmark optymalizacji (G1–G4, G7) i E2E na XTX

**Commit 1af7fd2 (2026-11-05) naprawił audyt 63e: jedno obciążenie renderowane na baseline (te same tokeny, ten sam reasoning effort) dla każdego ramienia, ramię decode T=1, rozgrzewka przed pomiarem, próg szumu, deep 32k w decyzji i potwierdzenie zwycięzcy.**

E2E na RX 7900 XTX (Qwen, baseline upstream-linux-x64-rocm vs kandydat `enigma`):
- 14:30 (stary bench): decode 34.9 → 101.8 t/s (+191.5%) — **nieuczciwe**, ramiona dostały różne prompty ([[lekcja-benchmark-te-same-tokeny]]).
- 15:08 (uczciwy bench, reasoning effort low): decode 35.0 → 97.8 t/s (+179.8%), potwierdzone powtórką (szum baseline 0.1%, próg 2.0%); greedy 102.7; prefill 1004 → 1041 t/s (+4%); deep 32630 tok. decode 30.3 → 111.3 t/s. Kandydat `lookup` odrzucony (+0.7%, w szumie).

Zawyżenie starym benchmarkiem: ~12 pkt proc. zysku.

## Powiązane
- [[produkt/_hub|produkt]]
- [[aplikacja-w-budowie]]
- [[lekcja-enigma-apu-jako-karta]]
- [[reward-hacking-inferencji]]
- [[lekcja-benchmark-te-same-tokeny]]
