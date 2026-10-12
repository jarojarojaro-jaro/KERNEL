#!/usr/bin/env bash
# One spec_sweep run (6 prompts x seeds, T=1) against a fresh server of the given build. Run under flock.
# usage: bench.sh LABEL BIN_DIR LIB_DIR MODEL [SEEDS]
set -euo pipefail
cd "$(dirname "$0")"
label=$1; bin=$2; lib=$3; model=$4; seeds=${5:-1,2,3}
port=18431
./server.sh "$bin" "$lib" "$model" $port 204800 > "logs/$label.server.log" 2>&1 &
srv=$!
trap 'kill $srv 2>/dev/null; for _ in $(seq 30); do kill -0 $srv 2>/dev/null || break; sleep 1; done; kill -9 $srv 2>/dev/null; wait $srv 2>/dev/null || true' EXIT
until curl -sf "http://127.0.0.1:$port/health" > /dev/null; do
    kill -0 $srv 2>/dev/null || { echo "$label: server failed"; exit 1; }
    sleep 1
done
~/qwen-opt/.venv/bin/python ~/qwen-opt/spec_sweep.py --label "$label" --port $port --temps 1.0 --seeds "$seeds"
