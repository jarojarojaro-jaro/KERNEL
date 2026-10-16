---
typ: repo
tags: [repo, llama-cpp, fork]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/03-silniki-i-stack.md:124-135,207
status: do-sprawdzenia
---
# ik_llama.cpp (ikawrakow)

**Trwały fork llama.cpp (MIT, od 2024-06) z kwantami IQK/trellis, mocny na CPU i MoE, ale bez ROCm, Vulkan i Metal.**

Raport 03 (2026-10): „last synced with upstream in August 2024” `[STALE?]`, więc rozjazd jest trwały. Ma kwanty IQK i trellis (KT), MLA, fused delta-net, MTP i DFlash. Pełnoprawne są tylko CPU (AVX2+/NEON) i CUDA (Turing+). Wydajność CPU pp do 3,27× `[STALE?]`. Wniosek dla nas: trwały fork daje przewagę na CPU i MoE, ale traci pokrycie sprzętu; dlatego nasz produkt trzyma łatki jako serię nad upstreamem zamiast twardego forka.

## Powiązane
- [[repo/_hub|repo]]
- [[llama-cpp-fork]]
- [[prism-llama-cpp]]
- [[analiza-platformy]]
