#!/bin/bash
# Sequential GPU test queue driven by a jobs file: ONE job at a time, GPU + quiet locks held across the whole file,
# topka stopped once at the start (topka-keeper brings it back afterwards). After every job the kernel log is checked
# for amdgpu faults/resets; the first one stops the queue (hardware rule). Job fds 8/9 are closed so nothing a job
# leaves behind can inherit the locks.
# Usage: run-jobs.sh JOBS_FILE      lines: name|timeout_s|cwd|command   (# comments, blank lines ignored)
# Logs: ~/qwen-opt/queue/logs/<name>.log and queue.log. Never edit a jobs file or this script while it runs
# (replace it atomically with mv). Cancel a waiting/running file: ~/qwen-opt/queue/cancel.sh <name>.
set -u
# Hardware safety: every build of our fork runs PM4 replay WHEN GGML_HIP_PM4 IS UNSET, in mode WA=0 (no GFX11 PRIV
# fix, report 17) — that path caused the 2026-10-19 21:10 page fault + GPU reset (norm-fuse tests had no PM4 env).
# Jobs get PM4 off unless they set it themselves (topka-config jobs export PM4=1 WA=2 GUARD=1 HSA_USE_SVM=0).
# QUEUE_PM4_SAFETY=1 marks that the 0 is this safety default, not a job's choice: run-topka.sh (the verified production
# config) then uses production PM4 instead of silently running PM4 off (2026-10-20: 136.2 vs 144.4 t/s, report 35).
[ -z "${GGML_HIP_PM4:-}" ] && export QUEUE_PM4_SAFETY=1
export GGML_HIP_PM4=${GGML_HIP_PM4:-0}
jobs=$1; L=~/qwen-opt/queue/logs; mkdir -p "$L"
log() { echo "$(date -u '+%F %T') $*" | tee -a "$L/queue.log"; }
mapfile -t JOBS < <(grep -vE '^\s*(#|$)' "$jobs")

# FIFO (2026-10-21): flock is not fair; with 10+ waiting runners one waited >1 h and lost its slot. Each runner takes
# a ticket and only competes for the GPU lock when it holds the oldest live ticket. Lock users outside the queue
# (topka-keeper, topka-restart, cpuheavy) are unaffected.
T=/tmp/gpu-tickets
ticket() { ( flock 7; "$@" ) 7>>/tmp/gpu-ticket.lock; }
take() { echo "$$ $(date +%s%N)" >> "$T"; }
prune() {
    local l out=""
    [ -f "$T" ] || return 0
    while read -r l; do
        [ -n "$l" ] && kill -0 "${l%% *}" 2>/dev/null && out+="$l"$'\n'
    done < "$T"
    printf '%s' "$out" > "$T"
}
drop() { grep -v "^$$ " "$T" > "$T.tmp"; mv "$T.tmp" "$T"; }
ticket take
log "queue $jobs: ${#JOBS[@]} jobs, ticket $$ (in line: $(grep -c . "$T")), waiting"
while :; do
    ticket prune
    [ "$(head -1 "$T" | cut -d' ' -f1)" = "$$" ] && break
    sleep 2
done
exec 8>>/tmp/gpu.lock 9>>/tmp/quiet.lock
flock 8; flock 9
ticket drop
log "queue: locks held, stopping topka"
# Wait for the process to EXIT, not just the port to close: VRAM is freed only at exit (2026-10-19 20:26 the first
# job's server OOM'd at load because topka still held 15.7 GB right after its port closed).
pkill -f 'llama-topka/bin/llama-server'; for _ in $(seq 60); do pgrep -f 'llama-topka/bin/llama-server' >/dev/null || break; sleep 1; done
for _ in $(seq 30); do [ "$(rocm-smi --showmemuse 2>/dev/null | grep -o 'VRAM%): [0-9]*' | grep -o '[0-9]*$')" -lt 10 ] 2>/dev/null && break; sleep 1; done
log "queue: topka stopped, VRAM $(rocm-smi --showmemuse 2>/dev/null | grep -o 'VRAM%): [0-9]*')"
for j in "${JOBS[@]}"; do
    IFS='|' read -r name to dir cmd <<<"$j"
    since=$(date '+%F %T'); t0=$(date +%s)
    log "START $name (timeout ${to}s): $cmd"
    ( cd "${dir/#\~/$HOME}" && exec 8>&- 9>&- && timeout "$to" bash -c "$cmd" ) > "$L/$name.log" 2>&1
    rc=$?
    log "END   $name rc=$rc $(( $(date +%s) - t0 ))s  $(rocm-smi --showtemp 2>/dev/null | grep -m1 -o 'junction) (C): [0-9.]*')"
    if journalctl -k --since "$since" --no-pager 2>/dev/null | grep -qiE 'amdgpu.*(page fault|fault|ring .* timeout|gpu reset|reset begin)'; then
        log "GPU FAULT after $name -> queue stopped"; journalctl -k --since "$since" --no-pager | grep -iE amdgpu | tail -20 >> "$L/queue.log"; exit 3
    fi
done
log "queue $jobs: done"
