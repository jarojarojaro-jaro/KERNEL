---
typ: metoda
tags: [metody, podrecznik, kernele]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/23f-podrecznik-optymalizacji-gpu.md:1-245
status: aktualne
---
# Podręcznik optymalizacji GPU (wejście dla nowego agenta)

**Decode przy batch 1 to strumień bajtów: Qwen3.8-27B plain czyta 16.82 GB/krok przy 75.7% pasma XTX, LFM2.5 1.777 GB/token przy 54%; vendorzy i konkurenci nie mają lepszej pętli GEMV niż nasza wielokolumnowa, najsłabsza gorąca ścieżka to MMVQ n=1, a największą dźwignią na XTX jest bezpieczne PM4 (raport 23f, synteza raportów RE, 2026-10-19).**

Pełny podręcznik (werdykt, ranking 14 zmian, liczby, checklista): [23f-podrecznik-optymalizacji-gpu.md](../../product/research/23f-podrecznik-optymalizacji-gpu.md).

Top rankingu: 1) PM4 z `WA=2` – LFM +13.5%, Qwen MTP +4.9% ([[mec-fw-dispatch-aql-gfx11]]); 2) MMVQ n=1 przez loader `mmvq_ld` – plain +2–5% ([[mmvq-n1-wiersze]]); 3) jedno przejście po KV w weryfikacji – MTP @94–113k +8% ([[fattn-kvq]]); 4) fuzje poza GEMV wg hipfire ≤ +3.5% ([[raport-23e-re-silniki]]); 5) trigger PDL na NVIDIA ([[pdl-mmvq-trigger]]); dalej Q6_K b128, klif VGPR ncols 5 ([[mmvq-multikolumnowe]]), lookup dla LFM, wiele strumieni, hinty NVIDIA, [[bariera-lds-rdna3]], trwały blok MoE (tylko gdy PM4 padnie), mniej bajtów stratnie, narzędzia-bramki ([[co-stats]], [[isa-kstat]], [[umr-offline-pm4]], [[physics-floor-check]]).

Mapa wiedzy: sprzęt [[rdna3-gfx1100]], [[karty-nvidia-parametry]], [[sm-86-89-120]]; roofline [[sufit-pasma-i-mapa-czasu]], [[lekcja-littles-law-gemv]], [[lekcja-sufit-wzorca]]; launch [[pm4-replay]], [[hip-graph-narzut]], [[lekcja-handoff-rdna3]]; numeryka [[zgodnosc-bitowa-md5]], [[bramka-kld-kanarki]]; profilowanie [[rocprof]], [[att-gfx1100]], [[dowod-z-profilu]]; pomiar [[pomiar-abba]], [[wyniki-negatywne]]; bezpieczeństwo [[2026-10-19-bezpieczenstwo-sprzetu]].

## Powiązane
- [[metody/_hub|Metody]]
- [[playbook-optymalizacji]]
- [[REKORDY]]
