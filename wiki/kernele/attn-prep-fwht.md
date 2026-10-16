---
typ: kernel
tags: [kernele, atencja, fwht]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:229,365-366; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:94,132-133,183
status: aktualne
---
# Wejście atencji jednym kernelem i rotacja Hadamarda (0019, 0057, 0058)

**Przy rotowanym KV (FWHT) przygotowanie q/k/v i zapis do cache robi jeden kernel zamiast pięciu, a rotację wyjścia wykonuje combine atencji.**

| łatka | co | zysk | wyłącznik |
|---|---|---|---|
| 0019 (A6, Qwen, 2026-10-12) | rotacja Hadamarda q/k w fuzji norm+rope | 1004 → 972 kerneli; 31.17 → 31.01 ms | brak (build) |
| 0057 (LFM runda 3, 2026-10-14) | q/k norm + rope + FWHT, FWHT v i oba zapisy KV (q8_0) w jednym kernelu | 4.043 → 3.907 ms/token | `GGML_HIP_ATTN_PREP` |
| 0058 | combine `kvq` robi FWHT wyjścia + q8_1 dla o-proj | 3.928 → 3.879 ms/token | `GGML_HIP_KVQ_FWHT` |

Grupa atencji (0055, 0057, 0058) dała ok. 12% zysku LFM (−0.207 ms/token). 0019 i 0057 to kod wspólny CUDA/HIP, 0058 tylko gfx110x (zależy od `kvq`). Wszystkie bitowe. 0057 w manifeście: kształt LFM2 (głowa 64, KV q8_0); raport 07 wymienia ją wśród fuzji z aliasowaniem buforów, ryzykownych na NVIDIA.

## Powiązane
- [[kernele/_hub|Kernele]]
- [[fattn-kvq]]
- [[fuzje-weryfikacji]]
- [[lfm-runda-3]]
- [[lfm2-5-24b-a2b]]
