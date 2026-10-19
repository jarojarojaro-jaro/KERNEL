---
typ: research
tags: [research, reverse-engineering, konkurencja]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/23e-re-silniki.md:1-35; ~/qwen-opt/re/engines/{hipfire,tqllm,magnitude,strata-tf}/NOTES.md
status: aktualne
---
# Raport 23e: RE kerneli dekodu konkurencyjnych silników

**Żaden konkurent nie ma lepszej pętli GEMV niż nasza: przewaga hipfire na XTX (54.3 vs nasze 43.2 t/s plain tg, krok 19.67 vs 23.15 ms) wynika w ~2.7 ms z mniejszej liczby bajtów (~14.3 GB/token, format MQ4G256V2 4.25 bpw, vs 16.83 GB) i w ~0.8 ms z fuzji poza GEMV, a nie z ISA (ich pętla n=1: 138 VALU na 32 wagi/lane, nasza q4_K 61 VALU) (raport 23e, CPU, 2026-10-19).**

Ranking:
1. ~~Rollback GDN przez replay zamiast snapshotów (Strata)~~ – **już mamy**: łatki 0033–0036, `LLAMA_GDN_REPLAY` domyślnie włączone ([[gdn-replay]]); pozycja raportu nieaktualna.
2. Stan GDN w Q8 (hipfire): 302 → ~76 MB odczytu+zapisu na token, ≈ −0.24 ms (+1% tg); stratne – kill: ΔKLD > 0.005 albo < +0.7%.
3. Fuzje poza GEMV (rmsnorm+rotate w prologu, qkvza w jednym GEMV, moe_down+combine+rmsnorm, conv1d+silu+qknorm): górna granica ~0.8 ms ≈ +3.5% tg; najpierw porównać listę kerneli na token.
4. MMVQ_IL (Strata), tylko NVIDIA: +4.2% sm_86, +1.3–2.2% sm_120.
5. Format ~4.25 bpw (~+15% tg) – decyzja jakościowa, poza zakresem ([[raport-18-nastepna-fala]] #9).

Odrzucone: tqLLM (plain 77% pasma = parytet), HyperQwen (GEMV = Marlin), Magnitude (na XTX 1.4–2.2× wolniejszy), TensorFold (HIP zamrożony), Maya (brak pomiarów XTX).

## Powiązane
- [[research/_hub|research]]
- [[hipfire]]
- [[raport-23b-re-kernele-amd]]
- [[raport-21g-nowe-silniki]]
