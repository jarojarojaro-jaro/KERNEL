#!/usr/bin/env bash
# Greedy (T=0) outputs of a build, plain and MTP speculative decode, for equality checks. Run under flock.
# usage: greedy.sh BIN_DIR LIB_DIR OUT_PREFIX [MODEL]   (MODEL: qwen | unc | lfm; env MODES, default "plain mtp", lfm: MODES=plain)
set -euo pipefail
bin=$1; lib=$2; out=$3; model=${4:-qwen}
case $model in
    qwen) M=$HOME/models/Qwen3.8-27B-UD-Q4_K_XL.gguf ;;
    unc)  M=$HOME/models/orca/Qwen3.8-27B-Uncensored-Q4_K_M.gguf ;;
    lfm)  M=$HOME/models/lfm/LFM2.5-24B-A2B-Q5_K_M.gguf ;;  # no MTP head: run with MODES=plain
esac
export LD_LIBRARY_PATH=$lib:/opt/rocm/core-10.0/lib
port=18433
prompts=('Explain how a hash map works, then implement one in C with open addressing.'
         'Napisz krótkie opowiadanie o latarniku i sztormie.')
for mode in ${MODES:-plain mtp}; do
    case $mode in
        plain) extra=() ;;
        mtp)   extra=(--spec-type draft-mtp --spec-draft-n-max 4 --spec-draft-vocab "$HOME/models/draft/draft_vocab_qwen38.txt" --spec-draft-vocab-n 65536) ;;
    esac
    "$bin/llama-server" --port $port --host 127.0.0.1 -np 1 --no-webui -m "$M" -ngl 999 -fa on \
        -ctk q4_0 -ctv q4_0 -c 8192 "${extra[@]}" > "$out.$mode.log" 2>&1 &
    pid=$!
    for _ in $(seq 180); do curl -sf http://127.0.0.1:$port/health >/dev/null && break; sleep 1; done
    : > "$out.$mode.txt"
    for p in "${prompts[@]}"; do
        curl -s http://127.0.0.1:$port/v1/chat/completions -H 'Content-Type: application/json' \
            -d "$(jq -n --arg p "$p" '{messages:[{role:"user",content:$p}],max_tokens:400,temperature:0,chat_template_kwargs:{enable_thinking:false}}')" \
            | jq -r '(.choices[0].message.reasoning_content // "") + (.choices[0].message.content // "")' >> "$out.$mode.txt"
    done
    kill $pid; for _ in $(seq 30); do kill -0 $pid 2>/dev/null || break; sleep 1; done; kill -9 $pid 2>/dev/null || true; wait $pid 2>/dev/null || true
done
md5sum "$out".*.txt
