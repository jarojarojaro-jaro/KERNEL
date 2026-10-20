#!/usr/bin/env bash
# ON the box: after q4: nvc tree (GGML_CUDA_MMVQ_RPB) — md5 gates off/RPB=8 (vs nv base), ABBA RPB=8 alone,
# final ABBA T (nvc, all off) vs T' (RPB=8 + LLAMA_SERVER_YIELD_FAST=2 + LLAMA_SPEC_COUPLED=1).
set -uo pipefail
R=/root/results/opt-4070ti-20261020
while [ ! -f $R/q4.done ]; do sleep 10; done
cd /root/cloud; C=/root/src/nvc/b89/bin
TK=$C ./gate.sh nvcoff
TK=$C TENV="GGML_CUDA_MMVQ_RPB=8" ./gate.sh rpb8
./ab.sh rpb8 "" "GGML_CUDA_MMVQ_RPB=8" $C $C
./ab.sh final "" "GGML_CUDA_MMVQ_RPB=8 LLAMA_SERVER_YIELD_FAST=2 LLAMA_SPEC_COUPLED=1" $C $C
TK=$C TENV="GGML_CUDA_MMVQ_RPB=8 LLAMA_SERVER_YIELD_FAST=2 LLAMA_SPEC_COUPLED=1" ./gate.sh tprime
touch $R/q5.done
