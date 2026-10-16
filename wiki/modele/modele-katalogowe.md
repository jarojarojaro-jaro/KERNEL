---
typ: model
tags: [modele, katalog, licencje]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/06-produkt-ux-prawo-biznes.md:50-53,64,95-97,355-364,445-448,500; ~/qwen-opt/cloud/models.tsv; ~/qwen-opt/cloud/PLAN-TESTOW.md:56,85-91; ~/KERNEL/product/research/10-post-training.md:138; ~/KERNEL/research_notes/Optymalizacja kerneli na AMD/local_llm_practice.md:36
status: aktualne
---
# Modele katalogu produktu i testów (gpt-oss, Gemma 4, Qwen3.5-9B, Bielik, Mistral)

**Modele z licencją Apache 2.0, które produkt ma polecać i które testujemy na kartach NVIDIA; dla nich nie mamy jeszcze własnych kerneli.**

| model | licencja | gdzie u nas | uwagi |
|---|---|---|---|
| gpt-oss-20b (MXFP4) | Apache 2.0 + usage policy | `models.tsv` (3090, 5060 Ti, 4060 Ti), drafter EAGLE3 | w MVP katalogu |
| Gemma 4 12B (Q4_K_M) | Apache 2.0 (od 2026-04-02) | `models.tsv` (3060) + drafter MTP | wg promptowy.pl najlepsza po polsku na 8 GB (72.3 pkt) |
| Qwen3.5-9B (Q4_K_M) | — | `models.tsv` (5060 Ti, 4060 Ti, 3060), bez MTP w GGUF | istnieją MTP, DFlash, EAGLE-3; na 9070 XT Vulkan Q6_K 62 t/s vs vLLM FP8 48 t/s |
| Bielik 11B v3 | Apache 2.0 | brak testów | rekomendowany na rynek PL; tokenizer APT4 (PL 3.22 → 1.62 tok/słowo); istnieje `Bielik-11B-v3.0-DFlash` |
| Mistral Small 4 | Apache 2.0 | brak testów | w MVP katalogu |

MVP katalogu (raport 06): Qwen3.8-27B, Gemma 4 (rozmiar wg VRAM), gpt-oss-20b, Bielik 11B v3, Mistral Small 4; LFM2.5 tylko w edycjach konsumenckich (próg przychodu). Wykluczone: **Llama 4** (brak praw dla firm z UE dla modeli multimodalnych), Gemma ≤3 tylko z ograniczeniami, Qwen Community License (Qwen3.8-Flash-Next) wymaga osobnej licencji dla „AI Work Assistant”.

Polski: tokenizer Qwen3 ma 2.69 tokenu na słowo (EN 1.17), stąd przyspieszenie liczy się po polsku bardziej.

## Powiązane
- [[modele/_hub|Modele]]
- licencje-modeli
- [[qwen3-8-27b]]
- raport-06-produkt-prawo
- [[inne-karty-nvidia]]
- [[modele-telefon]]: osobny projekt na telefon (MiniCPM-V, EmbeddingGemma)
