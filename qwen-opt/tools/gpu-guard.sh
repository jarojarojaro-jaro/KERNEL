#!/bin/bash
# GPU safety guard for the local RX 7900 XTX.
# Stops (kills every llama-server / llama-bench / llama-perplexity / test-backend-ops / magnitude-engine
# except the user's server on :8080... no: except processes listening on 8080) and exits 3 on:
#   - a new amdgpu page fault, ring timeout or GPU reset in the kernel log
#   - hotspot >= 100 C or VRAM >= 98 C
#   - fan below 2500 RPM at >= 50% busy for 20 s while the card is hot (hotspot >= 80 C or VRAM >= 82 C)
#     (firmware zero-RPM keeps the fan stopped while the card is still cool)
# Exits 4 (no kill) as an early warning at VRAM >= 85 C or hotspot >= 90 C.
# Cheap: the kernel log is followed once (journalctl -f) instead of being rescanned every poll.
set -u
log=~/qwen-opt/tools/gpu-guard.log
dev=/sys/class/drm/card0/device
hw=$(echo $dev/hwmon/hwmon*)
hits=$(mktemp /tmp/gpu-guard-hits.XXXXXX)
journalctl -k -f -n 0 -o short-iso --no-pager 2>/dev/null \
    | grep --line-buffered -E 'amdgpu.*(page fault|ring .* timeout|GPU reset begin|MES might be)' > "$hits" &
follower=$!
trap 'kill $follower 2>/dev/null; pkill -P $$ 2>/dev/null; rm -f "$hits"' EXIT
slowfan=0
stop() {
    echo "$(date -u '+%F %T') STOP: $1" | tee -a "$log"
    keep=$(ss -ltnp 'sport = :8080' 2>/dev/null | grep -o 'pid=[0-9]*' | cut -d= -f2)
    for sig in TERM KILL; do
        for p in $(pgrep -f 'llama-server|llama-bench|llama-perplexity|test-backend-ops|magnitude-engine'); do
            [ -n "$keep" ] && [ "$p" = "$keep" ] && continue
            kill -$sig "$p" 2>/dev/null
        done
        sleep 3
    done
    exit 3
}
echo "$(date -u '+%F %T') guard started" >> "$log"
while true; do
    [ -s "$hits" ] && stop "kernel: $(head -c 200 "$hits")"
    hot=$(( $(cat $hw/temp2_input) / 1000 )); mem=$(( $(cat $hw/temp3_input) / 1000 ))
    busy=$(cat $dev/gpu_busy_percent 2>/dev/null || echo 0); rpm=$(cat $hw/fan1_input 2>/dev/null || echo 0)
    [ "$hot" -ge 100 ] && stop "hotspot ${hot} C"
    [ "$mem" -ge 98 ] && stop "VRAM ${mem} C"
    if [ "$busy" -ge 50 ] && [ "$rpm" -lt 2500 ] && { [ "$hot" -ge 80 ] || [ "$mem" -ge 82 ]; }; then slowfan=$((slowfan + 2)); else slowfan=0; fi
    [ "$slowfan" -ge 20 ] && stop "fan ${rpm} RPM at ${busy}% busy for 20 s while hot (hotspot ${hot} C, VRAM ${mem} C)"
    if [ "$mem" -ge 85 ] || [ "$hot" -ge 90 ]; then
        echo "$(date -u '+%F %T') WARN: hotspot ${hot} C, VRAM ${mem} C, fan ${rpm} RPM, busy ${busy}%" | tee -a "$log"; exit 4
    fi
    sleep 2
done
