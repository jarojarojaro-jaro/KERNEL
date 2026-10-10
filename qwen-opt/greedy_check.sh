#!/usr/bin/env bash
# Greedy (temp 0) output of a build, plain decode and MTP/DFlash speculative decode, for equivalence checks.
# usage: greedy_check.sh BIN_DIR LIB_DIR OUT_PREFIX
set -euo pipefail
bin=$1; lib=$2; out=$3
export LD_LIBRARY_PATH=$lib:/opt/rocm/core-10.0/lib
M=~/models/Qwen3.8-27B-UD-Q4_K_XL.gguf
D=~/models/draft/Qwen3.8-27B-DFlash2-Q4_K_M.gguf
prompt='Explain how a hash map works, then implement one in C with open addressing.'
for mode in plain mtp dflash; do
    case $mode in
        plain)  extra=() ;;
        mtp)    extra=(--spec-type draft-mtp --spec-draft-n-max 4) ;;
        dflash) extra=(-md "$D" -ngld 99 --spec-type draft-dflash --spec-draft-n-max 6) ;;
    esac
    "$bin/llama-server" --port 8097 --host 127.0.0.1 -np 1 --no-webui -m "$M" -ngl 999 -fa on \
        -ctk q4_0 -ctv q4_0 -c 8192 "${extra[@]}" > "$out.$mode.log" 2>&1 &
    pid=$!
    for _ in $(seq 180); do curl -sf http://127.0.0.1:8097/health >/dev/null && break; sleep 1; done
    curl -s http://127.0.0.1:8097/v1/chat/completions -H 'Content-Type: application/json' \
        -d "$(jq -n --arg p "$prompt" '{messages:[{role:"user",content:$p}],max_tokens:400,temperature:0,chat_template_kwargs:{enable_thinking:false}}')" \
        | jq -r '.choices[0].message.content' > "$out.$mode.txt"
    kill $pid; wait $pid 2>/dev/null || true
done
md5sum "$out".*.txt
