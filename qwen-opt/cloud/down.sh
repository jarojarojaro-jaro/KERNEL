#!/usr/bin/env bash
# Destroy instances by id (irreversible; storage billing stops only on destroy, not on stop) and print the balance.
#   down.sh [instance_id ...] [--go]      (no id: the one up.sh recorded last in state/current)
# Dry run by default. Also stops the local watchdog of each instance. Always prints the remaining credit.
# By id only (decision 2026-10-19 „chmura bez destroy all”): there is no --all; buildfarm-* (the rbuild build server,
# shared by all agents) is refused unless its id is passed explicitly — use ~/qwen-opt/cloud/buildfarm.sh down for it.
set -euo pipefail
. "$(dirname "$0")/lib.sh"
[ "${1:-}" = --all ] && die "--all was removed (decision 2026-10-19: destroy only by id); pass the instance ids"
if [ $# -gt 0 ]; then
    ids="$*"
else
    ids=$(inst_id 2>/dev/null || echo "<instance_id>")
    if [ "$ids" != "<instance_id>" ] && [ -n "${VAST_API_KEY:-}" ] &&
       inst_json "$ids" | jq -e '(.label // "") | startswith("buildfarm")' > /dev/null 2>&1; then
        die "state/current $ids is the buildfarm build server; pass its id explicitly (or buildfarm.sh down)"
    fi
fi
for iid in $ids; do
    run vastai destroy instance "$iid" -y
    pidf=$STATE/watchdog-$iid.pid
    if [ -f "$pidf" ]; then run kill "$(cat "$pidf")"; [ "$GO" = 1 ] && rm -f "$pidf"; fi
    [ "$GO" = 1 ] && [ "$(cat "$STATE/current" 2>/dev/null)" = "$iid" ] && rm -f "$STATE/current"
done
print_balance
