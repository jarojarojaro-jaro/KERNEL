#!/usr/bin/env bash
# Local kill timer: destroys a Vast instance N hours after start (up.sh launches it detached with --go).
#   watchdog.sh <instance_id> <hours> [--go]
# Exits early when the instance is gone (down.sh, self-destruct). Without --go it only prints what it would do.
set -uo pipefail
. "$(dirname "$0")/lib.sh"
[ $# -ge 2 ] || { sed -n 2,4p "$0"; exit 2; }
iid=$1; hours=$2
deadline=$(jq -r '.deadline // empty' "$STATE/$iid.json" 2>/dev/null | cut -d. -f1)
[ -n "$deadline" ] || deadline=$(awk -v h="$hours" -v t="$(date +%s)" 'BEGIN { printf "%d", t + h * 3600 }')
if [ "$GO" != 1 ]; then
    echo "[dry-run] would destroy instance $iid at $(date -d "@$deadline" '+%F %T'), polling every 60 s"
    run vastai destroy instance "$iid" -y
    exit 0
fi
need_key
echo $$ > "$STATE/watchdog-$iid.pid"
echo "$(date '+%F %T') watchdog for $iid, deadline $(date -d "@$deadline" '+%F %T')"
while [ "$(date +%s)" -lt "$deadline" ]; do
    sleep 60
    # gone = the instance list came back as a JSON array without it; API errors never end the watchdog
    l=$(vastai show instances --raw 2>/dev/null)
    if jq -e --argjson id "$iid" 'type == "array" and (map(select(.id == $id)) | length == 0)' <<<"$l" > /dev/null 2>&1; then
        echo "$(date '+%F %T') instance $iid is gone; watchdog exits"
        rm -f "$STATE/watchdog-$iid.pid"; exit 0
    fi
done
for i in 1 2 3 4 5; do
    echo "$(date '+%F %T') deadline reached, destroying $iid (try $i)"
    vastai destroy instance "$iid" -y && break
    sleep 30
done
rm -f "$STATE/watchdog-$iid.pid"
print_balance
