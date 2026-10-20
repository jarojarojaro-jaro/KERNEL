#!/usr/bin/env bash
# Report 40 (draft acceptance on E0 prose): one fresh production topka server (run-topka.sh qwen: MTP n=4 + lookup 3
# W16, coupled, GPU verify, PM4 WA=2 + GUARD, HSA_USE_SVM=0) with the per-step lookup log on, then the E0 prose set
# at T=1 (seeds SEEDS, default 1..8) and at T=0 (one pass, greedy = seed-independent). Run ONLY from the GPU queue.
# usage: pa_arm.sh LABEL        env: SEEDS, T0 (default 1 = also the T=0 pass), XENV="K=V ..." (arm switches, e.g. DRAFT_N=3)
set -euo pipefail
label=$1
here=$HOME/qwen-opt/prose-accept
logdir=$here/logs
mkdir -p "$logdir"
export ROCM_DIR=$HOME/llama-topka PORT=${PORT:-18761}
export GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0
export LOG=$logdir/$label.server.log
export LLAMA_SPEC_LOOKUP_LOG=$logdir/$label.lk.jsonl
rm -f "$LLAMA_SPEC_LOOKUP_LOG"
[ -n "${XENV:-}" ] && for kv in $XENV; do export "$kv"; done
echo "arm $label XENV=${XENV:-}"
pkill -f 'llama-topka/bin/llama-server' && sleep 5 || true
"$HOME/qwen-opt/lookup/vram_ok.sh"
taskset -c 2-5 "$HOME/qwen-opt/run-topka.sh" qwen > "$logdir/$label.launch.log" 2>&1 &
srv=$!
stop() { pkill -f "llama-server.*--port $PORT" || true
         for _ in $(seq 20); do pgrep -f "llama-server.*--port $PORT" >/dev/null || break; sleep 1; done
         pkill -9 -f "llama-server.*--port $PORT" || true; wait $srv 2>/dev/null || true; }
trap stop EXIT
trap 'exit 1' TERM INT
for _ in $(seq 180); do curl -sf "http://127.0.0.1:$PORT/health" > /dev/null && break
    kill -0 $srv 2>/dev/null || { echo "$label: server failed"; tail -5 "$logdir/$label.launch.log"; exit 1; }
    sleep 1
done
head -1 "$logdir/$label.launch.log"
py=$HOME/qwen-opt/.venv/bin/python
taskset -c 2-5 "$py" "$here/pa_bench.py" --label "$label" --port "$PORT" --temp 1.0 \
    --seeds "${SEEDS:-1,2,3,4,5,6,7,8}" --out "$logdir/pa.jsonl"
if [ "${T0:-1}" = 1 ]; then
    taskset -c 2-5 "$py" "$here/pa_bench.py" --label "$label" --port "$PORT" --temp 0.0 --seeds 1 --warmup 0 \
        --out "$logdir/pa.jsonl"
fi
grep -h "context lookup" "$LOG" | tail -1 || true
