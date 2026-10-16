---
typ: repo
tags: [repo, galezie, mmq, gdn]
aktualizacja: 2026-10-16
zrodlo: ~/wt/qwen5/QWEN5-ROUND5.md:1-25
status: aktualne
---
# Gałąź opt-qwen5 (runda 5 Qwena)

**Gałąź `opt-qwen5` @ `2aa6999ed` (2026-10-15) z `c36fd2c87`: próby GDN fast i podwójnego bufora y w MMQ, obie wycofane, plus ablacja P0 prefillu MMQ.**

Pomiar 2026-10-15: GDN fast zmienił md5 (plain `0b7b073b` zamiast `c4708318`) – wycofany (`5b1fdbc2f`). Podwójny bufor y (YDB=2): pp4096 1066/1065 vs 1097/1091 bez niego, −2.6%, bitowo – wycofany. Ablacja P0 (pp4096): normalnie 1094/1085; bez ładowań 1219 (+11.9%); bez barier 1173 (+7.6%); bez vec_dot 3254 (3.0x). Wniosek: MMQ jest ograniczone matematyką/epilogiem (~0.61 ms z 0.918 ms na token), nie ładowaniem – to skierowało rundę 6 na epilog. Około 00:45 użytkownik zakazał pracy na GPU, ~02:00 znów pozwolił.

## Powiązane
- [[repo/_hub|repo]]
- [[galezie-rund]]
- [[opt-mmq6]]
- [[qwen-runda-5]]
- [[ablacja]]
