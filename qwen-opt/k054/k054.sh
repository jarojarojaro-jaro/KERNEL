#!/usr/bin/env bash
# K-054: EvalPlus codegen (HumanEval+ 164, MBPP+ 378) at --reasoning-effort xhigh in <= 10 min slices.
# usage: k054.sh SLICE [humaneval|mbpp]
# Production config on :18795 (../k048/srv.sh, EFFORT=xhigh), evalplus/gen.py (resumable: done tasks are skipped) into
# ~/qwen-opt/evalplus/runs/uncensored-xhigh/, cut at ~500 s after the job start (the answer in flight is lost and
# redone by the next slice). Compared on the same task subset with runs/uncensored-low (2026-11-09) by k054_cmp.py.
set -u
here=$(cd "$(dirname "$0")" && pwd); . "$here/../k048/srv.sh"
EP=$HOME/qwen-opt/evalplus; R=$EP/runs/uncensored-xhigh; mkdir -p "$R"
ds=${2:-humaneval}
t0=$(date +%s)
~/qwen-opt/l1tok/chat8080.sh stop
trap 'srv_stop nowait' EXIT
srv_start "$R/server-$ds-$1" EFFORT=xhigh || exit 1
curl -s "127.0.0.1:$PORT/props" > "$R/props.json"
left=$(( 500 - ($(date +%s) - t0) ))
before=$(wc -l < "$R/$ds.jsonl" 2>/dev/null || echo 0)
timeout $left "$EP/.venv/bin/python" "$EP/gen.py" --dataset "$ds" --base-url "http://127.0.0.1:$PORT/v1" \
    --model uncensored --out "$R/$ds.jsonl" > "$R/gen-$ds-$1.log" 2>&1
echo "$ds slice $1: rc $? (124 = cut), answers $before -> $(wc -l < "$R/$ds.jsonl"), $(( $(date +%s) - t0 )) s"
