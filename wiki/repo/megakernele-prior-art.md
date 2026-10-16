---
typ: repo
tags: [repo, megakernel, cuda]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15a-monokernel.md:43-46,94-116
status: aktualne
---
# Megakernele: Hazy, MPK i inne (prior art)

**Hazy Megakernels (interpreter instrukcji per SM ze stronicowanym SMEM) i MPK/Mirage (kompilator tGraph) osiągają 71–80% pasma przy batch 1, wobec ≤ 50% kernel-per-op; na RDNA3 publicznego megakernela nie ma.**

- **Hazy** („No Bubbles”): Llama-3.2-1B BF16 < 1 ms/forward na H100 = 78% pasma, 2.5× vLLM, 1.5× SGLang; SMEM stronicowany 13 × 16 KiB, liczniki `atomicAdd`, podział MLP na 4 chunki; budżet B200: 250/600 µs na hand-offy aktywacji, 200 na liczenie, 30 na czekanie na wagi.
- **MPK / Mirage** (arXiv 2512.22219, OSDI ’26): do 1.7×; Qwen3-8B A100 14.5 → 12.5 ms (podłoga ~10 ms, 80%); launch na B200 3.8 µs eager i 0.8 µs w grafach.
- **Lucebox** (3090): Qwen3.5-0.8B BF16 413 vs 267 t/s llama.cpp (1.55×) – jedyny dowód na konsumenckiej karcie.
- **TensorFold** (M5): megakernel z barierą siatki przegrał (4.6–18 µs/fazę vs 4.01 µs relaunchu).
- **llama.cpp:** brak PR megakernela; PDL #22522 scalone (+5–13% tg na Blackwell); #28863 – brak megakernela na AMD.
- HipKittens celuje w CDNA, nie RDNA.

## Powiązane
- [[repo/_hub|repo]]
- [[vllm-monokernel]]
- [[lucebox]]
- [[tensorfold]]
- [[raport-15a-monokernel]]
