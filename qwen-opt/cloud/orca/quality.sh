#!/usr/bin/env bash
# Quality gate for GGML_CUDA_KVQ on Orca + prefill (MMQ) probes, on the rented 3090.
#   1. capture top-20 next-token distributions with kvq=0 and kvq=1 at ctx 8192, compare KL and top-1 agreement
#   2. llama-bench prefill probes: ubatch 512/1024/2048, FORCE_MMQ 0/1 (pp2048)
set -u
B=/root/w/fork/build/bin
M=/root/models/OrcaCyber-Nano-1.0-AI-Defense-Mix-15.7G.gguf
VOCAB=/root/cloud/draft_vocab_qwen38.txt
PORT=18440
RES=/root/results/$(date +%Y%m%d-%H%M)/kvq-quality
mkdir -p "$RES"/{logs,lb}
export LD_LIBRARY_PATH=$B
val=${1:-all}

stop() { pkill -9 -f "llama[-]server.*--port $PORT" 2>/dev/null; sleep 2; }
start() {  # kvq
    stop
    env LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_GPU_VERIFY=1 LLAMA_SPEC_COUPLED=1 \
        LLAMA_SERVER_YIELD_FAST=2 LLAMA_CKPT_VRAM=2 LLAMA_CHAT_NATIVE=0 \
        LLAMA_SERVER_SAFE_SPECIAL=1 LLAMA_SERVER_SAFE_TOOLS=1 GGML_CUDA_KVQ=$1 \
        $B/llama-server --host 127.0.0.1 --port $PORT --no-webui -m "$M" -fa on -ctk q4_0 -ctv q4_0 \
        -c 8192 -np 1 -ngl 999 -fit off --jinja --spec-type draft-mtp --spec-draft-n-max 2 \
        -ctkd q4_0 -ctvd q4_0 --spec-draft-vocab "$VOCAB" --spec-draft-vocab-n 65536 \
        --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs > "$RES/logs/kl.kvq$1.log" 2>&1 &
    for _ in $(seq 300); do curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1 && return 0; sleep 1; done
    return 1
}

if [[ " $val " == *" all "* || " $val " == *" quality "* ]]; then
    if [ ! -f /root/.orca-cache-warm ]; then dd if="$M" of=/dev/null bs=8M status=none && touch /root/.orca-cache-warm; fi
    start 0 && python3 /root/cloud/kl.py capture --port $PORT --out "$RES/kl_vec.json" --tokens 64 --nprobs 20
    start 1 && python3 /root/cloud/kl.py capture --port $PORT --out "$RES/kl_kvq.json" --tokens 64 --nprobs 20
    python3 /root/cloud/kl.py compare --a "$RES/kl_vec.json" --b "$RES/kl_kvq.json"
    stop
fi

if [[ " $val " == *" all "* || " $val " == *" prefill "* ]]; then
    for ub in 512 1024 2048; do
        $B/llama-bench -m "$M" -p 2048 -n 0 -r 3 -fa on -ctk q4_0 -ctv q4_0 -ngl 999 -ub $ub -o jsonl \
            > "$RES/lb/ub$ub.jsonl" 2> "$RES/logs/lb.ub$ub.log"
        printf 'ub%-5s ' "$ub"; python3 -c "
import json
r=[json.loads(l) for l in open('$RES/lb/ub$ub.jsonl')]
print('pp2048=%.0f t/s' % r[0]['avg_ts'])
"
    done
    for fm in 0 1; do
        GGML_CUDA_FORCE_MMQ=$fm $B/llama-bench -m "$M" -p 2048 -n 0 -r 3 -fa on -ctk q4_0 -ctv q4_0 -ngl 999 \
            -o jsonl > "$RES/lb/mmq$fm.jsonl" 2> "$RES/logs/lb.mmq$fm.log"
        printf 'FORCE_MMQ=%s ' "$fm"; python3 -c "
import json
r=[json.loads(l) for l in open('$RES/lb/mmq$fm.jsonl')]
print('pp2048=%.0f t/s' % r[0]['avg_ts'])
"
    done
fi
echo "done -> $RES"
