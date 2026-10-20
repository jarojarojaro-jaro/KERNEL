#!/usr/bin/env bash
# Pull the results of an instance into ~/qwen-opt/cloud/results/<class>-<date>/ (rsync, resumable).
#   collect.sh [instance_id] [--go]      (dry run by default; instance id defaults to the last one from up.sh)
# Copies /root/results/ (bench data, logs, hw snapshot) plus /root/run.log; never the models or build trees.
set -euo pipefail
. "$(dirname "$0")/lib.sh"
dest=$CLOUD_DIR/results
if [ "$GO" = 1 ]; then
    iid=$(inst_id "${1:-}"); need_key
    inst_ssh "$iid" || die "no ssh endpoint for $iid"
else
    iid=$(inst_id "${1:-}" 2>/dev/null || echo "<instance_id>")
    SSH_HOST="<host>"; SSH_PORT="<port>"
fi
ssh_cmd="ssh $(printf '%q ' "${SSH_OPTS[@]}")-p $SSH_PORT"
run mkdir -p "$dest"
# /root/results/<class>-<date>/ -> results/<class>-<date>/ ; "current" is a symlink on the instance, skip it.
# --backup: a later instance of the same class+date must never silently overwrite earlier local results
# (2026-10-18: a QuantKLD 3060 overwrote report 09's hw/ and build/ in results/3060-20261016/).
run rsync -az --partial --backup --suffix=".prev-$(date +%Y%m%d%H%M%S)" --exclude current -e "$ssh_cmd" "root@$SSH_HOST:/root/results/" "$dest/"
run rsync -az -e "$ssh_cmd" "root@$SSH_HOST:/root/run.log" "$dest/run-$iid.log"
[ "$GO" = 1 ] && ls -d "$dest"/*/ | tail -3
print_balance
