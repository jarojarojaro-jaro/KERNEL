---
typ: lekcja
tags: [lekcje, produkt, enigma, modele]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/product/research/67b-wybor-modeli-nvidia.md; 67-nvidia-vast-kampania.md:11-23
status: aktualne
---
# Domyślny pick kalkulatora to nie wybór modelu

**Kampania NVIDIA zaczęła się od modeli, które planer Enigmy sam wybrał (Gemma 4 12B na 10–12 GB, 27B UD-Q3_K_XL przy 135k na 16 GB, 160k na 24 GB); użytkownik słusznie je odrzucił, a przegląd bazy wiedzy dał na 12 GB 27B 2,6× szybszy (3060: Bonsai 2 + MTP 58,3 t/s wobec Saluki 22,2) i 262 144 na 24 GB (2026-11-07).**

Reguła:
- przed testami produktu przejrzeć bazę wiedzy pod kątem już zmierzonych modeli i trików (Saluki/Bonsai/ISTA/LFM, rezerwa MTP z raportu 65, 262k na 3090 z raportu 56) i powiedzieć wprost, co już wiemy;
- kalkulator może dawać pierwsze przybliżenie, ale finalny wybór i kontekst ustala pomiar na karcie;
- znany fakt typu „pełny kontekst się mieści” zgłaszać od razu, nie dopiero po pytaniu.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[jak-przyspieszylismy-nvidia]]
- [[najpierw-baza-kb]]
- [[final-modele-per-vram]]
