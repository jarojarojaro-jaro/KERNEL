---
typ: lekcja
tags: [lekcje, cuda]
aktualizacja: 2026-10-16
zrodlo: ~/qwen-opt/cloud/CUDA-AUDIT.md:176-190
status: aktualne
---
# PDL na Blackwell: kernel musi czekać na poprzednika

**Na sm_120 llama.cpp startuje kernele wcześniej (PDL); nowy kernel bez `ggml_cuda_pdl_sync` może czytać dane, zanim poprzedni skończy.**

Dotyczyło łatek 0053 (`norm_router_topk_f32`) i 0057 (`attn_prep_f32`); znalezione przeglądem kodu przed pierwszym GPU, poprawione w `cuda-compat` (commit 14506801c). Na sm_86/sm_89 problemu nie ma. Reguła: każdy nowy kernel uruchamiany przez `ggml_cuda_kernel_launch` woła `pdl_sync` przed pierwszym zależnym odczytem.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[cuda-compat]]
- [[sm-86-89-120]]
- [[rtx-5060-ti]]
