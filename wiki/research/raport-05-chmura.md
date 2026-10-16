---
typ: research
tags: [research, chmura, ceny]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/05-chmura-gpu-do-testow.md:11-58
status: aktualne
---
# Raport 05: chmura GPU do testów

**NVIDIA wynajmujemy tanio (Vast od 0.08 $/h), a konsumenckich Radeonów z rootem w chmurze praktycznie nie ma, więc AMD, Intel kupujemy, Apple wynajmujemy w Scaleway.**

- Mediany Vast on-demand 2026-10-15: RTX 3060 0.08 $, 3090 0.23 $, 4090 0.51 $, 5060 Ti 0.16 $, 5070 0.29 $, 5090 0.73 $ (445 ofert); macierz 8 kart NVIDIA × 80 h/mies. ≈ 190 $/mies.
- AMD: na Vast zero ofert; Salad ma RX 7800 XT–9070 XT za 0.04–0.17 $/h, ale tylko kontener WSL2 bez `/dev/kfd`; Hostkey bare metal z R9700 za €0.471/h; GigaGPU abonament z root.
- Apple: Scaleway Mac mini M4 16 GB €0.22/h, minimum 24 h.
- Na kontenerach brak Nsight Compute, rocprofv3 z licznikami i blokady zegarów; działa Vast VM i bare metal.
- Używane karty (eBay, 90 dni): 3090 €1,224, 7900 XTX €837, 9070 XT €694, 3060 €257.
- Budżety: MVP ≈ 500–600 $/mies. + jednorazowo €1.5–2k, beta ≈ 1.2–1.5k $/mies., launch ≈ 2.5–3.5k $/mies.

## Powiązane
- [[research/_hub|research]]
- [[raport-04-sprzet]]
- [[raport-02-autotuning]]
- [[vast-ai]]
- [[hostkey]]
- [[scaleway]]
