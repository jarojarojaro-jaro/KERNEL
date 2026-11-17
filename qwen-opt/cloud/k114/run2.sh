#!/usr/bin/env bash
# K-114 part 2 (the published fork archive has no llama-bench): plain decode without speculation (target pass time)
# and cold prefill ~4k/~14k through llama-server. Needs run.sh's setup (/root/fork, /root/m.gguf, /root/res).
# ON the box, detached: setsid nohup bash /root/k114/run2.sh > /dev/null 2>&1 < /dev/null &   marker /root/res/DONE2
set -uo pipefail
R=/root/res; F=/root/fork; M=/root/m.gguf
exec >> "$R/run2.log" 2>&1
ph() { echo "$(date +%s) $*" | tee -a "$R/phases.txt"; }
B=$(dirname "$(find "$F/x" -name llama-server -type f | head -1)"); export LD_LIBRARY_PATH=$B
pgrep -f "query-gpu=timestamp" > /dev/null || (nvidia-smi --query-gpu=timestamp,power.draw,power.limit,temperature.gpu,clocks.sm,clocks.mem,utilization.gpu,memory.used --format=csv,noheader -l 1 >> "$R/smi.csv") &
SMI=$!
srv() {  # label ctx -> starts plain server (no speculation), waits for health, echoes pid
    env GGML_CUDA_KVQ=1 LLAMA_GPU_VERIFY=1 "$B/llama-server" -m "$M" -c "$2" -ngl 999 -fa on -ctk q4_0 -ctv q4_0 -ub 512 \
        -np 1 --jinja --alias k114 --host 127.0.0.1 --port 8090 --no-webui > "$R/logs/server-$1.log" 2>&1 < /dev/null &
    local pid=$!
    for _ in $(seq 600); do curl -fs localhost:8090/health > /dev/null && break; kill -0 $pid 2> /dev/null || break; sleep 1; done
    echo $pid
}
stop() { kill -TERM "$1"; for _ in $(seq 60); do kill -0 "$1" 2> /dev/null || break; sleep 1; done; kill -KILL "$1" 2> /dev/null; wait "$1" 2> /dev/null; }
pid=$(srv plain 8192)
TEMPS=0 TOKENIZE_PORT=8090 timeout 600 python3 /root/k114/bench.py plain 8090 k114 short > "$R/logs/plain.bench.log" 2>&1
stop "$pid"; ph "arm plain"
pid=$(srv prefill 20480)
timeout 900 python3 /root/k114/pf.py 8090 > "$R/logs/prefill.log" 2>&1
nvidia-smi --query-gpu=memory.used --format=csv,noheader > "$R/logs/prefill.vram"
stop "$pid"; ph "prefill"
kill $SMI 2> /dev/null; ph done2; touch "$R/DONE2"
