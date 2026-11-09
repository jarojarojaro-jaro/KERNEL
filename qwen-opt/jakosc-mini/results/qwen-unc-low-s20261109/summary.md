# jakość-mini: qwen-unc (effort low, seed 20261109)

model: `Qwen3.8-27B-Uncensored-Q4_K_M.gguf`, n_ctx 262144, max_tokens 32768, T=0, subsets `subsets/s20261109`, HumanEval+ reused from an EvalPlus run: 30

| kategoria | n | poprawne | acc % | 95% CI (Wilson) | sparsowane/odp. | ucięte | tok/odp. | wall s |
|---|---|---|---|---|---|---|---|---|
| GSM8K | 50 | 50 | 100.0 | 92.9–100.0 | 50/50 | 0 | 301 | 113 |
| MMLU-Pro | 140 | 115 | 82.1 | 75.0–87.6 | 139/140 | 1 | 1699 | 1729 |
| PL (Global-MMLU pl) | 50 | 43 | 86.0 | 73.8–93.0 | 50/50 | 0 | 856 | 379 |
| HumanEval+ | 30 | 28 | 93.3 | 78.7–98.2 | 30/30 | 0 | 820 | 153 |
| BFCL v3 | 20 | 19 | 95.0 | 76.4–99.1 | 20/20 | 0 | 148 | 32 |
| **razem (mikro)** | 290 | 255 | 87.9 | 83.7–91.2 | 289/290 | 1 | 1115 | 2406 |

Średnia makro 5 kategorii: 91.3%

## MMLU-Pro wg dziedzin (n=10, orientacyjnie)

| kategoria | n | poprawne | acc % | 95% CI (Wilson) | sparsowane/odp. | ucięte | tok/odp. | wall s |
|---|---|---|---|---|---|---|---|---|
| biology | 10 | 9 | 90.0 | 59.6–98.2 | 10/10 | 0 | 876 | 76 |
| business | 10 | 8 | 80.0 | 49.0–94.3 | 10/10 | 0 | 651 | 46 |
| chemistry | 10 | 8 | 80.0 | 49.0–94.3 | 10/10 | 0 | 1908 | 123 |
| computer science | 10 | 9 | 90.0 | 59.6–98.2 | 10/10 | 0 | 959 | 76 |
| economics | 10 | 10 | 100.0 | 72.2–100.0 | 10/10 | 0 | 769 | 61 |
| engineering | 10 | 8 | 80.0 | 49.0–94.3 | 9/10 | 1 | 9028 | 600 |
| health | 10 | 7 | 70.0 | 39.7–89.2 | 10/10 | 0 | 901 | 76 |
| history | 10 | 8 | 80.0 | 49.0–94.3 | 10/10 | 0 | 1121 | 103 |
| law | 10 | 7 | 70.0 | 39.7–89.2 | 10/10 | 0 | 1432 | 120 |
| math | 10 | 9 | 90.0 | 59.6–98.2 | 10/10 | 0 | 2395 | 143 |
| other | 10 | 6 | 60.0 | 31.3–83.2 | 10/10 | 0 | 829 | 70 |
| philosophy | 10 | 8 | 80.0 | 49.0–94.3 | 10/10 | 0 | 738 | 64 |
| physics | 10 | 9 | 90.0 | 59.6–98.2 | 10/10 | 0 | 1306 | 95 |
| psychology | 10 | 9 | 90.0 | 59.6–98.2 | 10/10 | 0 | 872 | 78 |

## BFCL wg kategorii

| kategoria | n | poprawne | acc % | 95% CI (Wilson) | sparsowane/odp. | ucięte | tok/odp. | wall s |
|---|---|---|---|---|---|---|---|---|
| multiple | 6 | 5 | 83.3 | 43.6–97.0 | 6/6 | 0 | 112 | 10 |
| parallel | 6 | 6 | 100.0 | 61.0–100.0 | 6/6 | 0 | 223 | 11 |
| simple | 8 | 8 | 100.0 | 67.6–100.0 | 8/8 | 0 | 119 | 11 |

## PL wg grup przedmiotów

| kategoria | n | poprawne | acc % | 95% CI (Wilson) | sparsowane/odp. | ucięte | tok/odp. | wall s |
|---|---|---|---|---|---|---|---|---|
| Humanities | 18 | 15 | 83.3 | 60.8–94.2 | 18/18 | 0 | 1014 | 165 |
| Medical | 5 | 4 | 80.0 | 37.6–96.4 | 5/5 | 0 | 1259 | 49 |
| Other | 4 | 4 | 100.0 | 51.0–100.0 | 4/4 | 0 | 568 | 20 |
| STEM | 9 | 8 | 88.9 | 56.5–98.0 | 9/9 | 0 | 663 | 52 |
| Social Sciences | 14 | 12 | 85.7 | 60.1–96.0 | 14/14 | 0 | 716 | 93 |

