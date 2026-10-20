#!/usr/bin/env bash
# ON the box: after q1 (q1.done): build the worker trees nva (GRID_SMEM) and nvc (RPB) — no benchmark runs meanwhile —
# then the MMVQ microbench of each (A..A order inside mb.sh).
set -uo pipefail
R=/root/results/opt-4070ti-20261020
while [ ! -f $R/q1.done ]; do sleep 10; done
cd /root/cloud
./bld.sh nva; ./bld.sh nvc
./mb.sh nva "-" "GGML_CUDA_MMVQ_GRID_SMEM=1"
./mb.sh nvc "-" "GGML_CUDA_MMVQ_RPB=1" "GGML_CUDA_MMVQ_RPB=4" "GGML_CUDA_MMVQ_RPB=8"
touch $R/q3.done
