---
typ: archiwum
tags: [archiwum, lfm, moe]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/product/research/16g-lfm-moe-pasmo.md:1-123
status: nieaktualne
wycofano: 2026-11-22
powod: ten sam raport 16g dwa razy
zastapiona_przez: testy/2026-10-18-lfm-moe-pasmo
---
# Raport 16g: pasmo kerneli MoE LFM2.5 na XTX

**Agent XtxLfmMoe rozłożył narzut matvec LFM2.5 (718 µs/token) na kernele, pokazał mikrobenchem i ATT, że gate+up ogranicza wzorzec dostępu, i zbudował bitowy kernel `GGML_HIP_MOE_GU_BLOCK` (`7c5b2a116`): LFM +0.33% (w szumie), Uncensored +1.39%, stabilniejsze tempo.**

Rekomendacja agenta: scalić z wyłącznikiem, domyślnie włączone – decyzja otwarta (Main/użytkownik, [[seria-amd-opt]]). Dalsze zyski matvec bez zmiany formatu wag małe; większa dźwignia to PM4-PDL / prefetch między kernelami (raport 15a).

Notatki: [[2026-10-18-lfm-moe-pasmo]], [[mmvq-moe-gate-up-blok]], [[att-gfx1100]], [[lekcja-sufit-wzorca]], [[lekcja-limit-mocy-285w]], [[2026-10-18-lfm-moe-negatywne]].

## Powiązane
- [[raport-15a-monokernel]]
- [[lfm2-5-24b-a2b]]
- [[lfm2-5-uncensored]]
