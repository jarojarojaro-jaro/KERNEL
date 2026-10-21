# 48. rms_norm 4 rows vs 5, a second GDN state bank (XTX, Qwen3.8-27B)

Continues 41 (XtxRE). Branch `~/wt/xtx-re` (local llama.cpp): 384a79577 (G2 prefetch, 41), 503e7a5d3 (bank v1), 4b01745c7 (bank v2).

## G2 (from 41): GGML_HIP_GDN_PREFETCH=1, E0 ABBA
tbo GATED_DELTA_NET / _LAG pass for 0 and 1; md5 Qwen c4708318 / 6f14e814 OK.
Prose (seeds 1,2, 6400 tok): off 78.95 / 79.01, on 78.87 / 78.89 t/s (-0.1%); mvs median 432.0/432.8 vs 433.8/432.9 (noise).
**Not adopted** (neutral; kernel -0.5 us/launch does not show up in the step).

## Lead 1: rms_norm_mul_f32_unrolled at 4 rows (5.6 us) slower than at 5 (4.44 us)
Trace `vcost/prof-gv1/off` (rocprofv3 kernel trace, PM4 off). 4-row norms (grid 4096) appear **only** in 3 isolated graphs of 132 norms each
(separated from the rest by >1 ms idle); none in steady-state generation (13464 calls at 5 rows in the decode bursts).
Inside those graphs the time per call falls along the graph: medians per 22 calls 9.5 -> 8.9 -> 7.1 -> 6.4 -> 5.9 -> 5.4 us
(second graph 8.5 -> 4.3), i.e. the clock ramps up after idle. An isolated 5-row graph has the same behaviour (6.1 us),
and 1-row calls (also isolated) take 4.56 us > 5 rows. **Conclusion: the difference is the power state after idle, not the row count;
no kernel fix; the 0.36 ms/step estimate does not apply (0 four-row norms per decode step).**

## Lead 2: second GDN state bank (LLAMA_GDN_BANK=1, default off)
Today every verify call replays the n_pend = 5 pending rows of the previous call (rollback by replay), on top of the 5 new rows.
v1: the kernel also writes the state after all rows into a bank in the cell's pend_l row (+n_embd_s floats/layer, ~150 MB);
the next call reads it (no replay) when no pending row was rolled back. Conv history untouched (lag[2] stays n_pend, flags in lag[3]).
v2: ping-pong between the s_l row and the bank (one holds the lagged state, the other the full state), so a full-accept step
writes one state (as without the bank) and replays nothing; after a rollback: replay + 2 writes. state_write takes the lagged state from its slot.

Gates (both versions): tbo GATED_DELTA_NET / _LAG 2/2, smoke PM4=0 md5 6f14e814 / c4708318, gate PM4=1 Qwen c4708318 / 6f14e814,
LFM 894e56e4, bank 0 == 1. **Bit-exact.**

E0 ABBA (seeds 1,2, PM4=1 WA=2 GUARD=1, SVM=0, topka config):

| | A1 (off) | B1 (on) | B2 (on) | A2 (off) | delta |
|---|---|---|---|---|---|
| v1 prose t/s | 78.99 | 78.63 | 78.66 | 78.95 | -0.42% |
| v1 mvs median | 433.1 | 435.9 | 436.4 | 432.9 | +0.7% (mvs-pad 33.60 -> 33.42 ms) |
| v2 prose t/s | 78.93 | 78.68 | 78.45 | 78.80 | -0.38% |
| v2 mvs median | 432.4 | 428.9* | 436.1 | 432.0 | +0.8% without *(one outlier mvs-sampling.h 34.15 ms) |

T=1 prose has the same tokens with bank off/on (bit-exact), so the loss is ms/step: at the prose acceptance rate the steps after a rollback
(replay + extra full-state write, 3.1 MB/layer) cost more than the full-accept steps save. On code (mvs, T=0, long accepts) it gains ~0.2 ms/step.
**Not adopted (regresses E0 prose).** Next variant, if anyone continues: write the full state only when the previous step kept all its rows
(streak predictor) - then a post-rollback step costs exactly what it costs today and prose should be >= 0.
