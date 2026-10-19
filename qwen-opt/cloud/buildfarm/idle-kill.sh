#!/usr/bin/env bash
# Runs ON the build server: destroys the instance (Vast API, per-instance CONTAINER_API_KEY) when no build has run
# for IDLE_S seconds (default 1800). remote-build.sh touches /root/bf/last-activity at start and end and holds
# /root/bf/active.lock shared while it builds, so a long build never counts as idle.
IDLE_S=${IDLE_S:-1800}
BF=/root/bf
set -a; . /etc/environment; set +a
while sleep 60; do
    flock -n -x "$BF/active.lock" true || continue          # a build is running
    age=$(( $(date +%s) - $(stat -c %Y "$BF/last-activity" 2>/dev/null || echo 0) ))
    [ "$age" -ge "$IDLE_S" ] || continue
    echo "$(date '+%F %T') idle ${age}s >= ${IDLE_S}s, destroying instance $CONTAINER_ID"
    curl -fsS -X DELETE -H "Authorization: Bearer $CONTAINER_API_KEY" \
        "https://console.vast.ai/api/v0/instances/$CONTAINER_ID/" && break
done
