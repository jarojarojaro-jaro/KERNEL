#!/usr/bin/env bash
# ABBA: production vs LLAMA_SPEC_LOOKUP_W=32 (the only knob that looked positive in final.sh)
set -u
B=/root/w/fork/build/bin
M=/root/models/OrcaCyber-Nano-1.0-AI-Defense-Mix-15.7G.gguf
VOCAB=/root/cloud/draft_vocab_qwen38.txt
PORT=18451
RES=/root/results/$(date +%Y%m%d-%H%M)/abba
mkdir -p "$RES"/{logs,sweep}
export LD_LIBRARY_PATH=$B
stop() { pkill -9 -f "llama[-]server.*--port $PORT" 2>/dev/null; sleep 2; }
start() { local envs=$1; stop
    env LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_GPU_VERIFY=1 LLAMA_SPEC_COUPLED=1 \
        LLAMA_SERVER_YIELD_FAST=2 LLAMA_TOKENIZE_PAR=8 LLAMA_CKPT_VRAM=2 LLAMA_CHAT_NATIVE=0 \
        LLAMA_SERVER_SAFE_SPECIAL=1 LLAMA_SERVER_SAFE_TOOLS=1 GGML_CUDA_KVQ=1 $envs \
        $B/llama-server --host 127.0.0.1 --port $PORT --no-webui -m "$M" -fa on -ctk q4_0 -ctv q4_0 \
        -c 32768 -np 1 -ngl 999 -fit off --jinja --spec-type draft-mtp --spec-draft-n-max 2 \
        -ctkd q4_0 -ctvd q4_0 --spec-draft-vocab "$VOCAB" --spec-draft-vocab-n 65536 \
        --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs > "$RES/logs/srv.log" 2>&1 &
    for _ in $(seq 300); do curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1 && return 0; sleep 1; done
    return 1; }
sweep() { local label=$1 envs=$2; start "$envs" || { echo "$label load failed"; return 1; }
    ( cd "$RES/sweep" && python3 /root/cloud/spec_sweep.py --label "$label|fork|mtp2|q4_0|32768" \
        --port $PORT --temps 1.0 --seeds 1,2 ) | tail -1; stop; }
sweep abba.base1 ""
sweep abba.w32_1 "LLAMA_SPEC_LOOKUP_W=32"
sweep abba.w32_2 "LLAMA_SPEC_LOOKUP_W=32"
sweep abba.base2 ""
echo done
