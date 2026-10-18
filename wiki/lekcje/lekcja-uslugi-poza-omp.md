---
typ: lekcja
tags: [lekcje, omp, proces]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/STAN-PRAC.md:1-10; `~/.omp/logs/omp.2026-10-16.1235.log`; komunikat Main do WikiIngest 2026-10-16
status: aktualne
---
# Awaria omp zabija usługi uruchomione w omp

**2026-10-16 o 17:48 UTC omp padł (`panic: Segmentation fault at address 0x0`, błąd Bun 1.4.3), wszyscy agenci zostali zaparkowani, a usługi uruchomione wewnątrz sesji omp – m.in. serwer podglądu strony na porcie 18433 – zginęły razem z nim.**

Reguła: długo żyjące usługi (podgląd strony, serwery llama, strażniki) uruchamiać odłączone od omp (`setsid`/`nohup`, tryb `detached` albo jednostka systemd użytkownika), z logiem na dysku. Po awarii: punkt kontrolny w `STAN-PRAC.md` (stan GPU, chmury, usług) i wznawianie agentów wiadomością.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-zombie-serwery]]
- [[lekcja-nadpisanie-dzialajacego-skryptu]]
- [[app-landing]]
