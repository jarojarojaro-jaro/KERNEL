---
typ: lekcja
tags: [lekcje, chmura, pomiar]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/product/research/16e-kwanty-kld.md:113-125,298
status: aktualne
---
# Host Vast z kartą przyciętą do 120 W

**RTX 3060 na hoście A w E1 miała limit mocy 120 W (domyślnie 170 W): Saluki plain 17.2 vs 23.0 t/s na hoście z raportu 09, MTP ×1.36 różnicy między hostami (2026-10-16).**

Reguła: przed porównaniem z innymi hostami sprawdzić `power.limit` w `hw/gpu.csv` (nvidia-smi); wyniki z przyciętej karty służą tylko do porównań w obrębie hosta, nie do kart produktu.

Powtórka 2026-11-07 (kampania 67): RTX 5090 dała 86,9 t/s na hoście z limitem 450 W i 102,2 t/s na hoście 575 W; dopiero A-B-B-A na jednym hoście pokazała, że różnica silników to ~9% (pin b11856 99,8 vs b12110 91,7). 4090 w 67c miała 250 W (domyślnie 450 W), więc jej 76,4 / 101,3 t/s jest zaniżone. Od tej kampanii limit mocy każdego hosta jest zapisywany przy wyniku.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-slaby-cpu-3090]]
- [[rtx-3060]]
- [[vast-ai]]
- [[jak-przyspieszylismy-nvidia]]
