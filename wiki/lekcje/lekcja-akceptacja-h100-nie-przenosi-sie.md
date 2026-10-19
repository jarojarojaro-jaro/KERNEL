---
typ: lekcja
tags: [lekcje, spekulacja, platforma]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21a-dspine.md:22-26,116-143; ~/KERNEL/product/research/16b-lookup-tail.md:59-64
status: aktualne
---
# Akceptacja z H100 nie przenosi się na XTX: koszt szerokości

**U autorów DSpine weryfikacja 16 tokenów kosztuje ≈ 1.04× krok AR (5.46 vs 5.25 ms na H100), a u nas V16/V1 = 1.34 przy 2k i 1.61 przy 64k – drafter b16 musi więc mieć 1.30–1.45× tok/krok MTP4 przy 2k i 1.46–1.60× przy 64k, żeby tylko wyjść na zero (raport 21a, 2026-10-19).**

Reguła: zysk drafterów z prac na H100 przeliczać przez naszą krzywą V(w, kontekst) ([[koszt-szerokosci-weryfikacji]]) i koszt draftu, zanim zacznie się port; „τ wyższe o X%” nie znaczy „t/s wyższe o X%”.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-koszt-szerokosci-backendu]]
- [[lekcja-sufit-bloku]]
- [[drafter-dspine]]
