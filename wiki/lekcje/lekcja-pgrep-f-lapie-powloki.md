---
typ: lekcja
tags: [lekcje, proces, gpu]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/17-gpu-page-fault.md:57-58,156; komunikat Main do WikiIngest 2026-10-19
status: aktualne
---
# `pgrep -f` łapie powłoki innych agentów

**`pgrep -f "llama-server.*--port 8080"` trafiał w powłoki innych agentów, które miały ten wzorzec w linii poleceń; fałszywe „serwer użytkownika na 8080” pomijało ramiona pomiarów i zmyliło diagnozę E-X4 (18.10 19:47–20:14), choć od 15.10 nie było żadnego logu serwera produkcyjnego (raport 17).**

Reguła: proces sprawdzać `pgrep -x llama-server` (+ `/proc/<pid>/cmdline`), a zajętość portu `ss -ltn 'sport = :8080'`; nigdy samym `pgrep -f` z wzorcem, który może wystąpić w czyjejś komendzie.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-pkill-wlasna-powloka]]
- [[lekcja-zombie-serwery]]
- [[serializacja-gpu]]
