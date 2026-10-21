---
typ: kernel
tags: [kernele, mmvq, spekulacja]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:38-47,59-78,89,241-256; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:76-77,96-97; ~/KERNEL/product/research/08-analiza-platformy-latek.md:24; ~/KERNEL/product/research/patch-manifest.json (0001, 0002, 0021, 0022); ~/KERNEL/product/research/16i-magnitude-co-robia-dobrze.md:89-95,240; ~/KERNEL/product/research/21l-reverse-engineering-gpu.md:40-41; ~/KERNEL/product/research/21l-skrypty/rga-livereg-mmvq-q4k-ncols5.txt; ~/KERNEL/product/research/47-kernel-lab.md:14-18; ~/KERNEL/product/research/50a-mmvq-q4k.md:9-14; ~/KERNEL/product/research/50b-mmvq-q5k.md:5-16; ~/KERNEL/product/research/50c-mmvq-q6k.md:5-20; ~/KERNEL/product/research/50d-mmvq-iq4xs.md:15-26
status: aktualne
---
# MMVQ wielokolumnowe (weryfikacja spekulacji)

**Kernel matvec, który przy weryfikacji 2–8 tokenów rozpakowuje wagi raz i mnoży je przez wszystkie kolumny; podstawa całego przyspieszenia spekulacji MTP/DFlash na RX 7900 XTX.**

Problem (NOTES): upstream liczył każdą kolumnę osobno, więc przy 8 kolumnach czytał 240–340 GB/s zamiast ~700.

**0001–0002 (2026-10-09, commity 95a0c83d6, 72cfa5656):** `vec_dot_q_multi`, człon min Q4_K/Q5_K z sum bloków q8_1 (połowa dp4a), szerokie ciągłe odczyty, 2 wiersze/blok przy 2–4 kolumnach i 4 przy 5–8. Typy: Q4_K, Q5_K, Q6_K, IQ4_XS, IQ4_NL, Q2_K, IQ2_*, IQ3_*, IQ1_*. Mikrobench 5120×17408, 8 kolumn: Q5_K 296 → 621 GB/s, Q2_K 132 → 272 GB/s. Qwen MTP n=4: 68.6 → 82.3 t/s (EN).

**0021–0022 (K1, 2026-10-13, 60ce2a71f + 9f83f1f81):** buffer resource + offsety 32-bit w SGPR, `amdgpu_waves_per_eu` per (typ, n), pipelining Q6_K, transponowany butterfly DPP, odczyty wag GLC|DLC. MMVQ w weryfikacji 24.3 → 22.1 ms; Qwen 35.67 → 33.17 ms/krok (88.1 → 94.7 t/s), Uncensored 33.79 → 32.02 (90.4 → 95.4).

Poprawność: bitowo identyczne (`test-backend-ops -o MUL_MAT` 2444/2444). Wyłącznik: brak, tylko build. Platformy (raport 08): ścieżka z 0001/0002/0021 nie ma strażnika arch, więc działa też na NVIDIA i innych RDNA (nigdy tam nieuruchomiona); 0022 tylko RDNA3.

Wzorzec z Magnitude (2026-10-16): swap-AB GEMV na `mma.m16n8k16` (wagi jako A, wiersze aktywacji jako N=8), wynik wiersza niezależny od M, więc M = 1..16 bitowo jak M = 1 – warunek weryfikacji W16 w trybie bitexact ([[raport-16i-magnitude]], technika #5).

Klif VGPR (21l, 2026-10-19): MMVQ Q4_K 4 kolumny 88–89 VGPR (16 fal/SIMD), 5 kolumn 140–141 (10 fal), 8 kolumn 190–191; szczyt 136 żywych VGPR w bloku `v_dot4_i32_iu8`. Kandydat: ncols=5 ≤ 120 VGPR (12 fal) albo weryfikacja jako 4+1 ([[co-stats]]).

## Aktualizacja 2026-10-21
- Profil klab topki: Q5_K 1.65 ms/krok (84% pasma), IQ4_XS 0.91, Q4_K 0.65, Q6_K 0.59 ([[raport-47-kernel-lab]]).
- Q4_K: pipe + 8 fal odrzucone ([[raport-46-mmvq-big]]); kernel strumieniowy −0.28 ms/krok `[SZACUNEK]` ([[raport-50a-mmvq-q4k]]).
- Q5_K: `big_rows` −1.3…−3.5% ([[raport-50b-mmvq-q5k]]); Q6_K: potok ping-pong −0.15 ms `[SZACUNEK]` ([[raport-50c-mmvq-q6k]]); IQ4_XS: `ryp2` −0.16 ms ([[raport-50d-mmvq-iq4xs]]); k/v 1024 wierszy −0.03 ms ([[raport-49-mmvq-ogon-1024]]).
- Wszystkie bitowo zgodne, żaden bez bramki md5/ABBA E0 (GPU stop 2026-10-21).

## Powiązane
- [[kernele/_hub|Kernele]]
- [[wmma-small-n]]: 9–16 kolumn
- [[mmvq-n1-wiersze]]: wariant 1-kolumnowy
- [[glowica-mtp]]
- [[sufit-pasma-i-mapa-czasu]]
