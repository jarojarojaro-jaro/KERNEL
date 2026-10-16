---
typ: eksperyment
tags: [eksperymenty, cache-promptu, konfiguracja]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:193-219; ~/KERNEL/qwen-opt/STATUS-NEXT.md:40-44
status: aktualne
---
# 2026-10-12: cache promptu, długi kontekst po `kvq` i testy bez zmian w kodzie (A7)

**Cache promptu llama-server działa dobrze na domyślnych ustawieniach; testy flag bez zmian w kodzie (A7) dały szum, a `-ub 2048` kończył się OOM.**

Cache promptu (dokument 27k tokenów, domyślne ustawienia serwera):

| scenariusz | przetworzone tokeny | czas |
|---|---|---|
| pierwsze pytanie (zimno) | 27332 | 31.9 s |
| pytanie uzupełniające | 24 | 0.7 s |
| nowa rozmowa, ten sam dokument | 517 | 1.2 s |
| powrót po innej rozmowie (28k) | 536 | 1.4 s |

Domyślne `--cache-ram 8192` i checkpointy już działają; `run-llm.sh` ustawia `--cache-ram 16384`.

Długi kontekst po kernelu `kvq` (long_ctx_bench, MTP n=4, T=0): decode 1.7k 78.6 → 92.9, 6.6k 75.5 → 81.4, 29.5k 62.4 → 74.4, 94k 43.0 → 70.9 t/s (+65%). KV draftu q4_0 (`-ctkd/-ctvd`): bez zysku (71.6 vs 70.9 przy 94k).

A7 (bez zmian w kodzie, ROCm):
- `-bs`: 41.69 vs 41.65 ms/krok — bez efektu;
- `ROCBLAS_USE_HIPBLASLT=1`: pp4096 1050 vs 1040 — szum;
- `-ub 1024`: +1%; `-ub 2048`: pp +3%, ale serwer z ctx 204800 → OOM (24.5 GB VRAM) przy pierwszym długim prompcie; zostaje ub 512.

Późniejsza analiza logów (STATUS-NEXT): w 9 sesjach LFM cache trafiał 91% tokenów (tura omp ~99.8%, mediana 25 nowych tokenów), prefill to 3.8% czasu GPU; pomysły (zapis prefiksu na dysk, checkpointy przy hybrydach) niezrobione.

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[fattn-kvq]]
- [[2026-10-12-rocm-vs-vulkan]]
- [[run-llm-sh]]
- [[lekcja-oom-ub2048]]
