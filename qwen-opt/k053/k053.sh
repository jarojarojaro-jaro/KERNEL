#!/usr/bin/env bash
# K-053: NInfer/YASAKANI scenario fixtures on the production config (:18795, ../k048/srv.sh). usage: k053.sh LABEL NAME...
set -u
label=$1; shift
here=$(cd "$(dirname "$0")" && pwd); . "$here/../k048/srv.sh"
out=$here/out; mkdir -p "$out"
~/qwen-opt/l1tok/chat8080.sh stop
trap 'srv_stop nowait' EXIT
srv_start "$out/$label" || exit 1
timeout 520 taskset -c 2-5 python3 "$here/k053.py" --port $PORT --out "$out/k053.jsonl" "$@"
