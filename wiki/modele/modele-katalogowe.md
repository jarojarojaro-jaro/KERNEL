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

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)

- Plan MVP katalogu z raportu 06 (Qwen3.8-27B, Gemma 4, gpt-oss-20b, Bielik 11B v3, Mistral Small 4) rozjechał się z tym, co wydaliśmy. W `app/engine/data/catalog.json` są: qwen38-27b, bonsai2-27b, qwen36-35b-a3b, flint-40b-a2.5b, lfm25-24b-a2b, gemma4-31b/26b-a4b/12b, qwen35-9b/4b, gpt-oss-20b, lfm25-2.6b. **Nie ma Bielika ani Mistrala Small 4**, choć to dwa modele polecane wprost dla rynku PL.
- To nie jest sprawa prędkości kerneli, tylko produktu: Bielik v3 z tokenizerem APT4 ma 1.62 tokenu na polskie słowo wobec 2.69 Qwena (`product/research/06-produkt-ux-prawo-biznes.md:95-97`), czyli po polsku ok. 1.66× mniej tokenów na tę samą odpowiedź — tyle, ile dają miesiące pracy nad kernelami. Ma też gotowy drafter DFlash.
- Raport 04 zalecał Bielika w tierach ≤ 12 GB i Apple 16 GB (`product/research/04-wykrywanie-sprzetu-i-dobor-modeli.md:337-345,554`) oraz własny pomiar PLCC, bo publicznych wyników dla Qwen3.8/Gemma 4 brak (`04:385,572`). Tego pomiaru nie zrobiliśmy; [[jakosc-mini]] ma PL tylko jako 50 pytań Global-MMLU.
- gpt-oss-120b, Kimi K3, GLM-5.2 to tiery 96–128 GB / serwerowe — poprawnie poza katalogiem konsumenckim.
- Co bierzemy: zanim dodamy kolejny kernel dla Qwena, sprawdzić na 8–12 GB pakiet „Bielik v3 + DFlash” (tokeny na słowo, t/s, jakość-mini PL) jako opcję dla polskiego użytkownika; decyzja o Mistralu Small 4 tylko dla 96–128 GB.

## Powiązane
- [[modele/_hub|Modele]]
- licencje-modeli
- [[qwen3-8-27b]]
- raport-06-produkt-prawo
- [[inne-karty-nvidia]]
- [[modele-telefon]]: osobny projekt na telefon (MiniCPM-V, EmbeddingGemma)
