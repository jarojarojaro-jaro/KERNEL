---
typ: model
tags: [modele, nvidia, moe, mamba]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/14-nemotron-3090.md:25-55,57-69,91-102; ~/qwen-opt/cloud/results/nemotron-3090-20261016/scorecard.md:1-14
status: aktualne
---
# NVIDIA Nemotron 3.5 Bolt 74B-A9B

**Hybrydowy MoE NVIDIA (Mamba-2 + LatentMoE + 8 warstw attention, ~9B aktywnych) w pliku IQ2_XXS 22 018 326 528 B; na RTX 3090 z drafterem DFlash nasz silnik daje 141.1 t/s.**

- Plik `NVIDIA-Nemotron-3.5-Bolt-74B-A9B-IQ2_XXS.gguf` (rewizja HF `f56d370e`), drafter `dflash-…-NVFP4.gguf` 998 242 560 B. Licencja OpenMDW-1.1 („ready for commercial or non-commercial use”).
- Arch `nemotron_h_moe`, 88 warstw: 40 Mamba-2 (d_inner 8192, state 128, `ssm_in`/`ssm_out` w NVFP4), 40 LatentMoE (latent 1024, top-9, liczba ekspertów różna w warstwach: 240/304/368/432/496, eksperci IQ2_XXS), 8 attention GQA 32/2 (Q8_0); słownik 131072; **brak głowicy MTP**.
- Bajty na token ~4.8 GB wag + ~0.34 GB stanu SSM → sufit ~150 t/s przy 805 GB/s.
- llama.cpp v0.7.0 obsługuje model i DFlash (`draft-dflash`, block 8). NVFP4 na Ampere idzie przez dp4a z tablicą.
- RTX 3090: A0 87.2 t/s, DFlash upstream 131.4, nasz tuned 141.1; bez draftera do 262144 kontekstu; przy 64k KV f16 zachowuje 97% prędkości, q8_0 78%.
- Upstreamowa fuzja topk-moe nie obsługuje tych liczb ekspertów (argsort i łańcuch bramki 0.95 ms/token) – stąd łatka `GGML_CUDA_TOPK_MOE_NP2`.

## Powiązane
- [[modele/_hub|Modele]]
- [[lfm2-5-24b-a2b]]
- [[drafter-dflash]]
- [[raport-14-nemotron-3090]]
- [[nemotron-kernele-cuda]]
- [[firma-nvidia]]
- [[star-elastic-2605-07182]]
