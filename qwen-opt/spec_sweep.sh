#!/usr/bin/env bash
# Restart run-llm.sh per speculative config and measure it with spec_sweep.py.
#   spec_sweep.sh "DRAFT_N=5 P_MIN=" "DRAFT_N=6 P_MIN=0.5" ...
# Logs GPU power/temps alongside (logs/sweep-gpu.csv).
set -euo pipefail
cd "$(dirname "$0")"
port=${PORT:-8080}
temps=${TEMPS:-1.0}

./gpu-power.sh monitor logs/sweep-gpu.csv > /dev/null &
mon=$!
trap 'kill $mon 2>/dev/null; pkill -f "llama-server.*--port $port" || true' EXIT

for cfg in "$@"; do
    pkill -f "llama-server.*--port $port" || true
    sleep 3
    env $cfg PORT=$port LOG=logs/sweep-server.log ./run-llm.sh > /dev/null 2>&1 &
    until curl -sf "http://127.0.0.1:$port/health" > /dev/null; do sleep 1; done
    .venv/bin/python spec_sweep.py --label "$cfg" --port "$port" --temps "$temps"
done
