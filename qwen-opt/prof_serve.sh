#!/usr/bin/env bash
# Kernel-level profile of llama-server under a real speculative-decoding workload.
# usage: prof_serve.sh OUTDIR -- <llama-server args>
set -euo pipefail
out=$1; shift; [ "$1" = "--" ] && shift
export LD_LIBRARY_PATH=/opt/rocm/core-10.0/lib
rm -rf "$out"
/opt/rocm/core-10.0/bin/rocprofv3 --kernel-trace --stats --output-format csv -d "$out" -o run -- \
    ~/llama-master/build-hip/bin/llama-server --port 8098 --host 127.0.0.1 -np 1 --no-webui "$@" > "$out.log" 2>&1 &
pid=$!
for _ in $(seq 300); do curl -sf http://127.0.0.1:8098/health >/dev/null && break; sleep 1; done
for p in "Write a Python function that implements an LRU cache class with get and put, with type hints and docstrings. Only code." \
         "Explain in three paragraphs why the sky appears blue during the day and red at sunset."; do
    curl -s http://127.0.0.1:8098/v1/chat/completions -H 'Content-Type: application/json' \
        -d "$(jq -n --arg p "$p" '{messages:[{role:"user",content:$p}],max_tokens:256,temperature:0,chat_template_kwargs:{enable_thinking:false}}')" \
        | jq -c '.timings | {predicted_n, predicted_per_second, draft_n, draft_n_accepted}'
done
# stop only the server itself (rocprofv3's own command line also contains the server args)
kill -TERM $(pgrep -f "^$HOME/llama-master/build-hip/bin/llama-server --port 8098") 2>/dev/null || true
for _ in $(seq 120); do kill -0 $pid 2>/dev/null || break; sleep 1; done
pkill -9 -f "^$HOME/llama-master/build-hip/bin/llama-server --port 8098" 2>/dev/null || true
find "$out" -name '*kernel_stats.csv'
