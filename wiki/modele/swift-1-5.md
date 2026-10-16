---
typ: model
tags: [modele, qwen, kwanty, licencje]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15e-kwantyzacja-nowa.md:33-40,130-150,238-246
status: aktualne
---
# Swift 1.5 (UkisAI): Qwen3.8-27B z krótszym myśleniem

**Fine-tune RL/OPD Qwen3.8-27B na krótsze myślenie (deklaracja: −41.9% średnio i −58.5% w medianie tokenów GPQA-D przy +0.31 pp); kwanty GSQ-RCO z alokacją ISTA 1:1, głowica MTP niedouczona, licencja z progiem US$1M przychodu.**

- Trunk zmieniony (`embed_tokens`, `layers.10.mlp.down_proj` różnią się od Qwena), config identyczny (`qwen3_5`, 64 warstwy).
- **Głowica MTP bajtowo identyczna z Qwenem** (SHA-256 próbek po 1 MiB w trzech tensorach `mtp.*`), a dostaje hidden state zmienione przez RL – akceptacja MTP niezmierzona, raczej niższa `[INFERENCE]`.
- Kwanty: ta sama alokacja per tensor co ISTA (`diff` IQ2_XS i IQ3_S: identyczne, 851 tensorów) + imatrix „V1MIX” + nieopublikowany refinement GSQ. Pliki: IQ2_XS 8.42 GB / 2.502 bpw, IQ2_S 9.26 / 2.751, IQ3_XXS 10.09 / 2.999, IQ3_S 11.77 / 3.498; `-mtp` +0.35 GB.
- KLD do **własnego** BF16 Swifta: 0.190 / 0.135 / 0.098 / 0.051 – nieporównywalne z ISTA (inna referencja).
- Deklaracja „9.18× szybciej” to jedno demo; karta BF16 mówi 1.95× (Amdahl przy −58.5% tokenów ≤ 2.4×).
- **Licencja Swift Open License v1.0:** komercyjnie tylko przy przychodzie < US$1M rocznie (§5), automatyczne wygaśnięcie przy naruszeniu (§12) – ryzyko dla B2B; decyzja otwarta.

## Powiązane
- [[modele/_hub|Modele]]
- [[qwen3-8-27b]]
- [[saluki]]
- [[ukisai]]
- [[raport-15e-kwantyzacja-nowa]]
- [[otwarte-decyzje-produktu]]
