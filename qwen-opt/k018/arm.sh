#!/usr/bin/env bash
# K-018 (AGR2) one ABBA arm: production topka-q70 config (qprep/srv.sh), the qprep-spec build for both arms.
#   off: production (lookup 3, W16, tail at match >= 6)
#   on:  + LLAMA_SPEC_LOOKUP_AGREE=1 (2-gram candidates whose continuation starts with the 4 MTP drafts -> tail)
# Workload (each prompt once per temperature/seed, fresh server per arm):
#   copy  copy_bench --set short (edit-2k/8k, strrep-en, hashline-pl, quote-pl, refactor-en), T=0 + T=1 seeds 1,2,3, 512 tok
#   mvs   copy_bench --set mvs, T=0, 1024 tok
#   chat  spec_sweep T=1 seeds 1,2,3 and T=0 seed 1, 400 tok (thinking on, the server default)
# Then the lookup counters of the server log (tails / agree tails, accepted tokens).
# usage: arm.sh LABEL off|on      (GPU queue only)
set -u
label=$1; mode=$2
. "$HOME/qwen-opt/qprep/srv.sh"
trap srv_kill EXIT
case $mode in
    off) export LLAMA_SPEC_LOOKUP_AGREE=0 ;;
    on)  export LLAMA_SPEC_LOOKUP_AGREE=1 ;;
    *) echo "mode off|on" >&2; exit 2 ;;
esac
dir=$HOME/qwen-opt/k018/logs
srv_start "$label" "$dir" || exit 1
py=$HOME/qwen-opt/.venv/bin/python
cd "$dir"
taskset -c 6-9 "$py" "$HOME/qwen-opt/lookup/copy_bench.py" --label "$label" --port "$PORT" --out "$dir/copy_bench.jsonl" \
    --set short --temps 0.0,1.0 --seeds 1,2,3 --tokens 512
taskset -c 6-9 "$py" "$HOME/qwen-opt/lookup/copy_bench.py" --label "$label" --port "$PORT" --out "$dir/copy_bench.jsonl" \
    --set mvs --temps 0.0 --tokens 1024
taskset -c 6-9 "$py" "$HOME/qwen-opt/spec_sweep.py" --label "$label-chat" --port "$PORT" --temps 1.0 --seeds 1,2,3 --tokens 400
taskset -c 6-9 "$py" "$HOME/qwen-opt/spec_sweep.py" --label "$label-chat" --port "$PORT" --temps 0.0 --seeds 1 --tokens 400
srv_stop
grep -h "context lookup:" "$dir/$label.server.log" | tail -2
