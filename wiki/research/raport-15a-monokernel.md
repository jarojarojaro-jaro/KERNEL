---
typ: research
tags: [research, megakernel, pm4, lfm]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15a-monokernel.md:1-28,118-168,206-215
status: aktualne
---
# Raport 15a: megakernele dla decode (vLLM MonoKernel)

**Trwały kernel *dataflow* z prefetchem wag mógłby dać LFM2.5 na XTX +12…+28% `[SZACUNEK]`, ale trwały kernel z barierami między fazami nie pobije PM4; tańszy pierwszy krok to „PM4-PDL” (+5…+15%, bitowo).**

Raport z 2026-10-16, bez GPU.
- **vLLM MonoKernel** (RFC #60904): jedna trwała siatka 256 CTA × 512 wątków na warstwę, bez bariery siatki, „tagged pairs”, wagi ładowane przed czekaniem; GLM-5.2 13.70 → 5.92 ms przy batch 1 na 8× MI350X, ale baza vLLM wykorzystuje tylko 5–8% pasma HBM (Mono 12–24%), a względem mocniejszej bazy (ATOM) to −22% TPOT.
- **Nasz budżet LFM na XTX** (taśma PM4, GGUF): 1.777 GB/token, podłoga 1.85 ms; dziś 3.40 ms/token = **54% pasma**; pula „DRAM prawie bezczynny” 1.23 ms (36%), z czego granice PM4 to tylko 0.14–0.26 ms.
- Stary szacunek „trwały kernel MoE po PM4 ≈ 1.4%” liczył tylko granice; zysk megakerneli to prefetch wag, nakładanie małych operacji i redundantne liczenie.
- Scenariusze: S1 PM4-PDL +9…+15%; S2 megakernel dataflow +12…+28%; fizyczna podłoga 2.564 ms (+33%).
- Qwen3.8-27B ma 76% pasma w plain decode, więc megakernel +3–6%.
- Ampere/Ada: brak PDL, granica grafu CUDA niezmierzona (literatura 0.8–1.3 µs), LFM na 3090 też 54% pasma – więcej do wzięcia niż na XTX z PM4.
- `hipLaunchAttributeExtDynDataPrefetch` jest w HIP 7.15, ale ROCr zwraca 0 regionów poniżej gfx12.5.
- Ranking: 1. mikrobench PM4-PDL (X1), 2. prefetch do MALL, 3. proces bezpieczeństwa z RFC, 4. pełny megakernel LFM (25–35 osobodni), 5. trwały blok MoE.
- arXiv 2605.07182 to inny temat (Star Elastic).

## Powiązane
- [[research/_hub|research]]
- [[research/raport-15-synteza|synteza fali 15]]
- [[vllm-monokernel]]
- [[megakernele-prior-art]]
- [[2026-10-16-budzet-lfm-megakernel]]
- [[pm4-replay]]
- [[lfm-runda-4-pm4]]
- [[star-elastic-2605-07182]]
- [[hip-dyn-data-prefetch]]
