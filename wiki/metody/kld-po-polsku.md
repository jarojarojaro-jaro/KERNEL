---
typ: metoda
tags: [metody, kld, polski, kwantyzacja]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/product/research/16e-kwanty-kld.md:69-98,154-158; ~/qwen-opt/cloud/results/quantkld-20261016/pod-final/res/corpora.md5
status: aktualne
---
# KLD kwantów na polskim tekście (protokół 16e)

**Referencja to prawdziwe BF16 (na 48 GB z `-fit on`, offload do RAM, 54–240 s na korpus), a ocena idzie na pięciu korpusach o stałych md5, w tym trzech polskich; KLD-PL/KLD-wiki pokazuje, czy kwant ma „angielski” imatrix.**

| korpus | co | md5 | ocena |
|---|---|---|---|
| wiki | `wiki.test.raw` | 7c0137fc… | 20 × 2048 |
| plprose | FineWeb-2 `pol_Latn` test, seed 0, 800k znaków | cae78980… | 20 × 2048 |
| chat | 36 promptów PL/EN, odpowiedzi Qwen Q8_0 teacher-forced | 783d39ac… | 11 × 2048 |
| code | 103 prywatne pliki `.py`/`.sh` | b2191461… | 20 × 2048 |
| long | „Lalka” t. 1, 160k znaków | a19a58a4… | 2 × 16384 |

Komenda: upstream `llama-perplexity` v0.7.0 `-fa on -b 2048 -ub 1024 --kl-divergence-base/--kl-divergence`. Powtarzalność: U3 wiki 0.038982 w obu rundach (A40 i A6000). Podłoga Q8_0 vs BF16 0.0006–0.0038.

Odczyt (2026-10-18): GSQ i UD tracą na PL mniej niż na wiki (PL/wiki 0.73–0.95), Saluki 1.24, Bonsai 1.44; czat najtrudniejszy (1.3–2 × PL proza); long/PL 1.08–1.25 – brak skoku na długim kontekście.

## Powiązane
- [[metody/_hub|Metody]]
- [[bramka-kld-kanarki]]
- [[lekcja-kld-protokoly]]
- [[2026-10-18-e1-kwanty-27b-kld]]
