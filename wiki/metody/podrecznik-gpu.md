---
typ: metoda
tags: [metody, podrecznik, kernele]
aktualizacja: 2026-11-22
zrodlo: ~/KERNEL/product/research/23f-podrecznik-optymalizacji-gpu.md:1-245; ~/KERNEL/product/research/23f-podrecznik-optymalizacji-gpu.md:12-30; ~/KERNEL/product/research/26-kolejka-gpu-wieczor.md:9
status: aktualne
---
# Podręcznik optymalizacji GPU (wejście dla nowego agenta)

**Decode przy batch 1 to strumień bajtów: Qwen3.8-27B plain czyta 16.82 GB/krok przy 75.7% pasma XTX, LFM2.5 1.777 GB/token przy 54%; vendorzy i konkurenci nie mają lepszej pętli GEMV niż nasza wielokolumnowa, najsłabsza gorąca ścieżka to MMVQ n=1, a największą dźwignią na XTX jest bezpieczne PM4 (raport 23f, synteza raportów RE, 2026-10-19).**

Pełny podręcznik (werdykt, ranking 14 zmian, liczby, checklista): [23f-podrecznik-optymalizacji-gpu.md](../../product/research/23f-podrecznik-optymalizacji-gpu.md).

Top rankingu: 1) PM4 z `WA=2` – LFM +13.5%, Qwen MTP +4.9% ([[mec-fw-dispatch-aql-gfx11]]); 2) MMVQ n=1 przez loader `mmvq_ld` – plain +2–5% ([[mmvq-n1-wiersze]]); 3) jedno przejście po KV w weryfikacji – MTP @94–113k +8% ([[fattn-kvq]]); 4) fuzje poza GEMV wg hipfire ≤ +3.5% ([[raport-23e-re-silniki]]); 5) trigger PDL na NVIDIA ([[pdl-mmvq-trigger]]); dalej Q6_K b128, klif VGPR ncols 5 ([[mmvq-multikolumnowe]]), lookup dla LFM, wiele strumieni, hinty NVIDIA, [[bariera-lds-rdna3]], trwały blok MoE (tylko gdy PM4 padnie), mniej bajtów stratnie, narzędzia-bramki ([[co-stats]], [[isa-kstat]], [[umr-offline-pm4]], [[physics-floor-check]]).

Mapa wiedzy: sprzęt [[rdna3-gfx1100]], [[karty-nvidia-parametry]], [[sm-86-89-120]]; roofline [[sufit-pasma-i-mapa-czasu]], [[lekcja-littles-law-gemv]], [[lekcja-sufit-wzorca]]; launch [[pm4-replay]], [[hip-graph-narzut]], [[lekcja-handoff-rdna3]]; numeryka [[zgodnosc-bitowa-md5]], [[bramka-kld-kanarki]]; profilowanie [[rocprof]], [[att-gfx1100]], [[dowod-z-profilu]]; pomiar [[pomiar-abba]], [[wyniki-negatywne]]; bezpieczeństwo [[2026-10-19-bezpieczenstwo-sprzetu]].

## Ze scalonej notatki: Raport 23f: podręcznik optymalizacji GPU A–Z

Decode batch 1 to strumień bajtów (Qwen plain 75.7% pasma XTX, LFM 54%); vendorzy nie mają lepszej pętli GEMV, najsłabsza ścieżka to MMVQ n=1, a największa dźwignia na XTX to bezpieczne PM4 (+13% LFM, +5% Qwen MTP) (2026-10-19).

- Ranking zmian (`23f:25-30`): PM4 `WA=2`, MMVQ n=1 przez loader `mmvq_ld`, jeden przebieg KV, fuzje według listy hipfire.
- Lista „nie robić”: PM4-PDL, prefetch L2/MALL osobnym dispatchem, nontemporal, wave64/VOPD w decode, split-K w MMVQ, WMMA dla n ≤ 8 (`23f:19`).
- Wynik w praktyce (2026-10-19/20): PM4 WA=2 +4.2% Qwen / +11.1% LFM wdrożone; MMVQ n=1 wide, bariera LDS, obłożenie n=5 – odrzucone ([[raport-26-kolejka-gpu]], [[raport-24n-mmvq-n5]]).
- Hub podręcznika: [[podrecznik-gpu]].

## Powiązane
- [[metody/_hub|Metody]]
- [[playbook-optymalizacji]]
- [[REKORDY]]
