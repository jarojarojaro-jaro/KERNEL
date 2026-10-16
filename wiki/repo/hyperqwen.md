---
typ: repo
tags: [repo, spekulacja, vllm, rtx-3090]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15b-spekulacja-frontier.md:9-10,39-44,60-101; ~/KERNEL/product/research/15d-prefill-dlugi-kontekst.md:15,57-58,96-97,124
status: aktualne
---
# HyperQwen (syv-ai, dawniej qwen38-27b-rtx3090)

**vLLM z łatkami dla Qwen3.8-27B na RTX 3090 (250 W): lookup sufiksu z kontekstu (LABD), blok 16, łańcuchy i prefix cache dla hybryd; 381 t/s dotyczy kopiowania dokumentu verbatim, a dla nas to głównie górny pułap dla 3090.**

Repo `syv-ai/HyperQwen` @ `95ee3b6` (2026-10-11).
- Historia: 08-17 66 → 84 t/s, 08-18 114/124, 08-19 lookup v1, 08-20 blok 16. Optymalizowane MTP „~82 → 114 t/s” (8 promptów, krótki kontekst) – wiarygodne.
- **381 t/s**: dokument 25k sklejony z ich własnej dokumentacji, polecenie „przepisz pierwsze 60 linii” – 14.97 tok/krok przy 39.3 ms/krok. Na zwykłym czacie pozycje 7–14 = 72/11 069 = 0.65% przyjętych tokenów; 133 vs 131 t/s w szumie.
- LABD: kernel Triton szuka najdłuższego sufiksu (6–12 tokenów) w historii; pozycje 8–15 wypełnia lookup, drafter DFlash2 daje 7; długi blok po 2 nasyconych krokach, trzymany 3. Bezstratne rozkładowo, nie bitowo.
- Prefix cache dla hybryd: TTFT drugiej tury przy 25k 22.4 → 0.56 s – to samo co nasz slot + checkpointy (XTX: 31.9 → 0.7 s).
- Górny pułap 3090 (vLLM, KV fp8): MTP-3 przy 112k 68.1 t/s (2.56 tok/krok); prefill 1k/16k/100k 1812/1595/997 t/s; KVarN k4v2 spowalnia spekulację 2.13× (68.1 → 32.0 t/s).
- Koszt kwantyzacji: lm_head GPTQ int4 PPL +0.6%, INT8_ACT w prefillu PPL +4.1%.
Werdykt: mechanizm przenośny tylko jako „ogon” (EXT); nadpisywanie głowy u nas szkodzi.

## Powiązane
- [[repo/_hub|repo]]
- [[tqllm]]
- [[lucebox]]
- [[raport-15b-spekulacja-frontier]]
- [[raport-15d-prefill-dlugi-kontekst]]
- [[rtx-3090]]
