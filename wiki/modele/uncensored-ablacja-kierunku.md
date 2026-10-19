---
typ: model
tags: [modele, uncensored, ablacja]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21e-kv-miedzy-modelami.md:86-118; ~/KERNEL/product/research/21e-skrypty/qwen_abl_s.txt; ~/KERNEL/product/research/21e-skrypty/lfm_abl.txt; ~/KERNEL/product/research/21e-skrypty/qwen_diff.txt
status: aktualne
---
# Uncensored = Main + edycja rank-1 kierunku w „pisarzach” strumienia

**Oba nasze modele Uncensored to analityczne edycje wag Maina, nie fine-tune: Qwen3.8-27B-Uncensored (OrcaRouter) ma jeden globalny kierunek r rzutowany ze wszystkich writerów strumienia rezydualnego (s = 0.994–1.000), a LFM2.5-Uncensored (AtomicChat) ma osobny kierunek r_l w każdej warstwie 14–39 ze skalą 1.75 (analiza wag na CPU, raport 21e, 2026-10-19).**

- **Qwen (Orca):** W' = (I − r rᵀ)·W dla `token_embd`, `attn_output`, `ssm_out`, `ffn_down` warstw 0–64 (z MTP; `nextn.eh_proj` nieruszony); |cos| 0.99–1.00 między writerami. Czytające (`attn_q/k/v`, `attn_qkv`, `ffn_up/gate`, `ssm_alpha/beta`) różnią się tylko szumem kwantów; wszystkie F32 i `output.weight` bajtowo identyczne. Edycja ≈ 1.3–1.6% normy writera (losowy kierunek: 1/√5120 = 1.40%) – mniejsza niż różnica kwantów między plikami (3–11%). Inny szablon czatu (starszy).
- **LFM (AtomicChat):** W' = (I − 1.75·r_l r_lᵀ)·W w warstwach 14–39 (s = 1.745–1.760, odbicie z nadmiarem do −0.75), warstwy 0–13 i embedding nieruszone (s ≈ 0); zgodne z metadanymi `atomic.abliterate.layers=14-39`, `scale=1.75`; router, shortconv i normy bajtowo identyczne.
- Metoda: dekwantyzacja par tensorów (gguf-py), SVD różnicy, skala z modelu `W_unc = (I − s·r rᵀ)·W_main`; kierunki zapisane w `21e-skrypty/r_qwen.npy` i `r_lfm.npy`. Zbadana próbka: 21 z ~131 writerów Qwena, wszystkie 40 warstw LFM.

Skutek: Uncensored może być trybem w locie na wagach Maina ([[przelaczanie-main-uncensored]]); pokrewne: Arditi i in. 2024 (arXiv 2406.11717).

## Powiązane
- [[modele/_hub|Modele]]
- [[qwen3-8-27b-uncensored]]
- [[lfm2-5-uncensored]]
- [[single-neuron-safety-2605-08513]]
