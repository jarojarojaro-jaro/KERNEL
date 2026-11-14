---
typ: llm
tags: [llm, fine-tuning, lora, peft, telegram]
aktualizacja: 2026-11-14
zrodlo: https://x.com/DailyDoseOfDS_/status/2121536126662128023 (Telegram „gpu”, 2026-11-14); arXiv 2106.09685 (LoRA), 2308.03303 (LoRA-FA), 2310.11454 (VeRA), 2309.02411 (Delta-LoRA), 2402.12354 (LoRA+); ~/KERNEL/product/research/69c-astra-stop.md:209; ~/KERNEL/product/research/62-weight-space-programming.md:279
status: aktualne
---
# PEFT: LoRA i warianty (LoRA-FA, VeRA, Delta-LoRA, LoRA+)

**Pięć sposobów taniego dostrajania LLM, w których nie trenuje się całej macierzy W, tylko małą poprawkę niskiego rzędu. Różnią się tym, co jest trenowane, a co zamrożone. To ściąga na przyszłe fine-tuningi (Astra-Stop, głowica MTP), a nie sposób na przyspieszenie (2026-11-14).**

| Metoda | Co się trenuje | Po co |
|---|---|---|
| LoRA (2106.09685) | dwie małe macierze A, B obok W; W zamrożone | adapter ma kilka MB zamiast kopii modelu |
| LoRA-FA (2308.03303) | tylko B, A zamrożone | mniej pamięci na aktywacje przy treningu |
| VeRA (2310.11454) | A i B losowe, zamrożone i wspólne dla wszystkich warstw; trenują się tylko wektory skali per warstwa | jeszcze mniej parametrów |
| Delta-LoRA (2309.02411) | A, B, a do W dodawana jest zmiana iloczynu AB między krokami | poprawka wyższego rzędu |
| LoRA+ (2402.12354) | jak LoRA, ale B ma większy learning rate niż A | szybsza zbieżność |

**Co to znaczy u nas:**
- Astra-Stop to właśnie LoRA rzędu 1 (`astra-stop-lora-unc.gguf`). llama.cpp ładuje takie adaptery jako GGUF `adapter.type=lora` przez `--lora`.
- **Adapter niescalony** dokłada w każdym kroku mnożenia przez A i B dla każdej dostrojonej macierzy, więc dekod zwalnia [INFERENCE, niezmierzone na XTX].
- **Adapter scalony z W i ponownie skwantowany** daje nowe wagi, czyli zmienia odpowiedzi. To zawsze decyzja właściciela ([[2026-11-05-tylko-bezstratne]]).
- **Zasada:** wybór metody PEFT zmienia tylko koszt treningu. Koszt inferencji zależy od tego, czy adapter jest scalony.

## Powiązane
- [[llm/_hub|llm]]
- [[trening-llm-mapa]]
- [[astra-stop]]
- [[speculators-specforge]]
