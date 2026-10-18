---
typ: lekcja
tags: [lekcje, kernele, pasmo]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/product/research/16g-lfm-moe-pasmo.md:43-65
status: aktualne
---
# Najpierw sufit wzorca dostępu, potem optymalizacja kernela

**Gate+up ekspertów LFM czytał 17.30 MB w 23.6–24.2 µs (673 GB/s), a sam odczyt tych samych bajtów tym samym wzorcem i siatką (2 wiersze gate + 2 up po 1408 B na falę, 3072 fale) bez żadnej arytmetyki trwał 22.4–24.4 µs – arytmetyka q8_1 ani gather nie były problemem (2026-10-18).**

Ten sam odczyt przy 4 wierszach na blok: 19.68 µs stabilnie (879 GB/s), więc dźwignią jest wzorzec (liczba krótkich strumieni), nie obliczenia. Down Q5_K: kernel 11.64 vs idealny odczyt 10.4–10.6 µs (~90% sufitu).

Reguła: przed przepisywaniem kernela pasmowego zmierzyć „czysty odczyt” z tym samym wzorcem i siatką; jeśli kernel jest blisko, zmieniać układ danych albo wzorzec, nie arytmetykę.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-bledny-roofline]]
- [[sufit-pasma-i-mapa-czasu]]
- [[mmvq-moe-gate-up-blok]]
