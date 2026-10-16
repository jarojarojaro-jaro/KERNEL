---
typ: repo
tags: [repo, ocena, trace]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/repos/27-flashinfer-bench-starter-kit.md:1-13,64; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:37
status: aktualne
---
# flashinfer-bench-starter-kit i FlashInfer-Bench

**Szablon zgłoszenia do konkursu MLSys 2026 (commit `75ccd05`, 2026-04-25) i format FlashInfer-Trace; werdykt: średnia (proces).**

Tory konkursu: fused MoE FP8, DSA sparse attention, GDN decode/prefill. Wszystko poza dwoma pomysłami to infrastruktura (zysk t/s 0). Dla nas: katalog prawdziwych workloadów z naszych trace'ów („co naprawdę biegnie w kroku i ile razy”) oraz offline analiza unii ekspertów dla spekulacji w LFM (przy losowym routingu ×1.54/×2.05/×2.98 bajtów dla k=2/3/5).

## Powiązane
- [[repo/_hub|repo]]
- [[flashinfer]]
- [[auto-gpu-kernel]]
- [[lfm2-5-24b-a2b]]
- [[repos-30-przeglad]]
