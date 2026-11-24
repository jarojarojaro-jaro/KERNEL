#!/usr/bin/env bash
# K-052: HRX (Lemonade hrx-b99 = ROCm/ggml-staging-automation tag hrx-b99 5fd7b14e: hrx-system 32b86d42 + AMD-Ecosystem
# llama.cpp hrx-graph-develop-v2 2ba2ddc7) as a kernel reference next to topka. Built by KqBuild 2026-11-24 in ~/hrx-b99
# (build_all.py --skip-fetch, ROCm root ~/opt/rocm-10.1, gfx1100; install ~/hrx-b99/build/llama.cpp-install).
# HRX has its own runtime (no ROCr queue, no gpu-guard): unknown card risk. KV f16 in both arms (HRX KV q4_0 support
# unknown), production model Qwen3.8-27B-Uncensored Q4_K_M, plain (no MTP). topka arm PM4=0. Port 18794, taskset -c 2-5.
#   smoke   HRX llama-server greedy T=0 plain (fusion/greedy.sh MODES=plain KV=f16): loads + non-empty text -> gate;
#           the md5 is informational only (another engine: equality with topka is not expected)
#   bench   llama-bench -fa 1 -p 512,4096 -n 128 -r 3, A = topka (production) B = HRX, A B B A
set -uo pipefail
K=K-052; B_BIN=$HOME/hrx-b99/build/llama.cpp-install/bin; B_LIB=$HOME/hrx-b99/build/llama.cpp-install/lib; B_ROOT=
export GGML_HIP_PM4=0 KVARGS="-ctk f16 -ctv f16"; unset QUEUE_PM4_SAFETY
. "$(dirname "$0")/kqb.sh"; need_build
case ${1:-} in
    smoke)
        rm -f "$OUT/$K.md5.PASS"
        ~/qwen-opt/l1tok/chat8080.sh stop
        ~/qwen-opt/lookup/vram_ok.sh || { echo "$K smoke: VRAM busy"; exit 1; }
        MODES=plain KV=f16 PORT=18794 timeout 400 taskset -c 2-5 ~/qwen-opt/fusion/greedy.sh "$B_BIN" "$B_LIB" "$OUT/$K-smoke" qwen > /dev/null
        f=$OUT/$K-smoke.plain.txt
        if [ -s "$f" ]; then touch "$OUT/$K.md5.PASS"; echo "RESULT $K smoke: OK, $(wc -w < "$f") words, md5 $(md5sum < "$f" | cut -c1-8) (informational)"
        else echo "RESULT $K smoke: FAIL (no text; see $OUT/$K-smoke.plain.log)"; tail -20 "$OUT/$K-smoke.plain.log"; exit 1; fi ;;
    bench) bench_abba -p 512,4096 -n 128 -r 3 ;;
    *) echo "usage: $0 smoke|bench" >&2; exit 2 ;;
esac
