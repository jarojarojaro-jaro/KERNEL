---
typ: eksperyment
tags: [eksperymenty, rx-7900-xtx, wdrozenie, prefill, prompt-cache, agent, rekord]
aktualizacja: 2026-11-09
zrodlo: branch topka-q70 (~/wt/l1-cachesave; c0576e3e8 + 3152b0bfa + 6f4ae4198 + 3191b25f4); qwen-opt/patches/topka-q70/; qwen-opt/deploy-q70/ (stage.sh, check.sh, swap.sh, deploy.jobs; ticket 22938); qwen-opt/run-topka.sh; qwen-opt/cachesave/summarize.py (grupa Q); qwen-opt/fa-d256/arm.sh; qwen-opt/speed_real.py; product/research/70-fa-d256-jak-to-zrobilismy.md §6
status: aktualne
---
# Wdrożenie topka-q70 na RX 7900 XTX: tura agenta −10,3%, fill 255k +5,6%, bitowo = (2026-11-09) — PASS, w produkcji

**Od 2026-11-09 15:00:16 UTC produkcja `~/llama-topka` = topka-q70 (topka-q63 `c0576e3e8` + cachesave #30137/huge pages + FA D256 wariant 83). Wszystkie bramki md5 identyczne, mediana tury agenta przy głębokości 76–112k 13 413 → 12 029 ms.**

## Co wdrożono
- **Silnik:** topka-q70 = topka-q63 `c0576e3e8` + cachesave (`3152b0bfa` + `6f4ae4198`: port upstream #30137 + `LLAMA_SERVER_CACHE_HUGE`, [[2026-11-08-cachesave-30137]]) + fa-d256 (`3191b25f4`, cherry-pick `32292cc0a`, `GGML_HIP_FA_D256_VAR`, [[2026-11-08-fa-d256-prefill]]). Gałąź `topka-q70` w worktree `~/wt/l1-cachesave`, pełny build `build-hip`. Łatki: `qwen-opt/patches/topka-q70/` (3 sztuki + README).
- **Instalacja:** kopia `build-hip/bin` jako `~/llama-topka.q70` (RUNPATH katalogu buildu → `$ORIGIN`, patchelf), ramiona pomiarowe na tej kopii, bramka md5 względem referencji produkcji, potem zamiana o 15:00:16 UTC. Backup `~/llama-topka.c0576e3e8`.
- **Sposób włączenia: domyślne w launcherze, nie w kodzie** (wariant A z raportu 70 §6.1). `run-topka.sh`: `GGML_HIP_FA_D256_VAR=83` tylko dla profili qwen/uncensored (`fa_var_default=0` dla lfm/flint — wariant strojony pod KV q4_0, f16 KV −2,4%) i `LLAMA_SERVER_CACHE_HUGE=1`; oba opisane w komentarzu nagłówka.
- **Łańcuch wdrożenia:** `qwen-opt/deploy-q70/` (`stage.sh`, `check.sh`, `swap.sh`, `deploy.jobs`), ticket kolejki 22938. `fa-d256/arm.sh` dostał override `ARM_ROCM_DIR`, `cachesave/summarize.py` grupę Q. rc=1 joba q70-fa to znany końcowy `grep` linii OOM bez trafienia (jak w fa-armA/B), nie błąd.

## Bramki (bitowo)
| kontrola | produkcja c0576e3e8 | q70 | wynik |
|---|---|---|---|
| long 32k md5 | e460e3b6 | e460e3b6 | = |
| fill 255k md5 | 31b6525a | 31b6525a | = |
| przełączanie wątków md5 | ea3bda5b | ea3bda5b | = |

## Szybkość (final mode eco 2200, Qwen3.8-27B-Uncensored Q4_K_M, KV q4_0, MTP n4, ctx 262 144)
| pomiar | baseline (A, c0576e3e8) | teraz (q70) | zmiana |
|---|---|---|---|
| prefill long 32k | 849,8 t/s | 859,1 t/s | +1,1% |
| fill 255k | 466,3 t/s, 546,8 s | **492,5 t/s, 517,7 s** | **+5,6%, −29 s** |
| decode po 255k | 72,7 t/s (wariant B) | 73,6 t/s | – |
| spec_sweep T=1, mediana | 119,4 (C1) / 118,1 (A1) | 119,3 t/s, 26,90 ms/krok | bez zmian |
| szczyt VRAM | 23 446 MiB | 23 398 MiB | – |

Baseline fill 255k dla A z [[2026-11-08-fa-d256-prefill]].

## Prawdziwa praca agenta (cachesave `switch.py`, 14 mierzonych tur, 2 wątki naprzemiennie, głębokość 76–112k, i ≥ 2)
| pomiar | produkcja A1 | C (tylko cachesave) | q70 | A1 → q70 |
|---|---|---|---|---|
| **mediana czasu tury (wall)** | 13 413 ms | 12 441 ms | **12 029 ms** | **−1 384 ms (−10,3%)** |
| suma wall | 187,9 s | 175,3 s | 168,5 s | −19,4 s |
| mediana prefillu na turę | 526,7 t/s | – | 550,7 t/s | +4,6% |
| suma czasu promptu | 165,3 s | – | 158,2 s | – |
| zapis wpisu cache (save total) | 1 055,5 ms | – | 285,9 ms | −73% |
| odczyt wpisu (load) | 256,1 ms | – | 171,9 ms | – |
| update cache | 1 321,7 ms | – | 463,0 ms | −65% |

Oba zyski się składają: cachesave skraca obsługę cache (~1 s na turę), FA 83 przyspiesza prefill dopisanego promptu przy dużej głębokości.

## Weryfikacja po zamianie
`/proc`: exe `~/llama-topka/bin/llama-server`, env `GGML_HIP_FA_D256_VAR=83 LLAMA_SERVER_CACHE_HUGE=1 GGML_HIP_PM4=1 LLAMA_SPEC_LOOKUP=3 LLAMA_GPU_VERIFY=1`, `-c 262144`. W trakcie zapisu na tym samym silniku leci benchmark EvalPlus (port 8097); :8080 wyłączony na czas benchmarku.

Prędkość w realnym użyciu (z timingów odpowiedzi benchmarków `*.stats.jsonl`) liczy nowe narzędzie `qwen-opt/speed_real.py` (`speed_real.py RUN_DIR … [--md OUT.md]`: decode ważony tokenami, mediana i p10/p90, akceptacja MTP/lookup, tokeny na krok, prefill, TTFT).

## Wycofanie
- Natychmiast: `GGML_HIP_FA_D256_VAR=0` i/lub `LLAMA_SERVER_CACHE_HUGE=0` + restart (wyniki bitowo te same).
- Pełne: `mv ~/llama-topka ~/llama-topka.q70 && mv ~/llama-topka.c0576e3e8 ~/llama-topka`, potem `run-topka.sh uncensored`.

## Powiązane
- [[eksperymenty/_hub|eksperymenty]]
- [[2026-11-08-fa-d256-prefill]]
- [[2026-11-08-cachesave-30137]]
- raport 70: `product/research/70-fa-d256-jak-to-zrobilismy.md` (§6 przepis wdrożenia — wykonany)
- [[qwen3-8-27b]]
- [[REKORDY]]
