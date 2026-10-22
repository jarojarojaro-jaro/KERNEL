#!/usr/bin/env bash
# Final squeeze: host-path knobs (GPU verify top-k, lookup width), concurrency, and the production reference.
set -u
B=/root/w/fork/build/bin
M=/root/models/OrcaCyber-Nano-1.0-AI-Defense-Mix-15.7G.gguf
VOCAB=/root/cloud/draft_vocab_qwen38.txt
PORT=18450
RES=/root/results/$(date +%Y%m%d-%H%M)/final
mkdir -p "$RES"/{logs,sweep,long}
export LD_LIBRARY_PATH=$B
stop() { pkill -9 -f "llama[-]server.*--port $PORT" 2>/dev/null; sleep 2; }
if [ ! -f /root/.orca-cache-warm ]; then dd if="$M" of=/dev/null bs=8M status=none && touch /root/.orca-cache-warm; fi

start() {  # np "ENV=.." [extra args]
    local np=$1 envs=$2; shift 2
    stop
    env LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_GPU_VERIFY=1 LLAMA_SPEC_COUPLED=1 \
        LLAMA_SERVER_YIELD_FAST=2 LLAMA_TOKENIZE_PAR=8 LLAMA_CKPT_VRAM=2 LLAMA_CHAT_NATIVE=0 \
        LLAMA_SERVER_SAFE_SPECIAL=1 LLAMA_SERVER_SAFE_TOOLS=1 GGML_CUDA_KVQ=1 $envs \
        $B/llama-server --host 127.0.0.1 --port $PORT --no-webui -m "$M" -fa on -ctk q4_0 -ctv q4_0 \
        -c 32768 -np "$np" -ngl 999 -fit off --jinja --spec-type draft-mtp --spec-draft-n-max 2 \
        -ctkd q4_0 -ctvd q4_0 --spec-draft-vocab "$VOCAB" --spec-draft-vocab-n 65536 \
        --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs "$@" > "$RES/logs/srv.$$.log" 2>&1 &
    for _ in $(seq 300); do curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1 && return 0; sleep 1; done
    return 1
}

sweep() {  # label envs
    local label=$1 envs=$2
    start 1 "$envs" || { echo "$label: load failed"; return 1; }
    ( cd "$RES/sweep" && python3 /root/cloud/spec_sweep.py --label "$label|fork|mtp2|q4_0|32768" \
        --port $PORT --temps 1.0 --seeds 1,2 ) | tail -1
    stop
}

echo "$(date -u +%T) final squeeze start -> $RES"
sweep base.prod ""
sweep verifyM64 "LLAMA_GPU_VERIFY_M=64"
sweep verifyM32 "LLAMA_GPU_VERIFY_M=32"
sweep lookupW32 "LLAMA_SPEC_LOOKUP_W=32"

start 2 "" && python3 /root/cloud/conc.py --port $PORT --label np2_req2 --requests 2 --tokens 400 --out "$RES/conc.jsonl"; stop
start 4 "" && python3 /root/cloud/conc.py --port $PORT --label np4_req4 --requests 4 --tokens 400 --out "$RES/conc.jsonl"; stop

# production reference at the full context
start 1 "" "-c 262144" || echo "262k load failed"
python3 /root/cloud/orca_measure.py long --port $PORT --label "final.262k.26k" --ctx 262144 --fracs 0.0998 \
    --tokens 64 --out "$RES/long/long.jsonl"
stop
echo "$(date -u +%T) final squeeze done"
