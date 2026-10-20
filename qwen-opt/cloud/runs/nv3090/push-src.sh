#!/usr/bin/env bash
# push-src.sh <iid> <name> [worktree] : rsync a worktree (sources only) to /root/src/<name> on the instance and
# the inst/ scripts to /root/cloud, then build it detached (build.sh <name>). nv-3090 round 2026-10-20.
set -euo pipefail
iid=$1; n=$2; wt=${3:-$HOME/wt/nv-3090}
NV=$HOME/qwen-opt/cloud/runs/nvfinal
. "$NV/lib.sh" > /dev/null 2>&1
read -r SSH_HOST SSH_PORT < "$NV/state/ssh-$iid"
e="ssh ${SSH_OPTS[*]} -o LogLevel=ERROR -p $SSH_PORT"
git -C "$wt" rev-parse --short HEAD > "$wt/.nv-head"; git -C "$wt" diff --stat >> "$wt/.nv-head"
$e "root@$SSH_HOST" "[ -d /root/src/$n ] || cp -a /root/src/nv0 /root/src/$n"
rsync -az --delete -e "$e" --exclude .git --exclude '/build*/' --exclude '*.gguf' --exclude /models --exclude /docs --exclude /media \
    "$wt/" "root@$SSH_HOST:/root/src/$n/"
rsync -az -e "$e" "$HOME/qwen-opt/cloud/runs/nv3090/inst/" "root@$SSH_HOST:/root/cloud/"
$e "root@$SSH_HOST" "cd /root/cloud && chmod +x *.sh && setsid nohup ./build.sh $n > /root/build-$n.out 2>&1 < /dev/null & echo build $n started"
