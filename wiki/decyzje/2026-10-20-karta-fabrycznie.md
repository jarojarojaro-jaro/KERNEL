---
typ: decyzja
tags: [decyzje, sprzet, bezpieczenstwo, rx-7900-xtx]
aktualizacja: 2026-10-20
zrodlo: ~/AGENTS.md:18; ~/KERNEL/product/research/22-rsi-f.md:90
status: aktualne
---
# 2026-10-20: karta zostaje na ustawieniach fabrycznych

**Decyzja użytkownika (2026-10-20): żadnego podkręcania pamięci ani rdzenia, żadnych zmian taktowań, napięć ani limitu mocy dla zysku prędkości – przyspieszamy wyłącznie programowo.**

- Dotyczy RX 7900 XTX na serwerze i każdej karty w chmurze.
- Zysk z OC nie liczy się jako wynik projektu; rekordy w [[REKORDY]] są na ustawieniach sterownika.
- Egzekucja w kodzie: bramka H7 fabryki hashuje OD_SCLK/OD_MCLK/OD_VDDGFX_OFFSET i `power1_cap` i odmawia pomiaru po zmianie (`22:90`); krzywa wentylatora jest wyłączona z hasha, bo wentylator ustawiamy dla bezpieczeństwa ([[2026-10-19-wentylator-100-przy-pracy]]).
- Wcześniejszy kontekst: [[2026-10-09-limit-mocy-odlozony]].

## Powiązane
- [[decyzje/_hub|decyzje]]
- [[2026-10-19-bezpieczenstwo-sprzetu]]
- [[2026-10-09-limit-mocy-odlozony]]
- [[2026-10-19-wentylator-100-przy-pracy]]
- [[raport-22-rsi-f]]
- [[REKORDY]]
