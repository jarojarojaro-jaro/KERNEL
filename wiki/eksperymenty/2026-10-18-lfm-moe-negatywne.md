---
typ: eksperyment
tags: [eksperymenty, lfm, moe, wyniki-negatywne]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/product/research/16g-lfm-moe-pasmo.md:43-65,97-103; ~/wt/lfmmoe-prof/rp_r6_{1,2,3}.txt, mb3.txt
status: aktualne
---
# 2026-10-18: wyniki negatywne MoE matvec LFM (mikrobench)

**Warianty kerneli MoE LFM2.5, które nie pomogły w mikrobenchu `moebench.hip` (zimne wagi, rocprofv3, 3 procesy); produkcja gate+up 23.6–24.2 µs, down Q5_K 11.64 µs.**

- 1/3/4/8 wierszy na falę i 2–8 fal na blok bez zmiany ogona: wolniej lub równo (4 wiersze 23.80 vs 22.64 µs; 4 wiersze + prefetch 35.9 µs – za dużo VGPR).
- Ładowania 16 B przez LDS (bariera co iterację): 40–52 µs.
- Pętla w pełni rozwinięta bez prefetchu (16 fal): 24.3 µs.
- Down „ekspert na falę” (4 fale/blok): Q5_K 11.56 vs 11.64 µs; 2–4 wiersze na falę 12.1–14.4.
- Down Q6_K ekspert na falę 13.16 µs – nie bitowe względem produkcji (2 fale na wiersz); wersja bitowa niezbudowana, sufit ~0.5%.
- Q6_K gate/up Uncensored (5 warstw): niezrobione, sufit ≈ 8 µs/token (0.2%).
- Liczniki STABLE_STD: niedostępne bez roota.

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[wyniki-negatywne]]
- [[2026-10-18-lfm-moe-pasmo]]
- [[lekcja-sufit-wzorca]]
