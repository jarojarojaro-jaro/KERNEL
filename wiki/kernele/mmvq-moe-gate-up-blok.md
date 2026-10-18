---
typ: kernel
tags: [kernele, mmvq, moe, lfm]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/product/research/16g-lfm-moe-pasmo.md:43-81; gałąź `opt-lfmmoe` @ `7c5b2a116` (`mmvq.cu`)
status: aktualne
---
# MMVQ MoE gate+up: blok jednej grupy q8_1 (`GGML_HIP_MOE_GU_BLOCK`)

**`mul_mat_vec_q_moe_gate_up_q5k<8>`: blok 16 fal liczy 32 wiersze jednej grupy q8_1 (każdy wiersz jak kernel 2-wierszowy), wagi następnej iteracji ładuje przed bieżącym iloczynem, a ogon q8_1 idzie przez LDS i jedną barierę zamiast fence + atomika ticketu; bitowo identyczny z produkcją.**

Zakres: RDNA3, jeden token, Q5_K, K = 2048, SWIGLU bez biasów, z kopią q8_1 (`GGML_HIP_GATE_UP_Q8`); inne typy i kształty idą starą drogą. Domyślnie włączony, `=0` wyłącza (commit `7c5b2a116`, gałąź `opt-lfmmoe` od `amd-opt` @ `f61994f58`).

Mikrobench (`moebench.hip`, 17.30 MB, 3 procesy): produkcja 24.16/23.64/24.04 µs → 22.32/22.52/22.28 µs (−7%); sam blok bez prefetchu 23.2–23.5, sam prefetch 23.0–23.2. ATT: ogon starego kernela to `s_waitcnt_vscnt` 1.7k + powrót ticketu 2.6k cykli na falę. In-model 25.36/27.24 → 24.84/25.00 µs.

test-backend-ops nie tworzy tej fuzji, więc pokrywają ją hashe logitów i greedy md5. Wynik end-to-end: [[2026-10-18-lfm-moe-pasmo]].

## Powiązane
- [[kernele/_hub|Kernele]]
- [[fuzje-lfm-moe]]
- [[mmvq-multikolumnowe]]
- [[lekcja-sufit-wzorca]]
- [[lfm2-5-24b-a2b]]
