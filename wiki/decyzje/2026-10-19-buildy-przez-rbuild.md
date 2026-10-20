---
typ: decyzja
tags: [decyzje, buildy, cpu, rbuild]
aktualizacja: 2026-10-20
zrodlo: ~/AGENTS.md:11,14; ~/KERNEL/product/research/25-buildfarm.md:7-10,24,55; ~/KERNEL/product/research/24a-bariera-lds.md:32
status: aktualne
---
# 2026-10-19: kompilacje tylko przez `rbuild` (zdalny serwer), bez cichego lokalnego fallbacku

**Decyzja (2026-10-19): każdy build forka idzie przez `~/qwen-opt/tools/rbuild <worktree> [cele]` na zdalnym serwerze 24 vCPU; lokalne buildy `-j2` trzymały quiet.lock ~50 min i GPU stało przy 11 zadaniach w kolejce.**

- Wynik zdalny jest bitowo zgodny z lokalnym ([[raport-25-buildfarm]]).
- Lokalnie (`--local`, `cpuheavy --quiet -j2`) tylko wtedy, gdy rbuild zgłosi, że serwer nie działa – i to jawnie, z informacją w raporcie (np. 24a: „lokalnie `-j2`, rbuild: serwer nieosiągalny”, `24a:32`). Cichy lokalny fallback nie jest dozwolony.
- Nigdy nie kompilujemy z blokadą GPU; jedno zadanie GPU ≤ 15 min (`~/AGENTS.md:14`).
- Build w trakcie pomiaru psuje wynik: [[lekcja-obciazenie-cpu]].

## Powiązane
- [[decyzje/_hub|decyzje]]
- [[raport-25-buildfarm]]
- [[2026-10-19-szanujemy-sprzet-serwera]]
- [[lekcja-obciazenie-cpu]]
