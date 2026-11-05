---
typ: repo
tags: [repo, atencja, dlugi-kontekst, odrzucone]
aktualizacja: 2026-11-05
zrodlo: ~/KERNEL/product/research/63c-amd-rocm-llamacpp.md:103-151,319-334; https://github.com/pentaCoxian/Qwen-QSA-llama.cpp (`fe08b16`, 2026-11-05)
status: aktualne
---
# Qwen-QSA-llama.cpp (pentaCoxian): rzadka atencja QSA dla Qwen3.8-27B

**Fork llama.cpp dokleja do 16 warstw pełnej atencji wyuczone indeksery (52.4M parametrów FP32, 300 kroków treningu); każde zapytanie czyta 2048 tokenów w blokach po 4. Na RTX 4090 przy 255K: decode 114.7 vs 40.6 t/s, prefill 2375 vs 1345 t/s (2026-11-05).**

- Wagi pnia bez zmian (indeksery z `higa2515/Qwen3.8-27B-QSA-BF16`), cały KV zostaje, sparse FA czyta Q8_0.
- Jakość: recall 24/24, two-hop 11/16 vs 12/16, PPL +2.44% przy 64k na UD-Q4_K_M; KL przy długim kontekście „not tested”.
- Liczby są z **4090, nie z XTX**. Nasz szacunek dla XTX (199k 74.5 → 105–115 t/s) to tylko arytmetyka.
- **Odrzucone 2026-11-05** ([[2026-11-05-tylko-bezstratne]]): zmienia wyjście. Port QSAPort zaparkowany. Bezstratna alternatywa dla długiego kontekstu: profil kroku i jedno przejście KV w [[fattn-kvq]].

## Powiązane
- [[repo/_hub|repo]]
- [[latent-sparse-attention]]
- [[qwen-warp]]
- [[raport-63-synteza]]
- [[qwen3-8-27b]]
