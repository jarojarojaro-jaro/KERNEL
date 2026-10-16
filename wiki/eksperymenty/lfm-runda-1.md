---
typ: eksperyment
tags: [eksperymenty, lfm, moe]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:343-351; ~/KERNEL/qwen-opt/research/lfm-decode.md
status: aktualne
---
# 2026-10-14: LFM runda 1 (łatki 0048–0052)

**Sampler kar, q8_1 z normy, fuzje shortconv i MoE down oraz 2 wiersze na blok w MMVQ: LFM tg128 197.4 → 220.4 t/s, serwer 172.9 → 218.6 t/s (+26%), bitowo identycznie.**

| łatka | zmiana | efekt |
|---|---|---|
| 0048 `LLAMA_SAMPLER_FAST_PENALTIES` | szybkie top-k za samplerem kar (GGUF LFM ma repeat_penalty 1.05) | serwer 5.79 → 5.11 ms/token |
| 0049 `GGML_HIP_Q8_IDS` | norma FFN pisze q8_1 dla ekspertów | 720 → 682 kerneli, 5.067 → 4.979 ms |
| 0050 `GGML_HIP_CONV_MUL` | mnożenia shortconv w SSM_CONV + q8_1 | → 595 kerneli, 4.800 ms |
| 0051 `GGML_HIP_MOE_DOWN_REDUCE` | down + ważenie + residual | → 521 kerneli, 4.817 → 4.642 ms |
| 0052 `GGML_HIP_MMVQ_N1_ROWS` | 2 wiersze na blok, K-quanty | 4.610 → 4.509 ms |

Wynik (przeplatane A/B z amd-opt e84abb808): llama-bench tg128 197.4 → 220.4 t/s (5.067 → 4.536 ms); serwer `lfm none` 172.9 → 218.6 t/s (217–219 na każdym typie promptu); Qwen MTP 29.12 → 29.17 ms/krok (szum). Greedy md5 bez zmian (LFM plain, Qwen plain + MTP).

Nie dało nic: Hadamard + quantize wyjścia atencji (4.474 → 4.490 ms), 4 wiersze na falę, rozwijanie pętli K, `--backend-sampling` (szybki, ale nie bitowo).

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[fuzje-lfm-moe]]
- [[lfm-shortconv]]
- [[lfm-runda-2]]
- [[lfm-baza]]
