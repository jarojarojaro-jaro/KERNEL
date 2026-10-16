---
typ: latka
tags: [latki, klasyfikacja, poprawnosc]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:7-26,55-70,147-155,174-185
status: aktualne
---
# Klasyfikacja 70 łatek (raport 07)

**Z 70 łatek 45 jest bitowo identycznych, a zysk Qwena (41.7 → 27.74 ms/krok) w ~48% pochodzi z łatek pod architekturę modelu, ~30% z łatek pod RDNA3, ~22% z ogólnych.**

Zależność (gdzie się przenosi):

| klasa | liczba | znaczenie |
|---|---|---|
| MODEL | 22 | GDN, MTP, MoE, conv LFM2 |
| AMD-RDNA3 | 18 | WMMA, DPP, VOPD, buffer resource, GLC/DLC, PM4 |
| GEN-CUDA/HIP | 12 | wspólny ggml-cuda, kompiluje się dla NVIDIA, nigdy tam nietestowany |
| GEN-host | 10 | CPU/host, każdy backend |
| VK-RDNA | 5 | Vulkan na RDNA |
| narzędzia | 3 | — |

Poprawność: BIT 45, SAME-TOK 6 (sampler), DIST 3 (zmienia tylko drafty), FIX 3, numeryka 7 (bramka KLD przeszły 0008, 0013, 0037, 0055; bez osobnej bramki 0006, 0009, 0011), inne 6. Kategorie: kernel 38, KV/stan 10, sampler-serwer 8, spekulacja 6, scheduler-graf 4, narzędzia 4.

LFM (5.07 → 3.40 ms/token): fuzje MoE ~34%, PM4 ~28%, shortconv ~22%, atencja ~12%, MMVQ n=1 + upload ~8%. Podział wewnątrz grup to szacunek raportu (`[INFERENCE]`).

Korekty raportu 08: część łatek „RDNA3” (0001/0002/0021/0025/0026) nie ma strażnika arch i działa też na NVIDIA oraz innych RDNA.

## Powiązane
- [[latki/_hub|Łatki]]
- [[seria-amd-opt]]
- [[patch-manifest]]
- raport-07-metody
- [[zgodnosc-bitowa-md5]]
