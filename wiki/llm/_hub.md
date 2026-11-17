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
## Notatki (4)

- [[mapa-inferencji-roadmap|Mapa inżynierii inferencji LLM: 114 tematów roadmapy a nasza wiedza]] — Roadmapa „LLM Inference Engineering” (17 części, 114 tematów) zestawiona z naszą bazą. 79 tematów mamy zmierzonych na własnym stosie, 15 tylko opisanych, 20 to luki. Luki skupiają się w wielu GPU (równoległość, dezagregacja), produkcji wielu użytkowników i interferencji prefill–decode (2026-11-15).
- [[trening-llm-mapa|Mapa: co już trenowaliśmy i dostrajaliśmy]] — Do 2026-11-13 trenowaliśmy tylko draftery (głowica MTP, DFlash2), żaden nie dał zysku. Model zmienialiśmy wyłącznie edycjami wag bez treningu (Uncensored, Astra-Stop). Jakość mierzą EvalPlus i jakość-mini: Qwen3.8-27B-Uncensored HE+ 92,7%, jakość-mini 87,9%.
- [[peft-lora-warianty|PEFT: LoRA i warianty (LoRA-FA, VeRA, Delta-LoRA, LoRA+)]] — Pięć sposobów taniego dostrajania LLM, w których nie trenuje się całej macierzy W, tylko małą poprawkę niskiego rzędu. Różnią się tym, co jest trenowane, a co zamrożone. To ściąga na przyszłe fine-tuningi (Astra-Stop, głowica MTP), a nie sposób na przyspieszenie (2026-11-14).
- [[sensenova-loop-9b|SenseNova-Loop-9B: model z pętlą warstw — pamięć jak 9B, pasmo jak ~14B, jakość wg producenta blisko Qwen3.8-27B]] — Model z prawdziwej firmy, z prawdziwymi wagami (Apache-2.0), ale jakość to na razie tylko tabela producenta. Dla nas najważniejsze są dwie rzeczy. Pętla zmienia liczenie sufitu: bajty na token liczymy z wykonań warstw, nie z rozmiaru pliku. Model jest też kandydatem do Enigmy na karty 8–16 GB, ale upstream llama.cpp go jeszcze nie obsługuje.
<!-- AUTO:END -->
