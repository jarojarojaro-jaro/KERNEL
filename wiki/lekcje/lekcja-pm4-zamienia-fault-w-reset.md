---
typ: lekcja
tags: [lekcje, pm4, awarie]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/17-gpu-page-fault.md:21,113,186-192
status: aktualne
---
# PM4 zamienia fault kernela w reset całego GPU

**Fault w taśmie PM4 kończył się resetem GPU 9 razy na 10 (MES nie umie zdjąć kolejki z IB i zhalt'owanymi falami), a ten sam typ faultu w zwykłej kolejce AQL (`moebench` ×3, 16.10) zabijał tylko proces (raport 17, 2026-10-19).**

Skutek resetu: VRAM lost, pada też serwer użytkownika, zeruje się krzywa wentylatora.

Reguła: eksperymentalne kernele testować z `GGML_HIP_PM4=0` (test-backend-ops i smoke w trybie grafu), PM4 włączać dopiero po przejściu; zgodne z [[2026-10-19-bezpieczenstwo-sprzetu]].

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[pm4-replay]]
- [[lekcja-wentylator-rdna3]]
- [[2026-10-19-page-faulty-gpu-analiza]]
