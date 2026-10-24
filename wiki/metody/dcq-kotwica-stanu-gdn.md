---
typ: metoda
tags: [metody, kwanty, gdn]
aktualizacja: 2026-10-24
zrodlo: ~/KERNEL/product/research/60c-quant-and-3090-engines.md:162-176,211-212; https://huggingface.co/Akahsizrr/mimo-v2.6-distill-qwen-9b-dcq (tools/quant_learned.py, results/*.json)
status: do-sprawdzenia
---
# DCQ: błąd stanu GDN w stracie kwantyzacji

**DCQ (Drift-Correcting Quantisation) uczy zaokrąglenia wag przez STE i dodaje do straty błąd końcowego stanu rekurencyjnego Gated DeltaNet. Pomysł jest przenośny, ale dowody autora są bardzo słabe.**

- Strata: `rel_mse(wyjście) + 0.25 · rel_mse(stan GDN)` plus kotwica do oryginalnych wag.
- Ustawienia: 60 kroków Adama, g=128 symetrycznie, kalibracja tylko 4 096 tokenów WikiText.
- Mapa wrażliwości (MiMo-V2.6-Distill-Qwen-9B, 24 warstwy GDN): `in_proj_qkv` przy 4 bitach ma rel. MSE stanu 0.0198 przy 0.0008 wyjścia, czyli **25× więcej**. `in_proj_a/b` są tanie.
- Dowody (n=20 na zadanie):
  - JSON GPTQ W4 (MMLU 0.80 / GSM8K 0.85) jest równy DCQ W4, choć karta pisze 0.75 / 0.80;
  - „AWQ 0.00” to 40/40 odpowiedzi uciętych limitem, a plik ma ten sam oid co `learned_w2`;
  - AIME BF16 0.20 nie ma pokrycia: w pliku n=2 i 0/2.
- U nas: `attn_qkv` w warstwach GDN Qwen3.8-27B to Q4_K/Q5_K. Plan [[raport-57g-quantalloc-ear]] obniża 15–18 z nich, więc ramię „qkv nietknięty” jest tanim testem. Wymaga BF16.

## Powiązane
- [[metody/_hub|metody]]
- [[kld-po-polsku]]
- [[bramka-kld-kanarki]]
- [[raport-60c-quant-3090]]
- [[kwanty-gguf]]
