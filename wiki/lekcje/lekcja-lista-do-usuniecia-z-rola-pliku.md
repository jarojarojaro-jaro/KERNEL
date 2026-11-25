---
typ: lekcja
tags: [lekcje, dysk, produkcja, jaroserverai]
aktualizacja: 2026-11-25
zrodlo: ~/qwen-opt/run-llm.sh:68 (jaroserverai); rozmowa 2026-11-25 18:18–18:25
status: aktualne
---
# Lista „do usunięcia” podaje rolę każdego pliku, nie tylko nazwę katalogu

**2026-11-25 w liście zajętości dysku jaroserverai podałem „orca 17 GB” jako zwykły katalog modelu; JARO kazał usunąć orca, a to był model produkcyjny czatu :8080 (`~/models/orca/Qwen3.8-27B-Uncensored-Q4_K_M.gguf`, `run-llm.sh:68`). Model został skasowany i trzeba go było pobrać ponownie (17 GB, ok. 7 MB/s, ok. 40 min), a czat nie mógł wstać.**

Reguła: zanim wypiszę katalogi do decyzji o usunięciu, sprawdzam, czy coś z nich korzysta (`grep -rn <ścieżka>` w `run-topka.sh`, `run-llm.sh`, `chat8080.sh`, `maya-atomic.json`, plikach `.jobs`), i przy każdej pozycji piszę rolę: produkcja / test w kolejce / nieużywany. Pozycje produkcyjne nigdy nie trafiają na listę „do usunięcia”, tylko do osobnej linii „zostaje (produkcja)”.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[jaroserverai]]
