# Sourced by the K-0xx queue job scripts (k048, k031, k053, k054): a test server of the PRODUCTION config
# (run-topka.sh uncensored: PM4 1 WA 2 GUARD 1, HSA_USE_SVM 0, MTP n4, lookup W16, ctx 262144) on port 18795, never 8080.
#   srv_start LOGPREFIX [VAR=value ...]   extra env for run-topka.sh/run-llm.sh (EXTRA_ARGS=-ub,1024, EFFORT=xhigh, ...)
#   srv_stop [nowait]                     ONE SIGTERM (after the slot is idle unless nowait), 60 s, then SIGKILL, by PID
PORT=18795
srv_pid() { pgrep -f "llama-server.*--port $PORT( |$)" | head -1; }
srv_start() {
    local log=$1; shift
    [ -n "$(srv_pid)" ] && { echo "port $PORT already has a llama-server"; return 1; }
    env "$@" PORT=$PORT LOG="$log.log" setsid nohup ~/qwen-opt/run-topka.sh uncensored > "$log.out" 2>&1 < /dev/null &
    for _ in $(seq 300); do curl -sf "127.0.0.1:$PORT/health" > /dev/null && return 0; sleep 1; done
    echo "server :$PORT did not come up ($log.out)"; tail -5 "$log.out"; srv_stop nowait; return 1
}
srv_stop() {
    local p; p=$(srv_pid); [ -n "$p" ] || return 0
    [ "${1:-}" = nowait ] || for _ in $(seq 60); do
        curl -s -m 2 "127.0.0.1:$PORT/slots" | grep -q '"is_processing":true' || break; sleep 1; done
    kill -TERM "$p"
    for _ in $(seq 60); do kill -0 "$p" 2>/dev/null || return 0; sleep 1; done
    kill -KILL "$p"; echo "server :$PORT SIGKILL after 60 s"
}
vram_mib() { echo $(( $(cat /sys/class/drm/card0/device/mem_info_vram_used) / 1048576 )); }
