#!/usr/bin/env bash
# Destroy an instance (irreversible; storage billing stops only on destroy, not on stop) and print the balance.
#   down.sh [instance_id|--all] [--go]
#   --all   every live instance whose label starts with qwenbench-
# Dry run by default. Also stops the local watchdog of that instance. Always prints the remaining credit.
set -euo pipefail
. "$(dirname "$0")/lib.sh"
if [ "${1:-}" = --all ]; then
    need_key
    ids=$(vastai show instances --raw | jq -r --arg p "$LABEL_PREFIX" '.[] | select((.label // "") | startswith($p)) | .id')
else
    ids=$(inst_id "${1:-}" 2>/dev/null || echo "<instance_id>")
fi
[ -n "$ids" ] || echo "no matching instances"
for iid in $ids; do
    run vastai destroy instance "$iid" -y
    pidf=$STATE/watchdog-$iid.pid
    if [ -f "$pidf" ]; then run kill "$(cat "$pidf")"; [ "$GO" = 1 ] && rm -f "$pidf"; fi
    [ "$GO" = 1 ] && [ "$(cat "$STATE/current" 2>/dev/null)" = "$iid" ] && rm -f "$STATE/current"
done
print_balance
