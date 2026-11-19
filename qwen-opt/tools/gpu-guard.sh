#!/bin/bash
# GPU safety guard for the local RX 7900 XTX.
# Stops every GPU test process (llama-server / llama-bench / llama-perplexity / test-backend-ops / magnitude-engine,
# matched by exact process name, never by command line: `pgrep -f` also matches agent shells, lekcja-pkill-wlasna-
# powloka) except production: the server listening on :8080, or one started with `--port 8080` that is still loading
# (a test server from the same ~/llama-topka binary on another port IS stopped). Exits 3 on:
#   - a new amdgpu page fault, ring timeout or GPU reset in the kernel log
#   - hotspot >= 100 C or VRAM >= 98 C
#   - fan below 2500 RPM at >= 50% busy for 20 s while the card is hot (hotspot >= 80 C or VRAM >= 82 C)
#     (firmware zero-RPM keeps the fan stopped while the card is still cool)
# Early warning at VRAM >= 85 C or hotspot >= 90 C: logged (at most once per 60 s), no kill, and the guard KEEPS
# RUNNING so the stop limits above still apply (2026-11-19: it used to `exit 4` here, which ended all protection).
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
slowfan=0; lastwarn=0
# exact comm names (the kernel truncates comm to 15 characters)
NAMES='^(llama-server|llama-bench|llama-perplexit|test-backend-op|magnitude-engin)$'
victims() {
    local keep p
    keep=$(ss -ltnp 'sport = :8080' 2>/dev/null | grep -o 'pid=[0-9]*' | cut -d= -f2)
    for p in $(pgrep "$NAMES"); do
        [ -n "$keep" ] && [ "$p" = "$keep" ] && continue
        tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null | grep -qE -- '--port 8080( |$)' && continue
        echo "$p"
    done
}
# One SIGTERM, wait up to 60 s for the processes to exit, then SIGKILL the rest (owner's rule: a forced kill in the
# middle of a PM4 replay can turn a fault into a reset; lekcja-pm4-zamienia-fault-w-reset).
stop() {
    echo "$(date -u '+%F %T') STOP: $1" | tee -a "$log"
    local ps left
    ps=$(victims)
    [ -n "$ps" ] && kill -TERM $ps 2>/dev/null
    for _ in $(seq 60); do
        left=$(for p in $ps; do kill -0 "$p" 2>/dev/null && echo "$p"; done)
        [ -z "$left" ] && break
        sleep 1
    done
    [ -n "${left:-}" ] && { echo "$(date -u '+%F %T') SIGKILL after 60 s: $left" >> "$log"; kill -KILL $left 2>/dev/null; }
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
        now=$(date +%s)
        if [ $((now - lastwarn)) -ge 60 ]; then
            echo "$(date -u '+%F %T') WARN: hotspot ${hot} C, VRAM ${mem} C, fan ${rpm} RPM, busy ${busy}%" | tee -a "$log"
            lastwarn=$now
        fi
    fi
    sleep 2
done
