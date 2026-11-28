---
typ: decyzja
tags: [decyzje, enigma, nvidia, 16gb, inkling, k204]
aktualizacja: 2026-11-28
zrodlo: panel JARO 2026-11-28 02:38 („1-4 tak”) na propozycje z 02:35
status: aktualne
---
# 2026-11-28: Enigma 16 GB przechodzi na Inklinga IQ3_S bez cenzury (5060 Ti, 4060 Ti)

**JARO (2026-11-28 02:38): „1-4 tak” — w tym punkt 4: zamiana modelu na stronie Enigmy 16 GB na Inklinga z K-204. 5060 Ti 66,5 t/s przy 262 144, 4060 Ti 48,6 przy 283 648 (+103–104% wobec Qwen3.8 IQ3_XXS na tym samym hoście); RTX 5080 zostaje na Qwenie do własnego pomiaru.**

- Wdrożone: `wiki/produkt/final-recipes-nvidia.md`, `product/SITE-NVIDIA.md`, aplikacja `app/engine` (silnik `enigma-cuda-inkling`, model `inkling2-mini` GSQ-IQ3_S, profil `inkling-unc-dspark2`, tylko Linux i tylko zmierzone karty).
- LoRA bez cenzury: `AtomicChat/Inkling-2-Mini-Uncensored-GGUF`, Apache-2.0 według karty HF (plik LICENSE do przeczytania przed wydaniem).
- W tej samej decyzji: K-207 (ablacja zamiast LoRA, Vast ok. 0,05 $), dłuższy kontekst Mai na AD (drafter), K-206 dla AD (niepotrzebne: AD już cały na szybkich kernelach).
