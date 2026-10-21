#!/usr/bin/env bash
# One arm of report 58 (draft-sample): p100_arm.sh (report 37/56) with a chat bench and a DFlash2 variant.
# A fresh llama-server through run-topka.sh (production topka config: MTP n=4 + lookup 3 W16, coupled, host-gap
# switches, PM4 WA=2 + GUARD, HSA_USE_SVM=0, GPU verify, ctx 204800, KV q4_0), the listed benchmarks, server stopped
# gracefully on exit. Run ONLY from the GPU queue. Stops topka (gracefully), never starts it.
# usage: ds_arm.sh LABEL BENCH[,BENCH...]
#   prose       prose_bench.py (8 PL/EN prose prompts, T=1, thinking off, 400 tok), seeds SEEDS (default 1,2)
#   prosethink  prose_bench.py --think, label think-LABEL (prose_sum prefix think-PREFIX)
#   chat        spec_sweep.py (EN/PL chat prompts, T=1, 400 tok), seeds SEEDS -> LOGDIR/spec_sweep.jsonl
#   mvs         copy_bench.py --set mvs T=0 1024 tok (code edit)
# env: BIN (install dir with bin/), PORT (default 18760), LOGDIR (default ~/qwen-opt/draft-sample/logs),
#      SPEC (mtp | dflash; dflash: run-topka.sh with spec=dflash, the DFlash2 Q4_K_M drafter of run-llm.sh; set
#      DRAFT_N=6 in XENV), XENV="K=V ..." exported last (the arm's switches).
set -euo pipefail
label=$1; benches=$2
D=$HOME/qwen-opt/draft-sample
bin=${BIN:-$D/inst}
[ -x "$bin/bin/llama-server" ] || { echo "$label: no $bin/bin/llama-server" >&2; exit 1; }
export ROCM_DIR=$bin PORT=${PORT:-18760}
# PM4 trap (24l, 35): run-jobs.sh exports GGML_HIP_PM4=0 and run-topka.sh keeps an inherited value -> set it here
export GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0
logdir=${LOGDIR:-$D/logs}
mkdir -p "$logdir"
export LOG=$logdir/$label.server.log
[ -n "${XENV:-}" ] && for kv in $XENV; do export "$kv"; done
launcher=$HOME/qwen-opt/run-topka.sh
if [ "${SPEC:-mtp}" = dflash ]; then
    # the production launcher with only its drafter swapped (spec=mtp -> dflash); everything else as topka
    launcher=$logdir/run-topka-dflash.sh
    sed 's/^spec=mtp$/spec=dflash/' "$HOME/qwen-opt/run-topka.sh" > "$launcher"
    grep -q '^spec=dflash$' "$launcher" || { echo "$label: run-topka.sh has no 'spec=mtp' line to swap" >&2; exit 1; }
    chmod +x "$launcher"
fi
echo "arm $label BIN=$bin SPEC=${SPEC:-mtp} XENV=${XENV:-}"
. "$D/ds_stop.sh"
# production topka (port 8080): idle /slots, one SIGTERM, 45 s, SIGKILL last
ds_stop 8080 'llama-topka/bin/llama-server' || true
"$HOME/qwen-opt/lookup/vram_ok.sh"
taskset -c 2-5 "$launcher" qwen > "$logdir/$label.launch.log" 2>&1 &
srv=$!
stop() { ds_stop "$PORT" "llama-server.*--port $PORT" || true; wait $srv 2>/dev/null || true; }
trap stop EXIT
trap 'exit 1' TERM INT
for _ in $(seq 180); do curl -sf "http://127.0.0.1:$PORT/health" > /dev/null && break
    kill -0 $srv 2>/dev/null || { echo "$label: server failed"; tail -5 "$logdir/$label.launch.log"; exit 1; }
    sleep 1
done
curl -sf "http://127.0.0.1:$PORT/health" > /dev/null || { echo "$label: server not healthy after 180 s"; exit 1; }
head -1 "$logdir/$label.launch.log"
grep -h "draft cutoff on the product\|adding speculative implementation" "$LOG" | head -3 || true
py=$HOME/qwen-opt/.venv/bin/python
cd "$logdir"
for b in ${benches//,/ }; do
    case $b in
        prose) taskset -c 2-5 "$py" "$HOME/qwen-opt/xtxroadmap/prose_bench.py" --label "$label" --port "$PORT" \
                   --seeds "${SEEDS:-1,2}" --out "$logdir/prose.jsonl" ;;
        prosethink) taskset -c 2-5 "$py" "$HOME/qwen-opt/xtxroadmap/prose_bench.py" --label "think-$label" --port "$PORT" \
                   --seeds "${SEEDS:-1,2}" --out "$logdir/prose.jsonl" --think ;;
        chat)  taskset -c 2-5 "$py" "$HOME/qwen-opt/spec_sweep.py" --label "$label" --port "$PORT" \
                   --temps 1.0 --seeds "${SEEDS:-1,2}" ;;
        mvs)   taskset -c 2-5 "$py" "$HOME/qwen-opt/lookup/copy_bench.py" --label "$label" --port "$PORT" \
                   --out "$logdir/copy_bench.jsonl" --set mvs --temps 0.0 --tokens 1024 ;;
        *) echo "unknown bench $b" >&2; exit 2 ;;
    esac
done
grep -h "context lookup" "$LOG" | tail -1 || true
