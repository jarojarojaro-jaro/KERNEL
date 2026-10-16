---
typ: repo
tags: [repo, spekulacja, dflash]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/repos/22-lucebox.md:1-55; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:32; ~/KERNEL/product/research/15d-prefill-dlugi-kontekst.md:3-14,49-56,64-82,254
status: aktualne
---
# Luce-Org/lucebox

**Serwer inferencji C++ z forkiem ggml i spekulacją DFlash2 (HEAD `54132ca`, 2026-10-14) na tym samym modelu i drafterze co my; werdykt: średnia.**

Ich pomiar (R9700, Qwen3.8-27B UD-IQ4_XS, T=0, HumanEval-10): DFlash2 blok 8 133.9 → blok 16 208.1 t/s, bajtowo jak AR; plain AR 32.3. Od 8K tokenów weryfikacja cięta do 8. Na RTX 3090: decode 413 vs 267 t/s llama.cpp (1.55×). Dla nas Q1: zdjąć przycięcie `n_max` w `common/speculative.cpp`, szacunek 175–300 t/s na kodzie zamiast ~110–130; oraz `LLAMA_ATTN_ROT_DISABLE=1` przy KV q8_0 (~1.5%, zmienia numerykę). To lucebox polecił hipfire.

## Aktualizacja 2026-10-16 (HEAD `6f2b179`, raport 15d)
- **PFlash v2** (PR #746, merge `c2569a0`): drafter Qwen3.5-0.8B BF16 (sha `cedf89af…`) liczy 15 bloków; sonda segmentów (263k parametrów), sonda żądania (265k) i głowica Q/K NoPE (2.62M) na residualu po bloku 14; budżet z krzywej 16384:0.315 → 120000:0.225; kompresja dopiero przy ≥ 16K niecache'owanych tokenów, sesje z narzędziami surowo. Jakość 92/124 vs 94, LongBench-v2 4/12 vs 7/12 (w PR na L40S 7/12 vs 6/12, czyli szum), MTRAG 189 vs 197 (pełny prefill tylko zamodelowany). TTFT ×3.7 na R9700.
- **KVFlash:** stratny (igła 14/16, zgodność tekstu GSM 8/10); bazowy prefill 694 t/s przy 32K vs llama.cpp 1168 t/s.
- **Dyskowy cache sesji:** sesja 45K po restarcie 2.6 s vs 56.2 s, bajtowo identycznie.
- #457: na gfx1100 `dflash_server` ~2× wolniejszy od llama.cpp.
Werdykt bez zmian (średnia), PFlash: pilot.

## Powiązane
- [[repo/_hub|repo]]
- [[hipfire]]
- [[drafter-dflash]]
- [[radeon-ai-pro-r9700]]
- [[repos-30-przeglad]]
- [[raport-15d-prefill-dlugi-kontekst]]
- [[hyperqwen]]
