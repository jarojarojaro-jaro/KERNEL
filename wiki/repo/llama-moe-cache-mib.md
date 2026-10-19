---
typ: repo
tags: [repo, llama-cpp, moe]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21g-nowe-silniki.md:419-430; ~/llama-master/common/arg.cpp:2795; llama.cpp PR #29887
status: aktualne
---
# llama.cpp `--moe-cache-mib`: cache ekspertów MoE w VRAM

**Upstream PR #29887 (scalony 2026-10-07, port z qvac-fabric) dodaje cache LRU ekspertów MoE w VRAM przy modelu w RAM: Flash-Next Q4_0 na 4090 25.0 → 40.7 t/s, na 5090 30.8 → 67.8 t/s; jest w bazie naszego forka (`common/arg.cpp:2795`) (raport 21g, 2026-10-19).**

Strata vs llama.cpp z tym cache na V100 (PCIe Gen3 ×4): ~2.4× (#3082). Dla nas kandydat do LFM na kartach 12 GB (LFM Q4_K_M 14.5 GB nie mieści się w 3060) razem z rozgrzewką cache z profilu i automatycznym wyłączaniem MTP, gdy eksperci idą z RAM (pomysł 4 z 21g).

## Powiązane
- [[repo/_hub|repo]]
- [[project-maya]]
- [[rtx-3060]]
