---
typ: lekcja
tags: [lekcje, pm4, rdna3, synchronizacja]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/product/research/16a-pm4-pdl.md:55-65,145-149
status: aktualne
---
# RDNA3: hand-off przez pamięć kosztuje prawie tyle co granica PM4

**Każdy protokół flag i ticketów między zależnymi kernelami na XTX kosztował prawie tyle, co pakiety granicy `CS_PARTIAL_FLUSH` + `ACQUIRE_MEM` (0.46–0.86 µs): przy 1024 blokach zostaje 6% zysku z usunięcia granicy, przy 1536–3072 blokach 29–44%, i to tylko z prefetchem wag do VGPR przed czekaniem (2026-10-18).**

- Jedna flaga pollowana przez cały grid jest wolniejsza od granicy; potrzeba ≥ 16 kopii po linii 128 B albo relay (jak `pre_poll` w MonoKernel).
- Atomik na blok producenta: +0.57 µs (1024 bloki) do +7.6 µs (3072, jeden adres).
- `RELEASE_MEM` z CP jako flaga nie zadziałał (czekanie wygasa) `[NIEZWERYFIKOWANE]`.

Reguła: zysk z „mniej granic” na RDNA3 bierze się tylko tam, gdzie hand-off nie wymaga atomika na blok – kernel dataflow (trwały blok MoE) albo fuzja producenta z konsumentem (gate+up → down).

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-megakernel-prefetch-nie-granica]]
- [[pm4-replay]]
- [[2026-10-18-pm4-pdl-x1]]
