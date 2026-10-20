---
typ: research
tags: [research, spekulacja, mtp, wynik-negatywny]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/24b-draft-pelny-slownik.md:6-17
status: aktualne
---
# Raport 24b: pełna głowica draftu dla tokenów spoza słownika 64k – odrzucone

**Przełączanie draftu MTP na pełny słownik (248k) przy tokenach OOV daje ujemny sufit netto we wszystkich grupach (−0.51% przy oknie W=16, −2.40% przy stałej pełnej głowicy), bo OOV to 2–5% tokenów, a pełna głowica kosztuje +5.6% kroku (2026-10-19).**

- OOV następnego tokenu: 2.8% ogółem, PL 3.7%, PL proza 5.0% (`24b:10-13`).
- Nawet okno tylko po OOV (W=4) wychodzi −0.13% (`24b:17`).
- Słownik draftu 64k zostaje. Kontynuacja z klastrowym ogonem: [[raport-21o-gemma]]. Analiza tokenów: [[2026-10-19-tokeny-spoza-slownika-draftu]].

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[2026-10-19-tokeny-spoza-slownika-draftu]]
- [[raport-21o-gemma]]
- [[glowica-mtp]]
