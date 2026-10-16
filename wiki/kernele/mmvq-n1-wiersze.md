---
typ: kernel
tags: [kernele, mmvq, lfm]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:349,374; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:127,139,184; ~/KERNEL/product/research/patch-manifest.json (0052, 0064); ~/KERNEL/qwen-opt/run-llm.sh:11
status: aktualne
---
# MMVQ 1-kolumnowe: 2 wiersze na blok (0052, 0064)

**Strojenie zwykłego matvec (dekodowanie bez spekulacji) pod gfx1100: blok liczy 2 wiersze zamiast jednego, najpierw dla K-quantów, potem także dla Q8_0.**

| łatka | co | zysk | wyłącznik |
|---|---|---|---|
| 0052 (LFM runda 1, 2026-10-14) | K-quanty: 2 wiersze/blok | 4.610 → 4.509 ms/token (+2.2%) | `GGML_HIP_MMVQ_N1_ROWS` |
| 0064 (runda 4) | Q8_0 dołącza do ścieżki 2 wierszy | LFM Uncensored 3.933 → 3.706 ms (+6.1%) | `GGML_HIP_MMVQ_N1_Q8_0` |

Razem z 0059 (zbiorczy upload) dały ok. 8% zysku kampanii LFM (−0.135 ms/token, raport 07). Bitowo identyczne. Tylko gfx110x (strażnik RDNA3_0); na innych kartach to parametr do przestrojenia ([[kernel-tuner]] ma przestrzeń NWARPS × ROWS dla 39 kształtów n=1). LFM Uncensored zyskuje więcej, bo ma więcej tensorów Q8_0.

## Powiązane
- [[kernele/_hub|Kernele]]
- [[mmvq-multikolumnowe]]
- [[kernel-tuner]]
- [[lfm2-5-uncensored]]
- [[lfm-runda-1]]
