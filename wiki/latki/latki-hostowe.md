---
typ: latka
tags: [latki, host, cpu]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:276-281,326-329,367; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:104,122,134,317
status: aktualne
---
# Łatki hostowe (CPU, pętla spekulacji)

**Zmiany po stronie CPU, które skracają krok niezależnie od GPU: asynchroniczne wejścia, zbiorczy upload, tani rollback i maska KQ w pętli spekulacji.**

| łatka | co | zysk | wyłącznik |
|---|---|---|---|
| 0029 (K3, 2026-10-13) | asynchroniczne wysyłanie wejść grafu (było 2 synchronizacje × 16 wejść/krok) | 32.20 → 31.89 ms/krok | `LLAMA_ASYNC_INPUTS` |
| 0047 (2026-10-14) | seq_rm po indeksie sekwencji zamiast skanu 204800 komórek, szybka maska KQ dla jednej sekwencji, kopia promptu tylko dla n-gram | rollback+process_token 236 → 6 µs; 29.36 → 28.94 ms, 102.6 → 104.2 t/s | `LLAMA_KV_MASK_FAST`, `LLAMA_KV_SEQ_RM_SCAN` |
| 0059 (LFM runda 3) | 12 uploadów wejść na token → jedna kopia H2D + kernel rozrzucający | 3.840 → 3.806 ms/token | `GGML_HIP_INPUT_BATCH` |

K3 łącznie (0029–0031, z samplerem): host na krok sample+accept 645 → 140 µs, post_decode 963 → 375 µs; Qwen 32.14 → 30.97 ms/krok (97.8 → 101.5 t/s). Wszystkie bitowe (sampler: te same tokeny).

Rodzina F1 raportu 07: przenosi się automatycznie na każdy model, GPU i backend. Raport rekomenduje 0029, 0047, 0059 do upstreamu.

## Powiązane
- [[latki/_hub|Łatki]]
- [[sampler-fast-path]]
- [[latki-spekulacji]]
- [[mtp-draft-graf]]
- [[2026-10-13-k3-host]]
