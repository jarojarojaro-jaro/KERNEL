#!/usr/bin/env bash
# Long-prompt profile of the production config at the full 262144 context: does a bigger ubatch fit, and how long
# does a 29k / 65k / 131k token prompt take (TTFT) with kvq on.
set -u
B=/root/w/fork/build/bin
M=/root/models/OrcaCyber-Nano-1.0-AI-Defense-Mix-15.7G.gguf
VOCAB=/root/cloud/draft_vocab_qwen38.txt
PORT=18443
RES=/root/results/$(date +%Y%m%d-%H%M)/ttft
mkdir -p "$RES"/{logs,long}
export LD_LIBRARY_PATH=$B
vram() { nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' '; }
stop() { pkill -9 -f "llama[-]server.*--port $PORT" 2>/dev/null; sleep 2; }
if [ ! -f /root/.orca-cache-warm ]; then dd if="$M" of=/dev/null bs=8M status=none && touch /root/.orca-cache-warm; fi

start() {  # ub
    stop
    env LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_GPU_VERIFY=1 LLAMA_SPEC_COUPLED=1 \
        LLAMA_SERVER_YIELD_FAST=2 LLAMA_CKPT_VRAM=2 LLAMA_CHAT_NATIVE=0 \
        LLAMA_SERVER_SAFE_SPECIAL=1 LLAMA_SERVER_SAFE_TOOLS=1 GGML_CUDA_KVQ=1 \
        $B/llama-server --host 127.0.0.1 --port $PORT --no-webui -m "$M" -fa on -ctk q4_0 -ctv q4_0 \
        -c 262144 -np 1 -ngl 999 -fit off --jinja -b "$1" -ub "$1" \
        --spec-type draft-mtp --spec-draft-n-max 2 -ctkd q4_0 -ctvd q4_0 \
        --spec-draft-vocab "$VOCAB" --spec-draft-vocab-n 65536 \
        --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs > "$RES/logs/server.ub$1.log" 2>&1 &
    for _ in $(seq 300); do curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1 && return 0; sleep 1; done
    return 1
}

echo "$(date -u +%T) ttft profile start -> $RES"
for ub in 512 1024 2048; do
    if start "$ub"; then
        echo "ub$ub loaded, VRAM $(vram) MiB"
        printf 'ub%-5s ' "$ub"
        python3 /root/cloud/orca_measure.py long --port $PORT --label "ttft.ub$ub.29k" --ctx 262144 \
            --fracs 0.1116 --tokens 32 --out "$RES/long/long.jsonl"
        stop
    else
        echo "ub$ub LOAD FAILED: $(grep -iE 'failed to allocate|out of memory|error' "$RES/logs/server.ub$ub.log" | tail -1 | cut -c1-120)"
        stop
    fi
done
for frac in 0.25 0.5; do
    if start 512; then
        printf 'ub512 frac%s ' "$frac"
        python3 /root/cloud/orca_measure.py long --port $PORT --label "ttft.ub512.frac$frac" --ctx 262144 \
            --fracs "$frac" --tokens 32 --out "$RES/long/long.jsonl"
        stop
    else
        echo "frac$frac load failed"; stop
    fi
done
echo "$(date -u +%T) ttft profile done"
