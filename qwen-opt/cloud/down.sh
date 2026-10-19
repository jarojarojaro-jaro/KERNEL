#!/usr/bin/env bash
# Destroy an instance (irreversible; storage billing stops only on destroy, not on stop) and print the balance.
#   down.sh [instance_id|--all] [--go]
#   --all   every live instance whose label starts with qwenbench- (never buildfarm-*)
# Dry run by default. Also stops the local watchdog of that instance. Always prints the remaining credit.
# buildfarm-* (the rbuild build server, shared by all agents) is destroyed only when its id is passed explicitly;
# use ~/qwen-opt/cloud/buildfarm.sh down for it.
set -euo pipefail
. "$(dirname "$0")/lib.sh"
if [ "${1:-}" = --all ]; then
    need_key
    ids=$(vastai show instances --raw | jq -r --arg p "$LABEL_PREFIX" \
        '.[] | select((.label // "") | startswith($p) and (startswith("buildfarm") | not)) | .id')
elif [ -n "${1:-}" ]; then
    ids=$1
else
    ids=$(inst_id 2>/dev/null || echo "<instance_id>")
    if [ "$ids" != "<instance_id>" ] && [ -n "${VAST_API_KEY:-}" ] &&
       inst_json "$ids" | jq -e '(.label // "") | startswith("buildfarm")' > /dev/null 2>&1; then
        die "state/current $ids is the buildfarm build server; pass its id explicitly (or buildfarm.sh down)"
    fi
fi
[ -n "$ids" ] || echo "no matching instances"
for iid in $ids; do
    run vastai destroy instance "$iid" -y
    pidf=$STATE/watchdog-$iid.pid
    if [ -f "$pidf" ]; then run kill "$(cat "$pidf")"; [ "$GO" = 1 ] && rm -f "$pidf"; fi
    [ "$GO" = 1 ] && [ "$(cat "$STATE/current" 2>/dev/null)" = "$iid" ] && rm -f "$STATE/current"
done
print_balance
