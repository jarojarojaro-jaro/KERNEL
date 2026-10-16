---
typ: lekcja
tags: [lekcje, chmura, cpu]
aktualizacja: 2026-10-16
zrodlo: ~/qwen-opt/cloud/results/3090-20261016/hw/hw.json:23; ~/.omp/agent/sessions/-tmp/2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5320,5379
status: aktualne
---
# Słaby CPU na wynajętym RTX 3090

**Agent wybrał najtańszą ofertę 3090 ($0.201/h) bez kryterium CPU i dostał Intel i7-4790 (4 rdzenie, 2014) z dyskiem 498 MB/s; mocniejsza oferta z 16 rdzeniami EPYC kosztowała ~$0.305/h.**

Wpływ (szacunki z 2026-10-16): kompilacja ok. 20–30 min dłużej (~$0.10), wczytanie modelu ~35 s, Qwen MTP mały wpływ (krok ~28 ms liczy głównie GPU), LFM (~3.4 ms/token) może tracić kilka procent na pracy hosta `[SZACUNEK]`. Decyzja: zostawić maszynę (słaby CPU jest bliższy prawdziwym graczom), zapisać CPU w opisie sprzętu, w `find.sh` dodać minimalne wymagania CPU i dysku. Pomysł: ta sama karta na słabym i mocnym CPU, by zmierzyć wpływ procesora.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-obciazenie-cpu]]
- [[lekcja-5060ti-bezczynna]]
- [[rtx-3090]]
- [[skrypty-chmury]]
