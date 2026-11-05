---
typ: repo
tags: [repo, konkurencja, nvidia]
aktualizacja: 2026-11-05
zrodlo: ~/KERNEL/product/research/32f-ninfer-tqllm-dflash2.md:1-22; ~/KERNEL/product/research/63a-silniki-lokalne.md:312-326
status: aktualne
---
# NInfer (Neroued/ninfer)

**Silnik z rekordami LocalMaxxing na NVIDIA; klon `a928f899` (dev, 2026-10-21) – liczby wiarygodne, ale mierzone przy T=0 na `reasoning-v1`, nieporównywalne z naszym czatem T=1.**

- 2026-11-05 (`a754fcf3`, 121 commitów od `a928f899`, R63a): prawie wyłącznie GLM-5-Next i DGX Spark; dokument wydajności 27B to „historyczna kampania”, na LocalMaxxing brak nowych wpisów 27B. Watch zawęzić do `docs/performance/qwen3.8-27b.md`. Fixture 12 zadań używa [[yasakani]].

## Powiązane
- [[repo/_hub|repo]]
- [[raport-32f-ninfer-tqllm]]
- [[tqllm]]
- [[raport-32d-localmaxxing]]
