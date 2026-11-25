#!/usr/bin/env bash
# GGML_HIP_Q2BW (topka-bw): test-backend-ops of the touched ops (Q2_0 MUL_MAT, MUL_MAT_ADD, MUL_MAT_PAIR,
# FFN_GATE_UP_DOWN, MUL_MAT_VEC_FUSION) vs the CPU backend, for the table's launch and every knob set. Runs ON the box.
# usage: bw-tbo.sh BUILD_BIN VARIANT...   VARIANT: base | NAME=VAL,NAME=VAL (env of one test-backend-ops run)
set -uo pipefail
B=$1; shift
export GGML_HIP_PM4=0 LD_LIBRARY_PATH=$B:/opt/rocm/core-10.0/lib
for v in "$@"; do
  envs=(); [ "$v" != base ] && IFS=, read -ra envs <<< "$v"
  for o in "MUL_MAT,MUL_MAT_ADD,MUL_MAT_PAIR,FFN_GATE_UP_DOWN:type_a=q2_0" "MUL_MAT_VEC_FUSION:type=q2_0"; do
    op=${o%%:*}; p=${o#*:}
    out=$(env "${envs[@]}" taskset -c 2-5 timeout 300 "$B/test-backend-ops" -b ROCm0 -o "$op" -p "$p" 2>&1)
    echo "TBO [$v] $op: $(echo "$out" | grep -E "tests passed" | tail -1 | xargs) fail=$(echo "$out" | grep -c "FAIL")"
    echo "$out" | grep "FAIL" | head -3 | cut -c1-200 | sed 's/^/  /'
  done
done
