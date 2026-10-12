#!/usr/bin/env bash
# rocprofv3 kernel trace of a build under a short spec-decoding workload. Run under flock.
# usage: prof.sh OUTDIR BIN_DIR LIB_DIR [MODEL]
set -euo pipefail
out=$1; bin=$2; lib=$3; model=${4:-qwen}
port=18432
rm -rf "$out"; mkdir -p "$(dirname "$out")"
here=$(dirname "$(readlink -f "$0")")
/opt/rocm/core-10.0/bin/rocprofv3 --kernel-trace --output-format csv -d "$out" -o run -- \
    "$here/server.sh" "$bin" "$lib" "$model" $port 32768 > "$out.log" 2>&1 &
pid=$!
for _ in $(seq 300); do curl -sf http://127.0.0.1:$port/health >/dev/null && break; sleep 1; done
for p in "Write a Python function that implements an LRU cache class with get and put, with type hints and docstrings. Only code." \
         "Explain in three paragraphs why the sky appears blue during the day and red at sunset."; do
    curl -s http://127.0.0.1:$port/v1/chat/completions -H 'Content-Type: application/json' \
        -d "$(jq -n --arg p "$p" '{messages:[{role:"user",content:$p}],max_tokens:256,temperature:0,chat_template_kwargs:{enable_thinking:false}}')" \
        | jq -c '.timings | {predicted_n, predicted_ms, draft_n, draft_n_accepted}'
done
kill -TERM $(pgrep -f "llama-server .*--port $port") 2>/dev/null || true
for _ in $(seq 60); do kill -0 $pid 2>/dev/null || break; sleep 1; done
pkill -9 -f "llama-server .*--port $port" 2>/dev/null || true
for _ in $(seq 60); do kill -0 $pid 2>/dev/null || break; sleep 1; done
find "$out" -name '*kernel_trace.csv'
