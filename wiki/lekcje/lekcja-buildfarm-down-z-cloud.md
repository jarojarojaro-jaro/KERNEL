---
typ: lekcja
tags: [lekcje, vast, chmura, narzedzia]
aktualizacja: 2026-11-05
zrodlo: ~/qwen-opt/cloud/state/watchdog-59279813.log; ~/qwen-opt/cloud/buildfarm.sh:3,82-84; ~/qwen-opt/cloud/up.sh:21,43; komunikat Main do WikiQ63 2026-11-06
status: aktualne
---
# `buildfarm.sh down` uruchamiaj z `~/qwen-opt/cloud`

**Buildfarm Vast z 2026-11-05 (14:46–15:05, koszt $0.027) został zniszczony poprawnie dopiero z katalogu `~/qwen-opt/cloud`: `vastai` to funkcja z `lib.sh`, nie binarka w PATH, więc z innego katalogu `down` nie znajduje polecenia.**

- Reguła: `cd ~/qwen-opt/cloud && ./buildfarm.sh down` i sprawdzenie, że watchdog zapisał „instance … is gone”.
- Druga poprawka: `up.sh` wymaga `--download-gb N` (ile GB pobierze maszyna: modele + źródła), a `buildfarm.sh up` przekazuje go dalej z domyślnym 15 GB. Bez tego filtr ofert pomijał koszt transferu ([[lekcja-vast-transfer-kosztuje]]).
- Watchdog z deadline’em (+3 h) jest siatką bezpieczeństwa, nie metodą zamykania.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-vast-cli-klucz]]
- [[lekcja-vast-transfer-kosztuje]]
- [[vast-ai]]
