#!/usr/bin/env bash
# ON a RTX 3090, Qwen base: run 1 T (ctx 204800) ran out of VRAM on the ~55.6k-token prompt (cudaMalloc of the
# compute buffer, server abort). Here U1 and T both at ctx 131072, ABBA U1 T T U1, long_bench.py 32k and 60k only.
# Labels qwen.U1c.p<i> / qwen.Tc.p<i> in $RES/logs (vram.jsonl, long.jsonl, *.server.log).
set -uo pipefail
H=/root/cloud; M=/root/models
RES=$(readlink -f /root/results/current); L=$RES/logs
UP=/root/bin/upstream; TK=/root/bin/topka2
PORT=18701 CTX=131072
GGUF=$M/Qwen3.8-27B-UD-Q4_K_XL.gguf
vram() { nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1; }
say() { echo "=== $(date +%T) $*"; }
pid=
srv_stop() {
    [ -n "$pid" ] || return 0
    kill "$pid" 2>/dev/null
    for _ in $(seq 30); do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
    kill -9 "$pid" 2>/dev/null; wait "$pid" 2>/dev/null; pid=
    sleep 3
}
trap srv_stop EXIT
prod=(-m "$GGUF" -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -c $CTX -np 1 --jinja --cache-ram 16384 --reasoning-effort low
      --host 127.0.0.1 --port $PORT --no-webui --spec-type draft-mtp --spec-draft-n-max 4 -ctkd q4_0 -ctvd q4_0)
arm() {  # U1|T pass
    local label=qwen.$1c.p$2; local slog=$L/$label.server.log
    say "arm $label"
    local v0; v0=$(vram)
    case $1 in
        U1) $UP/llama-server "${prod[@]}" > "$slog" 2>&1 & ;;
        T)  env LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16 LLAMA_SERVER_CACHE_SHARE_MIN=1024 LLAMA_GPU_VERIFY=1 \
                LLAMA_SERVER_REASONING_CONTROL=0 $TK/llama-server "${prod[@]}" \
                --spec-draft-vocab $H/draft_vocab_qwen38.txt --spec-draft-vocab-n 65536 \
                --spec-draft-head-type iq4_xs --spec-mtp-type iq4_xs > "$slog" 2>&1 & ;;
    esac
    pid=$!
    for _ in $(seq 600); do curl -sf "http://127.0.0.1:$PORT/health" > /dev/null && break; kill -0 "$pid" 2>/dev/null || break; sleep 1; done
    curl -sf "http://127.0.0.1:$PORT/health" > /dev/null || { say "$label failed"; tail -20 "$slog"; srv_stop; return 0; }
    sleep 3
    echo "{\"label\":\"$label\",\"vram_before_mb\":$v0,\"vram_loaded_mb\":$(vram),\"n_ctx\":\"$CTX\"}" | tee -a "$L/vram.jsonl"
    python3 $H/long_bench.py --label "$label" --port $PORT --out "$L/long.jsonl" --sizes 32k,60k
    echo "{\"label\":\"$label\",\"vram_peak_after_60k_mb\":$(vram)}" | tee -a "$L/vram.jsonl"
    srv_stop
}
for _ in $(seq 1200); do [ -f "$GGUF.ok" ] && break; sleep 3; done
arm U1 1; arm T 1; arm T 2; arm U1 2
touch "$RES/main.done"; say "fin60k done"
