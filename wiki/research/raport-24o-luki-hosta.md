---
typ: research
tags: [research, host, pm4, topka]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/24o-luki-hosta.md:3-6,10-23,27-33; ~/qwen-opt/queue/logs/hg-sweep1.log:2,5; wynik `python3 ~/qwen-opt/hostgap/hg_summary.py` (2026-10-20)
status: aktualne
---
# Raport 24o: luki hosta w kroku spekulacji MTP

**„~4 ms bezczynności na krok” z rocprofv3 to w ~80% granice AQL przy PM4=0 (959 × 3.41 µs); trzy bezstratne przełączniki (`YIELD_FAST=2`, `PM4_MIN_DISPATCH=16`, `PM4_LAZY_EXEC=1`) dały w A/B czat 113.8 → 117.9 t/s (2026-10-20).**

- Prawdziwe luki hosta (ślad PM4=1): handshake yield ~100 → 3.8 µs/krok, re-capture przy n_kv do 13.5 ms co 256 tokenów, host decode 160–240 µs × 3 grafy (`24o:17-23`).
- Bramka md5: c4708318 / 6f14e814 / 894e56e4 bez zmian (`24o:36-38`).
- A/B (1 przebieg na ramię): spec_sweep T=1 A 113.8 t/s 28.56 ms/krok, B 117.9 t/s 27.40 ms/krok (`hg-sweep1.log:2,5`); `hg_summary`: mvs −3.6% ms/krok, czat −3.9%.
- Host gap ~1 ms/krok to kilka procent t/s – pomiar nie może dzielić CPU z buildem: [[lekcja-obciazenie-cpu]].

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[pm4-replay]]
- [[lekcja-obciazenie-cpu]]
- [[raport-24m-weryfikacja-gpu]]
