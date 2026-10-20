---
typ: research
tags: [research, fuzje, normy, wynik-negatywny]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/24u-norm-quant.md:7-12,18-30,50-52
status: aktualne
---
# Raport 24u: osobny kernel rms_norm × w + quantize q8_1 – stop, zysk ≈ 0

**Założenie zlecenia było nieaktualne: w topce norma × w i kwantyzacja q8_1 już są jednym launchem (`rms_norm_mul_f32_unrolled` z `q8`), a pozostałe `quantize_q8_1` to 6 × 2.04 µs ≈ 0.012 ms/krok przy progu 0.25 ms (2026-10-20, bez GPU).**

- Klasa „quantize 0.20 ms” z 24k to głównie `k_set_rows_quant` (zapis KV q4_0), nie aktywacje (`24u:28`).
- Krótkie kernele po dużym MMVQ trwają dłużej: norma 5 wierszy 4.48 vs 2.72 µs – ~40% kosztu normy to ta kara (`24u:34,52`).
- Ewentualny zysk z likwidacji kary ≤ 132 × 1.8 µs ≈ 0.24 ms/krok (`24u:45`). Ogon producenta odrzucony w [[raport-24l-fuzja-norm]].

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[raport-24l-fuzja-norm]]
- [[raport-24g-hipfire]]
- [[raport-24k-koszt-weryfikacji]]
