#!/usr/bin/env bash
# R69b Q1 phases ON the box:  run.sh fork|warp|warpdef|forkre   (logs -> /root/res/logs, rows -> /root/res/bench.jsonl)
#   fork    our enigma-cuda-fork (published kvqleana + b12110 cudart), SITE-NVIDIA §4 flags, -c 262144: all blocks
#   warp    qwen-warp v0.8.0 --profile long --max-model-len 262144 (int4 KV + host tables, MTP k3 + lookup tail): all blocks
#   warpdef qwen-warp default profile (bf16 KV, tables on GPU, max-model-len 20480): short + 16k (their 155 t/s headline)
#   forkre  fork again, short only (drift check, same session)
set -uo pipefail
RES=/root/res; M=/root/models; F=/root/fork; W=/root/qwen-warp
mkdir -p "$RES/logs"
phase=$1
BLOCKS_ALL=${BLOCKS_ALL:-"short depth:15872 depth:65024 depth:130560 depth:261444 prefill:16000"}
log() { echo "=== $(date +%T) $*"; }
pgrep -f 'nvidia-smi --query-gpu=timestamp' > /dev/null || nohup nvidia-smi \
    --query-gpu=timestamp,memory.used,power.draw,power.limit,temperature.gpu,clocks.sm,clocks.mem,utilization.gpu \
    --format=csv,noheader -l 1 >> "$RES/smi.csv" 2>&1 < /dev/null &

wait_health() {  # port pid timeout
    for _ in $(seq "$3"); do
        kill -0 "$2" 2> /dev/null || { log "server died"; return 1; }
        curl -fs "http://127.0.0.1:$1/health" > /dev/null && return 0
        sleep 1
    done
    return 1
}
stop() { kill "$1" 2> /dev/null; for _ in $(seq 60); do kill -0 "$1" 2> /dev/null || break; sleep 1; done; kill -9 "$1" 2> /dev/null; sleep 3; }

fork() {  # label blocks...
    local label=$1; shift
    local bin; bin=$(cat "$F/.bindir")
    echo "$label start $(date +%s)" >> "$RES/phases.txt"
    env LD_LIBRARY_PATH="$bin" GGML_CUDA_KVQ=1 LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_GPU_VERIFY=1 \
        LLAMA_SERVER_CACHE_SHARE_MIN=1024 LLAMA_SERVER_REASONING_CONTROL=0 \
        "$bin/llama-server" -m "$M/Qwen3.8-27B-UD-Q4_K_XL.gguf" -c 262144 -ngl 999 -fa on -ctk q4_0 -ctv q4_0 \
        -b 2048 -ub 256 -np 1 --alias enigma-test --jinja --spec-type draft-mtp --spec-draft-n-max 4 -ctkd q4_0 -ctvd q4_0 \
        --spec-draft-vocab "$F/draft_vocab_qwen38.txt" --spec-draft-vocab-n 65536 --spec-draft-head-type iq4_xs \
        --spec-mtp-type iq4_xs --host 127.0.0.1 --port 8080 --no-webui > "$RES/logs/$label.log" 2>&1 < /dev/null &
    local pid=$!
    wait_health 8080 $pid 900 || { log "$label not healthy"; tail -20 "$RES/logs/$label.log"; stop $pid; return 1; }
    log "$label ready, vram $(nvidia-smi --query-gpu=memory.used --format=csv,noheader)"
    nvidia-smi --query-gpu=memory.used --format=csv,noheader > "$RES/logs/$label.vram-load"
    TOKENIZE_PORT=8080 python3 /root/nv/bench.py "$label" 8080 enigma-test "$@" 2>&1 | tee -a "$RES/logs/$label.bench.log"
    stop $pid
    echo "$label end $(date +%s)" >> "$RES/phases.txt"
}

warp() {  # label "serve flags" blocks...
    local label=$1 flags=$2; shift 2
    echo "$label start $(date +%s)" >> "$RES/phases.txt"
    # shellcheck disable=SC2086
    (cd "$W" && exec env SWIFT_MODEL="$M/swift" HF_HUB_OFFLINE=1 .venv/bin/python server/serve.py --model "$M/swift" \
        --host 127.0.0.1 --port 8000 --vision off $flags) > "$RES/logs/$label.log" 2>&1 < /dev/null &
    local pid=$!
    wait_health 8000 $pid 1800 || { log "$label not healthy"; tail -30 "$RES/logs/$label.log"; stop $pid; pkill -f server/serve.py; return 1; }
    log "$label ready, vram $(nvidia-smi --query-gpu=memory.used --format=csv,noheader)"
    nvidia-smi --query-gpu=memory.used --format=csv,noheader > "$RES/logs/$label.vram-load"
    python3 /root/nv/bench.py "$label" 8000 swift "$@" 2>&1 | tee -a "$RES/logs/$label.bench.log"
    stop $pid; pkill -f server/serve.py; sleep 3
    echo "$label end $(date +%s)" >> "$RES/phases.txt"
}

case $phase in
    fork)    fork F262k $BLOCKS_ALL ;;
    warp)    warp W262k "--profile long --max-model-len 262144" $BLOCKS_ALL ;;
    warpdef) warp Wdef "--max-model-len 20480" short depth:15872 ;;
    forkre)  fork F262k-re short ;;
    *) echo "usage: run.sh fork|warp|warpdef|forkre"; exit 2 ;;
esac
