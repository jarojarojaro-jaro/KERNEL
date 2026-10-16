---
typ: lekcja
tags: [lekcje, spekulacja, polski]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/16d-magnitude-vs-nasz.md:12-19,81-88,108-117; ~/KERNEL/product/research/16i-magnitude-co-robia-dobrze.md:295-301
status: aktualne
---
# Głęboki drafter vs MTP: kopia vs polski

**DFlash2 u Magnitude daje 7.3–7.8 tok/krok na kopii i edycji kodu, ale 1.32 na polskiej prozie (27B, 3090), a DFlash na 9B 1.00; nasze MTP n=4 ma sufit 5, za to na pl-proza 1.97 (27B) i 1.71 (9B) (2026-10-16).**

Przyczyna po stronie draftera: trening DFlash na ~800K próbkach Nemotron v2 + CodeAlpaca, bez polskiego (arXiv 2602.06036 §5). Reguła: drafter wybierać per klasa ruchu (kopia/kod vs proza PL), a wyniki zawsze raportować osobno dla obu klas; jeden „sweep” ukrywa obie skrajności (mediana 27B: 65.7 = 65.7 t/s).

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-sufit-bloku]]
- [[lekcja-sondy-en-na-polskim]]
- [[drafter-dflash]]
- [[glowica-mtp]]
