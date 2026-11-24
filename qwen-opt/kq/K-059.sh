#!/usr/bin/env bash
# K-059: LocalMaxxing reasoning-v1/code-v1 (T=0, 320 tok., thinking on) on the PRODUCTION config, test port 18796, never 8080.
# PM4 rule: run-topka.sh uncensored sets GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0 (see ../k048/srv.sh);
# server and client under taskset -c 2-5. usage: K-059.sh ARM [VAR=value ...]  (fresh: LLAMA_SPEC_LOOKUP=0)
set -u
arm=$1; shift
here=$(cd "$(dirname "$0")" && pwd); . ~/qwen-opt/k048/srv.sh
PORT=18796
out=$here/out; mkdir -p "$out"
~/qwen-opt/l1tok/chat8080.sh stop
trap 'srv_stop nowait' EXIT
srv_start "$out/K-059-$arm" GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0 "$@" || exit 1
timeout 500 taskset -c 2-5 python3 "$here/K-059.py" --port $PORT --arm "$arm" --reps 3 --out "$out/K-059.jsonl"
