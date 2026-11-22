---
typ: karta
tags: [karty, amd, maszyna]
aktualizacja: 2026-11-22
zrodlo: ~/kernel/system.md (sekcja „Na jaroserverai”); ~/kernel/zasady-jaroserverai.md; ~/KERNEL/wiki/decyzje/2026-10-20-karta-fabrycznie.md; ~/KERNEL/wiki/decyzje/2026-11-06-profil-eco-2200.md
status: aktualne
karta: jaroserverai
vram: 24 GB (RX 7900 XTX)
pasmo: 960 GB/s
gdzie: dom JARO, Tailscale
stan: zwykle wyłączony; włącza JARO
---
# jaroserverai: maszyna z naszą RX 7900 XTX

**Domowa maszyna JARO z jedyną naszą stałą kartą GPU, [[rx-7900-xtx]] (24 GB, gfx1100): produkcyjny czat na :8080 i wszystkie testy XTX przez kolejkę GPU; zwykle wyłączona, testy tylko na wyraźne polecenie JARO.**

- **Produkcja:** czat :8080 (topka, Qwen3.8-27B-Uncensored Q4_K_M ze spekulacją MTP); startuje go tylko `topka-keeper.sh`, test zatrzymuje go tylko pod własną blokadą GPU i przywraca `chat8080.sh restore`.
- **Kolejka GPU:** `~/qwen-opt/queue/run-jobs.sh` (linie `nazwa|timeout|katalog|polecenie`, FIFO, blokady `/tmp/gpu.lock` i `/tmp/quiet.lock`), jedno zadanie ≤ 15 min, ostatnie zawsze przywraca :8080; strażnik [[gpu-guard]] pilnuje temperatur.
- **Karta:** fabryczne ustawienia ([[2026-10-20-karta-fabrycznie]]), profil eco 2200 MHz ([[2026-11-06-profil-eco-2200]]); absolutne liczby z eco są ~7% niżej niż ze stock, porównujemy tylko w tej samej sesji.
- **PM4:** każdy test naszego forka z jawnym `GGML_HIP_PM4=0` albo `GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0`.
- **CPU:** ciężkie przez `cpuheavy` (2 sloty × 2 rdzenie, nice 19), kompilacje przez `rbuild`; testowe serwery `taskset -c 2-5`.
- **Przerwy:** maszyna znika z Tailscale bez ostrzeżenia (2026-11-20 ~20:52 i ~00:30, 2026-11-21 ~11:48); zadań sprzed przerwy nie zakładamy jako wykonanych.

## Powiązane
- [[rx-7900-xtx]]
- [[google-colab]]
- [[vast-ai]]
- [[KOLEJKA-TESTOW]]
