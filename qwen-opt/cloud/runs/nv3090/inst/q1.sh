#!/usr/bin/env bash
# ON the instance: queue 1 (nv-3090, 2026-10-20): wait for the baseline, build pipe (no benchmark during the build),
# then quick gate + ABBA per idea: L2PF (existing switch), OCC=12 (occ build), PIPE=1 (pipe build).
set -uo pipefail
cd /root/cloud
while [ ! -f /root/results/nv3090/logs/base.done ]; do sleep 10; done
./build.sh pipe
./idea.sh l2pf nv0 "" nv0 "GGML_CUDA_MMVQ_L2PF=1"
./idea.sh occ12 occ "" occ "GGML_CUDA_MMVQ_OCC=12"
./idea.sh pipe1 pipe "" pipe "GGML_CUDA_MMVQ_PIPE=1"
touch /root/results/nv3090/logs/q1.done
