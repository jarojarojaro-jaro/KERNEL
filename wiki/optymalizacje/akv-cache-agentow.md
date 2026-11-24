---
typ: optymalizacja
tags: [optymalizacje, cache, agent, kv]
aktualizacja: 2026-10-24
zrodlo: ~/KERNEL/product/research/60d-serving-kernels-cache.md:167-183,224-227; https://arxiv.org/abs/2610.28577; https://github.com/thu-nics/AKV (`c567a42`)
status: aktualne
technika: AKV drop + repozycjonowanie KV
werdykt: w-toku
zysk: −27.7% kosztu API u autorów (GPT-OSS-120B); repos odpada u nas (IMROPE)
dowod: ~/KERNEL/product/research/60d-serving-kernels-cache.md
model: qwen3-8-27b
---
# AKV: agent/harness edytuje własne KV (drop + repozycjonowanie RoPE)

**AKV (Tsinghua NICS, arXiv 2610.28577, Apache-2.0, łatany SGLang) usuwa KV starych wyników narzędzi i przenumerowuje klucze K ← R(q)R(p)⁻¹K bez re-prefillu: −27.7% kosztu w centach API, jakość +1.3…+2.1 pkt średnio, 1.18× wyjścia i 1.53× wejścia przy szczycie (GPT-OSS-120B, 8× A800) (raport 60d, 2026-10-24).**

- Polityka: KV 12 ostatnich wyników narzędzi + całe rozumowanie. Repos dopiero po progu 96K/192K. Wariant z narzędziem `drop_context` dla modelu. Bez fine-tuningu.
- Rotacja w FP32: odwrotna, potem do przodu, nie o deltę (1 ULP BF16 się wzmacnia). Wymaga KV niekwantyzowanego, bez spekulacji.
- U nas: Qwen3.8 = IMROPE, więc llama.cpp nie robi `seq_add`/shift (`get_can_shift()==false`) i **repos odpada**. Sam drop (`seq_rm`) działa tylko w 16 warstwach atencji, a stan GDN zachowuje informację z usuniętych tokenów.
- Koszt wdrożenia wysoki: cache kluczowany historią operacji, spany wiadomości, KV MTP, checkpointy. Najpierw tani test sufitu na transkryptach omp (T5 w raporcie 60d).

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)

Werdykt „repos odpada przy IMROPE, drop drogi” dotyczył tylko silnika. Praca uczy też czegoś o harnessie i serwerze (dane z `product/research/60d-serving-kernels-cache.md`, §3.3 i tabela liczb):
- **Mniej kontekstu = lepszy agent, nie tylko tańszy.** AKV z polityką „zostaw 12 ostatnich wyników narzędzi i całe rozumowanie” podniosło średnią jakość względem pełnego kontekstu o 1,3–2,1 pkt na trzech modelach (MiniMax-M2.7 52,4 → 53,7, GPT-OSS-120B 51,0 → 53,1, MiroThinker 44,1 → 45,8; Tab. 1). Sama polityka żyje w harnessie, a omp to nasz harness, więc można ją sprawdzić na transkryptach bez zmian w silniku (T5).
- **Wariant tekstowy był w pracy osobną bazą** („Text Eng.”, AKV −21,9% kosztu względem niej). Usunięcie starych wyników narzędzi z tekstu łamie prefiks, więc u nas kosztuje pełny prefill: Qwen 53k to ~61,5 s (`STAN-PRAC.md:47`). Sprzątanie ma więc sens rzadko, przy progu (jak repos AKV przy 96K), a nie co turę. Za to działa także dla hybrydy GDN, gdzie drop w KV nie działa.
- **Model może sam sprzątać kontekst** (narzędzie `drop_context`, tylko stare wyniki narzędzi, pierwsze 2 wiadomości chronione). To pomysł na narzędzie omp, nie na kernel.
- **Serwer:** AKV kluczuje cache historią operacji (ten sam tekst ≠ ten sam KV). Nasz llama-server ignoruje `prompt_cache_key` wysyłany przez omp (60d, tabela 3.2), więc nie wie nawet, która sesja jest która. To tańsza luka do zamknięcia niż drop KV.
- **Bierzemy:** test polityki „12 ostatnich wyników narzędzi” na transkryptach omp (jakość i tokeny) oraz obsługę `prompt_cache_key` w wyborze slotu. Repos i drop w KV nadal odpadają.

## Powiązane
- [[ksztalt-ruchu-agentowego]]
- [[pamiec-stanu-gdn]]
- [[sglang-hicache]]
- [[raport-60d-serving-kernels-cache]]
