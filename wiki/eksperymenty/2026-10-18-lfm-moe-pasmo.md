---
typ: eksperyment
tags: [eksperymenty, lfm, moe, pasmo]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/product/research/16g-lfm-moe-pasmo.md:1-93; ~/wt/lfmmoe-prof/{base_tr_1.txt,base_rp_1.txt}; ~/wt/lfmmoe-prof/frozen/{abba_lfm.txt,abba_unc.txt,check1.txt}
status: aktualne
---
# 2026-10-16/18: pasmo kerneli MoE LFM2.5 na XTX

**Narzut matvec LFM2.5 to 718 µs/token (2644 vs 1926 µs idealnego strumienia przy 900 GB/s); gate+up ekspertów (247 µs, 673 GB/s) ogranicza wzorzec dostępu, nie obliczenia, a nowy kernel `GGML_HIP_MOE_GU_BLOCK` daje LFM tylko +0.33% (szum), Uncensored +1.39%.**

Profil (PM4 trace, µs/token narzutu): gate+up ekspertów 247, in_proj+conv 145, down Q5_K+Q6_K 129, out_proj 92; głowica Q6_K 894 GB/s (2 µs). Zgodne z 15a (698 µs).

Kryterium zabicia (ustalone przed pomiarem): llama-bench tg128 ABBA ≥ +0.7% przy niezmienionych hashach logitów i md5 `894e56e4`.

| pomiar (ABBA, ten sam build) | `=0` | domyślnie | zmiana |
|---|---|---|---|
| LFM llama-bench tg128, 12 procesów | 291.26 t/s (286.78–294.04) | 292.22 (291.38–293.05) | +0.33% |
| LFM spec_sweep `lfm none` | 290.25 | 290.85 | +0.2% |
| Uncensored llama-bench, 8 procesów | 264.60 | 268.27 | +1.39% |

In-model gate+up 25.36/27.24 → 24.84/25.00 µs (znika bimodalność między procesami), ale out_proj 5.48 → 5.76–5.84 µs ([[lekcja-limit-mocy-285w]]). Bitowe: hashe 64 kroków (LFM `a7ce25b73f887fed`, Uncensored `f74300e3142a5535`), md5 `894e56e4…` w obu ustawieniach. Werdykt: dla LFM kryterium niespełnione, dla Uncensored spełnione; scalenie otwarte ([[seria-amd-opt]], kandydat 0071).

Dalej: sufit obecnego formatu 19.7 µs (4 wiersze/blok) vs 22.3 dziś – wymaga przepakowania wag (~3% `[SZACUNEK]`); in_proj/out_proj raczej PM4-PDL (15a).

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[mmvq-moe-gate-up-blok]]
- [[att-gfx1100]]
- [[2026-10-18-lfm-moe-negatywne]]
- [[2026-10-16-budzet-lfm-megakernel]]
- [[lfm-runda-4-pm4]]
