#!/usr/bin/env bash
# ON the box: [TENV=..] prof.sh <label> [arm] — nsys trace of one server arm (default T) for a short workload: chat T=1
# en-code + pl-proza seed 1 (400 tok) and mvs T=0 one prompt; then nsys stats (kernel sum, API sum) to prof/<label>.*
set -uo pipefail
. /root/cloud/lib4070.sh
lab=$1; a=${2:-T}; P=$RES/prof; mkdir -p "$P"
NSYS=$(command -v nsys || ls /opt/nvidia/nsight-systems/*/bin/nsys | head -1)
PFX="$NSYS profile -t cuda,nvtx -s none --cpuctxsw=none --cuda-graph-trace=${GTRACE:-node} -f true -o $P/$lab"
say "prof $lab arm $a"
srv "$a" "$P/$lab.server.log" || { say "server failed"; tail -5 "$P/$lab.server.log"; exit 1; }
python3 - "$PORT" > "$P/$lab.workload.txt" <<'EOF'
import json, sys, urllib.request
port = int(sys.argv[1])
def chat(p, n, t, s, think=True):
    body = {"messages": [{"role": "user", "content": p}], "max_tokens": n, "temperature": t, "seed": s, "cache_prompt": False}
    if not think: body["chat_template_kwargs"] = {"enable_thinking": False}
    r = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    t = json.load(urllib.request.urlopen(r, timeout=600))["timings"]
    print(json.dumps(t), flush=True)
chat("Hi", 16, 0.0, 0)
chat("Write a complete Python module implementing a thread-safe LRU cache with TTL expiry: type hints, docstrings, and a full pytest test suite. Write all the code, no placeholders.", 400, 1.0, 1)
chat("Napisz opowiadanie (około 800 słów) o starym latarniku, który pewnej sztormowej nocy dostaje sygnał z okrętu, który zatonął 50 lat temu.", 400, 1.0, 1)
EOF
srv_stop
sleep 5
"$NSYS" stats -q -r cuda_gpu_kern_sum,cuda_api_sum -f csv -o "$P/$lab" "$P/$lab.nsys-rep" > /dev/null 2>&1
"$NSYS" export -t sqlite -f true -o "$P/$lab.sqlite" "$P/$lab.nsys-rep" > /dev/null 2>&1
ls -la "$P" | grep "$lab"
