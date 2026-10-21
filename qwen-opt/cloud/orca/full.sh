#!/usr/bin/env bash
# Short-context A/B of kvq at full GPU power + serving concurrency, on the rented 3090.
set -u
B=/root/w/fork/build/bin
M=/root/models/OrcaCyber-Nano-1.0-AI-Defense-Mix-15.7G.gguf
VOCAB=/root/cloud/draft_vocab_qwen38.txt
PORT=18437
RES=/root/results/$(date +%Y%m%d-%H%M)/all-3090
mkdir -p "$RES"/{logs,sweep}
stop() { pkill -9 -f "llama[-]server.*--port $PORT" 2>/dev/null; sleep 2; }

start() {  # kvq np
    stop
    env LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_GPU_VERIFY=1 LLAMA_SPEC_COUPLED=1 \
        LLAMA_SERVER_YIELD_FAST=2 LLAMA_CKPT_VRAM=2 LLAMA_CHAT_NATIVE=0 \
        LLAMA_SERVER_SAFE_SPECIAL=1 LLAMA_SERVER_SAFE_TOOLS=1 GGML_CUDA_KVQ=$1 \
        $B/llama-server --host 127.0.0.1 --port $PORT --no-webui -m "$M" -fa on -ctk q4_0 -ctv q4_0 \
        -c 32768 -np "$2" -ngl 999 -fit off --jinja --spec-type draft-mtp --spec-draft-n-max 2 \
        -ctkd q4_0 -ctvd q4_0 --spec-draft-vocab "$VOCAB" --spec-draft-vocab-n 65536 \
        --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs > "$RES/logs/srv.kvq$1.np$2.log" 2>&1 &
    for _ in $(seq 300); do curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1 && return 0; sleep 1; done
    return 1
}

if [ ! -f /root/.orca-cache-warm ]; then dd if="$M" of=/dev/null bs=8M status=none && touch /root/.orca-cache-warm; fi

for kvq in 1 0; do
    start "$kvq" 1 || { echo "kvq$kvq load failed"; continue; }
    ( cd "$RES/sweep" && python3 /root/cloud/spec_sweep.py --label "all.kvq$kvq.sweep32k|fork|mtp2|q4_0|32768" \
        --port $PORT --temps 1.0 --seeds 1,2 ) | tail -1
    stop
done

start 1 1 && python3 /root/cloud/conc.py --port $PORT --label np1_req1 --requests 1 --tokens 400 --out "$RES/conc.jsonl"; stop
start 1 2 && python3 /root/cloud/conc.py --port $PORT --label np2_req2 --requests 2 --tokens 400 --out "$RES/conc.jsonl"; stop
echo "done -> $RES"
