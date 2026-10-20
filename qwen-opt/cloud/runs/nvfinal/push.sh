#!/usr/bin/env bash
# push.sh <instance_id> <qwen|uncensored> --go : prebuilt binaries (upstream, topka2) + instance scripts, then
# boot.sh <model> detached.
set -euo pipefail
. "$(dirname "$0")/lib.sh"
iid=$1; model=$2
for p in upstream topka2; do
    [ -f "$STATE/$p.tar.zst" ] || run tar -C "$RUN_DIR/pkg/$p" --zstd -cf "$STATE/$p.tar.zst" .
done
files=("$RUN_DIR"/inst/* "$STATE/upstream.tar.zst" "$STATE/topka2.tar.zst")
[ "$GO" = 1 ] && { inst_ssh "$iid" || die "no ssh endpoint for $iid"; } || { SSH_HOST="<host>"; SSH_PORT="<port>"; }
run ssh "${SSH_OPTS[@]}" -p "$SSH_PORT" "root@$SSH_HOST" mkdir -p /root/cloud
run scp "${SSH_OPTS[@]}" -P "$SSH_PORT" "${files[@]}" "root@$SSH_HOST:/root/cloud/"
run ssh "${SSH_OPTS[@]}" -p "$SSH_PORT" "root@$SSH_HOST" \
    "cd /root/cloud && chmod +x *.sh && setsid nohup ./boot.sh $model > /root/run.log 2>&1 < /dev/null &"
