---
typ: lekcja
tags: [lekcje, chmura, pomiar]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/product/research/16e-kwanty-kld.md:113-125,298
status: aktualne
---
# Host Vast z kartą przyciętą do 120 W

**RTX 3060 na hoście A w E1 miała limit mocy 120 W (domyślnie 170 W): Saluki plain 17.2 vs 23.0 t/s na hoście z raportu 09, MTP ×1.36 różnicy między hostami (2026-10-16).**

Reguła: przed porównaniem z innymi hostami sprawdzić `power.limit` w `hw/gpu.csv` (nvidia-smi); wyniki z przyciętej karty służą tylko do porównań w obrębie hosta, nie do kart produktu.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-slaby-cpu-3090]]
- [[rtx-3060]]
- [[vast-ai]]
