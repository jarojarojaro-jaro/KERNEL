---
typ: repo
tags: [repo, megakernel, cuda]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/product/research/15a-monokernel.md:43-46,94-116; ~/KERNEL/product/research/66c-hyperkernel-megakernele.md:128-139; ~/KERNEL/product/research/66b-1cat-tokenspeed.md:192
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

## Aktualizacja 2026-11-07 (R66c)
- **Hyperkernel** (B300): rezydentny megakernel w stylu Hazy wygenerowany automatycznie, tylko binaria ([[hyperkernel]]).
- **MPK HIP, PR #820** (2026-11-02, otwarty): pierwszy otwarty runtime megakernela w HIP, gfx950 (CDNA4), „static megakernel” na typ warstwy; Kimi K3 TP8 2.02× przy bs1, 1.24–1.28× przy bs64; GSM8K 0.954 vs 0.958. Na RDNA3 trzeba przepisać asm (sc0/sc1 → glc/dlc), wave64 → wave32, MFMA → WMMA.
- **NVIDIA `sgl-nvidia-mega`** (port na B200, `8315e890`): +40…56% na użytkownika przy 1–8 równoległych, remis przy 9–32; KL 0.0044; **2 zawieszenia w 12.5 h**, produkcja wróciła na zwykłą ścieżkę.
- **Fleet** (AMD Research, arXiv 2604.15379): trwały runtime z zadaniami per chiplet, MI350 Qwen3-8B 1.3–1.5× vs vLLM przy bs 1–8. Na RDNA3 (jeden die) przenosi się tylko lokalność cache.
- **Ada-MK** (arXiv 2605.11581): harmonogram wyliczony offline, L20 +23.6% vs TRT-LLM przy bs1.
- **TokenSpeed monokernel** (gfx950, jedno trwałe uruchomienie na warstwę): „580 vs 377 t/s”, CI 443 ([[tokenspeed]]).
- Dla nas: [[budzet-megakernela-qwen-xtx]].

## Powiązane
- [[repo/_hub|repo]]
- [[vllm-monokernel]]
- [[lucebox]]
- [[tensorfold]]
- [[raport-15a-monokernel]]
