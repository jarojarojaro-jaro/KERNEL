#!/usr/bin/env bash
# push-diff.sh <iid> <name> <worktree> [base=nv-3090-base]: seed /root/src/<name> from /root/src/nv0 on the instance,
# then rsync only the files that differ between <base> (the commit /root/src/nv0 was pushed from) and the worktree
# (committed + uncommitted), then build detached. Faster than push-src.sh over a slow uplink. nv-3090 round 2026-10-20.
set -euo pipefail
iid=$1; n=$2; wt=$3; base=${4:-123f93c1f}
NV=$HOME/qwen-opt/cloud/runs/nvfinal
. "$NV/lib.sh" > /dev/null 2>&1
read -r SSH_HOST SSH_PORT < "$NV/state/ssh-$iid"
e="ssh ${SSH_OPTS[*]} -o LogLevel=ERROR -p $SSH_PORT"
files=$(cd "$wt" && { git diff --name-only "$base"; git ls-files --others --exclude-standard; } | sort -u | grep -v '^build' || true)
echo "files: $files"
$e "root@$SSH_HOST" "rm -rf /root/src/$n && cp -a /root/src/nv0 /root/src/$n"
[ -n "$files" ] && (cd "$wt" && printf '%s\n' $files | rsync -az --files-from=- -e "$e" ./ "root@$SSH_HOST:/root/src/$n/")
rsync -az -e "$e" "$HOME/qwen-opt/cloud/runs/nv3090/inst/" "root@$SSH_HOST:/root/cloud/"
[ -n "${NOBUILD:-}" ] && { echo "pushed $n (no build)"; exit 0; }
$e "root@$SSH_HOST" "cd /root/cloud && chmod +x *.sh && setsid nohup ./build.sh $n > /root/build-$n.out 2>&1 < /dev/null & echo build $n started"
