---
typ: model
tags: [modele, lfm, moe]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:333-341,354,363; ~/KERNEL/qwen-opt/STATUS-NEXT.md:12; ~/KERNEL/product/research/06-produkt-ux-prawo-biznes.md:51,355; ~/KERNEL/product/research/10-post-training.md:141; ~/KERNEL/qwen-opt/tools/kld-canary.md:66-67; ls ~/models (2026-10-16)
status: aktualne
---
# LFM2.5-24B-A2B (Liquid AI)

**MoE 24B z ~2B aktywnymi parametrami i warstwami krótkiej konwolucji; na RX 7900 XTX z 173 do 294 t/s, bez spekulacji (brak draftera).**

Architektura (`lfm2moe`, NOTES 2026-10-14): 40 warstw (30 shortconv + 10 GQA 32/8), 2 pierwsze gęste, potem MoE 64 ekspertów / 4 aktywne (ffn 1536), emb 2048, słownik 128k, głowica związana z `token_embd` (Q6_K, 205 MiB). Eksperci Q5_K/Q6_K = 15.1 GiB z ~16 GiB. Bajty na token ≈ 1.8 GB → próg pasma ~1.9 ms (~500 t/s).

Plik: `~/models/lfm/LFM2.5-24B-A2B-Q5_K_M.gguf` (15.86 GiB). Ustawienia (`run-llm.sh lfm`): ctx 131072, **KV q8_0** (decyzja użytkownika), bez spekulacji.

Wyniki: baza na forku przed pracą pod LFM — czat 173 t/s, tg128 198 t/s (upstream 169.3); po rundach 1–4 (2026-10-15): **293.7 t/s**, 3.41 ms/krok, pp4096 6175, tg128 289.7.

KV q8_0 vs f16: KLD 0.044 (q4_0: 0.128). Draftery: brak (jest tylko DFlash dla LFM2.5-1.2B / VL-3B). W `~/models/lfm` leży też LFM2.5-2.6B-QAD-Q4_0 (1.48 GiB), bez pomiarów w notatkach.

Licencja: LFM Open License v1.0 — za darmo komercyjnie tylko poniżej 10 M$ rocznego przychodu (dotyczy też klientów B2B).

## Powiązane
- [[modele/_hub|Modele]]
- [[lfm2-5-uncensored]]
- [[fuzje-lfm-moe]]
- liquid-ai
- [[lfm-runda-4-pm4]]
