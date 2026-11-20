---
typ: llm
tags: [llm, modele, moe, looped-transformer, thinking-machines, unsloth, telegram]
aktualizacja: 2026-11-20
zrodlo: thinkingmachines.ai/news/inkling-2-mini (2026-11-20), HF unsloth/Inkling-2-Mini-GGUF, mainline llama.cpp 5f83714 (src/models/inkling2.cpp); link od właściciela (Telegram 23:29)
status: aktualne
---
# Inkling 2 Mini (Thinking Machines, 2026-11-20): MoE z pętlą warstw, jakość jak Qwen3.8-27B przy ~5× mniejszym odczycie na token

**Prawdziwy i ważny dla nas: według producenta jakość Qwen3.8-27B (AA Index 20,1 vs 20,1) przy ok. 3,3 GB odczytu wag na token zamiast ~16 GB.**

W kodowaniu agentowym jest lepszy (DeepSWE 48,2 vs 42,2%), więc na XTX powinien dekodować kilka razy szybciej [INFERENCE]. Do sprawdzenia na naszej karcie: K-133.

## Mechanizm
- 24 warstwy, 4 bloki po 6. **Dwa środkowe bloki liczą się 3 razy z tymi samymi wagami**, co daje 48 przejść warstw na token z 24 zapisanych.
- „Attention residuals”: każda warstwa sama miesza wyjścia wcześniejszych bloków. Między pętlami płynie „wiadomość” z bramką.
- MoE: 128 ekspertów, 8 aktywnych. 26,4B parametrów, 3,4B aktywnych na przejście, **5,4B efektywnie aktywnych** z pętlami.
- Atencja hybrydowa: lokalna (SWA) + globalna. Kontekst do 1M.
- Trenowany natywnie w NVFP4 (eksperty), 4 ostatnie warstwy w MXFP8, ~20 GB. Multimodalny (obraz → tekst). Apache 2.0.
- Pętla daje te same odpowiedzi przy krótszym rozumowaniu: 3703 → 1731 tokenów myślenia (1 vs 3 przejścia, GPQA).

## Liczby producenta (Inkling 2 Mini vs Qwen3.8-27B)
- AA Index v5: 20,1 vs 20,1. DeepSWE v1.1: 48,2 vs 42,2%. SWE-bench Pro v2 Hard: 77,9 vs 73,8%. SWE-bench Verified: 79,2 vs 77,8%.
- Terminal Bench 2.1: 71,6 vs 73,0%. MCP Atlas: 82,7 vs 77,3%. LongBench v2: 66,9 vs 52,3%.
- Słabszy na czacie wieloturowym (MultiChallenge 50,0%) i w instrukcjach z wieloma warunkami. Wiedza zgodna z rozmiarem (AA-Omniscience −8,6 vs −6,4).
- Mocno ułożony pod bezpieczeństwo („misbehavior” 9,8 vs 57,7%). Nasza produkcja to Qwen Uncensored, więc to inny charakter modelu.
- GGUF od Unsloth: UD-Q4_K_M 16,61 GB, KLD 0,0108 vs Q8, zgodność top-1 97,9%. UD-IQ4_XS 15,73 GB.

## Jabłka do jabłek: XTX i inne karty
- **Odczyt na token** [INFERENCE]: 5,4B × ~0,6 B (Q4_K_M) ≈ 3,3 GB. Środkowe warstwy są czytane 3 razy, bo nie mieszczą się w 96 MB Infinity Cache. Qwen3.8-27B czyta ~16 GB na token.
- **Sufit pasma dekodu:**
  - XTX (960 GB/s): ~290 t/s; realnie MoE na RDNA3 ~50–60% sufitu, czyli ~150–170 t/s. Qwen3.8-27B dziś ma 42 t/s bez spekulacji i 107–126 t/s ze spekulacją.
  - RTX 3090 (936 GB/s): podobnie.
  - 5060 Ti 16 GB (448 GB/s): ~135 t/s sufitu, ale UD-Q4_K_M (16,6 GB) się nie mieści; IQ3_XXS 11,7 GB się mieści.
  - Apple M5 Pro 48 GB: działa (demo producenta).
- **NVFP4 natywnie:** przyspieszenie tensorowe tylko na Blackwell (5060 Ti / 50xx: FP4). Na XTX, Ampere i Apple idzie przez GGUF (Q4_K) z KLD 0,011.
- **Silnik:** mainline llama.cpp ma architekturę `inkling2` (`src/models/inkling2.cpp` w klonie 5f83714 z 2026-11-20). **Topka (baza b11528) jej nie ma**, więc potrzebny rebase (K-056) albo port architektury. Brak głowicy MTP [INFERENCE: nie ma jej w karcie modelu], więc spekulacja tylko z lookupu albo z osobnego draftera.

## Lekcje
- Pętla warstw to nowy wymiar kompromisu jakość / pasmo: mniej wag, więcej obliczeń na wagę. Dla dekodu ograniczonego pasmem (batch 1) oznacza to więcej jakości na GB/s, dopóki pętla nie mieści się w cache.
- Pomysł na nasz silnik [INFERENCE]: przy pętli te same wagi idą 3 razy z rzędu. Kernel MoE, który trzyma kafel wag w LDS albo L2 przez 3 przejścia, oszczędzi do 2/3 odczytu środkowych bloków.

## Powiązane
- [[KOLEJKA-TESTOW]] (K-133)
- [[ZRODLA]]
