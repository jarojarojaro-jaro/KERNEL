#!/usr/bin/env bash
# K-051: kernel-log lines "init_user_pages: Failed to get user pages" per server start, mmap vs no mmap
# (topka flag `-lm mmap` / `-lm none`; production config on test port 18795, server stopped after health). Queue only.
set -u
export GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0
cnt() { journalctl -k -b 0 --no-pager 2>/dev/null | grep -c 'init_user_pages: Failed to get user pages'; }
for mode in mmap none mmap none; do
    n0=$(cnt); t0=$(date +%s)
    PORT=18795 LOG=/tmp/k051-$mode.log EXTRA_ARGS=-lm,$mode setsid ~/qwen-opt/run-topka.sh uncensored > /tmp/k051-$mode.launch.log 2>&1 &
    srv=$!
    for _ in $(seq 240); do curl -sf 127.0.0.1:18795/health > /dev/null && break; kill -0 $srv 2>/dev/null || break; sleep 1; done
    up=$(( $(date +%s) - t0 )); ok=$(curl -s 127.0.0.1:18795/health)
    sleep 3
    kill -TERM -- -$srv 2>/dev/null; for _ in $(seq 30); do kill -0 $srv 2>/dev/null || break; sleep 1; done; kill -KILL -- -$srv 2>/dev/null
    sleep 2; n1=$(cnt)
    echo "K051 -lm $mode: init_user_pages lines $((n1 - n0)), start-to-health ${up}s, health: $ok"
done
