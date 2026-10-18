---
typ: lekcja
tags: [lekcje, chmura, obraz]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/product/research/16e-kwanty-kld.md:304
status: aktualne
---
# `bootstrap.sh` bez `python3-numpy` psuje repack Bonsai

**`pq2_to_q2.py` (repack Bonsai PQ2_0 → Q2_0) wymaga `python3-numpy`, którego nie ma ani w obrazie CUDA, ani w `bootstrap.sh`; repack padł dwa razy (3060 A w rundzie 1, 3060 B w rundzie 2), ~2 min GPU straty (2026-10-16/18).**

Reguła: każdy skrypt uruchamiany na instancji ma zależności w bootstrapie, sprawdzone lokalnie w czystym obrazie przed wynajmem.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-brak-column-w-obrazie]]
- [[bonsai]]
- [[skrypty-chmury]]
