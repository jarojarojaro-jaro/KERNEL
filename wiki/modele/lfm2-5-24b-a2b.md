---
typ: model
tags: [modele, lfm, moe]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:333-341,354,363; ~/KERNEL/qwen-opt/STATUS-NEXT.md:12; ~/KERNEL/product/research/06-produkt-ux-prawo-biznes.md:51,355; ~/KERNEL/product/research/10-post-training.md:141; ~/KERNEL/qwen-opt/tools/kld-canary.md:66-67; ls ~/models (2026-10-16); ~/KERNEL/product/research/09-chmura-5060ti.md:76-86,156,164-186,197; ~/KERNEL/product/research/09-chmura-3090.md:53-61; ~/KERNEL/product/research/16g-lfm-moe-pasmo.md:15-33,83-89
status: aktualne
---
# LFM2.5-24B-A2B (Liquid AI)

**MoE 24B z ~2B aktywnymi parametrami i warstwami krótkiej konwolucji; na RX 7900 XTX z 173 do 294 t/s, bez spekulacji (brak draftera).**

Architektura (`lfm2moe`, NOTES 2026-10-14): 40 warstw (30 shortconv + 10 GQA 32/8), 2 pierwsze gęste, potem MoE 64 ekspertów / 4 aktywne (ffn 1536), emb 2048, słownik 128k, głowica związana z `token_embd` (Q6_K, 205 MiB). Eksperci Q5_K/Q6_K = 15.1 GiB z ~16 GiB. Bajty na token ≈ 1.8 GB → próg pasma ~1.9 ms (~500 t/s).

Plik: `~/models/lfm/LFM2.5-24B-A2B-Q5_K_M.gguf` (15.86 GiB). Ustawienia (`run-llm.sh lfm`): ctx 131072, **KV q8_0** (decyzja użytkownika), bez spekulacji.

Wyniki: baza na forku przed pracą pod LFM — czat 173 t/s, tg128 198 t/s (upstream 169.3); po rundach 1–4 (2026-10-15): **293.7 t/s**, 3.41 ms/krok, pp4096 6175, tg128 289.7.

KV q8_0 vs f16: KLD 0.044 (q4_0: 0.128). Draftery: brak (jest tylko DFlash dla LFM2.5-1.2B / VL-3B). W `~/models/lfm` leży też LFM2.5-2.6B-QAD-Q4_0 (1.48 GiB), bez pomiarów w notatkach.

Na NVIDIA (raport 09, 2026-10-16): RTX 3090 Q5_K_M A0 180.2 → nasz silnik 263.9 t/s (profil Ampere); RTX 5060 Ti Q4_K_M 147.69 → 207.86 t/s. Q5_K_M (15.86 GiB) nie mieści się w 16 GB (z `--n-cpu-moe 6` tylko 120.9 t/s tg128). Najlepszy plik dla 16 GB to oficjalny **QAD-Q4_0** Liquid (quantization-aware distillation, 13.58 GB): KLD 0.2029 (Q4_K_M 0.2008), PPL(Q)/PPL(Q8) 0.869, serwer 164.5 → 226.8 t/s (+38%) i md5 forka = upstream. Prefill LFM rośnie o +56% z `-b 2048 -ub 2048`.

Licencja: LFM Open License v1.0 — za darmo komercyjnie tylko poniżej 10 M$ rocznego przychodu (dotyczy też klientów B2B).

Pasmo MoE (16g, 2026-10-18): narzut matvec 718 µs/token; gate+up ekspertów 673 GB/s, in_proj+conv 593, out_proj 519, głowica Q6_K 894 GB/s. Kandydat `GGML_HIP_MOE_GU_BLOCK`: +0.33% (szum), usuwa rozrzut między procesami (llama-bench 286.8–294.0 → 291.4–293.1 t/s) ([[2026-10-18-lfm-moe-pasmo]]).

## Powiązane
- [[modele/_hub|Modele]]
- [[lfm2-5-uncensored]]
- [[fuzje-lfm-moe]]
- [[liquidai]]
- [[lfm-runda-4-pm4]]
- [[raport-09-chmura-5060ti]]
