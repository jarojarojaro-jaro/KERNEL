---
typ: lekcja
tags: [lekcje, chmura, koszty]
aktualizacja: 2026-10-20
zrodlo: vastai show invoices-v1 --charges -s 2026-10-20 (pozycje bwd/gpu/disk instancji opt-*); vastai show instance 56904167 (inet_down_cost 0.039 $/GB)
status: aktualne
---
# Transfer na Vast kosztował więcej niż karty

**2026-10-20 kampania opt-* (6 kart, plan $4.54 za 5 h) zjadła $6.90 w ~2.5 h: GPU $2.67, dysk ~$0.4, pobieranie $3.80 (55%). Kredyt skończył się w połowie testów.**

Przyczyna: wyszukiwanie ofert sortowało tylko po `dph_total`, a `dph_total` nie zawiera transferu („plus bandwidth”). Host 5060 Ti liczył 0.039 $/GB pobrania (≈ $39/TB): ~44 GB modeli = $1.72, czterokrotnie więcej niż sama karta. Na 3060 ($0.055/h) transfer $0.86 = 5× koszt GPU. Do tego cztery nieudane boxy 3090 (limit mocy 200 W, HF 26 KB/s) i kilka kwantów pobieranych na każdą maszynę.

Reguły:
- Filtr ofert: `inet_down_cost` ≤ 0.002 $/GB (najlepiej 0) albo licz `dph_total × h + GB × inet_down_cost` i sortuj po sumie.
- Jeden kwant na kartę, wybrany lokalnie przed wynajmem; pobierać raz.
- Przed pomiarami: limit mocy (`nvidia-smi -q -d POWER`) i szybkość pobierania (test 1 GB); zły host → zniszcz od razu.
- Budżet podawany użytkownikowi = GPU + dysk + transfer, z zapasem 30%.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-vast-cli-klucz]]
- [[lekcja-vast-authorized-keys]]
- [[2026-10-16-nie-placimy-za-przestoj]]
