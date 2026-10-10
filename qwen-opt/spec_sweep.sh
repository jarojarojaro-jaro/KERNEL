#!/usr/bin/env bash
# Restart run-llm.sh per speculative config and measure it with spec_sweep.py.
#   [RUN_ARGS="qwen dflash"] spec_sweep.sh "DRAFT_N=5 P_MIN=" "DRAFT_N=6 P_MIN=0.5" ...
# Logs GPU power/temps alongside (logs/sweep-gpu.csv).
set -euo pipefail
cd "$(dirname "$0")"
port=${PORT:-8080}
temps=${TEMPS:-1.0}

./gpu-power.sh monitor logs/sweep-gpu.csv > /dev/null &
mon=$!
# llama-server with a DFlash drafter can hang on SIGTERM; escalate so the next config never shares VRAM or the port
stop_server() {
    pkill -f "llama-server.*--port $port" || return 0
    for _ in $(seq 15); do pgrep -f "llama-server.*--port $port" > /dev/null || return 0; sleep 1; done
    pkill -9 -f "llama-server.*--port $port" || true
    sleep 2
}
trap 'kill $mon 2>/dev/null; stop_server' EXIT

for cfg in "$@"; do
    stop_server
    env $cfg PORT=$port LOG=logs/sweep-server.log ./run-llm.sh ${RUN_ARGS:-} > /dev/null 2>&1 &
    srv=$!
    until curl -sf "http://127.0.0.1:$port/health" > /dev/null; do
        kill -0 $srv 2>/dev/null || { echo "$cfg: server failed to start (logs/sweep-server.log)"; continue 2; }
        sleep 1
    done
    .venv/bin/python spec_sweep.py --label "$cfg" --port "$port" --temps "$temps"
done
