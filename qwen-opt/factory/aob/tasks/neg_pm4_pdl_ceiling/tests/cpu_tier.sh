#!/usr/bin/env bash
# CPU tier (21i §5.2 item 1), hidden; run by the planner after the agent phase. Never touches the GPU.
# Prints one JSON line: {"cpu_pass": 0|1, "f2p_cpu": 0..1}
set -euo pipefail
WS=${WS:?}
STATUS=ready
if [ "$STATUS" != ready ]; then echo '{"cpu_pass": null, "reason": "needs-fixture"}'; exit 2; fi
WS="$WS" bash "$(dirname "$0")/../environment/build.sh" >/dev/null && echo '{"cpu_pass": 1, "f2p_cpu": null}' || echo '{"cpu_pass": 0, "f2p_cpu": 0}'
