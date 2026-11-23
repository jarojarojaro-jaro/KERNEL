---
typ: lekcja
tags: [lekcje, moe, spekulacja, inkling]
aktualizacja: 2026-11-23
zrodlo: REKORDY.md (Qwen3.8-27B XTX: tg128 43,2 t/s, xbench Q4 251,9, T=0,7 79,0); qwen-opt/queue/logs/ink-r11-tg.log i ink-r11-serve.log (Inkling AD-Q4_K, KV q4_0, 2026-11-23); DUO-INKLING.md (liczba kerneli)
status: aktualne
---
# Dlaczego gęsty Qwen 27B ze zgadywaniem jest na XTX szybszy od małego MoE Inkling

**Bez zgadywania MoE wygrywa (Inkling 60,6 t/s vs Qwen 43,2 t/s, +40%), ale ze zgadywaniem gęsty model odjeżdża (kopie 251,9 vs 95,2 t/s), bo weryfikacja kilku tokenów w gęstym modelu czyta wagi raz, a w MoE każdy token wybiera innych ekspertów.**

- **Sufit pasma:** Qwen czyta ~16 GB na token (sufit ~58 t/s), osiąga 43 (~74% sufitu). Inkling czyta ~3,3 GB (sufit ~290), osiąga ~61 (~21%): zjada go ~2000 małych kerneli na token przy 48 przejściach warstw (pętla 12 warstw × 3), a nie pasmo.
- **Weryfikacja zgadywania:** w gęstym modelu sprawdzenie 5 tokenów kosztuje niewiele więcej niż 1 (te same wagi, mnożone przez 5 kolumn — [[mmvq-multikolumnowe]]). W MoE 8 tokenów × top-8 to do 64 różnych ekspertów: koszt rośnie prawie liniowo, więc spekulacja daje mniej.
- **Dojrzałość:** Qwen ma za sobą miesiące łatek (MTP z głowicą IQ4_XS, słownik 64k, PM4); Inkling ma 3 dni.
- **Wniosek na każdą kartę:** małe aktywne parametry pomagają w dekodzie bez spekulacji; przy spekulacji liczy się koszt weryfikacji, a ten w MoE zależy od rozrzutu ekspertów. Maya łagodzi to kontrolerem (wyłącza zgadywanie, gdy się nie opłaca).

## Powiązane
- [[inkling-2-mini]]
- [[maya-ik2-inkling]]
- [[mmvq-multikolumnowe]]
