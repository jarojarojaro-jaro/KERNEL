---
typ: repo
tags: [repo, agenci, antyoszustwo]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15f-agentowa-nauka.md:28-34,82,124-137
status: aktualne
---
# KernelGuard (GPU MODE)

**Zestaw 62 deterministycznych detektorów oszustw w zgłoszeniach kerneli, każdy z fixture’em historycznego hacka, plus „physics floor” z roofline’u; odsetek oszukanych zgłoszeń spadł z 3.45% do 0.37% w 32 dni.**

Repo `gpu-mode/kernelguard` @ `6797d26`, ICML 2026 AIWILD.
- Liczby autorów: 3.45% (4889/141800) → 0.37% (152/40998); 182 798 zgłoszeń z 3 konkursów AMD w KernelBot. Część spadku może wynikać z efektu odstraszania `[INFERENCE]`.
- Reguły: monkeypatch timera, cache wyników, replay grafu CUDA przez ctypes, gałąź „tryb ewaluatora”, obniżenie precyzji, wielostrumieniowość bez synchronizacji; każda z `RulePolicy` i `mapped_positive_fixtures`.
- Physics floor: `t_min = max(FLOPs/peak, bytes/BW, launch)`; poniżej – krytyczne; flagi przy > 100× i < 5 µs.
- Znaleziska drogiego sędziego LLM są destylowane do tanich reguł.
Uwaga: reguły zależą od kontraktu pomiaru – u nich replay grafu to hack, u nas replay PM4 to legalna optymalizacja. Kopiujemy konstrukcję, nie listę; nasze 17 trybów awarii z raportu 07 to gotowe fixture’y.

## Powiązane
- [[repo/_hub|repo]]
- [[sakana-agentic-scientist]]
- [[kernelbench]]
- [[raport-15f-agentowa-nauka]]
- [[fabryka-v1]]
