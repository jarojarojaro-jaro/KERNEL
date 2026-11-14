#!/usr/bin/env bash
# jakość-mini on THIS machine's GPU for a run-topka.sh model profile (other hosts: run.py gen --base-url ... directly).
#
#   local.sh [--profile uncensored] [--port 8098] [--effort low] [--label qwen-unc] [--seed 20261109]
#            [--reuse-humaneval DIR] [--after PID] CMD
#
#   all      submit + code-eval + report (blocks until the queue has run the job; --after PID first waits for PID to exit,
#            e.g. an earlier queue runner this job must follow)
#   submit   write <label>.jobs (gen + restore) and run it through ~/qwen-opt/queue/run-jobs.sh (FIFO, GPU locks)
#   gen      [GPU, inside the queue] `PORT=<port> EFFORT=<effort> run-topka.sh <profile>` on its own port, run.py gen
#            (290 questions, T=0, sequential), stop the server (ONE SIGTERM, 60 s, then SIGKILL)
#   restore  [inside the queue] production :8080 = run-topka.sh uncensored; checks /health, n_ctx 262144 and the binary
#            ~/llama-topka/bin/llama-server
#   eval     [CPU, outside the queue] run.py code-eval: HumanEval+ in the sandbox (nice 19, systemd scope 4G / 200%)
#   report   run.py report -> runs/<label>-<effort>-s<seed>/summary.{md,json}
# run-topka.sh / run-llm.sh variables (CTX, KV, DRAFT_N, ROCM_DIR, EXTRA_ARGS, ...) pass through the environment.
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
profile=uncensored port=8098 effort=low label=qwen-unc seed=20261109 reuse= after=
while [ $# -gt 1 ]; do
    case $1 in
        --profile) profile=$2; shift 2 ;; --port) port=$2; shift 2 ;; --effort) effort=$2; shift 2 ;;
        --label) label=$2; shift 2 ;; --seed) seed=$2; shift 2 ;; --reuse-humaneval) reuse=$2; shift 2 ;;
        --after) after=$2; shift 2 ;;
        *) echo "unknown option $1" >&2; exit 2 ;;
    esac
done
cmd=${1:?usage: local.sh [options] all|submit|gen|restore|eval|report}
R=$D/runs/$label-$effort-s$seed; mkdir -p "$R"
PY=${PY:-$HOME/qwen-opt/evalplus/.venv/bin/python}
[ "$port" = 8080 ] && [ "$cmd" = gen ] && { echo "gen must not use the production port 8080" >&2; exit 2; }

srv_pid() { pgrep -f "llama-server.*--port $1( |$)" | head -1; }
stop_srv() {  # ONE SIGTERM, wait 60 s, then SIGKILL
    local p; p=$(srv_pid "$1") || return 0; [ -n "$p" ] || return 0
    kill -TERM "$p"
    for _ in $(seq 60); do kill -0 "$p" 2>/dev/null || { echo "server :$1 stopped"; return 0; }; sleep 1; done
    kill -KILL "$p"; echo "server :$1 SIGKILL after 60 s"
}

case $cmd in
gen)
    [ -n "$(srv_pid "$port")" ] && { echo "port $port already has a llama-server" >&2; exit 3; }
    trap 'stop_srv $port' EXIT
    PORT=$port EFFORT=$effort LOG=$R/server.log setsid nohup ~/qwen-opt/run-topka.sh "$profile" > "$R/server.out" 2>&1 < /dev/null &
    for _ in $(seq 600); do curl -sf "127.0.0.1:$port/health" > /dev/null && break; sleep 1; done
    curl -sf "127.0.0.1:$port/health" > /dev/null || { echo "server :$port did not come up" >&2; tail -20 "$R/server.out"; exit 4; }
    echo "server :$port up, bin $(readlink -f /proc/$(srv_pid "$port")/exe), profile $profile, effort $effort"
    "$PY" "$D/run.py" gen --port "$port" --model-label "$label" --effort "$effort" --seed "$seed" --out "$R" \
        ${reuse:+--reuse-humaneval "$reuse"} ;;
restore)
    if [ -z "$(srv_pid 8080)" ]; then
        setsid nohup ~/qwen-opt/run-topka.sh uncensored > "$R/restore.out" 2>&1 < /dev/null &
    else echo "chat :8080 already running"; fi
    for _ in $(seq 300); do curl -sf 127.0.0.1:8080/health > /dev/null && break; sleep 1; done
    curl -sf 127.0.0.1:8080/health > /dev/null || { echo "RESTORE FAILED: no /health" >&2; exit 5; }
    n=$(curl -s 127.0.0.1:8080/props | python3 -c 'import json,sys; print(json.load(sys.stdin)["default_generation_settings"]["n_ctx"])')
    bin=$(readlink -f "/proc/$(srv_pid 8080)/exe")
    echo "chat :8080 up, n_ctx $n, bin $bin"
    [ "$n" = 262144 ] || { echo "RESTORE: n_ctx $n != 262144" >&2; exit 6; }
    [ "$bin" = "$HOME/llama-topka/bin/llama-server" ] || { echo "RESTORE: binary $bin" >&2; exit 7; } ;;
submit)
    J=$D/$label.jobs
    env_pass=""; for v in CTX KV DRAFT_N ROCM_DIR EXTRA_ARGS LLAMA_SPEC_LOOKUP; do [ -n "${!v:-}" ] && env_pass+="$v=${!v} "; done
    cat > "$J.tmp" <<EOF
# jakość-mini $label: run-topka.sh $profile, effort $effort, seed $seed, own port $port ($(date -u '+%F %T'), local.sh submit).
# HumanEval+ code runs afterwards on CPU in the sandbox (local.sh eval), outside the queue.
jakosc-$label-gen|21600|$D|${env_pass}./local.sh --profile $profile --port $port --effort $effort --label $label --seed $seed${reuse:+ --reuse-humaneval $reuse} gen
jakosc-$label-restore8080|600|$D|./local.sh --label $label --effort $effort --seed $seed restore
EOF
    mv "$J.tmp" "$J"
    if [ -n "$after" ]; then
        echo "waiting for pid $after to exit before queueing"
        while kill -0 "$after" 2>/dev/null; do sleep 20; done
    fi
    ~/qwen-opt/queue/run-jobs.sh "$J" ;;
eval) "$PY" "$D/run.py" code-eval "$R" ;;
report) "$PY" "$D/run.py" report "$R" ;;
all) "$0" --profile "$profile" --port "$port" --effort "$effort" --label "$label" --seed "$seed" \
        ${reuse:+--reuse-humaneval "$reuse"} ${after:+--after "$after"} submit
     grep -q "END   jakosc-$label-gen rc=0" ~/qwen-opt/queue/logs/queue.log || echo "WARNING: gen job did not end rc=0" >&2
     "$0" --label "$label" --effort "$effort" --seed "$seed" eval
     "$0" --label "$label" --effort "$effort" --seed "$seed" report ;;
*) echo "unknown command $cmd" >&2; exit 2 ;;
esac
