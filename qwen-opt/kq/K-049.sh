#!/usr/bin/env bash
# K-049: topka-q70 (3191b25f4, = production ~/llama-topka) built with ROCm 10.1 (~/opt/rocm-10.1, AMD clang 24) and run on
# the 10.1 runtime, vs production (ROCm 10.0). Build ~/wt/k049-rocm101/build-hip (KqBuild 2026-11-24, cpuheavy -j2);
# ROCM_DIR for run-topka.sh/xtxbench = ~/kqbuild/inst/K-049 (bin -> that build, lib -> ~/opt/rocm-10.1/lib).
# PM4 rule: new runtime -> GGML_HIP_PM4=0 in every arm (A too, so the A/B is fair). Ports 18794, taskset -c 2-5.
# usage: K-049.sh md5|xtx      (md5 = fresh greedy gate vs production refs; xtx = xtxbench t1 decode 1.7k + prefill 32k)
set -uo pipefail
K=K-049; B_BIN=$HOME/wt/k049-rocm101/build-hip/bin; B_LIB=$HOME/opt/rocm-10.1/lib; B_ROOT=$HOME/kqbuild/inst/K-049
export GGML_HIP_PM4=0; unset QUEUE_PM4_SAFETY
. "$(dirname "$0")/kqb.sh"; need_build
case ${1:-} in
    md5) md5_gate ;;
    xtx) xtx_ab --prefill 32768 ;;
    *) echo "usage: $0 md5|xtx" >&2; exit 2 ;;
esac
