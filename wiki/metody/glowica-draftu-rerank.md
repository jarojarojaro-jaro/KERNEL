---
typ: metoda
tags: [metody, spekulacja, glowica, mtp]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/product/research/66d-saber-engine-rdna.md:101-117,158; Saber `dflash_head.hip:1-40,88-93,607-610` (c8a1e84)
status: do-sprawdzenia
---
# Głowica draftu: grube przejście + dokładny rerank top-K

**Saber liczy głowicę draftu w int2 (kandydaci = maksima bloków po 64 kolumny, KCAND 8), a potem dokładnie przelicza tylko kandydatów na wierszach pełnej precyzji („kilkaset KB wobec 0.167 GiB”); u nas ten sam trik może odzyskać −2–3% akceptacji, które kosztuje głowica MTP w IQ4_XS (łatka 0032) (raport 66d, 2026-11-07).**

- Dziś: głowica i blok MTP przekwantowane do IQ4_XS, słownik 65 536; draft 4.82 → 3.62 ms/krok, akceptacja −2–3%, netto +1–3% ([[latki-spekulacji]]). Głowica draftu to 178 MB na przebieg ([[lekcja-lm-head-bottleneck]]).
- Ramię B1: IQ4_XS jak dziś + rerank top-8 na wierszach Q6_K `output.weight` (`get_rows` + mul_mat 8 × 5120). Szacunek spec_sweep +1…3%.
- Ramię B2: Q2_K na słowniku 65 536 + rerank, ~110 MB na przebieg, +1…4% `[SZACUNEK]`.
- Bezstratne: zmienia tylko draft, weryfikacja nietknięta, md5 bez zmian.
- Bramka offline: czy top-8 grubej głowicy zawiera argmax Q6_K na zalogowanych logitach. Potem spec_sweep T=1 + E0 + `mvs`, ABBA.

## Powiązane
- [[metody/_hub|metody]]
- [[glowica-mtp]]
- [[latki-spekulacji]]
- [[saber-engine]]
- [[lekcja-mtp-glowica-optimum]]
- [[raport-66-synteza]]
