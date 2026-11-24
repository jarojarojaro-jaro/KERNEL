---
typ: ekosystem
tags: [ekosystem, dsl, pdl]
aktualizacja: 2026-11-24
zrodlo: ~/KERNEL/qwen-opt/research/repos/13-cutile-python.md:1-21; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:23
status: aktualne
---
# NVIDIA/cutile-python (cuTile)

**Kafelkowy DSL NVIDIA kompilowany do Tile IR (commit `d9d8520`, 2026-10-13); bierzemy odpowiednik PDL na AMD; werdykt: niska–średnia.**

PDL jako operacja języka, dzielenie pętli K/V wg maski (do +32% FA prefill, pomiar NVIDIA), FMHA decode sm100a bez osobnego kernela combine, model checker harmonogramów bez GPU. Dla nas: wcześniejszy start następnego kernela przez `hipExtAnyOrderLaunch` + flagę (L5, szacunek −0.2…−0.45 ms/token).

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)
- Poza PDL repo uczy, jak sprawdzać protokoły synchronizacji bez karty: `experimental/task_scheduling/src/task_scheduling/exhaustive_checker.py` przechodzi wszystkie przeploty acquire/wait/commit/release i szuka zakleszczeń, wyścigów i aliasów buforów na CPU (`qwen-opt/research/repos/13-cutile-python.md:19,54-55`).
- Nasz odpowiednik: błędy protokołów (tickety „ostatni blok”, PM4 replay) wychodzą dopiero na karcie, jako page fault albo reset; `run-jobs.sh` umie tylko zatrzymać kolejkę po fakcie (`qwen-opt/queue/run-jobs.sh:2-4,10-12`), [[gpu-guard]] zabija procesy po fakcie.
- Co bierzemy: zasadę „protokół najpierw na CPU, potem na kartę” (ta sama, która odsiała Enigma Turbo w 2 min na CPU, [[enigma-turbo-gemini-2026-11-20]]); mały checker przeplotów dla ticketów i przyszłych kerneli trwałych przed pierwszym uruchomieniem na XTX. Do dziś nie zrobione.
- Werdykt dla prędkości bez zmian (niska–średnia); dla bezpieczeństwa labu: średnia.

## Powiązane
- [[tilelang]]
- [[tilegym]]
- [[lekcja-pdl-sm120]]
- [[repos-30-przeglad]]
