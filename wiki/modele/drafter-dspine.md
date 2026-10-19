---
typ: model
tags: [modele, spekulacja, drafter]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21a-dspine.md:13-38,39-77,307-321; https://arxiv.org/abs/2609.36173; https://huggingface.co/tencent/Qwen3-8B-DSpine-b16
status: aktualne
---
# Drafter DSpine (Tencent YouTu): DFlash z przyczynowym kręgosłupem

**Drafter z rodziny DFlash (5 warstw, blok 16, K/V z cech 5 warstw celu, wspólny embedding i LM head) z trzema zmianami: atencja w bloku przyczynowa, po każdej warstwie bramkowana wiadomość z przewidywanej cechy poprzednika (przestrzeń 1024-d z wybielonych wierszy LM head celu) i wybór tokenu warunkowany poprzednikiem („transition cache”, K=16) (arXiv 2609.36173v2, 2026-10-10).**

- 8B: 1.24 mld parametrów BF16, plik 2.48 GB; trening ≤ 3072 tokenów, dane Open-PerfectBlend (1.42 M próbek, praktycznie tylko EN, ~42% matematyki) – brak PL i długiego kontekstu.
- τ Qwen3-8B przy tych samych danych (karta HF): T=0 7.83 vs DFlash2 7.55 (+3.7%), T=1 6.98 vs 6.53 (+6.9%); artykuł (ShareGPT) 4.82 vs 4.39 (+10%). Nagłówek „+27.8% nad DFlash” liczy od DFlasha przetrenowanego przez autorów (3.77) zamiast oficjalnego (5.92) – [[lekcja-naglowki-drafterow]].
- Przepustowość H100 +11.1% nad DFlash2 `[INFERENCE]`. Wsparcie tylko SGLang 0.5.20 (BF16, kwantyzacja zablokowana); w llama.cpp brak, port do forka 5–7 osobodni (mamy graf DFlash/DFlash2, przyczynową atencję draftu, wstrzykiwanie cech; brakuje konwertera, zapisów „bridge” i transition cache).
- 27B: zapowiedziany, niedostępny (2026-10-19). Ocena na XTX: [[raport-21a-dspine]].

## Powiązane
- [[modele/_hub|Modele]]
- [[drafter-dflash]]
- [[glowica-mtp]]
- [[lekcja-drafter-gleboki-vs-mtp]]
