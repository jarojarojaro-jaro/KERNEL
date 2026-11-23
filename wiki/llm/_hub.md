---
typ: hub
tags: [llm, hub]
aktualizacja: 2026-11-22
zrodlo: wiki/tools/wiki.py index
status: aktualne
streszczono: 2026-11-22
---
# LLM: trening, dostrajanie i jakość modeli

**Główna sekcja o samych modelach językowych: trening i dostrajanie (draftery, głowica MTP, LoRA, edycje wag), jakość (benchmarki) i pomysły na przyszłe fine-tuningi. Optymalizacja silnika (kernele, łatki, spekulacja w runtime) zostaje w swoich folderach.**

<!-- Jarvo:STRESZCZENIE -->
Trening, dostrajanie (LoRA/PEFT, draftery, głowica MTP), edycje wag i jakość modeli; mapa: [[trening-llm-mapa]]. Inkling 2 Mini: [[inkling-2-mini]].
<!-- /Jarvo:STRESZCZENIE -->

Punkt startowy: [[trening-llm-mapa]] (co już trenowaliśmy, z wynikami, i gdzie leżą starsze notatki). Zasada na produkcję bez zmian: przyspieszamy tylko bezstratnie, a wszystko, co zmienia odpowiedzi modelu (fine-tune, LoRA, edycje wag), jest osobnym tematem i decyzją właściciela ([[2026-11-05-tylko-bezstratne]]).

Wróć: [[index|Strona główna]]. Lista niżej jest generowana przez `python3 tools/wiki.py index`; nie edytuj jej ręcznie.

<!-- AUTO:START -->
## Notatki (5)

- [[mapa-inferencji-roadmap|Mapa inżynierii inferencji LLM: 114 tematów roadmapy a nasza wiedza]] — Roadmapa „LLM Inference Engineering” (17 części, 114 tematów) zestawiona z naszą bazą. 79 tematów mamy zmierzonych na własnym stosie, 15 tylko opisanych, 20 to luki. Luki skupiają się w wielu GPU (równoległość, dezagregacja), produkcji wielu użytkowników i interferencji prefill–decode (2026-11-15).
- [[trening-llm-mapa|Mapa: co już trenowaliśmy i dostrajaliśmy]] — Do 2026-11-13 trenowaliśmy tylko draftery (głowica MTP, DFlash2), żaden nie dał zysku. Model zmienialiśmy wyłącznie edycjami wag bez treningu (Uncensored, Astra-Stop). Jakość mierzą EvalPlus i jakość-mini: Qwen3.8-27B-Uncensored HE+ 92,7%, jakość-mini 87,9%.
- [[peft-lora-warianty|PEFT: LoRA i warianty (LoRA-FA, VeRA, Delta-LoRA, LoRA+)]] — Pięć sposobów taniego dostrajania LLM, w których nie trenuje się całej macierzy W, tylko małą poprawkę niskiego rzędu. Różnią się tym, co jest trenowane, a co zamrożone. To ściąga na przyszłe fine-tuningi (Astra-Stop, głowica MTP), a nie sposób na przyspieszenie (2026-11-14).
- [[qwen38-27b-pi-adapter|Qwen3.8-27B-pi-adapted: LoRA wytrenowana RL-em pod agenta pi — nasz model bazowy, dużo mniej wywołań narzędzi]] — Hugging Face wytrenował adapter LoRA (r = 32, 0,64 GB) do Qwen3.8-27B, czyli naszego modelu bazowego, uczeniem ze wzmocnieniem (RL) wewnątrz agenta pi. Pod pi: SWE-bench Pro (hard 51) 29,4 → 62,7%, Terminal-Bench 2.1 39,5 → 55,8%, 55–62% mniej wywołań narzędzi. Nasz omp to fork pi, więc to najbliższy nam gotowy „dostrojony pod agenta” model, ale trzeba to sprawdzić na naszym stosie i w omp.
- [[vocab-surgery|„Vocab Surgery”: zdjęcie cenzury przez edycję kilkunastu wierszy embeddingu i lm_head]] — Pliny (2026-11-22) zdejmuje odmowy z Inkling-2-Mini bez ruszania warstw: przesuwa 7 wierszy embeddingu (z 201 024) w stronę „zgodnych” tokenów i zmniejsza do 10% 10 wierszy macierzy wyjściowej; deklaruje odmowy bliskie zeru na 800+ promptach i pomijalną stratę jakości, ale bez metody pomiaru (deklaracja, niezmierzone u nas).
<!-- AUTO:END -->
