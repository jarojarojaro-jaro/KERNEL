#!/usr/bin/env bash
# K-028: xtxbench runtime switch smoke (GGML_HIP_RUNTIME_SWITCH_FILE hook, branch xtxbench d5454e084) on the fresh build
# ~/wt/xtxbench/build-hip (KqBuild 2026-11-24, rbuild --local, llama-server + llama-bench). Ports 18794, taskset -c 2-5.
#   md5     fresh-start greedy gate of the hook build vs production refs (mandatory fresh arm, K-001 state leak)
#   switch  xtxbench t1 on ONE server: A = hook build, B = --var-switch GGML_HIP_MMVQ_PAIR=0 (no restart), production PM4
#           (run-topka.sh uncensored: PM4=1 WA=2 GUARD=1 HSA_USE_SVM=0); decode 1.7k + prefill 4k; flip must be logged
#   bench   llama-bench A B B A production vs hook build (hook off = no cost), PM4=0
set -uo pipefail
K=K-028; B_BIN=$HOME/wt/xtxbench/build-hip/bin; B_LIB=/opt/rocm/core-10.0/lib; B_ROOT=$HOME/wt/xtxbench/build-hip
. "$(dirname "$0")/kqb.sh"; need_build
case ${1:-} in
    md5) export GGML_HIP_PM4=0; unset QUEUE_PM4_SAFETY; md5_gate ;;
    switch)
        need_pass switch
        cd ~/qwen-opt/xtxbench || exit 1
        timeout 840 "$PY" xtxbench.py t1 --label K-028-switch --base "$B_ROOT" --var-switch GGML_HIP_MMVQ_PAIR=0 \
            --snap-compat --t0 none --depths 1700 --prefill 4096
        rc=$?
        d=$(ls -td ~/qwen-opt/xtxbench/runs/*-t1-K-028-switch 2>/dev/null | head -1)
        n=$(cat "$d"/srv-*.log "$d"/srv-*.out 2>/dev/null | grep -c 'ggml_cuda_rt_switch: gen')
        echo "RESULT $K switch: xtxbench rc $rc, run $d, switch flips logged by the server: $n"
        exit $rc ;;
    bench) export GGML_HIP_PM4=0; unset QUEUE_PM4_SAFETY; bench_abba -p 4096 -n 128 -r 2 ;;
    *) echo "usage: $0 md5|switch|bench" >&2; exit 2 ;;
esac
