---
typ: eksperyment
tags: [eksperymenty, rx-7900-xtx, jakosc, evalplus, uncensored]
aktualizacja: 2026-11-09
zrodlo: ~/KERNEL/qwen-opt/evalplus/uncensored-low/{summary.md,summary.json,speed.md,gen-wall.txt}; ~/KERNEL/qwen-opt/evalplus/overhead.py; ~/qwen-opt/evalplus/runs/uncensored-low/ (surowe generacje); https://www.localmaxxing.com/en/benchmarks/humaneval-plus; https://evalplus.github.io/leaderboard.html; https://huggingface.co/Qwen/Qwen3.8-27B
status: aktualne
---
# EvalPlus: Qwen3.8-27B-Uncensored Q4_K_M, produkcja XTX, effort low (2026-11-09)

**Produkcyjny model czatu ma greedy pass@1 HumanEval 97,6 / HumanEval+ 92,7 / MBPP 92,9 / MBPP+ 80,2 %, przy ~750 tokenach i ~4,9 s na odpowiedź; to pierwszy przebieg bramki [[evalplus-jakosc-kodu|jakość-mini]].**

Warunki: silnik topka-q70 (`~/llama-topka`, build `b11647-3191b25f4`), `run-topka.sh uncensored` (konfiguracja produkcyjna, n_ctx 262144, MTP n=4 + lookup), port 8097, `--reasoning-effort low`, T=0, evalplus 0.3.1 (prompt i `sanitize` evalplus), `max_tokens` 32768. Kolejka ticket 23234, gen 15:00–15:44 UTC; :8080 przywrócone (n_ctx 262144, binarka `~/llama-topka/bin/llama-server`). Wykonanie kodu: CPU, piaskownica Landlock (opis w notatce metody).

| zbiór | pass@1 % | 95% CI (Wilson) | tok/odp. | ucięte | wall gen |
|---|---|---|---|---|---|
| HumanEval | 97,6 (160/164) | 93,9–99,0 | 786 | 0 | 808 s |
| HumanEval+ | 92,7 (152/164) | 87,6–95,8 | | | |
| MBPP | 92,9 (351/378) | 89,8–95,0 | 704 | 0 | 1819 s |
| MBPP+ | 80,2 (303/378) | 75,8–83,9 | | | |

Razem 2627 s generacji, 542 odpowiedzi, myślenie ~1,3 tys. znaków/odp.

**Porównanie publiczne** (różne harnessy, tylko orientacyjnie): karta modelu [Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B) nie podaje HumanEval/MBPP (kod: LiveCodeBench v6 90,3). [EvalPlus leaderboard](https://evalplus.github.io/leaderboard.html) nie ma Qwen3.x (najbliżej Qwen2.5-Coder-32B-Instruct 92,1 / 87,2 / 90,5 / 77,0). [LocalMaxxing HumanEval+](https://www.localmaxxing.com/en/benchmarks/humaneval-plus) (stan 2026-11-09): Qwen3.8-27B Q4_K_XL 90,9% (8 przebiegów), Q6_K_XL 92,1%, Q4_K_M 91,0% (100 z 164). Nasze 92,7% mieści się w tym przedziale.

**Czy effort low kosztuje dokładność:** niezmierzone wprost (brak ramienia medium/xhigh). Brak uciętych odpowiedzi i HumanEval+ na poziomie publicznych pomiarów pełnej wagi → na tym zbiorze nie widać straty [WNIOSEK, nie pomiar]. Test: `jakosc-mini.sh --effort xhigh --port 8097 all`.

## Prędkość na prawdziwych zadaniach
`speed_real.py` z `timings` llama-server; T=0, effort low (czat zwykle T=1; odniesienie spec_sweep T=1: mediana 119,3 t/s).

| zbiór | odp. | tok/odp. | dekod t/s (ważone) | mediana [p10–p90] | akceptacja | tok/krok | prompt tok (med.) | prefill t/s | TTFT ms (med.) |
|---|---|---|---|---|---|---|---|---|---|
| HumanEval+ | 164 | 786 | 174,2 | 175,8 [158,1–204,1] | 0,745 | 4,82 | 157 | 534,8 | 311 |
| MBPP+ | 378 | 704 | 156,7 | 154,3 [140,3–169,9] | 0,702 | 4,31 | 79 | 380,8 | 222 |

Razem 394 859 tokenów, dekod ważony 162,0 t/s.

**Narzut na żądanie** (`overhead.py`): `wall − prompt_ms − predicted_ms` mediana 75 ms (p90 98) HE+, 74 ms (p90 104) MBPP+; dopasowanie liniowe `prompt_ms ≈ 155 ms + 0,98 ms/tok` (HE+), `133 ms + 1,10 ms/tok` (MBPP+) — TTFT krótkiego promptu to głównie stały koszt, nie przepustowość prefillu. Stały koszt ~230 ms (HE+) / ~207 ms (MBPP+) = 4,7% / 4,3% średniej odpowiedzi 4,9 / 4,8 s. Dekod HE+: 182,5 t/s dla odpowiedzi < 400 tok., 162,8 t/s > 1500 tok. Obserwacja i możliwy bezstratny cel; przyczyn nie mierzono.

## Powiązane
- [[eksperymenty/_hub|eksperymenty]]
- [[evalplus-jakosc-kodu]]
- [[2026-11-09-wdrozenie-topka-q70]]
- [[modele/qwen3-8-27b-uncensored|Qwen3.8-27B-Uncensored]]
- [[astra-stop]]: następny kandydat bramki
