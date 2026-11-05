---
typ: repo
tags: [repo, atencja, dlugi-kontekst, odrzucone]
aktualizacja: 2026-11-05
zrodlo: ~/KERNEL/product/research/63d-atencja-spec-kwant.md:9-19,67-167; https://github.com/Prefrontal-AI/latent-sparse-attention (`5ebea73`, 2026-11-04); arXiv 2610.42147 v2
status: aktualne
---
# Latent Sparse Attention (Prefrontal AI + ETH)

**Klucze bez RoPE rzutowane do 64 wymiarów, klastrowane metodą Warda w kubełki; zapytanie wybiera top-1024 kubełków. Nagłówkowe 72.4× (prefill jednej warstwy) i TTFT ~1/9 dotyczą 10M tokenów na 8×H200; przy 512k TTFT 1.03× (H200) i 0.68× (B300) (2026-11-05).**

- Baseline „pełna atencja” to Qwen ze stałym YaRN ×40 także przy 4k; mapę destylowano pod tę rotację. Na natywnym RoPE nikt jej nie mierzył.
- W tej samej tabeli block-sparse flat (styl QSA) wygrywa do 512k (1.61×).
- U nas atencja to 11.5% prefillu przy 32k i 51% przy 262k (model T(N) = aN + bN²); port 4–7 tygodni.
- **Odrzucone** ([[2026-11-05-tylko-bezstratne]]): rzadka atencja zmienia wyjście. Lekcja: „N× przy 10M” nie przenosi się na ≤ 262k.

## Powiązane
- [[repo/_hub|repo]]
- [[qwen-qsa-llama-cpp]]
- [[strata-kva]]
- [[raport-63-synteza]]
- [[opoznienia-ttft]]
