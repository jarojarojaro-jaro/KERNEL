---
typ: repo
tags: [repo, spekulacja, dflash]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/repos/22-lucebox.md:1-55; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:32
status: aktualne
---
# Luce-Org/lucebox

**Serwer inferencji C++ z forkiem ggml i spekulacją DFlash2 (HEAD `54132ca`, 2026-10-14) na tym samym modelu i drafterze co my; werdykt: średnia.**

Ich pomiar (R9700, Qwen3.8-27B UD-IQ4_XS, T=0, HumanEval-10): DFlash2 blok 8 133.9 → blok 16 208.1 t/s, bajtowo jak AR; plain AR 32.3. Od 8K tokenów weryfikacja cięta do 8. Na RTX 3090: decode 413 vs 267 t/s llama.cpp (1.55×). Dla nas Q1: zdjąć przycięcie `n_max` w `common/speculative.cpp`, szacunek 175–300 t/s na kodzie zamiast ~110–130; oraz `LLAMA_ATTN_ROT_DISABLE=1` przy KV q8_0 (~1.5%, zmienia numerykę). To lucebox polecił hipfire.

## Powiązane
- [[repo/_hub|repo]]
- [[hipfire]]
- [[drafter-dflash]]
- [[radeon-ai-pro-r9700]]
- [[repos-30-przeglad]]
