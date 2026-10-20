---
typ: research
tags: [research, kwanty, kompresja, wynik-negatywny]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/24t-entropia-wag.md:8-17,50-57,82
status: aktualne
---
# Raport 24t: bezstratna kompresja entropijna wag GGUF (DFloat11/ZipNN) – kill

**Kody kwantów K-quant/IQ4 są prawie maksymalnie losowe (Q4_K 3.86/4 b, Q5_K 4.86/5, Q6_K 5.79/6): sufit kody + skale ≈ 5.0% bajtów/token (Qwen) i ≈ 5.1% (LFM), a kodek z losowym dostępem daje 0–0.9% – poniżej bramki 8% (2026-10-20).**

- Najlepszy model kontekstowy: 2.83% bajtów/token Qwen (0.48 GB z 16.83 GB), 2.92% LFM (`24t:10`).
- Huffman + indeks 16 b/blok ~0.6%/0.9%; stałe sloty 0.00%; rANS 0.35%/0.53%; zstd -19 na Q5_K 1.000 (`24t:14-17`).
- Powrót tylko dla formatów z redundancją (BF16/FP8, NVFP4) (`24t:82`). Kwanty: [[kwanty-gguf]].

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[kwanty-gguf]]
- [[raport-15e-kwantyzacja-nowa]]
- [[wyniki-negatywne]]
