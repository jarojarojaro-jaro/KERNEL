---
typ: narzedzie
tags: [narzedzia, profilowanie, rocm]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/product/research/16g-lfm-moe-pasmo.md:35-41,107,110-111
status: aktualne
---
# ATT (thread trace) na gfx1100

**Śledzenie instrukcji fali (ATT) działa na RX 7900 XTX w ROCm 10.0: `rocprofv3 --att --att-target-cu 1 --att-simd-select 0 --kernel-include-regex … --kernel-iteration-range …` z `GGML_HIP_PM4=0`; skrypt `att_model.sh` i parser `attsum.py` w `~/wt/lfmmoe-prof/` (2026-10-18).**

Co daje (jeden SIMD jednego CU, mediany fal, LFM2.5 in-model):
- gate+up ekspertów: 85% latencji w `s_waitcnt vmcnt`, VALU 7.5% → za mało ładowań w locie, nie ALU;
- down Q5_K/Q6_K: 33–43% to samo wydawanie VMEM (kolejka pełna małych ładowań `b32`/`d16`), 37–45% `s_waitcnt vmcnt`;
- in_proj+conv: 75–83% `s_waitcnt vmcnt`;
- w mikrobenchu koszt ogona q8_1: fence 1.7k + ticket 2.6k cykli na falę.

Ograniczenia: PM4 musi być wyłączone (rocprof nie widzi taśmy PM4); liczniki przy `--perf-level STABLE_STD` wymagają roota.

## Powiązane
- [[narzedzia/_hub|Narzędzia]]
- [[reactor-monitor]]
- [[pm4-replay]]
- [[2026-10-18-lfm-moe-pasmo]]
