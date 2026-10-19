---
typ: decyzja
tags: [decyzje, konkurencja, spekulacja]
aktualizacja: 2026-10-19
zrodlo: ~/.omp/agent/sessions/-tmp/2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:6291; ~/KERNEL/product/research/16i-magnitude-co-robia-dobrze.md:36-40,323-336; ~/KERNEL/product/research/16j-magnitude-vulkan-xtx.md:7-13; ~/KERNEL/product/research/16k-sprzezone-probkowanie.md:152-170; ~/KERNEL/product/research/16b-lookup-tail.md:10-23
status: aktualne
---
# 2026-10-16: badamy podejście Magnitude i przejmujemy, co działa

**Użytkownik (2026-10-16, 17:22 UTC): „oni coś zrobili dobrze, trzeba to zbadać i zobaczyć, czy możemy wykorzystać” – po wynikach 16d, gdzie Magnitude wygrał code-edit 156.1 vs 105.2 t/s.**

Pierwsza analiza: [[raport-16i-magnitude]] (sufit bloku + kontroler, nie kernele). Uruchomione wątki (2026-10-16):
- **XtxLookupTail** – ogon z lookupu doklejany do MTP4 do 8/16 wierszy na XTX (E-X1, E-X2): mvs ×2.41 przy W16 ([[raport-16b-lookup-tail]]);
- **CoupledSampling** – sprzężone próbkowanie draftu, raport 16k (E-X4): bezstratne, zysk MTP nierozstrzygnięty, nie domyślnie ([[raport-16k-sprzezone-probkowanie]]);
- **MagnitudeVulkanXtx** – Magnitude przez Vulkan na 7900 XTX, raport 16j (E-X5) – zrobione 2026-10-18: na XTX Magnitude ~2× wolniejszy ([[raport-16j-magnitude-vulkan-xtx]]).

Kolejność wg 16i: ogon → kontroler szerokości (E-X3) → sprzężone próbkowanie → DFlash2 jako drugi drafter (opcjonalnie). Warunek: polskie pisanie bez regresji (spec_sweep ≥ −0.5%), pomiary GPU za zgodą.

## Powiązane
- [[decyzje/_hub|Decyzje]]
- [[firma-magnitude]]
- [[kontroler-szerokosci-draftu]]
- [[sprzezone-probkowanie-draftu]]
