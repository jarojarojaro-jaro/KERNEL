#!/usr/bin/env bash
# GGML_HIP_Q2BW full-step microbench (test-mmvq-bw: every Bonsai 2.5 27B matrix of a decode step as its own tensor,
# ~7.2 GB of Q2_0, graphs with the model's fusions): ms/step and GB/s per knob set for the step, the FFN, the
# projections and the vocab head, and bitwise parity of the step's outputs vs the table's launch ("base").
# 1 column (decode) with every knob, 2 and 3 columns (MTP verify) with the knobs they have. Runs ON the box.
# usage: bw-bench.sh BUILD_BIN [ROUNDS]
set -uo pipefail
B=$1 R=${2:-3}
export GGML_HIP_PM4=0 LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib
~/qwen-opt/l1tok/chat8080.sh stop
Q=GGML_HIP_Q2BW=1
N1=(base
    "$Q,GGML_HIP_Q2BW_U=1,GGML_HIP_Q2BW_WPB=1"
    "$Q,GGML_HIP_Q2BW_U=1"
    "$Q"
    "$Q,GGML_HIP_Q2BW_WPB=1"
    "$Q,GGML_HIP_Q2BW_WPB=8"
    "$Q,GGML_HIP_Q2BW_U=4"
    "$Q,GGML_HIP_Q2BW_R=2"
    "$Q,GGML_HIP_Q2BW_U=1,GGML_HIP_Q2BW_R=4"
    "$Q,GGML_HIP_Q2BW_U=4,GGML_HIP_Q2BW_R=2"
    "$Q,GGML_HIP_Q2BW_NT=1"
    "$Q,GGML_HIP_Q2BW_NT=2"
    "$Q,GGML_HIP_Q2BW_NT=3"
    "$Q,GGML_HIP_Q2BW_U=4,GGML_HIP_Q2BW_NT=1"
    "$Q,GGML_HIP_Q2BW_R=2,GGML_HIP_Q2BW_NT=1"
    "$Q,GGML_HIP_Q2BW_W=1"
    "$Q,GGML_HIP_Q2BW_W=1,GGML_HIP_Q2BW_U=4"
    "$Q,GGML_HIP_Q2BW_W=1,GGML_HIP_Q2BW_U=4,GGML_HIP_Q2BW_NT=1")
N3=(base
    "$Q,GGML_HIP_Q2BW_U=1,GGML_HIP_Q2BW_WPB=1"
    "$Q"
    "$Q,GGML_HIP_Q2BW_R=2"
    "$Q,GGML_HIP_Q2BW_U=1,GGML_HIP_Q2BW_R=4"
    "$Q,GGML_HIP_Q2BW_NT=1"
    "$Q,GGML_HIP_Q2BW_R=2,GGML_HIP_Q2BW_NT=1"
    "$Q,GGML_HIP_Q2BW_WPB=8")
echo "== n=1"
taskset -c 2-5 timeout 400 "$B/test-mmvq-bw" -n 1 -r "$R" -i 10 "${N1[@]}" 2>&1 | grep -vE "^ggml_cuda_init|^  Device"
for n in 3 2; do
  echo "== n=$n"
  taskset -c 2-5 timeout 250 "$B/test-mmvq-bw" -n $n -r "$R" -i 10 "${N3[@]}" 2>&1 | grep -vE "^ggml_cuda_init|^  Device"
done
