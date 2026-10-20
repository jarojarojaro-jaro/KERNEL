---
typ: research
tags: [research, podrecznik, optymalizacja]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/23f-podrecznik-optymalizacji-gpu.md:12-30; ~/KERNEL/product/research/26-kolejka-gpu-wieczor.md:9
status: aktualne
---
# Raport 23f: podręcznik optymalizacji GPU A–Z

**Decode batch 1 to strumień bajtów (Qwen plain 75.7% pasma XTX, LFM 54%); vendorzy nie mają lepszej pętli GEMV, najsłabsza ścieżka to MMVQ n=1, a największa dźwignia na XTX to bezpieczne PM4 (+13% LFM, +5% Qwen MTP) (2026-10-19).**

- Ranking zmian (`23f:25-30`): PM4 `WA=2`, MMVQ n=1 przez loader `mmvq_ld`, jeden przebieg KV, fuzje według listy hipfire.
- Lista „nie robić”: PM4-PDL, prefetch L2/MALL osobnym dispatchem, nontemporal, wave64/VOPD w decode, split-K w MMVQ, WMMA dla n ≤ 8 (`23f:19`).
- Wynik w praktyce (2026-10-19/20): PM4 WA=2 +4.2% Qwen / +11.1% LFM wdrożone; MMVQ n=1 wide, bariera LDS, obłożenie n=5 – odrzucone ([[raport-26-kolejka-gpu]], [[raport-24n-mmvq-n5]]).
- Hub podręcznika: [[podrecznik-gpu]].

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[podrecznik-gpu]]
- [[raport-26-kolejka-gpu]]
- [[raport-24n-mmvq-n5]]
- [[wyniki-negatywne]]
