---
typ: repo
tags: [repo, apple, mlx, gdn, gramatyka]
aktualizacja: 2026-10-24
zrodlo: ~/KERNEL/product/research/60b-apple-engines-bonsai.md:3.3; ~/qwen-opt/research/Locals (c0f9baa) README.md:66-74,120-128,175-188; docs/why-faster/README.md:31-41,103-108; docs/runtime/README.md:107-127; https://arxiv.org/abs/2610.09139
status: aktualne
---
# Locals (Generated-Computers/Locals)

**Serwer MLX dla agentów; „przełom w złożoności” dotyczy automatów gramatyki, nie DeltaNet, a kernel GDN to jeden launch na krok wart 1–2% – na nasze kernele HIP nic nie przenosi (raport 60b).**

- Praca arXiv 2610.09139 (Asadulaev): osiągalność w grafach o niewielu ścieżkach w O(log² n / log log n) pamięci; w silniku: tokeny wymuszone bez modelu, maska na GPU (3 MB zamiast do 1.5 GB), 16 agentów z narzędziami 2.5× szybciej niż mlx-lm + llguidance.
- GDN: `gdn_kernel.py` = conv + norma q/k + rekurencja + gated norm w jednym kernelu Metal (S ≤ 16, stany per token do cofania draftu); ablacja 267.6 → 272.7 tok/s (+1.9%).
- Źródło 3× (M2 Pro, Qwen3.5-4B, 8 żądań 87 → 271 tok/s): kernele 4-bit pod 2–16 wierszy, fp16 na M1/M2, fuzja projekcji, pipelining.
- Nie szybszy: jedno żądanie (64 vs 61 tok/s), prompty, formaty poza affine 4-bit g64, M5.
- Apache-2.0; compwatch (C).

## Powiązane
- [[repo/_hub|repo]]
- [[omlx]]
- [[gdn-replay]]
- [[raport-60b-apple-bonsai]]
