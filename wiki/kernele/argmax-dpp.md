---
typ: kernel
tags: [kernele, dpp, mtp]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:262; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:101; ~/KERNEL/product/research/08-analiza-platformy-latek.md:24; ~/KERNEL/product/research/patch-manifest.json (0026)
status: aktualne
---
# Argmax z DPP (0026)

**Argmax po słowniku w drafcie MTP: 16 ładowań w locie i wymiana między lane'ami przez DPP zamiast pamięci LDS; 16.8 → 4.3 µs na wywołanie.**

- Łatka 0026, runda K2 (gałąź `opt-k2`, 2026-10-13).
- Gdzie: greedy drafty MTP (argmax liczony na GPU od 0020, [[mtp-draft-graf]]).
- Zysk: 16.8 → 4.3 µs na wywołanie. Wkład do K2 łącznie: Qwen 33.17 → 32.14 ms/krok.
- Poprawność: bitowo identyczne (greedy md5 plain + MTP równe po każdym kroku K2).
- Wyłącznik: `GGML_HIP_ARGMAX_FAST=0`.
- Platformy: kod wspólny CUDA/HIP bez strażnika arch, więc według raportu 08 aktywny także na NVIDIA i innych RDNA (DPP row_xmask/permlanex16 od gfx10); na NVIDIA nigdy nieuruchomiony.

## Powiązane
- [[kernele/_hub|Kernele]]
- [[rmsnorm-dpp]]
- [[mtp-draft-graf]]
- [[rdna3-gfx1100]]
- [[2026-10-13-k2-male-kernele]]
