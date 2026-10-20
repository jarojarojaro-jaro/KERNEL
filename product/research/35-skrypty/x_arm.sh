#!/usr/bin/env bash
# One arm of the report-35 experiments: a fresh llama-server started through run-topka.sh (exact production topka
# config: MTP + lookup 3 W16, coupled, host-gap switches, PM4 WA=2 + GUARD, HSA_USE_SVM=0, GPU verify, ctx 204800),
# the listed benchmarks, then the server is stopped. Run ONLY from the GPU queue (run-jobs.sh holds the locks).
# Stops topka, never starts it.
# usage: x_arm.sh LABEL BENCH[,BENCH...]
#   reason  reason_bench.py (LocalMaxxing reasoning-v1 + code-v1, T=0, thinking on, 3 nonces, 512 tok)
#   sweep   spec_sweep.py T=1, SEEDS (default 1,2)
#   mvs     copy_bench.py --set mvs T=0 1024 tok
#   doc     doc_bench.py (short documents ~1k/1.7k/3.4k tokens, T=0, 256 tok, thinking off)
#   ttft    ckpt/ttft.py fresh prompts 2k/8k (3 reps) and 32k (1 rep)
#   replay  ckpt/replay.py omp agent session, plain scenario, +500-token turn, 2 runs
#   pen     spec_sweep.py T=1 with sampler penalties P0 / presence 1.5 / repeat 1.05 on one server (P0 P1 R R P1 P0)
# env: BIN (default ~/llama-topka), PORT (default 18740), LOGDIR (default ~/qwen-opt/xtxlab/logs), every run-topka.sh
#      / run-llm.sh variable (DRAFT_N, LLAMA_GPU_VERIFY, ...) passes through; XENV="K=V ..." is exported last.
set -euo pipefail
label=$1; benches=$2
export ROCM_DIR=${BIN:-$HOME/llama-topka} PORT=${PORT:-18740}
# PM4 trap: run-jobs.sh exports GGML_HIP_PM4=0 and run-topka.sh keeps an inherited value, so the production PM4
# env is set here explicitly (override only through XENV)
export GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0
logdir=${LOGDIR:-$HOME/qwen-opt/xtxlab/logs}
mkdir -p "$logdir"
export LOG=$logdir/$label.server.log
[ -n "${XENV:-}" ] && for kv in $XENV; do export "$kv"; done
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
        reason) taskset -c 2-5 "$py" "$HOME/qwen-opt/xtxlab/reason_bench.py" --label "$label" --port "$PORT" ;;
        sweep)  taskset -c 2-5 "$py" "$HOME/qwen-opt/spec_sweep.py" --label "$label" --port "$PORT" --temps 1.0 \
                    --seeds "${SEEDS:-1,2}" ;;
        mvs)    taskset -c 2-5 "$py" "$HOME/qwen-opt/lookup/copy_bench.py" --label "$label" --port "$PORT" \
                    --out "$logdir/copy_bench.jsonl" --set mvs --temps 0.0 --tokens 1024 ;;
        doc)    taskset -c 2-5 "$py" "$HOME/qwen-opt/xtxlab/doc_bench.py" --label "$label" --port "$PORT" ;;
        ttft)   taskset -c 2-5 "$py" "$HOME/qwen-opt/xtxlab/ckpt/ttft.py" --label "$label" --port "$PORT" \
                    --sizes 2048,8192 --reps 3 --out "$logdir/ttft.jsonl"
                taskset -c 2-5 "$py" "$HOME/qwen-opt/xtxlab/ckpt/ttft.py" --label "$label" --port "$PORT" \
                    --sizes 32768 --reps 1 --out "$logdir/ttft.jsonl" ;;
        replay) for r in 1 2; do taskset -c 2-5 "$py" "$HOME/qwen-opt/xtxlab/ckpt/replay.py" --label "$label-r$r" \
                    --port "$PORT" --scenario plain --grow 500 --out "$logdir/replay.jsonl"; done ;;
        pen)    # one server, sampler penalties are per request: P0 none, P1 presence 1.5, R repeat 1.05 (P0 P1 R R P1 P0)
                for arm in P0 P1 R R P1 P0; do
                    case $arm in P0) x='{}' ;; P1) x='{"presence_penalty": 1.5}' ;; R) x='{"repeat_penalty": 1.05}' ;; esac
                    taskset -c 2-5 "$py" "$HOME/qwen-opt/spec_sweep.py" --label "$label-$arm" --port "$PORT" \
                        --temps 1.0 --seeds "${SEEDS:-1,2}" --extra "$x"
                done ;;
        *) echo "unknown bench $b" >&2; exit 2 ;;
    esac
done
grep -h "context lookup" "$LOG" | tail -1 || true
