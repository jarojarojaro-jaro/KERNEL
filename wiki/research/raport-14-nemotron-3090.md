---
typ: research
tags: [research, chmura, nvidia, sm-86, moe]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/14-nemotron-3090.md:1-231; ~/qwen-opt/cloud/results/nemotron-3090-20261016/scorecard.md:1-14
status: aktualne
---
# Raport 14: Nemotron 3.5 Bolt 74B-A9B na RTX 3090

**Nemotron 3.5 Bolt 74B-A9B (IQ2_XXS, 22 GB) mieści się na RTX 3090 z drafterem DFlash; nasz silnik po dwóch nowych łatkach daje 87.2 → 141.1 t/s (×1.62 vs domyślny llama.cpp, ×1.07 vs najlepsze flagi upstream), ale KLD jest niezmierzone.**

Vast 2026-10-16, ~2.3 h zamiast planowanych 10 h (limit zapytań agenta), koszt ≈ $0.52, instancja zniszczona. Host: Threadripper PRO 5945WX z kwotą 4.6 CPU (`-t 4 -tb 4`), limit mocy 350 W.
- Model: 88 warstw (40 Mamba-2, 40 LatentMoE z 240/304/368/432/496 ekspertami i top-9, 8 attention), licencja OpenMDW-1.1, brak MTP. Szacowany sufit ~150 t/s.
- 24 GB: bez draftera pełne 256K (KV f16 23.4 GB); z DFlash KV q4_0 do 131072, q8_0 do 98304.
- DFlash (drafter NVFP4 działa na Ampere przez dp4a): optimum n_max 5 (137.6 t/s w sondzie), nie 7 z przepisu vLLM; weryfikacja +~2.5 ms na każdy token draftu.
- spec_sweep (6 promptów × 3 seedy, ABBA): A0 87.2, A1 (DFlash upstream) 131.4, A2 (fork) 129.0, **tuned 141.1 t/s**; bez draftera fork +4.4% (86.8 → 90.6).
- Nowe łatki (gałąź `nemotron-3090`): `GGML_CUDA_TOPK_MOE_NP2` (−280 kerneli/token, zmienia bity), `GGML_CUDA_MMVQ_N1_IQ2` (bitowo neutralna), `GGML_CUDA_IQ2_LUT` (wolniejsza, opt-in). tg128 91.1 → 96.7 (+6.1%).
- Długi kontekst: przy 64k KV f16 traci 3%, KV q8_0 22–24%.
- test-backend-ops 19573/19573; greedy md5 fork ≠ upstream, KLD niezmierzone.
- Pułapka: upstream `-fit on` nie mierzy draftera (67 vs 95 t/s).

## Powiązane
- [[research/_hub|research]]
- [[raport-09-chmura-3090]]
- [[nemotron-3-5-bolt-74b-a9b]]
- [[2026-10-16-nemotron-3090]]
- [[rtx-3090]]
- [[lekcja-fit-mtp-16gb]]
