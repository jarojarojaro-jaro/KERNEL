---
typ: research
tags: [research, nvidia, rtx-3090, rtx-3060, wyniki]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/27-3090-final.md:20-35,42-44,211-213,243-247
status: aktualne
---
# Raport 27: RTX 3090 i 3060 – finał przed/po (Qwen, Uncensored, Saluki)

**Na 3090 topka (lookup W16 + share + GPU verify, `cuda-topka2` `2a261101b`) daje czat T=1 93.3 t/s vs upstream z MTP 75.3 (+24%) i gołe 42.9 (×2.17), code-edit 348.9 vs 109.5 (×3.19); 3060 Saluki 24.0 → 38.2 t/s (×1.59) (2026-10-19/20).**

- Qwen 3090: greedy T=0 103.4 vs 76.7; decode po 16k/32k 89.1/79.9 vs 70.0/64.0 (`27:21-23`).
- Uncensored 3090: czat 75.3 vs 58.5 (+28.6%), mvs 319.5 vs 92.7 (`27:27-29`).
- `LLAMA_GPU_VERIFY` na CUDA: md5 off == on 22/22; mvs +6.0% / +8.6% w jednym przejściu (`27:43-44`).
- Limit: topka przy ctx 204800 na 24 GB NVIDIA kończy się OOM przy prompcie ~55.6k – domyślny ctx ≤ 131072 (`27:211-213,243`).
- Vast: filtrować `cuda_vers>=12.8`, dla 12 GB RAM hosta ≥ 24 GB (`27:246-247`). Rekordy: [[REKORDY]]. Karty: [[rtx-3090]], [[rtx-3060]].

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[rtx-3090]]
- [[rtx-3060]]
- [[raport-24e-nvidia-runda]]
- [[saluki]]
- [[REKORDY]]
