---
typ: model
tags: [modele, moe, kwanty, trellis]
aktualizacja: 2026-10-24
zrodlo: ~/KERNEL/product/research/60c-quant-and-3090-engines.md:92-136,196-205; https://huggingface.co/agentionai/Qwen3.8-Flash-Next-Gyro-Coder-GGUF; https://gitlab.com/agentionai-group/agention-gyro
status: do-sprawdzenia
model: gyro-coder
rozmiar: Flash-Next 256/512 ekspertów
kwant: TQ2_T
karty: strix-halo
wynik: gyro-coder | strix-halo | 0.118 KLD | KLD do Q8_0; C++, -c 2048 | 2026-10-24
---
# Gyro-Coder (Qwen3.8-Flash-Next, 256/512 ekspertów) i format Gyro TQ

**AgentionAI przyciął Flash-Next do 256 z 512 ekspertów w każdej warstwie, zapisał ich w trellisie TQ2_T (2.125 bpw) i zmieścił model w 19.92 GiB GPU. Do tego dochodzi 50.7 GiB tabeli n-gramów na NVMe.**

- Selekcja ekspertów: przeszukiwanie ewolucyjne, ~2 200 kandydatów w 14 przebiegach. Kryterium nie opublikowano.
- Jakość względem pełnego Q8_0 (`-c 2048`): KLD/top-1 C++ 0.118 / 94.5%, Python 0.165 / 93.1%, held-out 0.579 / 70.8%. Zadania: 13/16, te same eksperty w 8 bitach 15/16.
- Prędkość: jedyny pomiar to Strix Halo (Vulkan, MTP), 11–22 t/s na strumień przy 2 strumieniach. Szacunek bajtów: ~4.9 GiB/token vs ~16.5 GB dla 27B U4 `[INFERENCE]`.
- Runtime: tylko fork `agentionai-group/llama.cpp` (`9aa51ce`) w Dockerze z Vulkanem. Kernele są też w `ggml-cuda`, ale HIP nie jest deklarowany. Stock llama.cpp, nasz fork i Strata 0.2.2 go nie ładują.
- Format (`agention-gyro` `587a526`, 2026-10-24, Apache-2.0):
  - typy TQK4–7, TQ2_T, TQP5–7 (1.125–3.625 bpw);
  - bloki po 128 wag, 15-bitowy stan, kodebook 2048;
  - obrót block-Hadamard zapisany w metadanych.

  Referencyjny enkoder jest jawny, ale „noticeably worse” od produkcyjnego.
- Dla nas: przy 24 GB nie dotyczy, bo U4 ma KLD 0.0117.

<!-- TABELE:START -->
## Wyniki z notatek (1)

Najlepszy wynik na metrykę z pól `wynik` notatek testów (tools/tabele.py, 2026-11-22); pełna tabela: [[najlepsze-wyniki]].

| karta | metryka | najlepszy | warunki | data | źródło |
|---|---|---|---|---|---|
| AMD Strix Halo [[strix-halo]] | KLD do Q8_0 | **0.118 KLD** | C++, -c 2048 | 2026-10-24 | [[gyro-coder]] |
<!-- TABELE:END -->

## Powiązane
- [[modele/_hub|modele]]
- [[raport-60c-quant-3090]]
- [[raport-21n-strata-gyro]]
- [[strata]]
- [[kwanty-gguf]]
