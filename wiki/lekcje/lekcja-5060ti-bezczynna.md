---
typ: lekcja
tags: [lekcje, chmura, koszt]
aktualizacja: 2026-10-16
zrodlo: ~/.omp/agent/sessions/-tmp/2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5372,5407
status: aktualne
---
# Wynajęta 5060 Ti stała bezczynnie

**Na 5060 Ti kompilacja skończyła się szybko, ale pomiary nie ruszyły, bo agent dopisywał skrypty; płatna karta stała z 0% GPU (2026-10-16 ok. 01:24 UTC).**

Reakcja: polecenie dla agenta, żeby natychmiast puścił pomiary, a resztę skryptów dopisywał, gdy GPU pracuje. Reguły od tego momentu: przedłużać instancję tylko, gdy GPU robi użyteczną pracę (bez płatnej bezczynności); przed wynajmem (np. RunPod do treningu MTP) przygotować i przetestować cały pipeline na CPU.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-brak-column-w-obrazie]]
- [[lekcja-slaby-cpu-3090]]
- [[rtx-5060-ti]]
- [[2026-10-16-budzety-chmury]]
