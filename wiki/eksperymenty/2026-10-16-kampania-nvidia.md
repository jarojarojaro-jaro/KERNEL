---
typ: eksperyment
tags: [eksperymenty, nvidia, chmura]
aktualizacja: 2026-10-16
zrodlo: ~/qwen-opt/cloud/PLAN-TESTOW.md:1-6,51-71,162-178; ~/qwen-opt/cloud/results/ (stan 2026-10-16 ok. 02:40 UTC)
status: do-sprawdzenia
---
# 2026-10-16: pierwsza kampania na kartach NVIDIA (Vast), w toku

**Faza 0 E2/E4: czy łatki forka działają poprawnie i dają zysk na NVIDIA; trzy karty (RTX 3060, 5060 Ti, 3090) jedna po drugiej, budżet ≤ $8, plan ~$2.5.**

Konfiguracje (bench.sh): A0 upstream bez flag („typowa aplikacja”), A1 upstream + konfiguracja (FA, KV q8_0, ctx 32k, MTP n=4), A2 fork z flagami A1, A2s fork z 31 przełącznikami = 0, A3 pełny stack (słownik draftu, draft IQ4_XS). Etapy: test-backend-ops → greedy md5 (świeże serwery) → bisekcja → llama-bench ABCDDCBA → spec_sweep ABBA.

Kryteria sukcesu: S1 kompilacja sm_86/89/120, S2 brak nowych błędów testów, S3 greedy A2 = A1 (`BIT`), S4 ms/krok A2 ≤ A1 + 1%, S5 liczby do ekranu wyniku, S6 koszt ≤ $8 i żadna instancja po terminie.

Stan w chwili zapisu: S1 spełnione (3090, 5060 Ti, 3060); S2 na 3090 tak (19253/19253), na 5060 Ti 2 FAIL w prologu GDN; S3 nie — `DIFF-BUILD` na wszystkich modelach; bisekcja na gałęziach z dodatkowymi wyłącznikami trwa. Szczegóły liczb: [[nvidia-wyniki-2026-10-16]].

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[nvidia-wyniki-2026-10-16]]
- [[harness-chmurowy]]
- [[cuda-compat]]
- faza-0
