#!/usr/bin/env bash
# K-130: topka-q70 (3191b25f4, = production ~/llama-topka) built with ROCm 10.2 (TheRock gfx110X 10.2.0 tarball in
# ~/rocm-10.2; /opt/rocm untouched) and run on the 10.2 runtime, vs production (ROCm 10.0). Build ~/wt/k130-rocm102/build-hip
# (KqBuild 2026-11-24); ROCM_DIR = ~/kqbuild/inst/K-130 (bin -> that build, lib -> ~/rocm-10.2/lib).
# PM4 rule: GGML_HIP_PM4=0 in every arm (item: "PM4=0 w teście"). Port 18794, taskset -c 2-5. Acceptance threshold >= 3%.
# usage: K-130.sh md5|tbo|xtx   (tbo = test-backend-ops MUL_MAT + FLASH_ATTN_EXT hsk=256 vs CPU on the 10.2 build)
set -uo pipefail
K=K-130; B_BIN=$HOME/wt/k130-rocm102/build-hip/bin; B_LIB=$HOME/rocm-10.2/lib; B_ROOT=$HOME/kqbuild/inst/K-130
export GGML_HIP_PM4=0; unset QUEUE_PM4_SAFETY
. "$(dirname "$0")/kqb.sh"; need_build
case ${1:-} in
    md5) md5_gate ;;
    tbo)
        need_pass tbo
        ~/qwen-opt/l1tok/chat8080.sh stop
        for spec in "MUL_MAT|" "FLASH_ATTN_EXT|hsk=256"; do
            op=${spec%%|*}; p=${spec#*|}; f=$OUT/$K-tbo-$op.txt
            LD_LIBRARY_PATH=$B_BIN:$B_LIB timeout 200 taskset -c 2-5 "$B_BIN/test-backend-ops" -b ROCm0 -o "$op" ${p:+-p "$p"} > "$f" 2>&1
            rc=$?
            echo "RESULT $K tbo $op${p:+ [$p]}: rc $rc, $(grep -Eo '[0-9]+/[0-9]+ tests passed' "$f" | tail -1), FAIL lines $(grep -c ': FAIL' "$f")"
        done ;;
    xtx) xtx_ab --prefill 32768 ;;
    *) echo "usage: $0 md5|tbo|xtx" >&2; exit 2 ;;
esac
