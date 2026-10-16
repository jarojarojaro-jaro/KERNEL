---
typ: repo
tags: [repo, llama-cpp, fork]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/03-silniki-i-stack.md:124-135,207; ~/KERNEL/product/research/15e-kwantyzacja-nowa.md:31,204-209
status: aktualne
---
# ik_llama.cpp (ikawrakow)

**Trwały fork llama.cpp (MIT, od 2024-06) z kwantami IQK/trellis (KT), mocny na CPU i MoE; pełne wsparcie tylko CPU i CUDA, Vulkan i HIP częściowo, port IQK do upstreamu odrzucony.**

Raport 03 (2026-10): „last synced with upstream in August 2024” `[STALE?]`, więc rozjazd jest trwały. Ma kwanty IQK i trellis (KT), MLA, fused delta-net, MTP i DFlash. Pełnoprawne są tylko CPU (AVX2+/NEON) i CUDA (Turing+). Wydajność CPU pp do 3,27× `[STALE?]`. Wniosek dla nas: trwały fork daje przewagę na CPU i MoE, ale traci pokrycie sprzętu; dlatego nasz produkt trzyma łatki jako serię nad upstreamem zamiast twardego forka.

Stan 2026-10-16 (raport 15e): HEAD `8d21687c`; typy trellis IQ1_KT 1.75, IQ2_KT 2.125, IQ3_KT 3.125, IQ4_KT 4.0 bpw. Vulkan ma tylko IQ4_KS/IQ4_KT, HIP idzie ścieżką dp4a (testowano gfx1030), Metal IQ4_KT odpada. Port IQK do upstreamu odrzucony (PR #19726, zamknięty 2026-02-23). Najlepszy publiczny plik Qwen3.8-27B: wiklif KTopt 10.31 GB, KLD 0.043/0.066 (kod/proza, ctx 4096) vs GSQ IQ3_XXS 0.060/0.078. Wzorzec portu do llama.cpp: `lrozewicz/kt-llama-cpp`.

## Powiązane
- [[repo/_hub|repo]]
- [[llama-cpp-fork]]
- [[prism-llama-cpp]]
- [[analiza-platformy]]
- [[exllamav3]]
- [[raport-15e-kwantyzacja-nowa]]
