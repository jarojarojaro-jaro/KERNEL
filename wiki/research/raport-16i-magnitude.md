---
typ: research
tags: [research, konkurencja, spekulacja]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/product/research/16i-magnitude-co-robia-dobrze.md:1-349; ~/KERNEL/product/research/16j-magnitude-vulkan-xtx.md:110
status: aktualne
---
# Raport 16i: Magnitude – co robią dobrze i co przejąć

**Analiza kodu Magnitude 0.2.9 (`954d677d`) i logów z 16d (tylko CPU): ich przewaga to sufit bloku DFlash2 i kontroler szerokości, nie kernele; najtańsza droga do ich wyniku to ogon z lookupu do 8 wierszy przy MTP4 (projekcja XTX code-edit ×1.4).**

Ranking technik (§4): 1) MTP4 + ogon lookup do 8 wierszy (+35…45% code-edit, 0 na pisaniu); 2) [[kontroler-szerokosci-draftu]] (+15…45% ponad #1); 3) [[sprzezone-probkowanie-draftu]]; 4) DFlash2 jako drugi drafter do kodu/EN; 5) weryfikacja 1..16 kolumn bitowo niezależna od M (swap-AB MMA); 6) jedno czytanie KV dla ≤ 16 wierszy; 7) PDL w grafach; 8) certyfikowany readout. Odrzucone: ich autotune, KV K8V4, taśma GDN, DSpark z przycinaniem.

Projekcja XTX d=2048 (§3): MTP4 27.74 ms, 177 t/s; + ogon do 8 wierszy 30.22 ms, 256 t/s (1.45×); 16 wierszy 34.87 ms, 426 t/s (2.41×) przy p = 0.99. Przy 64k: 8 wierszy ~1.3×.

Plan GPU (§8): E-X0 krzywa V(w, d) na XTX; E-X1 akceptacja ogona per głębokość (shadow); E-X2 ogon W8/W16 (kill < +20% mvs); E-X3 kontroler (`LLAMA_SPEC_LOOKUP=3`); E-X4 sprzężone próbkowanie (kill < +2%); E-X5 Magnitude Vulkan na XTX; E-C1 krzywa szerokości na 3090; E-C2 head-to-head na 3090 (cel code-edit ≥ 150 t/s). Stan: [[2026-10-16-badamy-magnitude]].

E-X5 zamknięte 2026-10-18: [[raport-16j-magnitude-vulkan-xtx]] – Magnitude na XTX ~2× wolniejszy.

## Powiązane
- [[research/_hub|research]]
- [[raport-16d-magnitude-vs-nasz]]
- [[raport-15b-spekulacja-frontier]]
- [[2026-10-16-magnitude-rozklad-wygranej]]
