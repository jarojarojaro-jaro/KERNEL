#!/usr/bin/env bash
# K-019 (cross-session suffix cache) one ABBA arm: production topka-q70 config (qprep/srv.sh), the qprep-spec build.
#   off: production (lookup 3, W16)
#   on:  + LLAMA_SPEC_SUFFIX=1 over a FIXED corpus: data/omp-outputs.ids = 46k assistant output pieces (text, rendered
#        tool calls) of 256 omp sessions of 2026-11 (other sessions than the replayed ones), LLAMA_SPEC_SUFFIX_LIVE=0 so
#        nothing this server generates enters the cache (no same-prompt leakage between requests or arms). The first
#        'on' arm tokenizes data/omp-outputs.txt with the model's vocab and writes the .ids file (~33 MB text).
# Workload: replay.py (61 recorded agent turns of 4 omp sessions, T=0, prompt cache on), then spec_sweep T=1 seed 1.
# usage: arm.sh LABEL off|on      (GPU queue only)
set -u
label=$1; mode=$2
. "$HOME/qwen-opt/qprep/srv.sh"
trap srv_kill EXIT
d=$HOME/qwen-opt/k019
case $mode in
    off) export LLAMA_SPEC_SUFFIX=0 ;;
    on)  export LLAMA_SPEC_SUFFIX=1 LLAMA_SPEC_SUFFIX_LIVE=0 LLAMA_SPEC_SUFFIX_FILE=$d/data/omp-outputs.ids \
                LLAMA_SPEC_SUFFIX_TEXT=$d/data/omp-outputs.txt ;;
    *) echo "mode off|on" >&2; exit 2 ;;
esac
dir=$d/logs
srv_start "$label" "$dir" || exit 1
grep -h "suffix cache:" "$dir/$label.server.log" | head -1
py=$HOME/qwen-opt/.venv/bin/python
cd "$dir"
taskset -c 6-9 "$py" "$d/replay.py" --port "$PORT" --label "$label" --out "$dir/replay.jsonl"
taskset -c 6-9 "$py" "$HOME/qwen-opt/spec_sweep.py" --label "$label-chat" --port "$PORT" --temps 1.0 --seeds 1 --tokens 400
srv_stop
grep -h "context lookup:" "$dir/$label.server.log" | tail -2
