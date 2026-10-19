---
typ: metoda
tags: [metody, prawo, reverse-engineering]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21l-reverse-engineering-gpu.md:65-74
status: aktualne
---
# Reverse engineering bibliotek producentów: tylko metadane i black-box

**Zasada z raportu 21l (rekomendacja, nie porada prawna, 2026-10-19): kody vendorów badamy tylko przez metadane i pomiary black-box; deasemblujemy wyłącznie nasze własne binarki i otwarte biblioteki.**

- AMD: rocBLAS/hipBLASLt na MIT z otwartymi YAML – to nie RE; firmware MES/ME/PFP z linux-firmware zakazuje RE w licencji – dekodujemy tylko własne pakiety PM4.
- NVIDIA: EULA CUDA §1.2 zabrania RE SDK (w tym cuBLAS) – z cuBLAS tylko `-res-usage` i pomiary; nasze cubiny deasemblować wolno `[INFERENCE]`.
- UE/PL: dyr. 2009/24/WE art. 5(3) (obserwacja i testy), art. 6 (dekompilacja tylko dla interoperacyjności); uPrAut art. 75–76; TSUE C-406/10 i C-13/20 – deasemblacja „żeby nauczyć się trików” to nie interoperacyjność, więc jej unikamy.

## Powiązane
- [[metody/_hub|Metody]]
- [[produkt-prawo]]
- [[raport-21l-re-gpu]]
