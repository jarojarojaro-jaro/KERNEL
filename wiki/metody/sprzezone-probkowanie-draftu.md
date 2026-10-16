---
typ: metoda
tags: [metody, spekulacja, sampler]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/16i-magnitude-co-robia-dobrze.md:28-32,81-88,240,302-307
status: aktualne
---
# Sprzężone próbkowanie draftu (coupled sampling)

**Magnitude losuje każdą propozycję draftu z tym samym ziarnem i pozycją co próbka celu (Gumbel-max na Philox4x32-10 kluczowany pozycją i tokenem), więc przy równych rozkładach draft i cel wybierają ten sam token także przy T=1; metoda bezstratna i przenośna 1:1.**

Dla nas: luka T=0 vs T=1 to dla MTP 2–6% (86.3 vs 81.1), dla DFlash 20% (90.6 vs 71.9 t/s). Koszt wdrożenia 2–3 osobodni: sampler celu musi stać się Gumbel-max (seed, pozycja, token), głowica MTP stosuje ten sam łańcuch (temp/top-k/top-p/min-p); zmienia teksty względem obecnych md5 przy tym samym seedzie. W trybie bitexact daje gwarancję: tekst ze spekulacją = bez niej przy każdej temperaturze, jeśli logity są bitowe.

Eksperyment E-X4 (spec_sweep T=1, zestaw odłożony), kill < +2%. Realizacja: agent CoupledSampling, raport 16k (2026-10-16, w toku).

## Powiązane
- [[metody/_hub|Metody]]
- [[kontroler-szerokosci-draftu]]
- [[2026-10-15-sampler]]
- [[batch-invariant]]
