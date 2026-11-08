#!/bin/bash
# One arm of the cache-save job: production config (run-topka.sh uncensored, ctx 262144, --cache-ram 40960, AP_TIMING)
# on port 8094 from ROCM_DIR, then switch.py / md5 / spec_sweep, then ONE SIGTERM (60 s) and SIGKILL.
#   arm.sh LABEL ROCM_DIR ITEMS [VAR=VALUE ...]     ITEMS: switch,md5,sweep
set -u
label=$1; rocm=$2; items=$3; shift 3
D=~/qwen-opt/cachesave; out=$D/results.jsonl; port=8094
log=$D/logs/server-$label.log; mkdir -p "$D/logs"
for kv in "$@"; do export "$kv"; done
export LLAMA_SERVER_AP_TIMING=1
sudo -n /usr/local/sbin/xtx-eco status 2>/dev/null | grep -q 'sclk cap (state): 2200' || { echo "eco 2200 not active" >&2; exit 3; }
env | grep -E '^LLAMA_SERVER_(CACHE_HUGE|AP_TIMING)' | sort
grep -E '^(AnonHugePages|MemAvailable)' /proc/meminfo
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
case ",$items," in *,switch,*)
    $py "$D/switch.py" --label "$label" --port $port --log "$log" --out "$out"
    grep -E '^AnonHugePages' /proc/meminfo ;;
esac
case ",$items," in *,md5,*)
    $py ~/qwen-opt/l1tok/suite.py --label "$label" --port $port --log "$log" --out "$out" --only md5 ;;
esac
case ",$items," in *,sweep,*)
    $py ~/qwen-opt/spec_sweep.py --label "cs-$label" --port $port --temps 1.0 --seeds 1,2,3 2>&1 | tee -a "$D/logs/sweep-$label.txt" | tail -2
    line=$(grep -E 'median' "$D/logs/sweep-$label.txt" | tail -1)
    echo "{\"label\": \"$label\", \"item\": \"sweep\", \"line\": \"$line\"}" >> "$out" ;;
esac
