#!/usr/bin/env bash
# Post-campaign fillers (run by the watcher after orca.sh exits, only while the deadline allows):
#   1) upstream + MTP (the main run skips it: spec_args returned non-zero for a base tree),
#   2) depth profile at the ideal ctx 262144 with the production config: fracs 0.25 / 0.5,
#   3) KV slope: load VRAM at 32k/64k/128k/256k ctx (no generation) if time is left.
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
W=/root/w; MODELS=/root/models
RES=$(ls -d /root/results/*/orca-3090 2>/dev/null | tail -1)
PORT=18434
BASE=$W/base/build/bin
FORK=$W/fork/build/bin
M=$MODELS/OrcaCyber-Nano-1.0-AI-Defense-Mix-15.7G.gguf
VOCAB=$HERE/draft_vocab_qwen38.txt
FORK_ENV="LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_SERVER_CACHE_SHARE_MIN=1024 \
LLAMA_GPU_VERIFY=1 LLAMA_SPEC_COUPLED=1 LLAMA_SERVER_YIELD_FAST=2 LLAMA_TOKENIZE_PAR=8 \
LLAMA_CKPT_VRAM=2 LLAMA_CHAT_NATIVE=0 LLAMA_SERVER_SAFE_SPECIAL=1 LLAMA_SERVER_SAFE_TOOLS=1 \
LLAMA_MTP_REQUANT_CACHE=/root/.cache/llama-mtp"
MTP_ARGS=(--spec-type draft-mtp --spec-draft-n-max 2 -ctkd q4_0 -ctvd q4_0
          --spec-draft-vocab "$VOCAB" --spec-draft-vocab-n 65536
          --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs)
deadline=$(cat /root/qwenbench-deadline 2>/dev/null || echo 0)
have() { [ "$(date +%s)" -lt $((deadline - $1)) ]; }
vram() { nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' '; }
stop() { pkill -f "llama[-]server.*--port $PORT" 2>/dev/null; sleep 3; pkill -9 -f "llama[-]server.*--port $PORT" 2>/dev/null; }
wait_up() { for _ in $(seq 300); do curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1 && return 0; pgrep -f "llama[-]server.*--port $PORT" >/dev/null || return 1; sleep 1; done; return 1; }

echo "$(date -u +%T) post start, results $RES, deadline $(date -u -d @$deadline +%T)"

if have 100000; then   # base+mtp4 already measured in the first post run
    stop
    env $FORK_ENV $BASE/llama-server --host 127.0.0.1 --port $PORT --no-webui -m "$M" -fa on -ctk q4_0 -ctv q4_0 \
        -c 32768 -np 1 -ngl 999 -fit off --jinja --spec-type draft-mtp --spec-draft-n-max 4 -ctkd q4_0 -ctvd q4_0 \
        > "$RES/logs/post.base.mtp4.log" 2>&1 &
    if wait_up; then
        ( cd "$RES/sweep" && python3 "$HERE/spec_sweep.py" --label "post.base.mtp4.q4_0.32k|base|mtp4|q4_0|32768" \
            --port "$PORT" --temps 1.0 --seeds 1,2 ) || true
    else
        echo "post: base+mtp4 failed to load"
    fi
    stop
fi

run_depth() {  # label ctx frac kv need_secs
    local label=$1 ctx=$2 frac=$3 kv=$4 need=$5
    have "$need" || { echo "$(date -u +%T) skip $label (time)"; return 0; }
    stop
    env $FORK_ENV $FORK/llama-server --host 127.0.0.1 --port $PORT --no-webui -m "$M" -fa on -ctk "$kv" -ctv "$kv" \
        -c "$ctx" -np 1 -ngl 999 -fit off --jinja "${MTP_ARGS[@]}" -ctkd "$kv" -ctvd "$kv" \
        > "$RES/logs/post.$label.log" 2>&1 &
    if wait_up; then
        python3 "$HERE/orca_measure.py" long --port "$PORT" --label "post.$label" --ctx "$ctx" \
            --fracs "$frac" --tokens 64 --out "$RES/long/long.jsonl" || true
    else
        printf '{"label": "post.%s", "ctx": %s, "frac": %s, "ok": false, "error": "load failed"}\n' \
            "$label" "$ctx" "$frac" >> "$RES/long/long.jsonl"
    fi
    stop
}
run_depth depth262k.mtp2.q4_0 262144 0.25 q4_0 700
run_depth depth262k.mtp2.q4_0 262144 0.5 q4_0 1500
run_depth depth131k.mtp2.f16 131072 0.25 f16 600
run_depth depth131k.mtp2.q4_0 131072 0.25 q4_0 600
run_depth depth262k.mtp2.q4_0 262144 0.75 q4_0 1100

if have 420; then
    printf '' > "$RES/long/kv-slope.jsonl"
    for ctx in 32768 65536 131072 262144; do
        have 300 || break
        stop
        env $FORK_ENV $FORK/llama-server --host 127.0.0.1 --port $PORT --no-webui -m "$M" -fa on -ctk q4_0 -ctv q4_0 \
            -c "$ctx" -np 1 -ngl 999 -fit off --jinja "${MTP_ARGS[@]}" > "$RES/logs/post.kv.$ctx.log" 2>&1 &
        if wait_up; then v=$(vram); ok=yes; else v=0; ok=no; fi
        printf '{"ctx": %s, "vram_mib": %s, "ok": "%s"}\n' "$ctx" "${v:-0}" "$ok" >> "$RES/long/kv-slope.jsonl"
        echo "$(date -u +%T) kv slope ctx $ctx -> ${v:-0} MiB ($ok)"
    done
fi
stop
python3 "$HERE/orca_measure.py" summary --dir "$RES" > "$RES/summary.txt" 2>&1 || true
echo "$(date -u +%T) post done"
