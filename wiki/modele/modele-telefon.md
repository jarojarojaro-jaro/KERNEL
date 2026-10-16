---
typ: model
tags: [modele, telefon, arm]
aktualizacja: 2026-10-16
zrodlo: ~/telefon/PROMPT-optymalizacja-modeli.md:1-4,56,58-61,83,104,129-131,135-159,163,180; ~/telefon/PROMPT-minicpm-speed.md:1-22; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:395
status: do-sprawdzenia
---
# Modele na telefon: MiniCPM-V 4.7 1B i EmbeddingGemma 2

**Osobny projekt (`jarojarojaro-jaro/phoneuse`): lokalny agent na telefonie realme Note 50 (Unisoc UMS9230H), gdzie EmbeddingGemma dopasowuje podpisy ekranu, a MiniCPM-V jest opcjonalny; zasada: model nigdy nie klika z pewnością w złe miejsce.**

Telefon: 2× Cortex-A75 + 6× Cortex-A55 (ARMv8.2-A, dotprod i fp16, bez i8mm/bf16/SVE), Mali-G57 MP1, RAM 2.8 GB (wolne zwykle ~200–300 MB), Android 15 bez roota.

**EmbeddingGemma 2** (271M parametrów, z czego ~134M to `token_embd`; architektura `gemma-embedding2` bez KV cache; tokenizer `gemma4` BPE): Q8_0 był najszybszy (87 tok/s) i najdokładniejszy; plik ~249 MB, przycięcie słownika ma dać ~150 MB [szacunek w prompcie]. Cel: ekran z 20 podpisami < 2 s, pamięć ≤ 150 MB Anon.

**MiniCPM-V 4.7 1B** (architektura `qwen35`, BPE): prompt 18 tok/s w serwerze vs 35 w llama-bench pp; ładowanie 14.8 s; plik ~670 MB (przycięcie słownika → ~350 MB [szacunek]). Bramka: zostaje tylko, jeśli na evalu 100 kroków zmniejsza liczbę „nie wiem” bez pewnego błędu i mieści się w ≤ 500 MB.

Prompt „minicpm-speed” przenosi nasz playbook (profil → najgorętszy kernel → poprawka NEON w `ggml-cpu`). Raport 07 cytuje dane użytkownika: prefill 35 → 100, decode 9 → 17–18 t/s (lokalnie brak logów).

## Powiązane
- [[modele/_hub|Modele]]
- [[playbook-optymalizacji]]
- [[kwanty-gguf]]
- [[decyzje/_hub|Decyzje]]
- [[modele-katalogowe]]
