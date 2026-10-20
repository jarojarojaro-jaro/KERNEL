---
typ: decyzja
tags: [decyzje, metodyka, gpu, budzet]
aktualizacja: 2026-10-20
zrodlo: ~/AGENTS.md:19; ~/KERNEL/product/research/24q-adaptacyjna-spekulacja.md:92; ~/KERNEL/product/research/24p-sprzezone-t1.md:12; polecenie użytkownika przekazane przez Main 2026-10-20
status: aktualne
---
# 2026-10-20: szybkie iteracje – ≤ 10 min GPU na pomysł, ≤ 20 min pracy na próbę

**Decyzja użytkownika (2026-10-20): test GPU jednego pomysłu maksymalnie 10 minut łącznie (krótka bramka + krótkie A/B, 2–3 seedy), jedna próba optymalizacji maksymalnie 20 minut pracy do pierwszego testu; nie wygrywa wyraźnie → odrzucamy i dalej.**

- Oceniamy po liczbach spekulacji (spec_sweep czat ms/krok i t/s, `mvs`/copy), nie po tg128 bez spekulacji – produkcja zawsze działa ze spekulacją.
- Przykłady zastosowania: 24q skrócił zestaw do 4 zadań po regule „≤ 10 min na pomysł” (`24q:92`); 24p zmierzył tylko T=1 w limicie (`24p:12`); LFM w [[raport-wyniki-xtx-2026-10-19]] mierzony w skróconym zakresie.
- Bez przeciągania i nadmiernej analizy; sufit liczony przed kodem ([[lekcja-wyrazna-wygrana-albo-nic]]).

## Powiązane
- [[decyzje/_hub|decyzje]]
- [[lekcja-wyrazna-wygrana-albo-nic]]
- [[2026-10-19-najlepiej-bez-pytania]]
- [[raport-24q-adaptacyjna-spekulacja]]
- [[pomiar-abba]]
