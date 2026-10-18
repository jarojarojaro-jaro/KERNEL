---
typ: model
tags: [modele, kwanty, qwen]
aktualizacja: 2026-10-16
zrodlo: ~/qwen-opt/cloud/runs/3060/pre/saluki-README.md; ~/qwen-opt/cloud/runs/3060/pre/saluki-head.json; ~/KERNEL/product/research/10-post-training.md:45,52,139,337,389,453; ~/KERNEL/product/research/09-chmura-3060.md:21-29,41-82,109-127,202-223; ~/KERNEL/product/research/15e-kwantyzacja-nowa.md:52-55,91,154-157; ~/KERNEL/product/research/16e-kwanty-kld.md:34-46
status: aktualne
---
# Underdog Saluki 27B 1.0 (Qwen3.8-27B w 2 bitach)

**Qwen3.8-27B skwantyzowany do 7.90 GB (IQ2-mix na bazie ISTA GSQ-RCO), strojony pod tool calling; na RTX 3060 działa z czystym upstreamem, ma najlepsze PPL i polszczyznę wśród naszych 2-bitowych 27B, ale bez MTP i z prędkością ~23 t/s.**

- Autor: ConwayResearch / Underdog, Apache-2.0; baza `Qwen/Qwen3.8-27B` i `ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF`. Deklaracje autora: tool calling 88 vs 84 pełny model; raport 10: AIME 2025 79.2 vs 96.7.
- Plik: same standardowe typy (IQ2_XXS 34% elementów, IQ3_S 11%, IQ1_M 11%, Q2_K 10%…), `token_embd` w IQ1_M; **brak tensorów MTP**. Istnieje społeczny wariant z MTP (`Kujira/…-MTP-…`).
- RTX 3060 (2026-10-16): PPL wikitext-2 (64×512) **7.6665 ± 0.150**; decode A0 22.1 → nasz silnik **23.4 t/s** (+4.8% vs flagi upstream, w tym ~2.4 pkt z `GATE_UP_Q8=0`); prefill −2%; VRAM ~9.7 GB. n-gram neutralny (akceptacja 0.09).
- md5 forka ≠ upstream, ale KLD forka 0.000650 vs szum upstreamu 0.000612 – PASS.
- Po polsku pisze czysto; zalecany dla aplikacji PL na 12 GB.

Uzupełnienie (raport 15e): nagłówek ma `general.name = "Qwen3.8-27B GSQ-RCO"` i `quantized_by = ISTA DASLab` – to plik z potoku ISTA z własną, niższą alokacją (~2.35 bpw); „strojenie pod tool calling” nieopisane. Graft MTP Kujiry (`Kujira/Underdog-Saluki-27B-1.0-MTP-GGUF`, 8.35 GB, głowica Qwena w Q8_0): RTX 3080 12 GB 41.2 → 66.2 t/s (×1.61), VRAM 11.5 GB, ctx ≤ 32k – najtańszy zysk dla 12 GB, nasz pomiar 3060 (23.4 t/s bez MTP) go nie użył.

E1 (2026-10-18): KLD do Qwen BF16 wiki 0.257, PL 0.320 (PL/wiki 1.24 – imatrix „angielski”); Swift IQ3_XXS-mtp daje tę samą prędkość z MTP przy KLD-PL 0.108.

## Powiązane
- [[modele/_hub|Modele]]
- [[bonsai]]
- [[qwen3-8-27b]]
- [[rtx-3060]]
- [[raport-09-chmura-3060]]
- [[conway-research]]
- [[raport-15e-kwantyzacja-nowa]]
