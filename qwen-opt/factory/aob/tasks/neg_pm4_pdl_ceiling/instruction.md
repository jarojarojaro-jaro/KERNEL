# Estimate a launch-overlap ceiling (CPU only)

Goal: estimate the end-to-end gain on the LFM decode tape of overlapping kernel launches with safe synchronisation,
from the provided text data only (hypothesis notes, launch trace of LFM, microbenchmark table). Then decide go/kill
at a +3 % threshold. Answer: `{"pred_effect_pct": <number>, "decision": "go"|"kill"}`.

This task has NO GPU: do not build, do not run anything on the GPU.

Answer as text; the planner scores it against hidden measurements.
