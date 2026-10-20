#!/usr/bin/env bash
# ON the box: bld.sh <tree> [targets...] — Release CUDA build of /root/src/<tree> into /root/src/<tree>/b89,
# sm_89 only, GGML_NATIVE (host CPU), ccache, -j = cgroup CPU quota (else nproc). Never run while a benchmark runs.
set -uo pipefail
t=$1; shift
targets=("$@"); [ ${#targets[@]} -gt 0 ] || targets=(llama-server llama-bench test-backend-ops)
S=/root/src; RES=/root/results/opt-4070ti-20261020
quota=$(awk '$1 != "max" { printf "%d", $1 / $2 }' /sys/fs/cgroup/cpu.max 2>/dev/null || true)
jobs=$(nproc); [ -n "$quota" ] && [ "$quota" -gt 0 ] && [ "$quota" -lt "$jobs" ] && jobs=$quota
export CCACHE_DIR=/root/.ccache CCACHE_BASEDIR=$S CCACHE_NOHASHDIR=true CCACHE_MAXSIZE=20G
t0=$(date +%s)
[ -f $S/$t/b89/build.ninja ] || cmake -S $S/$t -B $S/$t/b89 -G Ninja -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON \
    -DCMAKE_CUDA_ARCHITECTURES=89 -DGGML_NATIVE=ON -DLLAMA_BUILD_TESTS=ON -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_CURL=OFF \
    -DCMAKE_C_COMPILER_LAUNCHER=ccache -DCMAKE_CXX_COMPILER_LAUNCHER=ccache -DCMAKE_CUDA_COMPILER_LAUNCHER=ccache \
    > "$RES/build/$t.cfg.log" 2>&1
cmake --build $S/$t/b89 -j "$jobs" --target "${targets[@]}" >> "$RES/build/$t.build.log" 2>&1
rc=$?
printf '{"tree":"%s","jobs":%d,"seconds":%d,"rc":%d,"t":"%s"}\n' "$t" "$jobs" "$(( $(date +%s) - t0 ))" $rc "$(date +%T)" \
    | tee -a "$RES/build/times.jsonl"
exit $rc
