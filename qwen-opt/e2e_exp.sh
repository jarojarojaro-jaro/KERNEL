#!/usr/bin/env bash
# One end-to-end experiment: write tuning macros, rebuild ggml-hip, serve-bench DFlash and MTP.
# usage: e2e_exp.sh LABEL "MACRO=VAL ..." [runs per prompt]
set -euo pipefail
label=$1; macros=$2; runs=${3:-3}
L=~/llama-master
inc=$L/ggml/src/ggml-cuda/mmvq-tune.inc
: > "$inc"
for m in $macros; do echo "#define ${m%%=*} ${m#*=}" >> "$inc"; done
export PATH=/opt/rocm/core-10.0/bin:$PATH
cmake --build $L/build-hip --target ggml-hip -j16 2>&1 | grep -E ' error' -A3 | head -20 || true
cd ~/qwen-opt
M=~/models/Qwen3.8-27B-UD-Q4_K_XL.gguf
D=~/models/draft/Qwen3.8-27B-DFlash2-Q4_K_M.gguf
B=$L/build-hip/bin/llama-server
show='import json,sys;d=json.loads(sys.stdin.read());print(d["label"],d["decode_tps"],d["per_prompt_decode"],d["draft_acceptance"])'
.venv/bin/python serve_bench.py --runs "$runs" --label "$label-dflash6" --bin $B -- -m $M -md $D -ngld 99 -ngl 999 -fa on \
    -ctk q4_0 -ctv q4_0 -c 131072 --spec-type draft-dflash --spec-draft-n-max 6 | python3 -c "$show"
.venv/bin/python serve_bench.py --runs "$runs" --label "$label-mtp4" --bin $B -- -m $M -ngl 999 -fa on \
    -ctk q4_0 -ctv q4_0 -c 131072 --spec-type draft-mtp --spec-draft-n-max 4 | python3 -c "$show"
