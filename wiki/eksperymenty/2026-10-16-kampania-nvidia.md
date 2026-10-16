---
typ: eksperyment
tags: [eksperymenty, nvidia, chmura, faza-0]
aktualizacja: 2026-10-16
zrodlo: ~/qwen-opt/cloud/PLAN-TESTOW.md:1-6,51-71,162-178; ~/KERNEL/product/research/09-chmura-3090.md:3-7,176-185; ~/KERNEL/product/research/09-chmura-5060ti.md:3-5,189-191,205-212; ~/KERNEL/product/research/09-chmura-3060.md:3-5,225-231
status: aktualne
---
# 2026-10-16: pierwsza kampania na kartach NVIDIA (Vast)

**Faza 0 E2/E4 zakończona: trzy karty (RTX 3090, 5060 Ti, 3060) równolegle, ≈ $2.77 z $5; łatki budują się i działają na NVIDIA, dają ×1.4–2.0 na Qwen/LFM, ale greedy nie jest bitowo równy upstreamowi.**

Konfiguracje: A0 upstream tylko `-m`, A1 najlepsze flagi upstream, A2 fork z flagami A1 (+ słownik draftu i IQ4_XS dla Qwena), A2-safe fork z 31 przełącznikami = 0, profil per arch. Etapy: test-backend-ops → greedy md5 na świeżych serwerach → bisekcja i diff węzłów → llama-bench ABCDDCBA → spec_sweep ABBA → nsys.

Kryteria (PLAN-TESTOW): S1 kompilacja – tak na sm_86 i sm_120 (sm_89 nietestowane, brak karty); S2 testy op – tak na sm_86, na sm_120 2 FAIL tolerancji w opie forka `GATED_DELTA_NET_PROLOGUE`; S3 greedy A2 = A1 – `DIFF-BUILD`, wytłumaczony łatkami z listy (0001/0002, 0013), KLD na 3060 na poziomie szumu; S4 ms/krok A2 ≤ A1 + 1% – tak, z zapasem; S5 liczby do ekranu wyniku – tak (`scorecard.json` dla 3 kart); S6 koszt ≤ $8 i żadna instancja po terminie – tak.

Koszt: 3090 ≈ $0.90, 5060 Ti ≈ $1.05, 3060 ≈ $0.82.

Incydenty: pierwsza instancja 3090 odrzucała klucz SSH (zniszczona po ~9 min); na 5060 Ti nadpisanie działającego skryptu przez `scp` przerwało fazę pomiaru; pierwsza seria sweepów na 5060 Ti odrzucona przez pułapkę `-fit on`. Szczegóły liczb: [[nvidia-wyniki-2026-10-16]].

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[nvidia-wyniki-2026-10-16]]
- [[harness-chmurowy]]
- [[cuda-compat]]
- [[2026-10-16-budzety-chmury]]
- [[lekcja-nadpisanie-dzialajacego-skryptu]]
