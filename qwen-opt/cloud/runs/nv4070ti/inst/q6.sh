#!/usr/bin/env bash
# ON the box (credit emergency): md5 gate RPB=8 on nvc, then final ABBA T (nvc off) vs T' (RPB=8 + YIELD_FAST=2 + COUPLED=1)
set -uo pipefail
R=/root/results/opt-4070ti-20261020
while [ ! -f $R/q4.done ]; do sleep 5; done
cd /root/cloud; C=/root/src/nvc/b89/bin
TK=$C TENV="GGML_CUDA_MMVQ_RPB=8" ./gate.sh rpb8
./ab.sh final "" "GGML_CUDA_MMVQ_RPB=8 LLAMA_SERVER_YIELD_FAST=2 LLAMA_SPEC_COUPLED=1" $C $C
touch $R/q6.done
