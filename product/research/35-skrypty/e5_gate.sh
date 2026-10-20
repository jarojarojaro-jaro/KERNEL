#!/usr/bin/env bash
# Report 35 E5 gate of ~/wt/bxadapt (topka + adapt-spec a69537d37 + batch-invariant c09ac6aab..365af3e5e):
#   1. test-backend-ops MUL_MAT + FLASH_ATTN_EXT with LLAMA_SPEC_BITEXACT=1 (the env-gated kernels)
#   2. switches off: greedy md5 = topka (plain c4708318, MTP 6f14e814)
#   3. LLAMA_SPEC_BITEXACT=1: plain == MTP n=4 == MTP + LLAMA_SPEC_DEPTH_ADAPT=1 (twice) == the same with GPU verify off
# PASS -> /tmp/x35/E5_PASS (the A/B jobs need it). Run ONLY from the GPU queue.
set -uo pipefail
bd=${BD:-$HOME/wt/bxadapt/build-hip}/bin
export GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0 LLAMA_GPU_VERIFY=1 PORT=18723
export LD_LIBRARY_PATH="$bd:/opt/rocm/core-10.0/lib"
trap 'pkill -f "$bd/llama-server" || true' EXIT
trap 'exit 1' TERM INT
pkill -f 'llama-topka/bin/llama-server' && sleep 5
"$HOME/qwen-opt/lookup/vram_ok.sh" || exit 1
mkdir -p /tmp/x35 && rm -f /tmp/x35/E5_PASS /tmp/x35/bx-*.txt
rc=0
for op in MUL_MAT FLASH_ATTN_EXT; do
    LLAMA_SPEC_BITEXACT=1 timeout 300 taskset -c 2-5 "$bd/test-backend-ops" -o $op > /tmp/x35/tbo-$op.log 2>&1
    r=$?; echo "test-backend-ops $op (BITEXACT=1): rc=$r $(grep -E 'tests passed|Backend .*: (OK|FAIL)' /tmp/x35/tbo-$op.log | tail -2 | tr '\n' ' ')"
    [ $r = 0 ] || rc=1
done
g() { local tag=$1; shift; env "$@" taskset -c 2-5 "$HOME/qwen-opt/fusion/greedy.sh" "$bd" "$bd" "/tmp/x35/bx-$tag" qwen > /dev/null 2>&1; }
g off
g bx LLAMA_SPEC_BITEXACT=1
g bxad1 MODES=mtp LLAMA_SPEC_BITEXACT=1 LLAMA_SPEC_DEPTH_ADAPT=1
g bxad2 MODES=mtp LLAMA_SPEC_BITEXACT=1 LLAMA_SPEC_DEPTH_ADAPT=1
g bxadgv0 MODES=mtp LLAMA_SPEC_BITEXACT=1 LLAMA_SPEC_DEPTH_ADAPT=1 LLAMA_GPU_VERIFY=0
for f in /tmp/x35/bx-*.txt; do echo "$(md5sum < "$f" | cut -c1-8) $(basename "$f") $(wc -c < "$f") B"; done
m() { md5sum < "/tmp/x35/bx-$1.txt" | cut -c1-8; }
[ "$(m off.plain)" = c4708318 ] && [ "$(m off.mtp)" = 6f14e814 ] && echo "switches off = topka" || { echo "switches off != topka"; rc=1; }
ref=$(m bx.plain)
for t in bx.mtp bxad1.mtp bxad2.mtp bxadgv0.mtp; do
    [ "$(m $t)" = "$ref" ] && echo "$t == bitexact plain ($ref)" || { echo "$t $(m $t) != bitexact plain $ref"; rc=1; }
done
grep -h "draft depth from acceptance" /tmp/x35/bx-bxad1.mtp.log | head -1
[ $rc = 0 ] && touch /tmp/x35/E5_PASS && echo "E5 gate PASS"
exit $rc
