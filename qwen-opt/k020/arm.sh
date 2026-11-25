#!/usr/bin/env bash
# K-020 (cost-weighted --cache-ram eviction) one arm: production topka-q70 config (qprep/srv.sh), the qprep-spec build,
# --cache-ram $CACHE_RAM (default 8192 MiB here, so 2 long threads + a few short entries overflow it; production 40960
# overflows the same way at ~5x the context, which does not fit a 15-min job).
#   lru:   production eviction (oldest entry first)
#   cost:  LLAMA_SERVER_CACHE_EVICT=cost, alpha 1 (Marconi: age rank + alpha * prefill-cost-per-byte, lowest first)
#   cost4: the same with LLAMA_SERVER_CACHE_EVICT_ALPHA=4 (cost per byte dominates age)
# Workload: replay.py (threads A, B of 24k tokens, 2 x 6 short 3k requests between their turns, 3 turns each).
# The eviction lines of the server log (sizes, n_tokens) follow the replay summary.
# usage: arm.sh LABEL lru|cost|cost4      (GPU queue only)
set -u
label=$1; mode=$2
. "$HOME/qwen-opt/qprep/srv.sh"
trap srv_kill EXIT
export CACHE_RAM=${CACHE_RAM:-8192}
case $mode in
    lru)   export LLAMA_SERVER_CACHE_EVICT=lru ;;
    cost)  export LLAMA_SERVER_CACHE_EVICT=cost LLAMA_SERVER_CACHE_EVICT_ALPHA=1 ;;
    cost4) export LLAMA_SERVER_CACHE_EVICT=cost LLAMA_SERVER_CACHE_EVICT_ALPHA=4 ;;
    *) echo "mode lru|cost|cost4" >&2; exit 2 ;;
esac
d=$HOME/qwen-opt/k020
dir=$d/logs
srv_start "$label" "$dir" || exit 1
py=$HOME/qwen-opt/.venv/bin/python
taskset -c 6-9 "$py" "$d/replay.py" --port "$PORT" --label "$label" --out "$dir/replay.jsonl"
srv_stop
grep -hE "removing (oldest entry|the entry cheapest)|exceeds cache size limit" "$dir/$label.server.log" | sed 's/^.*- //' | head -40
