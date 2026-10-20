#!/usr/bin/env bash
# One arm of report 37 (E0 prose metric + the item ABBAs): a fresh llama-server through run-topka.sh (production topka
# config: MTP n=4 + lookup 3 W16, coupled, host-gap switches, PM4 WA=2 + GUARD, HSA_USE_SVM=0, GPU verify, ctx 204800,
# KV q4_0), the listed benchmarks, server stopped on exit. Run ONLY from the GPU queue (run-jobs.sh holds the locks).
# Stops topka, never starts it.
# usage: p100_arm.sh LABEL BENCH[,BENCH...]
#   prose  prose_bench.py (8 PL/EN prose prompts, T=1, thinking off, 400 tok), seeds SEEDS (default 1..8)
#   mvs    copy_bench.py --set mvs T=0 1024 tok (code edit, md5 per file)
# env: BIN (default ~/llama-topka; a build dir with bin/ or the bin dir itself), PORT (default 18760),
#      LOGDIR (default ~/qwen-opt/prose100/logs), XENV="K=V ..." exported last (the arm's switches).
set -euo pipefail
label=$1; benches=$2
bin=${BIN:-$HOME/llama-topka}
[ -x "$bin/bin/llama-server" ] || { [ -x "$bin/llama-server" ] && bin=$(dirname "$bin"); }
export ROCM_DIR=$bin PORT=${PORT:-18760}
# PM4 trap (24l, 35): run-jobs.sh exports GGML_HIP_PM4=0 and run-topka.sh keeps an inherited value -> set it here
export GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0
logdir=${LOGDIR:-$HOME/qwen-opt/prose100/logs}
mkdir -p "$logdir"
export LOG=$logdir/$label.server.log
[ -n "${XENV:-}" ] && for kv in $XENV; do export "$kv"; done
echo "arm $label BIN=$bin XENV=${XENV:-}"
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
cd "$logdir"
for b in ${benches//,/ }; do
    case $b in
        prose) taskset -c 2-5 "$py" "$HOME/qwen-opt/xtxroadmap/prose_bench.py" --label "$label" --port "$PORT" \
                   --seeds "${SEEDS:-1,2,3,4,5,6,7,8}" --out "$logdir/prose.jsonl" ;;
        mvs)   taskset -c 2-5 "$py" "$HOME/qwen-opt/lookup/copy_bench.py" --label "$label" --port "$PORT" \
                   --out "$logdir/copy_bench.jsonl" --set mvs --temps 0.0 --tokens 1024 ;;
        prosethink) taskset -c 2-5 "$py" "$HOME/qwen-opt/xtxroadmap/prose_bench.py" --label "$label-think" --port "$PORT" \
                   --seeds "${SEEDS:-1,2,3,4,5,6,7,8}" --out "$logdir/prose.jsonl" --think ;;
        *) echo "unknown bench $b" >&2; exit 2 ;;
    esac
done
grep -h "context lookup" "$LOG" | tail -1 || true
