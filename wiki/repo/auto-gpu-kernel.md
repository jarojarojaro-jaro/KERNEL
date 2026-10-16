---
typ: repo
tags: [repo, agenci, gdn]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/repos/14-auto-gpu-kernel.md:1-22; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:24
status: aktualne
---
# Dogacel/auto-gpu-kernel (i fork ludoo)

**Harness agenta do pisania kerneli (upstream `db02153`, 2026-09-12) i fork `ludoo` z GDN o geometrii naszego Qwena; werdykt: średnia.**

Autor wygrał nim MLSys 2026 FlashInfer contest (B200). Fork `ludoo` (`54e3c5f`) optymalizuje `gdn-rec` o tej samej geometrii co Qwen3.8-27B (H=16, HV=48, K=V=128) z weryfikacją T=5, z kontraktem „fold” (bitowa kolejność arytmetyki, wolne wszystko wokół). Zbiorcze (coalesced) ładowanie stanu GDN: u nich 20.6 → 11.3 µs, bitowo (pomiar na GB10). U nas Q3.

## Powiązane
- [[repo/_hub|repo]]
- [[tilegym]]
- [[ako4all]]
- [[gdn-fast]]
- [[repos-30-przeglad]]
