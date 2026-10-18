---
typ: firma
tags: [ludzie-firmy, konkurencja]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/product/research/16d-magnitude-vs-nasz.md:5-28,119-138; ~/KERNEL/product/research/16i-magnitude-co-robia-dobrze.md:11-40,308-321; ~/KERNEL/product/research/16j-magnitude-vulkan-xtx.md:10-13,85-91
status: aktualne
---
# Magnitude (magnitudedev): najbliższy konkurent

**Zespół z własnym silnikiem w Ruście; wygrywa z nami tam, gdzie kopiuje (code-edit 1.35–1.56×) dzięki drafterowi DFlash2 i adaptacyjnej szerokości draftu, a przegrywa na polskim, bez draftera, w prefillu i na 16 GB (pomiary 2026-10-16).**

Mocne strony: code-edit 156.1 vs 105.2 t/s (3090 27B), kod przy T=1 +21…+38%, kontroler szerokości bez strojenia przez użytkownika, sprzężone próbkowanie, Mac/Metal i Vulkan, desktop i integracje agentów.

Słabe: polski (9B sweep 68.2 vs 121.0 t/s; drafter trenowany bez PL), bez draftera na poziomie upstreamu (LFM 209.0 vs 291.6), prefill 64k 86.4 vs 72.4 s, brak IQ2_S/Q4_1 (żaden 27B na 16 GB), LFM 64k OOM na 16 GB, brak HIP (AMD tylko Vulkan), autotune w release 67/67 domyślnych.

Decyzja użytkownika: badać ich podejście i przejąć, co się da ([[2026-10-16-badamy-magnitude]]).

Na AMD (16j, 2026-10-18): przez Vulkan na 7900 XTX ~2× wolniejszy od nas (Qwen sweep 50.1 vs 100.0, code-edit 87.7 vs 170.0 t/s; LFM ×1.42–×2.24), bo każdy szerszy krok jest drogi (blok 8 = ×3.0 kroku 1-wierszowego). Konkurent w instalacji, nie w wydajności ([[2026-10-18-magnitude-vulkan-xtx]]).

## Powiązane
- [[ludzie-firmy/_hub|Ludzie i firmy]]
- [[magnitude]]
- [[turbollm]]
- [[produkt-ryzyka]]
- [[2026-10-16-magnitude-vs-fork]]
