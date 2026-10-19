#!/bin/bash
# GPU safety guard for the local RX 7900 XTX. Polls every 2 s. On any of:
#   - a new amdgpu page fault, ring timeout or GPU reset in the kernel log
#   - hotspot >= 100 C or VRAM >= 98 C
#   - GPU busy >= 50% while the fan is below 2500 RPM for 20 s
# it kills every llama-server / llama-bench / llama-perplexity / test-backend-ops / magnitude-engine,
# writes the reason to ~/qwen-opt/tools/gpu-guard.log and exits 3 (the parent agent is woken up).
# The production server on :8080 is left alone (the user's own).
set -u
log=~/qwen-opt/tools/gpu-guard.log
dev=/sys/class/drm/card0/device
hw=$(echo $dev/hwmon/hwmon*)
since=$(date '+%Y-%m-%d %H:%M:%S')
slowfan=0
stop() {
    echo "$(date -u '+%F %T') STOP: $1" | tee -a "$log"
    for p in $(pgrep -f 'llama-server|llama-bench|llama-perplexity|test-backend-ops|magnitude-engine'); do
        grep -q -- '--port 8080' /proc/$p/cmdline 2>/dev/null && continue
        kill "$p" 2>/dev/null
    done
    sleep 3
    for p in $(pgrep -f 'llama-server|llama-bench|llama-perplexity|test-backend-ops|magnitude-engine'); do
        grep -q -- '--port 8080' /proc/$p/cmdline 2>/dev/null && continue
        kill -9 "$p" 2>/dev/null
    done
    exit 3
}
echo "$(date -u '+%F %T') guard started" >> "$log"
while true; do
    ev=$(journalctl -k --since "$since" --no-pager 2>/dev/null | grep -m1 -E 'amdgpu.*(page fault|ring .* timeout|GPU reset begin|MES might be)')
    [ -n "$ev" ] && stop "kernel: ${ev:0:200}"
    hot=$(( $(cat $hw/temp2_input) / 1000 )); mem=$(( $(cat $hw/temp3_input) / 1000 ))
    busy=$(cat $dev/gpu_busy_percent 2>/dev/null || echo 0); rpm=$(cat $hw/fan1_input 2>/dev/null || echo 0)
    [ "$hot" -ge 100 ] && stop "hotspot ${hot} C"
    [ "$mem" -ge 98 ] && stop "VRAM ${mem} C"
    # firmware zero-RPM keeps the fan stopped while the card is still cool (seen: 0 RPM at hotspot 65-67 C,
    # 3300+ RPM from ~70 C), so a stopped fan only counts as a failure once the card is actually warm
    if [ "$busy" -ge 50 ] && [ "$rpm" -lt 2500 ] && { [ "$hot" -ge 80 ] || [ "$mem" -ge 82 ]; }; then slowfan=$((slowfan + 2)); else slowfan=0; fi
    [ "$slowfan" -ge 20 ] && stop "fan ${rpm} RPM at ${busy}% busy for 20 s while hot (hotspot ${hot} C, VRAM ${mem} C)"
    # early warning (no kill): wake the parent agent so it acts before limits are near
    if [ "$mem" -ge 85 ] || [ "$hot" -ge 90 ]; then
        echo "$(date -u '+%F %T') WARN: hotspot ${hot} C, VRAM ${mem} C, fan ${rpm} RPM, busy ${busy}%" | tee -a "$log"; exit 4
    fi
    sleep 2
done
