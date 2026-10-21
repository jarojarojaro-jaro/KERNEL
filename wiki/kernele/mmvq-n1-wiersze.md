---
typ: kernel
tags: [kernele, mmvq, lfm]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:349,374; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:127,139,184; ~/KERNEL/product/research/patch-manifest.json (0052, 0064); ~/KERNEL/qwen-opt/run-llm.sh:11; ~/KERNEL/product/research/09-chmura-3090.md:103,110-125; ~/KERNEL/product/research/09-chmura-5060ti.md:124,207; ~/KERNEL/product/research/09-chmura-3060.md:159; git -C ~/llama-master log -1 3da7a02ec; git -C ~/llama-master log -1 007000aaa; git -C ~/llama-master log -1 71412d9c6; ~/KERNEL/product/research/14-nemotron-3090.md:134,139-141; ~/KERNEL/product/research/23b-re-kernele-amd.md:20-22,40
status: aktualne
---
# MMVQ 1-kolumnowe: 2 wiersze na blok (0052, 0064)

**Strojenie zwykłego matvec (dekodowanie bez spekulacji) pod gfx1100: blok liczy 2 wiersze zamiast jednego, najpierw dla K-quantów, potem także dla Q8_0.**

| łatka | co | zysk | wyłącznik |
|---|---|---|---|
| 0052 (LFM runda 1, 2026-10-14) | K-quanty: 2 wiersze/blok | 4.610 → 4.509 ms/token (+2.2%) | `GGML_HIP_MMVQ_N1_ROWS` |
| 0064 (runda 4) | Q8_0 dołącza do ścieżki 2 wierszy | LFM Uncensored 3.933 → 3.706 ms (+6.1%) | `GGML_HIP_MMVQ_N1_Q8_0` |

Razem z 0059 (zbiorczy upload) dały ok. 8% zysku kampanii LFM (−0.135 ms/token, raport 07). Bitowo identyczne. Tylko gfx110x (strażnik RDNA3_0); na innych kartach to parametr do przestrojenia ([[kernel-tuner]] ma przestrzeń NWARPS × ROWS dla 39 kształtów n=1). LFM Uncensored zyskuje więcej, bo ma więcej tensorów Q8_0.

## Na NVIDIA: `GGML_CUDA_MMVQ_N1_ROWS` (2026-10-16)
Ta sama bitowa ścieżka „2/4 wiersze na blok” udostępniona na CUDA dla Q4_K/Q5_K/Q6_K/Q8_0/Q4_0/Q3_K/IQ4_XS/IQ3_S/NVFP4 (commit `007000aaa` / `71412d9c6`). Wynik zależy od architektury:
- **sm_86 (RTX 3090):** `=2` daje +8.5% LFM i +7.2% Qwen tg128 (`=4`: +5.8 / +5.0); od `3da7a02ec` domyślnie 2 na sm_80..87 w `cuda-3090-opt`;
- **sm_120 (RTX 5060 Ti):** szkodzi – LFM −2.7%, Qwen −1.7% (`=4`: LFM −15%), więc tam zostaje 1;
- RTX 3060 (sm_86) nie był mierzony z tym przełącznikiem; eksperyment `GGML_CUDA_MMVQ_N1_WIDE` (8 warpów na wiersz) dał −12.6…−21% i nie wszedł.
Dla Nemotron 3.5 Bolt (2026-10-16) dołożono `GGML_CUDA_MMVQ_N1_IQ2`: IQ2_XXS w ścieżce 2 wierszy na blok na sm_80–87, bitowo neutralne (część zysku tg128 91.1 → 96.7 razem z `TOPK_MOE_NP2`).
Wniosek: przełącznik tylko z predykatem per arch w manifeście (sm_80–87 tak, Blackwell nie); Ada sm_89 do ustalenia.

## OrcaCyber-Nano-1.0 (IQ4_XS) na 3090, 2026-10-21
W linii `topka` przełącznika brakowało — dołożony (`6cf6ced`, `GGML_CUDA_MMVQ_N1_ROWS`, domyślnie 0 = tabela, IQ4_XS
włączony do ścieżki). Zmierzone: tg128 40.32 → 43.43 t/s (+7.7%) na VN, 46.19 → 47.35 (+2.5%) na QC; `=4` gorzej
(40.93 / 44.98). `test-backend-ops -o MUL_MAT` (iq4_xs): 2/2 backendy OK, wynik bitowo ten sam.
**Na serwerze z MTP zysku nie ma** (72.7 vs 72.5): hot spotem jest verify batch (ncols=3, ścieżka multi-column),
a nie jednokolumnowy decode. Szczegóły: [[raport-56-orca-3090]].

23b (2026-10-19): ścieżka n=1 nadal ładuje upstreamowo – 18 `global_load_b32`/`d16` na iterację (Q4_K, 3.3 B na instrukcję); kandydat: loader `mmvq_ld` z wielokolumnowej (b128, bitowo zgodny), szacunek plain +2–5%, LFM +2–5% ([[raport-23b-re-kernele-amd]]).

## Powiązane
- [[kernele/_hub|Kernele]]
- [[mmvq-multikolumnowe]]
- [[kernel-tuner]]
- [[lfm2-5-uncensored]]
- [[lfm-runda-1]]
- [[raport-09-chmura-3090]]
- [[sm-86-89-120]]
- [[nemotron-kernele-cuda]]
