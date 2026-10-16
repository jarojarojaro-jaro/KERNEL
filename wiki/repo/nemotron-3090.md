---
typ: repo
tags: [repo, llama-cpp, galezie, cuda]
aktualizacja: 2026-10-16
zrodlo: git -C ~/llama-master log -1 e46d34e0e; git -C ~/llama-master worktree list; ~/KERNEL/product/research/14-nemotron-3090.md:7,128-135
status: aktualne
---
# Gałąź nemotron-3090

**Gałąź `nemotron-3090` @ `e46d34e0e` (2026-10-16, worktree `~/wt/nemotron-opt`) = `cuda-3090-opt` (`3da7a02ec`) + 1 commit z przełącznikami pod Nemotron 3.5 Bolt na Ampere.**

Commit: „CUDA: Nemotron 3.5 Bolt on Ampere – `GGML_CUDA_TOPK_MOE_NP2` (fused topk-moe for 240/304/368/432/496 experts), `GGML_CUDA_MMVQ_N1_IQ2` (IQ2_XXS 2 rows/block), `GGML_CUDA_IQ2_LUT`”; zawiera nowe testy TOPK_MOE w test-backend-ops (niewykonane na GPU – etap przerwany). Szczegóły i pomiary w notatce kernela.

## Powiązane
- [[repo/_hub|repo]]
- [[cuda-v070]]
- [[galezie-rund]]
- [[nemotron-kernele-cuda]]
- [[raport-14-nemotron-3090]]
