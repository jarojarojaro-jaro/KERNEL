---
typ: repo
tags: [repo, profilowanie, mcp]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21j-flameox.md:57-129,200-215; https://github.com/morluto/flameox (`c7ea167`, 0.2.9)
status: aktualne
---
# morluto/flameox: orkiestrator profilerów dla agentów (MCP)

**MIT, wersja 0.2.9 (HEAD `c7ea167`, 2026-10-11), 523 commity w 79 dni, 400/400 issues od autora, Devin współautorem 9 commitów, 210 gwiazdek; 26 operacji / 51 narzędzi MCP; na naszym CPU 649 testów OK, 11 pominiętych w 98 s; obsługa rocprofv3 ma jeden test, sprawdzający tylko argumenty (raport 21j, 2026-10-19).**

NVIDIA (nsys, ncu, compute-sanitizer, Triton) obsłużona szerzej, niesprawdzone; Vulkan i HIP brak. Ten sam autor co [[smokinggun]]. Werdykt: nie instalować; ewentualnie tylko CLI `analyze` offline (np. nsys z chmury NVIDIA), nigdy MCP z capture ([[raport-21j-flameox]]).

## Powiązane
- [[repo/_hub|repo]]
- [[rocprof]]
- [[raport-21j-flameox]]
