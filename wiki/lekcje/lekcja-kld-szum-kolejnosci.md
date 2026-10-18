---
typ: lekcja
tags: [lekcje, kld, determinizm]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/product/research/16c-kvq-cuda.md:137-145,160-168; ~/qwen-opt/cloud/results/kvq-cuda-20261016/kld/; ~/KERNEL/product/research/16c-kvq-cuda.md:207-210
status: aktualne
---
# Bramka KLD 2σ leży w szumie kolejności sumowania

**To samo jądro kvq na CUDA z innym podziałem KV (`GGML_CUDA_KVQ_BPSM=1`, zmienia tylko kolejność sumowania) przesunęło mean KLD o ±1–1.9σ, a dla LFM oblało bramkę (ΔKLD +1.47σ, same top −1.88σ, 99.9% ×1.278) przy identycznej arytmetyce (2026-10-16).**

Skutek: FAIL kvq dla Qwen ub1 (+2.53σ) nie odróżnia się od szumu; w tej samej serii dwie pary wyszły −2.0σ na korzyść kvq.

Reguła: przy werdykcie bramki 2σ / ×1.25 dodawać kontrolę „to samo jądro, inny podział” i dłuższy tekst (`--chunks` ≥ 4) zanim zmiana zostanie odrzucona albo dostanie wyjątek.

Powtórka 2026-10-18 (5 × 8192): ten sam efekt na ogonie – kvq vs kvq z innym podziałem 99.9% ×0.69, vec vs kvq-bpsm1 ×1.41; statystyka 99.9% opiera się na ~41 tokenach.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-kolejnosc-akumulacji-fa]]
- [[lekcja-kld-protokoly]]
- [[bramka-kld-kanarki]]
- [[2026-10-16-kvq-cuda-zostaje]]
