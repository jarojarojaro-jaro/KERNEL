#!/bin/bash
# The user's chat server on :8080 around a GPU job.
#   chat8080.sh stop      ONE SIGTERM (after the slot is idle, up to 60 s), wait up to 60 s for the exit, then SIGKILL
#   chat8080.sh restore   run-topka.sh uncensored (production), wait for /health, verify n_ctx 262144
set -u
case ${1:-} in
stop)
    p=$(pgrep -f "llama-server.*--port 8080( |$)") || { echo "chat :8080 not running"; exit 0; }
    for _ in $(seq 60); do curl -s -m 2 127.0.0.1:8080/slots | grep -q '"is_processing":true' || break; sleep 1; done
    kill -TERM $p
    for _ in $(seq 60); do kill -0 $p 2>/dev/null || { echo "chat :8080 stopped"; exit 0; }; sleep 1; done
    kill -KILL $p; echo "chat :8080 SIGKILL after 60 s" ;;
restore)
    pgrep -f "llama-server.*--port 8080( |$)" > /dev/null && { echo "chat :8080 already running"; } || \
        setsid nohup ~/qwen-opt/run-topka.sh uncensored > ~/qwen-opt/l1tok/logs/chat-restore.out 2>&1 < /dev/null &
    for _ in $(seq 300); do curl -sf 127.0.0.1:8080/health > /dev/null && break; sleep 1; done
    curl -sf 127.0.0.1:8080/health > /dev/null || { echo "RESTORE FAILED: no /health" >&2; exit 5; }
    n=$(curl -s 127.0.0.1:8080/props | python3 -c 'import json,sys; print(json.load(sys.stdin)["default_generation_settings"]["n_ctx"])')
    echo "chat :8080 up, n_ctx $n, bin $(readlink -f /proc/$(pgrep -f 'llama-server.*--port 8080( |$)' | head -1)/exe)"
    [ "$n" = 262144 ] || { echo "RESTORE: n_ctx $n != 262144" >&2; exit 6; } ;;
*) echo "usage: chat8080.sh stop|restore" >&2; exit 2 ;;
esac
