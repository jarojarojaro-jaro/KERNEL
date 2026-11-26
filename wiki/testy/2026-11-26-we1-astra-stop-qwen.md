---
typ: test
tags: [testy, edycja-wag, astra-stop, qwen, lora, xtx]
aktualizacja: 2026-11-26
zrodlo: ~/qwen-opt/we1/res/summary.md (jaroserverai), ~/qwen-opt/queue/logs/we1-*.log; adapter ~/qwen-opt/we1/astra-lora-unc.gguf (90 496 B, sha f75fbfb3…)
status: aktualne
---
# 2026-11-26 WE1: Astra-Stop (rank-1 `</think>`) na Qwen3.8-27B Uncensored, XTX, LoRA w locie, skale 0 / 0,5 / 1 / 1,5

**Wynik negatywny przy produkcyjnym effort low: edycja nie skraca myślenia (mediana tokenów myślenia 281,5 → 334,5 przy skali 1, suma czasu +6,4%; skala 1,5: −1,9% czasu, ale 2 przecieki `</think>` i 19/20 zadań), jakość bez zmian (GSM8K 40/40, HumanEval+ 20/20 przy każdej skali), KLD na zwykłym tekście w szumie (skala 1: 0,0054 vs podłoga ub256 0,0086), a LoRA w locie kosztuje −6,7% dekodu (43,42 → 40,51 t/s). Zysk −35% z 69c dotyczył effort xhigh (myślenie 26k tokenów); przy krótkim myśleniu kierunek `</think>` nie ma czego skracać.**

| skala | mediana myślenia | suma czasu 20 zadań | przecieki | zadania | GSM8K | HumanEval+ | mean KLD |
|---|---|---|---|---|---|---|---|
| 0 | 281,5 | 91,2 s | 0 | 20/20 | 40/40 | 20/20 | – |
| 0,5 | 381,5 | 117,9 s (+29%) | 0 | 19/20 | 40/40 | 20/20 | 0,0016 |
| 1,0 | 334,5 | 107,1 s (+17%) | 0 | 20/20 | 40/40 | 20/20 | 0,0054 |
| 1,5 | 320,5 | 96,2 s (+5%) | 2 | 19/20 | 40/40 | 20/20 | 0,0147 |

- Pułapka uruchomienia potwierdzona i ominięta: serwer z `--lora-scaled plik:0`; żądanie bez pola `lora` = dokładnie baza (md5 równe).
- Decyzja: nie wdrażamy Astra-Stop przy effort low; ewentualny test przy xhigh tylko, jeśli JARO używa wysokiego effortu.

## Powiązane
- [[astra-stop]]
- [[edycja-wag-backlog-2026-11-26]]
