---
typ: decyzja
tags: [decyzje, cpu, proces]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/AGENTS.md:7; komunikat Main do WikiIngest 2026-10-19 (CPU 73 °C)
status: aktualne
---
# 2026-10-19: szanujemy sprzęt serwera (CPU i narzędzia w tle)

**Twarda zasada z `AGENTS.md` (2026-10-19): ciężkie skrypty CPU `nice -n 19` i ≤ 4 wątki, kompilacje `nice -n 10 -j6`, bez pętli z drogimi komendami (pełny `journalctl`, `find ~`), headless Chrome zamykany od razu po testach, narzędzia działające w tle mają kosztować ~0 CPU; dla GPU obowiązuje [[2026-10-19-bezpieczenstwo-sprzetu]].**

Tło: Chrome zostawiony z animowaną stroną palił ~90% rdzenia przez 3 h ([[lekcja-chrome-zostawiony]]); obciążenie CPU zaburza pomiary GPU ([[lekcja-obciazenie-cpu]]).

**Zaostrzenie (użytkownik, 2026-10-19, CPU 73 °C):** każda ciężka komenda CPU (kompilacje, także nvcc/cicc/hipcc, buildy cmake, deasemblacja dużych bibliotek, `strings`/grep po dużych binarkach, kompilatory shaderów, analizy w Pythonie, embeddingi) tylko jako `flock /tmp/cpuheavy.lock nice -n 19 taskset -c 0-3 <cmd>` – jedno ciężkie zadanie naraz u wszystkich agentów, maks. 4 rdzenie, buildy `-j4`. Lekkie odczyty (cat, małe grepy, `git log`) bez blokady. Pliku blokady nigdy nie usuwać ani nie odtwarzać ([[lekcja-nie-odtwarzac-lockow]]).

**Kolejne zaostrzenie (użytkownik, 2026-10-19, CPU 67–73 °C, cieplej niż GPU):** nowe ciężkie komendy `flock /tmp/cpuheavy.lock nice -n 19 taskset -c 0-1 <cmd>`, buildy `-j2`, buildy CUDA tylko dla potrzebnej architektury (`CMAKE_CUDA_ARCHITECTURES=86` albo `120`, nie obie).

## Powiązane
- [[decyzje/_hub|Decyzje]]
- [[2026-10-19-bezpieczenstwo-sprzetu]]
- [[lekcja-limit-cpu-kontenera]]
