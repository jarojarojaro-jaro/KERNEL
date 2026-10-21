---
typ: lekcja
tags: [lekcje, build, kolejka]
aktualizacja: 2026-10-21
zrodlo: git 1a5bfdc
status: aktualne
---
# rbuild pod flock = deadlock

**2026-10-20 `rbuild` wywołany w procesie, którego przodek trzymał quiet.lock przez `flock`, czekał na tę samą blokadę (przez cpuheavy) i zatrzymał kolejkę GPU; od 1a5bfdc rbuild odmawia startu w takim przypadku.**



## Powiązane
- [[lekcje/_hub|lekcje]]
- [[2026-10-19-buildy-przez-rbuild]]
- [[lekcja-kolejka-fifo-bilety]]
