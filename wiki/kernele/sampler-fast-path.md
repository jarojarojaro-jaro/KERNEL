---
typ: kernel
tags: [kernele, sampler, host]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:277-278,345,381-392; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:106,123,140-144,266; ~/KERNEL/qwen-opt/STATUS-NEXT.md:16,20-21
status: aktualne
---
# Szybka ścieżka samplera (0031, 0048, 0065–0069)

**Sampler wybiera top-k bez sortowania całego słownika (128k LFM / 248k Qwen); kolejne łatki usunęły sytuacje, w których klient (web UI, kary, gramatyka narzędzi) po cichu wracał na wolną ścieżkę.**

| łatka | przypadek | wyłącznik |
|---|---|---|
| 0031 (K3, 2026-10-13) | top-k bez pełnej tablicy kandydatów, leniwa kopia samplera; sample+accept 645 → 140 µs | `LLAMA_SAMPLER_FAST_TOPK`, `LLAMA_SPEC_LAZY_SAVE` |
| 0048 (2026-10-14) | za samplerem kar (GGUF LFM ma repeat_penalty 1.05); LFM 5.79 → 5.11 ms/token | `LLAMA_SAMPLER_FAST_PENALTIES` |
| 0065 | serwer ignoruje `reasoning_control` z web UI (obejście, zastąpione przez 0066) | `LLAMA_SERVER_REASONING_CONTROL` |
| 0066–0069 (2026-10-15) | budżet myślenia, `n_probs`, `logit_bias` (≤64 tokeny), gramatyka (także leniwa gramatyka narzędzi omp; nie przy `grammar_first`) | `LLAMA_SAMPLER_FAST_RBUDGET/NPROBS/LOGIT_BIAS/GRAMMAR` |

Wynik slow → fast (serwer, 2026-10-15): narzędzia omp LFM 254.2 → 294.3, Qwen MTP 104.8 → 113.2 t/s; budżet myślenia LFM 256.9 → 292.9, Qwen 99.3 → 107.0.

Poprawność: te same tokeny (SAME-TOK): harness CPU 312k wektorów, 0 różnic; `samp_ab.py` md5 tekstu i wywołań narzędzi fast == slow w 5 przypadkach. Kod hosta: przenosi się na każdą platformę i GPU; raport 07 rekomenduje go do upstreamu.

## Powiązane
- [[kernele/_hub|Kernele]]
- samp-ab
- [[latki-hostowe]]
- [[lfm2-5-24b-a2b]]
- [[2026-10-15-sampler]]
