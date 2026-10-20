---
typ: eksperyment
tags: [eksperymenty, topka, host-gap, sprzezone]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/PODSUMOWANIE-NOC-2026-10-20.md:3,9-14,20-24,32-36
status: aktualne
---
# 2026-10-20: podsumowanie nocy – topka-next (coupled + host-gap) i stan prac

**Nowa topka (`9056cea22`, sprzężone próbkowanie + przełączniki host-gap) zbudowana w `~/qwen-opt/topka-next`, md5 OK, ale niezainstalowana; A/B host-gap przy coupled=1 w obu ramionach: czat 113.0 → 114.6 t/s (+1.4%), każdy prompt szybszy (2026-10-20).**

- md5: Qwen plain `c4708318`, MTP `6f14e814`, LFM `894e56e4`, przełączniki on == off (`PODSUMOWANIE:9`).
- A/B T=1, seedy 1–3, ABBA: proza PL 93.4 → 96.1, EN chat 93.3 → 94.7, ms/krok 27.7–28.2 → 27.3–27.7 (`PODSUMOWANIE:10`; plik źródłowy `~/qwen-opt/hostgap/logs-next/SUMMARY-sweep.txt` poza repo).
- A/B `mvs` przerwane: testy na XTX wstrzymane na noc decyzją użytkownika (~03:15) (`PODSUMOWANIE:3,11`).
- PAIR2 bez pomiaru ([[raport-24w-pair2]]); 24q i 24v odrzucone; 4060 Ti zmierzona ([[raport-29-4060ti]]).
- Rano: A/B `mvs`, instalacja topka-next z 3 przełącznikami host-gap, PAIR2, karta 4060 Ti na stronę (`PODSUMOWANIE:32-36`).
- Poprzednio: [[raport-24o-luki-hosta]], [[raport-24p-sprzezone-t1]].

## Powiązane
- [[eksperymenty/_hub|eksperymenty]]
- [[raport-24o-luki-hosta]]
- [[raport-24p-sprzezone-t1]]
- [[raport-24w-pair2]]
- [[REKORDY]]
