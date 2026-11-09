#!/bin/bash
# One arm of the L1 job (66-SYNTEZA items 7/8): production config (run-topka.sh uncensored: final mode, ctx 262144,
# MTP n4, SAFE_SPECIAL/SAFE_TOOLS, AP_TIMING) on port 8093 from ROCM_DIR, then suite.py, then ONE SIGTERM.
#   arm.sh LABEL ROCM_DIR ITEMS [VAR=VALUE ...]      e.g. arm.sh B1 ~/wt/l1-tokparse/build-hip replay,stream,md5,sweep LLAMA_SERVER_TOK_CACHE=1
set -u
label=$1; rocm=$2; items=$3; shift 3
D=~/qwen-opt/l1tok; out=$D/results.jsonl; port=8093
log=$D/logs/server-$label.log; mkdir -p "$D/logs"
for kv in "$@"; do export "$kv"; done
export LLAMA_SERVER_AP_TIMING=1
# final mode: eco 2200 must be in place (never changed here)
sudo -n /usr/local/sbin/xtx-eco status 2>/dev/null | grep -q 'sclk cap (state): 2200' || { echo "eco 2200 not active" >&2; exit 3; }
env | grep -E '^LLAMA_SERVER_(TOK_CACHE|PARSE_INC|STREAM_STEP|AP_TIMING|SAFE_)' | sort
PORT=$port LOG=$log ROCM_DIR=$rocm ~/qwen-opt/run-topka.sh uncensored > "$D/logs/run-$label.out" 2>&1 &
for _ in $(seq 300); do curl -sf "127.0.0.1:$port/health" > /dev/null && break; sleep 1; done
curl -sf "127.0.0.1:$port/health" > /dev/null || { echo "server $label did not come up" >&2; tail -20 "$log" >&2; exit 4; }
stop() {
    local p; p=$(pgrep -f "llama-server.*--port $port( |$)") || return 0
    kill -TERM $p  # exactly ONE SIGTERM
    for _ in $(seq 60); do kill -0 $p 2>/dev/null || return 0; sleep 1; done
    kill -KILL $p
}
trap stop EXIT
py=~/qwen-opt/.venv/bin/python
suite=${items/,sweep/}; suite=${suite/sweep,/}; suite=${suite/sweep/}
# SUITE_ARGS: extra suite.py arguments (e.g. --stream-modes true --gen-tokens 4096); SWEEP_SEEDS (default 1: short)
[ -n "$suite" ] && $py "$D/suite.py" --label "$label" --port $port --log "$log" --out "$out" --only "$suite" ${SUITE_ARGS:-}
case ",$items," in *,sweep,*)
    $py ~/qwen-opt/spec_sweep.py --label "l1-$label" --port $port --temps 1.0 --seeds "${SWEEP_SEEDS:-1}" 2>&1 | tee -a "$D/logs/sweep-$label.txt" | tail -2
    line=$(grep -E 'median' "$D/logs/sweep-$label.txt" | tail -1)
    echo "{\"label\": \"$label\", \"item\": \"sweep\", \"line\": \"$line\"}" >> "$out" ;;
esac
grep -c "MISMATCH" "$log" | sed "s/^/$label MISMATCH lines: /"
