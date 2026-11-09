#!/usr/bin/env bash
# R69b Q1 local helper:  q.sh ssh <cmd> | push | collect   (instance = ~/qwen-opt/cloud/state/current)
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
cmd=${1:-}; shift || true
REST=("$@")
cd "$HOME/qwen-opt/cloud"
set --
. ./lib.sh
iid=$(cat "$STATE/current")
f=$HERE/ep
if [ -s "$f" ] && [ "$(cut -d' ' -f1 "$f")" = "$iid" ]; then read -r _ SSH_HOST SSH_PORT < "$f"
else inst_ssh "$iid" && echo "$iid $SSH_HOST $SSH_PORT" > "$f"; fi
case $cmd in
    ssh) ssh "${SSH_OPTS[@]}" -o LogLevel=ERROR -p "$SSH_PORT" "root@$SSH_HOST" "${REST[@]}" ;;
    push)
        ssh "${SSH_OPTS[@]}" -o LogLevel=ERROR -p "$SSH_PORT" "root@$SSH_HOST" "mkdir -p /root/nv"
        scp "${SSH_OPTS[@]}" -o LogLevel=ERROR -P "$SSH_PORT" -q "$HERE"/inst/* "$HOME/KERNEL/app/engine/data/corpus.txt" "root@$SSH_HOST:/root/nv/" ;;
    collect)
        dst=$HOME/qwen-opt/cloud/results/nv69q-3090-$(date +%Y%m%d); mkdir -p "$dst"
        rsync -a --exclude docs -e "ssh ${SSH_OPTS[*]} -o LogLevel=ERROR -p $SSH_PORT" "root@$SSH_HOST:/root/res/" "$dst/"
        echo "collected -> $dst" ;;
    *) echo "usage: q.sh ssh <cmd> | push | collect"; exit 2 ;;
esac
