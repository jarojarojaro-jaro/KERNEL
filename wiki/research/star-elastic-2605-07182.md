---
typ: research
tags: [research, nvidia, trening]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15a-monokernel.md:11,217-229
status: aktualne
---
# Star Elastic (arXiv 2605.07182)

**Praca NVIDIA o zagnieżdżonych podmodelach Nemotron Nano v3 (30B → 23B/12B z jednego post-trainingu) i osobnym podmodelu dla fazy myślenia; nie dotyczy kerneli, dla nas niska istotność.**

- Nemotron Nano v3 30B/3.6A daje 23B/2.8A i 12B/2.0A przy 160B tokenów; router trenowany end-to-end, curriculum KD.
- „Elastic budget control”: mniejszy podmodel dla thinking, większy dla odpowiedzi – do 16% wyższa dokładność albo 1.9× niższa latencja (vLLM, BF16, batch 16–40).
- RTX Pro 6000: 12B NVFP4 7426 tok/s vs 30B BF16 2178 tok/s (agregat przy dużym batchu, nie batch 1).
Dla nas: zagnieżdżony podmodel tego samego modelu mógłby być drafterem self-spec ze wspólnym KV, ale to nie nasz model; trening to temat raportu 10. Trafił do raportu 15a przez błędny numer arXiv.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)

- Stary werdykt „niska istotność” patrzył tylko na kernele XTX. Dla produktu to wzór „jeden plik, trzy rozmiary”: NVIDIA wydała to jako `NVIDIA-Nemotron-Labs-3-Elastic-30B-A3B` (BF16 i NVFP4) z trzema zagnieżdżonymi wariantami 30B/23B/12B w jednym checkpoincie (https://huggingface.co/nvidia/NVIDIA-Nemotron-Labs-3-Elastic-30B-A3B-NVFP4).
- Nasz odpowiednik: katalog Enigmy dobiera osobny plik i kwant pod każdą kartę (`app/engine/src/server/catalog/index.ts:214-246`), czyli osobne pobranie na każdy tier. Model elastyczny pozwoliłby pobrać raz i wyciąć rozmiar pod VRAM przy ładowaniu `[INFERENCE: llama.cpp nie ma dziś takiego wycinania]`.
- „Elastic budget control” (mały podmodel myśli, duży odpowiada; do 1.9× niższej latencji przy tym samym wyniku) to ten sam pomysł, co nasz drafter z tych samych wag (self-spec ze wspólnym KV), tylko wytrenowany.
- Dla nauki: przepis treningowy (router end-to-end, curriculum KD, 160B tokenów na 2 podmodele) jest punktem odniesienia przy rozmowie o własnym drafterze w [[raport-10-post-training]].
- Co bierzemy: obserwować, czy pojawi się elastyczny wariant Qwena lub GGUF z wycinaniem; wtedy to temat katalogu, nie kerneli.

## Powiązane
- [[research/_hub|research]]
- [[raport-15a-monokernel]]
- [[raport-10-post-training]]
- [[nemotron-3-5-bolt-74b-a9b]]
