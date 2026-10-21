#!/usr/bin/env bash
# GGML_CUDA_KVQ A/B on the 3090: kvq-mma reads q4_0 KV directly (whole GQA group in one pass) instead of the vec
# kernel that re-reads KV per Q head. Interleaved to survive the shared-host drift.
set -u
B=/root/w/fork/build/bin
M=/root/models/OrcaCyber-Nano-1.0-AI-Defense-Mix-15.7G.gguf
VOCAB=/root/cloud/draft_vocab_qwen38.txt
PORT=18435
RES=$(ls -d /root/results/*/kernel-3090 2>/dev/null | tail -1)
[ -n "$RES" ] || RES=/root/results/kvq
mkdir -p "$RES"/{logs,long}
stop() { pkill -9 -f "llama[-]server.*--port $PORT" 2>/dev/null; sleep 2; }

start() {  # kvq ctx n [extra args...]
    local kvq=$1 ctx=$2 n=$3; shift 3
    stop
    env LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_GPU_VERIFY=1 LLAMA_SPEC_COUPLED=1 \
        LLAMA_SERVER_YIELD_FAST=2 LLAMA_CKPT_VRAM=2 LLAMA_CHAT_NATIVE=0 \
        LLAMA_SERVER_SAFE_SPECIAL=1 LLAMA_SERVER_SAFE_TOOLS=1 GGML_CUDA_KVQ=$kvq \
        $B/llama-server --host 127.0.0.1 --port $PORT --no-webui -m "$M" -fa on -ctk q4_0 -ctv q4_0 \
        -c "$ctx" -np 1 -ngl 999 -fit off --jinja --spec-type draft-mtp --spec-draft-n-max "$n" \
        -ctkd q4_0 -ctvd q4_0 --spec-draft-vocab "$VOCAB" --spec-draft-vocab-n 65536 \
        --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs "$@" > "$RES/logs/kvq$kvq.$ctx.n$n.log" 2>&1 &
    for _ in $(seq 300); do curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1 && return 0; sleep 1; done
    return 1
}

depth() {  # kvq label
    local kvq=$1 label=$2
    start "$kvq" 32768 2 || { echo "$label: load failed"; return 1; }
    python3 /root/cloud/orca_measure.py long --port $PORT --label "$label" --ctx 32768 \
        --fracs 0.8 --tokens 64 --out "$RES/long/long.jsonl"
    stop
}

sweep() {  # kvq label
    local kvq=$1 label=$2
    start "$kvq" 32768 2 || { echo "$label: load failed"; return 1; }
    ( cd "$RES/sweep" && python3 /root/cloud/spec_sweep.py --label "$label|fork|mtp2|q4_0|32768" \
        --port $PORT --temps 1.0 --seeds 1,2 ) | tail -1
    stop
}

md5() {  # kvq label
    local kvq=$1 label=$2
    start "$kvq" 8192 2 || { echo "$label: load failed"; return 1; }
    h=$(python3 /root/cloud/orca_measure.py md5 --port $PORT --label "$label" --out "$RES/logs/$label.txt" | tail -1)
    echo "md5 $label = $h"
    printf '%s\t%s\n' "$label" "$h" >> "$RES/md5-kvq.tsv"
    stop
}

# the model is mmap'd: a cold page cache turns the first prefill into a 15.7 GB disk read (measured 0.4-1.1 tok/s)
if [ ! -f /root/.orca-cache-warm ]; then
    echo "$(date -u +%T) warming page cache (15.7 GB)"
    dd if="$M" of=/dev/null bs=8M status=none && touch /root/.orca-cache-warm
fi
echo "$(date -u +%T) kvq A/B start -> $RES"
depth 1 kvq1_depth29k
depth 0 kvq0_depth29k
depth 1 kvq1_depth29k_b
depth 0 kvq0_depth29k_b
sweep 1 kvq1_sweep32k
sweep 0 kvq0_sweep32k
md5 1 kvq1_md5
md5 0 kvq0_md5
echo "$(date -u +%T) kvq A/B done"
