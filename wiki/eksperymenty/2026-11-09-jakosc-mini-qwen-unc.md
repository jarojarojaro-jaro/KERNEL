---
typ: eksperyment
tags: [eksperymenty, jakosc, benchmark, qwen-uncensored, rx-7900-xtx, predkosc]
aktualizacja: 2026-11-09
zrodlo: ~/KERNEL/qwen-opt/jakosc-mini/results/qwen-unc-low-s20261109/{summary.md,speed.md,speed-mmlu-pro-domains.md}; ~/qwen-opt/jakosc-mini/runs/qwen-unc-low-s20261109/{meta.json,scored.jsonl,humaneval_plus_eval.json}; ~/qwen-opt/queue/logs/queue.log (2026-11-09 15:44:30–16:22:22)
status: aktualne
---
# jakość-mini na produkcyjnym Qwen3.8-27B-Uncensored (2026-11-09)

**Pierwszy bieg [[jakosc-mini]]: 255/290 = 87.9% (95% CI 83.7–91.2%), średnia makro 91.3%; GSM8K 50/50, BFCL 19/20, HumanEval+ 28/30, PL 43/50, MMLU-Pro 115/140.**

Warunki: `run-topka.sh uncensored` (topka-q70, build `b11647-3191b25f4`, Q4_K_M, n_ctx 262144) na własnym porcie przez kolejkę, `reasoning_effort` low, T=0, max_tokens 32768, seed/podzbiory 20261109. Generacja 260 odpowiedzi 2253 s; 30 HumanEval+ wzięte z biegu [[evalplus-jakosc-kodu|EvalPlus]] (te same ustawienia, uzgodnione z EvalPlusQwen). Restore :8080 OK (n_ctx 262144, `~/llama-topka/bin/llama-server`).

| kategoria | n | wynik | 95% CI | tok/odp. |
|---|---|---|---|---|
| GSM8K | 50 | 100.0% | 92.9–100.0 | 301 |
| MMLU-Pro | 140 | 82.1% | 75.0–87.6 | 1699 |
| PL (Global-MMLU pl) | 50 | 86.0% | 73.8–93.0 | 856 |
| HumanEval+ | 30 | 93.3% | 78.7–98.2 | 820 |
| BFCL v3 | 20 | 95.0% | 76.4–99.1 | 148 |

- Sparsowane 289/290: jedyny brak to MMLU-Pro `11632` (engineering) ucięty na 32 768 tokenach (pętla myślenia), stąd 9028 tok/odp. w engineering.
- HumanEval+ 124 i 151: base pass, plus fail. BFCL `multiple_193`: „Eiffel Tower, Paris” zamiast „Eiffel Tower” (ścisłe porównanie BFCL).
- MMLU-Pro per dziedzina 6–10/10 (n=10, CI ~±20 pp): orientacyjnie.

## Prędkość na prawdziwych zadaniach
`speed_real.py` (timings llama-server per odpowiedź). Uwaga: T=0 i effort low; czat zwykle T=1, odniesienie spec_sweep T=1 = 119.3 t/s ([[qwen3-8-27b]]).

| zbiór | odp. | dekod t/s (ważone) | mediana [p10–p90] | akceptacja | tok/krok | prefill t/s | TTFT ms |
|---|---|---|---|---|---|---|---|
| BFCL | 20 | 169.5 | 160.2 [149.2–174.9] | 0.787 | 4.6 | 715.1 | 625 |
| GSM8K | 50 | 156.7 | 157.7 [142.9–167.9] | 0.747 | 4.26 | 419.6 | 254 |
| HumanEval+ | 30 | 174.8 | 175.9 [159.2–196.0] | 0.74 | 4.84 | 513.2 | 311 |
| MMLU-Pro | 140 | 143.3 | 131.9 [115.3–163.9] | 0.625 | 3.99 | 639.2 | 368 |
| PL | 50 | 120.1 | 117.9 [108.0–130.6] | 0.535 | 3.25 | 605.7 | 314 |

Razem 323 261 tokenów, dekod ważony 142.4 t/s. MMLU-Pro wg dziedzin: od 116.0 t/s (history, akceptacja 0.515) do 173.0 (math, 0.676); tekst humanistyczny i PL ≈ 116–126 t/s, matematyka/kod 157–175 t/s (`speed-mmlu-pro-domains.md`).

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[jakosc-mini]]
- [[evalplus-jakosc-kodu]]
- [[modele/qwen3-8-27b-uncensored|Qwen3.8-27B-Uncensored]]
- [[2026-11-09-wdrozenie-topka-q70]]
