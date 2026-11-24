#!/usr/bin/env bash
# K-040: topka-q70 (3191b25f4, = production ~/llama-topka) rebuilt with CMAKE_HIP_FLAGS
# "-mllvm --amdgpu-unroll-threshold-local=600" in ~/wt/k040-unroll/build-hip (KqBuild 2026-11-24, ROCm 10.0 as production).
# Run ONLY if the ISA of the hot kernels changed (isadiff in /tmp/kq/build-results.md). PM4=0 both arms. Port 18794,
# taskset -c 2-5.   usage: K-040.sh md5|bench   (bench = llama-bench -p 4096 -n 128 -r 3, A B B A, KV q4_0)
set -uo pipefail
K=K-040; B_BIN=$HOME/wt/k040-unroll/build-hip/bin; B_LIB=/opt/rocm/core-10.0/lib; B_ROOT=$HOME/wt/k040-unroll/build-hip
export GGML_HIP_PM4=0; unset QUEUE_PM4_SAFETY
. "$(dirname "$0")/kqb.sh"; need_build
case ${1:-} in
    md5) md5_gate ;;
    bench) bench_abba -p 4096 -n 128 -r 3 ;;
    *) echo "usage: $0 md5|bench" >&2; exit 2 ;;
esac
