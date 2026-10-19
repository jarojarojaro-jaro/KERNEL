---
typ: decyzja
tags: [decyzje, cpu, proces]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/AGENTS.md:7
status: aktualne
---
# 2026-10-19: szanujemy sprzęt serwera (CPU i narzędzia w tle)

**Twarda zasada z `AGENTS.md` (2026-10-19): ciężkie skrypty CPU `nice -n 19` i ≤ 4 wątki, kompilacje `nice -n 10 -j6`, bez pętli z drogimi komendami (pełny `journalctl`, `find ~`), headless Chrome zamykany od razu po testach, narzędzia działające w tle mają kosztować ~0 CPU; dla GPU obowiązuje [[2026-10-19-bezpieczenstwo-sprzetu]].**

Tło: Chrome zostawiony z animowaną stroną palił ~90% rdzenia przez 3 h ([[lekcja-chrome-zostawiony]]); obciążenie CPU zaburza pomiary GPU ([[lekcja-obciazenie-cpu]]).

## Powiązane
- [[decyzje/_hub|Decyzje]]
- [[2026-10-19-bezpieczenstwo-sprzetu]]
- [[lekcja-limit-cpu-kontenera]]
