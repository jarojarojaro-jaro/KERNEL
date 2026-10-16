---
typ: firma
tags: [ludzie-firmy, konkurencja]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/16d-magnitude-vs-nasz.md:5-28,119-138; ~/KERNEL/product/research/16i-magnitude-co-robia-dobrze.md:11-40,308-321
status: aktualne
---
# Magnitude (magnitudedev): najbliższy konkurent

**Zespół z własnym silnikiem w Ruście; wygrywa z nami tam, gdzie kopiuje (code-edit 1.35–1.56×) dzięki drafterowi DFlash2 i adaptacyjnej szerokości draftu, a przegrywa na polskim, bez draftera, w prefillu i na 16 GB (pomiary 2026-10-16).**

Mocne strony: code-edit 156.1 vs 105.2 t/s (3090 27B), kod przy T=1 +21…+38%, kontroler szerokości bez strojenia przez użytkownika, sprzężone próbkowanie, Mac/Metal i Vulkan, desktop i integracje agentów.

Słabe: polski (9B sweep 68.2 vs 121.0 t/s; drafter trenowany bez PL), bez draftera na poziomie upstreamu (LFM 209.0 vs 291.6), prefill 64k 86.4 vs 72.4 s, brak IQ2_S/Q4_1 (żaden 27B na 16 GB), LFM 64k OOM na 16 GB, brak HIP (AMD tylko Vulkan – na XTX niezmierzone), autotune w release 67/67 domyślnych.

Decyzja użytkownika: badać ich podejście i przejąć, co się da ([[2026-10-16-badamy-magnitude]]).

## Powiązane
- [[ludzie-firmy/_hub|Ludzie i firmy]]
- [[magnitude]]
- [[turbollm]]
- [[produkt-ryzyka]]
- [[2026-10-16-magnitude-vs-fork]]
