# report 58: graceful server stop (report 55): wait until /slots is idle (60 s max), ONE SIGTERM, 45 s, SIGKILL only
# as a last resort (never mid PM4 tape). Source it; usage: ds_stop PORT PGREP_PATTERN   (returns 1 if nothing ran)
ds_stop() {
    local port=$1 pat=$2
    pgrep -f "$pat" > /dev/null || return 1
    for _ in $(seq 60); do
        curl -s -m 2 "127.0.0.1:$port/slots" 2>/dev/null | grep -q '"is_processing":true' || break
        sleep 1
    done
    pkill -TERM -f "$pat" || true
    for _ in $(seq 45); do pgrep -f "$pat" > /dev/null || return 0; sleep 1; done
    echo "ds_stop: '$pat' still up after 45 s, SIGKILL" >&2
    pkill -KILL -f "$pat" || true
    sleep 2
}
