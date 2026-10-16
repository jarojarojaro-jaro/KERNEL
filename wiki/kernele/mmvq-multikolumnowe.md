---
typ: kernel
tags: [kernele, mmvq, spekulacja]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:38-47,59-78,89,241-256; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:76-77,96-97; ~/KERNEL/product/research/08-analiza-platformy-latek.md:24; ~/KERNEL/product/research/patch-manifest.json (0001, 0002, 0021, 0022)
status: aktualne
---
# MMVQ wielokolumnowe (weryfikacja spekulacji)

**Kernel matvec, który przy weryfikacji 2–8 tokenów rozpakowuje wagi raz i mnoży je przez wszystkie kolumny; podstawa całego przyspieszenia spekulacji MTP/DFlash na RX 7900 XTX.**

Problem (NOTES): upstream liczył każdą kolumnę osobno, więc przy 8 kolumnach czytał 240–340 GB/s zamiast ~700.

**0001–0002 (2026-10-09, commity 95a0c83d6, 72cfa5656):** `vec_dot_q_multi`, człon min Q4_K/Q5_K z sum bloków q8_1 (połowa dp4a), szerokie ciągłe odczyty, 2 wiersze/blok przy 2–4 kolumnach i 4 przy 5–8. Typy: Q4_K, Q5_K, Q6_K, IQ4_XS, IQ4_NL, Q2_K, IQ2_*, IQ3_*, IQ1_*. Mikrobench 5120×17408, 8 kolumn: Q5_K 296 → 621 GB/s, Q2_K 132 → 272 GB/s. Qwen MTP n=4: 68.6 → 82.3 t/s (EN).

**0021–0022 (K1, 2026-10-13, 60ce2a71f + 9f83f1f81):** buffer resource + offsety 32-bit w SGPR, `amdgpu_waves_per_eu` per (typ, n), pipelining Q6_K, transponowany butterfly DPP, odczyty wag GLC|DLC. MMVQ w weryfikacji 24.3 → 22.1 ms; Qwen 35.67 → 33.17 ms/krok (88.1 → 94.7 t/s), Uncensored 33.79 → 32.02 (90.4 → 95.4).

Poprawność: bitowo identyczne (`test-backend-ops -o MUL_MAT` 2444/2444). Wyłącznik: brak, tylko build. Platformy (raport 08): ścieżka z 0001/0002/0021 nie ma strażnika arch, więc działa też na NVIDIA i innych RDNA (nigdy tam nieuruchomiona); 0022 tylko RDNA3.

## Powiązane
- [[kernele/_hub|Kernele]]
- [[wmma-small-n]]: 9–16 kolumn
- [[mmvq-n1-wiersze]]: wariant 1-kolumnowy
- [[glowica-mtp]]
- [[sufit-pasma-i-mapa-czasu]]
