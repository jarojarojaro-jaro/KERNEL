---
typ: metoda
tags: [metody, spekulacja, sampler]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/16i-magnitude-co-robia-dobrze.md:28-32,81-88,240,302-307; ~/KERNEL/product/research/16k-sprzezone-probkowanie.md:35-75
status: aktualne
---
# Sprzężone próbkowanie draftu (coupled sampling)

**Magnitude losuje każdą propozycję draftu z tym samym ziarnem i pozycją co próbka celu (Gumbel-max na Philox4x32-10 kluczowany pozycją i tokenem), więc przy równych rozkładach draft i cel wybierają ten sam token także przy T=1; metoda bezstratna i przenośna 1:1.**

Dla nas: luka T=0 vs T=1 to dla MTP 2–6% (86.3 vs 81.1), dla DFlash 20% (90.6 vs 71.9 t/s). Koszt wdrożenia 2–3 osobodni: sampler celu musi stać się Gumbel-max (seed, pozycja, token), głowica MTP stosuje ten sam łańcuch (temp/top-k/top-p/min-p); zmienia teksty względem obecnych md5 przy tym samym seedzie. W trybie bitexact daje gwarancję: tekst ze spekulacją = bez niej przy każdej temperaturze, jeśli logity są bitowe.

Eksperyment E-X4 (spec_sweep T=1, zestaw odłożony), kill < +2%. Realizacja: agent CoupledSampling, [[raport-16k-sprzezone-probkowanie]].

Implementacja i wynik (16k, 2026-10-18): fork za `LLAMA_SPEC_COUPLED` (0 wył., 1 cel + draft sprzężone, 2 kontrola z draftem greedy), sampler celu zastępuje `dist` przy T > 0, klucz = indeks tokenu w sekwencji, resample gramatyki w osobnej domenie szumu, szybkie ścieżki samplera zostają dokładne; weryfikacja nadal dopasowaniem prefiksu. Zysk MTP nierozstrzygnięty, nie domyślnie ([[2026-10-18-sprzezone-probkowanie-mtp]]).

## Powiązane
- [[metody/_hub|Metody]]
- [[kontroler-szerokosci-draftu]]
- [[2026-10-15-sampler]]
- [[batch-invariant]]
