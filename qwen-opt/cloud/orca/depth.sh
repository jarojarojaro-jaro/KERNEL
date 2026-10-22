#!/usr/bin/env bash
# Depth profile at the production ctx (262144, KV q4_0): drafter length vs depth, then TTFT at 65k/131k prompts.
set -u
B=/root/w/fork/build/bin
M=/root/models/OrcaCyber-Nano-1.0-AI-Defense-Mix-15.7G.gguf
VOCAB=/root/cloud/draft_vocab_qwen38.txt
PORT=18434
RES=$(ls -d /root/results/*/kernel-3090 2>/dev/null | tail -1)
[ -n "$RES" ] || RES=/root/results/depth
mkdir -p "$RES"/{logs,long}
stop() { pkill -9 -f "llama[-]server.*--port $PORT" 2>/dev/null; sleep 2; }
start() {  # n ctx
    stop
    env LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_GPU_VERIFY=1 LLAMA_SPEC_COUPLED=1 \
        LLAMA_SERVER_YIELD_FAST=2 LLAMA_CKPT_VRAM=2 LLAMA_CHAT_NATIVE=0 \
        LLAMA_SERVER_SAFE_SPECIAL=1 LLAMA_SERVER_SAFE_TOOLS=1 \
        $B/llama-server --host 127.0.0.1 --port $PORT --no-webui -m "$M" -fa on -ctk q4_0 -ctv q4_0 \
        -c "$2" -np 1 -ngl 999 -fit off --jinja --spec-type draft-mtp --spec-draft-n-max "$1" \
        -ctkd q4_0 -ctvd q4_0 --spec-draft-vocab "$VOCAB" --spec-draft-vocab-n 65536 \
        --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs > "$RES/logs/depth.n$1.$2.log" 2>&1 &
    for _ in $(seq 300); do curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1 && return 0; sleep 1; done
    return 1
}

for n in 1 2 3; do
    start "$n" 262144 || { echo "n=$n load failed"; continue; }
    python3 /root/cloud/orca_measure.py long --port $PORT --label "depth.n$n.q4_0.262k" --ctx 262144 \
        --fracs 0.125 --tokens 64 --out "$RES/long/long.jsonl"
done

for frac in 0.25 0.5; do
    start 2 262144 || { echo "frac=$frac load failed"; continue; }
    python3 /root/cloud/orca_measure.py long --port $PORT --label "depth.n2.q4_0.262k.frac$frac" --ctx 262144 \
        --fracs "$frac" --tokens 64 --out "$RES/long/long.jsonl"
done
stop
echo "depth done -> $RES"
