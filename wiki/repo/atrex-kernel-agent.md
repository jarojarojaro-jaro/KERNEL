---
typ: repo
tags: [repo, agenci, rocprof]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/repos/25-atrex-kernel-agent.md:1-9,43,189-193; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:35
status: aktualne
---
# alibaba/atrex-kernel-agent (AKA)

**Orkiestrator agentów kodujących dla jednego operatora naraz (HEAD `5ad94ff`, 2026-10-14, v0.3.0); bierzemy narzędzia pomiarowe; werdykt: średnia (narzędzia).**

Kerneli ani wiedzy o RDNA3 brak, pętla agenta dubluje KernelBench/KernelAgent/AKO4ALL. Warte przejęcia: przepis i parser thread trace rocprofv3 (ATT) jako zamiennik martwych liczników PMC na gfx1100, sufit pasma per rozmiar, sondy czasu w kernelach. Przestroga z raportu: stosunek `SQ_LDS_BANK_CONFLICT/SQ_INSTS_LDS` 72.7% na instrukcję przy 3.7% czasu GPU wprowadza w błąd. Liczba „do 1.55×” z WeChata niesprawdzalna (captcha).

## Powiązane
- [[repo/_hub|repo]]
- [[ako4all]]
- [[mixbench]]
- [[rocprof]]
- [[repos-30-przeglad]]
