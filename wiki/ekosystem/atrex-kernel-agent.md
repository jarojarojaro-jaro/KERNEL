---
typ: ekosystem
tags: [ekosystem, agenci, rocprof]
aktualizacja: 2026-11-24
zrodlo: ~/KERNEL/qwen-opt/research/repos/25-atrex-kernel-agent.md:1-9,43,189-193; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:35
status: aktualne
---
# alibaba/atrex-kernel-agent (AKA)

**Orkiestrator agentów kodujących dla jednego operatora naraz (HEAD `5ad94ff`, 2026-10-14, v0.3.0); bierzemy narzędzia pomiarowe; werdykt: średnia (narzędzia).**

Kerneli ani wiedzy o RDNA3 brak, pętla agenta dubluje KernelBench/KernelAgent/AKO4ALL. Warte przejęcia: przepis i parser thread trace rocprofv3 (ATT) jako zamiennik martwych liczników PMC na gfx1100, sufit pasma per rozmiar, sondy czasu w kernelach. Przestroga z raportu: stosunek `SQ_LDS_BANK_CONFLICT/SQ_INSTS_LDS` 72.7% na instrukcję przy 3.7% czasu GPU wprowadza w błąd. Liczba „do 1.55×” z WeChata niesprawdzalna (captcha).

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)
Werdykt „średnia: bierzemy narzędzia pomiarowe” pominął główną lekcję: jak budować pracę agentów, żeby agent nie mógł sam ogłosić sukcesu (`qwen-opt/research/repos/25-atrex-kernel-agent.md:16-26`):
- **A1 mechaniczny nadzorca:** o przyjęciu i końcu decyduje kod, nie samoocena agenta; agent oddaje tylko `candidate_ready`/`pivot`/`blocked` (`docs/design.md:24-27`).
- **A4 wynik przypięty do hasha** dokładnie tego zacommitowanego pliku; **A3** ABBA w jednej alokacji GPU, wszystkie przebiegi muszą przejść.
- **A8 osobny recenzent numeryki:** inny agent czyta kod kandydata i referencję, zleca ≤ 3 celowane rozkłady wejść z cytatem linii; tolerancji agent nie ustala (rel-L2 ≤ 1e-3 stała).
- **A6 „optimization dropout”:** po zastoju świeży agent dostaje pamięć z zamaskowaną częścią porażek, żeby nie kotwiczyć się w starych wnioskach.
- **Nasz odpowiednik:** [[fabryka-v1]] / [[fabryka-cli]] (weryfikator jedynym piszącym werdykty, karta przed pomiarem, ledger z hashami), rdzeń G0–G5 zbudowany 10-16.
- **Gdzie nam nie wyszło:** Enigma Turbo (Gemini, 2026-11-20) nie przeszedł przez żaden nadzorca: testy pisał ten sam agent, na syntetycznym modelu, i ogłosił „ALL PASS” przy bełkocie ([[enigma-turbo-gemini-2026-11-20]]). A1 i A8 to dokładnie brakujące ogniwa.
- Bierzemy: kod od każdego agenta (Kernel, Gemini, podagenci) idzie na kartę tylko przez weryfikator fabryki albo bramkę z prawdziwym GGUF (md5/KLD względem llama.cpp); przy nowych kernelach sondy numeryczne zleca osobny agent.

## Powiązane
- [[ako4all]]
- [[mixbench]]
- [[rocprof]]
- [[repos-30-przeglad]]
