---
typ: metoda
tags: [metody, cache, agent, kv]
aktualizacja: 2026-10-24
zrodlo: ~/KERNEL/product/research/60d-serving-kernels-cache.md:167-183,224-227; https://arxiv.org/abs/2610.28577; https://github.com/thu-nics/AKV (`c567a42`)
status: aktualne
---
# AKV: agent/harness edytuje własne KV (drop + repozycjonowanie RoPE)

**AKV (Tsinghua NICS, arXiv 2610.28577, Apache-2.0, łatany SGLang) usuwa KV starych wyników narzędzi i przenumerowuje klucze K ← R(q)R(p)⁻¹K bez re-prefillu: −27.7% kosztu w centach API, jakość +1.3…+2.1 pkt średnio, 1.18× wyjścia i 1.53× wejścia przy szczycie (GPT-OSS-120B, 8× A800) (raport 60d, 2026-10-24).**

- Polityka: KV 12 ostatnich wyników narzędzi + całe rozumowanie. Repos dopiero po progu 96K/192K. Wariant z narzędziem `drop_context` dla modelu. Bez fine-tuningu.
- Rotacja w FP32: odwrotna, potem do przodu, nie o deltę (1 ULP BF16 się wzmacnia). Wymaga KV niekwantyzowanego, bez spekulacji.
- U nas: Qwen3.8 = IMROPE, więc llama.cpp nie robi `seq_add`/shift (`get_can_shift()==false`) i **repos odpada**. Sam drop (`seq_rm`) działa tylko w 16 warstwach atencji, a stan GDN zachowuje informację z usuniętych tokenów.
- Koszt wdrożenia wysoki: cache kluczowany historią operacji, spany wiadomości, KV MTP, checkpointy. Najpierw tani test sufitu na transkryptach omp (T5 w raporcie 60d).

## Powiązane
- [[metody/_hub|metody]]
- [[ksztalt-ruchu-agentowego]]
- [[pamiec-stanu-gdn]]
- [[sglang-hicache]]
- [[raport-60d-serving-kernels-cache]]
