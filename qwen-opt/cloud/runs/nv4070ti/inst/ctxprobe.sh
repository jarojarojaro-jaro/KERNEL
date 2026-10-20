#!/usr/bin/env bash
# ON the box: ctxprobe.sh <arm> <ctx...> — for each ctx: start the arm, VRAM after load, then one long prompt that
# fills the context to ~ctx-700 tokens (T=0, 256 new tokens) while nvidia-smi samples VRAM every 0.5 s; peak recorded.
# Rows: logs/ctxprobe.jsonl (+ long.jsonl via long_bench). Server logs: logs/probe.<arm>.<ctx>.server.log
set -uo pipefail
. /root/cloud/lib4070.sh
arm=$1; shift
for c in "$@"; do
    CTX=$c; label=probe.$arm.$c.ub$UB; slog=$L/$label.server.log
    say "probe $label"
    srv "$arm" "$slog" || { say "$label: did not start"; grep -iE "out of memory|failed|error" "$slog" | tail -5
        echo "{\"label\":\"$label\",\"start\":false}" >> "$L/ctxprobe.jsonl"; continue; }
    sleep 2; v_load=$(vram)
    ( while sleep 0.5; do vram; done ) > "$L/$label.vram.trace" 2>/dev/null & sp=$!
    chars=$(( (c - 1200) * 3450 / 1000 ))   # corpus60k: 198000 chars = 55.6k tokens (3.56 chars/token)
    python3 $H/long_bench.py --label "$label" --port $PORT --out "$L/long.jsonl" --sizes "c$chars" 2>&1 | head -1
    kill $sp 2>/dev/null; wait $sp 2>/dev/null
    peak=$(sort -n "$L/$label.vram.trace" | tail -1)
    alive=$(kill -0 "$pid" 2>/dev/null && echo true || echo false)
    kv=$(grep -m3 -E "KV buffer size|compute buffer size|CUDA0 model buffer" "$slog" | tr -s ' ' | tr '\n' '|' | sed 's/"//g')
    echo "{\"label\":\"$label\",\"ctx\":$c,\"vram_load_mb\":$v_load,\"vram_peak_mb\":$peak,\"total_mb\":12282,\"alive\":$alive,\"bufs\":\"$kv\"}" | tee -a "$L/ctxprobe.jsonl"
    srv_stop
done
