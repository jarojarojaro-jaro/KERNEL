---
typ: repo
tags: [repo, lm-head, rdna3]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/18-nastepna-fala.md:455-465; http://knlp.io/lm_head_decode.html; https://github.com/mcgrof/knlp/tree/main/lm_head/kernel
status: aktualne
---
# knlp: certyfikowana głowica LM przy dekodowaniu

**Metoda: słownik w 256 blokach, offline baza PCA stanów (r ≈ 0.36·d), cień int8 `W_U·B` i normy reszt wierszy; w dekodowaniu górna granica każdego logitu z Cauchy'ego–Schwarza, a bloki otwiera się, aż najlepszy dokładny logit przewyższy granice reszty – bezstratnie. U nich na W7900 (gfx1100) głowica Qwen2.5-7B ×1.97 przy batch 1, ~5× mniej bajtów, batch 4/8 ×1.36/×1.41.**

Na Qwen3.8-27B nie działa: stany mają wysoki wymiar efektywny (ρ/‖h‖ = 0.39 przy r = 0.36·d), certyfikat otwiera 97.5% bloków ([[2026-10-19-certyfikowana-glowica-pilot]]). Kernele w Triton. Pokrewne: VocabTrim (arXiv 2506.22694).

## Powiązane
- [[repo/_hub|repo]]
- [[raport-18-nastepna-fala]]
- [[latki-spekulacji]]
