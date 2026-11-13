---
typ: hub
tags: [llm, hub]
aktualizacja: 2026-11-13
zrodlo: wiki/tools/wiki.py index
status: aktualne
---
# LLM: trening, dostrajanie i jakość modeli

**Główna sekcja o samych modelach językowych: trening i dostrajanie (draftery, głowica MTP, LoRA, edycje wag), jakość (benchmarki) i pomysły na przyszłe fine-tuningi. Optymalizacja silnika (kernele, łatki, spekulacja w runtime) zostaje w swoich folderach.**

Punkt startowy: [[trening-llm-mapa]] (co już trenowaliśmy, z wynikami, i gdzie leżą starsze notatki). Zasada na produkcję bez zmian: przyspieszamy tylko bezstratnie, a wszystko, co zmienia odpowiedzi modelu (fine-tune, LoRA, edycje wag), jest osobnym tematem i decyzją właściciela ([[2026-11-05-tylko-bezstratne]]).

Wróć: [[index|Strona główna]]. Lista niżej jest generowana przez `python3 tools/wiki.py index`; nie edytuj jej ręcznie.

<!-- AUTO:START -->
## Notatki (1)

- [[trening-llm-mapa|Mapa: co już trenowaliśmy i dostrajaliśmy]] — Do 2026-11-13 trenowaliśmy tylko draftery (głowica MTP, DFlash2), żaden nie dał zysku. Model zmienialiśmy wyłącznie edycjami wag bez treningu (Uncensored, Astra-Stop). Jakość mierzą EvalPlus i jakość-mini: Qwen3.8-27B-Uncensored HE+ 92,7%, jakość-mini 87,9%.
<!-- AUTO:END -->
