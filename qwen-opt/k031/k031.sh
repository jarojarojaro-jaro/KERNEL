#!/usr/bin/env bash
# K-031: host timeline of the decode step at long context, production config on :18795 (../k048/srv.sh) with
# LLAMA_HOSTGAP_TRACE=16. Arm A = production (LLAMA_KV_MASK_FAST default on: fast KQ-mask build), arm B =
# LLAMA_KV_MASK_FAST=0 (generic O(n_kv x n_tokens) loop = a slower host mask). If the step wall grows by B's extra
# `graph->inputs` time, the mask build sits on the critical path and taking it off (K-031) saves A's graph->inputs.
# One arm per job: fresh server, kvq-once/lc.py cold prompt per depth (T=0, 256 tokens, md5), K-033 DPM poll alongside.
# usage: k031.sh A|B LABEL DEPTHS          Queue only.
set -u
arm=$1; label=$2; depths=$3
here=$(cd "$(dirname "$0")" && pwd); . "$here/../k048/srv.sh"
out=$here/out; mkdir -p "$out"
py=$HOME/qwen-opt/.venv/bin/python
env_=(LLAMA_HOSTGAP_TRACE=16); [ "$arm" = B ] && env_+=(LLAMA_KV_MASK_FAST=0)
~/qwen-opt/l1tok/chat8080.sh stop
bash ~/qwen-opt/k033/dpm_poll.sh "$out/dpm-$label.txt" & poll=$!
trap 'kill $poll 2>/dev/null; srv_stop nowait' EXIT
echo "$label: arm $arm env ${env_[*]} depths $depths"
srv_start "$out/$label" "${env_[@]}" || exit 1
timeout "${LC_TIMEOUT:-480}" taskset -c 2-5 "$py" ~/qwen-opt/kvq-once/lc.py --port $PORT --label "$label" --out "$out/lc.jsonl" --depths "$depths"
srv_stop
kill $poll
nice python3 ~/qwen-opt/kvq-once/hg_parse.py "$out/$label.out" --depths "$depths"
nice python3 ~/qwen-opt/k033/dpm_sum.py "$out/dpm-$label.txt"
