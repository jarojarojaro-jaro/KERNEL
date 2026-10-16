---
typ: repo
tags: [repo, galezie, gdn]
aktualizacja: 2026-10-16
zrodlo: ~/wt/gdn6/REPORT.md:1-25; ~/wt/qwen5/QWEN5-ROUND5.md:10-16; git -C ~/llama-master log -1 0d89ce56c
status: do-sprawdzenia
---
# Gałąź opt-gdn6 (szybki kernel GDN, bitowy z konstrukcji)

**Gałąź `opt-gdn6` @ `0d89ce56c` (2026-10-15): osobny szybki kernel GDN dla RDNA, zbudowany tak, by był bitowo identyczny; oba commity NIEZMIERZONE (brak GPU w tej rundzie).**

Commity na `c36fd2c87`: `b4e819237` – kernel `gated_delta_net_fast_cuda<128, l2_qk, lag_t>` z sumami DPP i nakładaniem łańcuchów kolejnych tokenów (`GGML_HIP_GDN_FAST=0` wyłącza); `0d89ce56c` – stan przenoszony 16-bajtowymi kawałkami przez 8.5 KB LDS (`GGML_HIP_GDN_B128=0`). Kernel bazowy nietknięty: `git diff` 379 wstawień, 0 usunięć. Dowód bitowości: emulacja symboliczna skompilowanego ISA (`gdnemu.py`/`isadiff.py`). Lekcja z rundy 5: poprzednia próba GDN zmieniła kontrakcję FMA (94 vs 83 FMA) i nie była bitowa.

## Powiązane
- [[repo/_hub|repo]]
- [[galezie-rund]]
- [[opt-qwen5]]
- [[gdn-fast]]
- [[gdnemu-isadiff]]
