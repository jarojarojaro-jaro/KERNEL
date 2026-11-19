# onstart-guard.sh: body of the Vast --onstart script (launch.sh prepends LIFE_S=, IDLE_S=, GRACE_S=, SETUP_S=).
# Instance-side cost guard, the backup of the Jarvo server's vast-reaper.sh (owner 2026-11-19: cards never sit idle).
# The instance deletes itself (CONTAINER_API_KEY) when:
#   older than LIFE_S; no /root/res/phases.txt SETUP_S after boot (setup never ran); the runner (/root/k114/run*) is gone
#   without /root/res/FINISHED for 5 min; every GPU < 5% for IDLE_S after the runner wrote "ready"; GRACE_S after FINISHED
#   (vast-reaper copies the results and destroys within ~2 min, this only fires when the server is down).
export -p | grep -E ' (CONTAINER_ID|CONTAINER_API_KEY)=' > /root/guard.env
printf 'LIFE_S=%s IDLE_S=%s GRACE_S=%s SETUP_S=%s\n' "$LIFE_S" "$IDLE_S" "$GRACE_S" "$SETUP_S" >> /root/guard.env
command -v curl > /dev/null || { apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq curl ca-certificates; } > /root/onstart-curl.log 2>&1
cat > /root/guard.sh <<'G'
#!/bin/bash
. /root/guard.env
gone() {
    echo "$(date +%T) $1: deleting myself" >> /root/guard.log
    curl -fsS -X DELETE -H "Authorization: Bearer $CONTAINER_API_KEY" "https://console.vast.ai/api/v0/instances/$CONTAINER_ID/" >> /root/guard.log 2>&1
}
t0=$(date +%s) idle=0 dead=0 fin=0
while sleep 30; do
    age=$(( $(date +%s) - t0 ))
    if [ $age -ge "$LIFE_S" ]; then gone "life ${LIFE_S}s"; continue; fi
    if [ -f /root/res/FINISHED ]; then fin=$((fin + 30)); [ $fin -ge "$GRACE_S" ] && gone "finished ${GRACE_S}s ago"; continue; fi
    if [ ! -f /root/res/phases.txt ]; then [ $age -ge "$SETUP_S" ] && gone "no runner after ${SETUP_S}s"; continue; fi
    if ! pgrep -f "[/]root/k114/run" > /dev/null; then dead=$((dead + 30)); [ $dead -ge 300 ] && gone "runner gone 300s"; continue; fi
    dead=0
    grep -q " ready" /root/res/phases.txt || continue
    u=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits | sort -n | tail -1)
    if [ "${u:-0}" -lt 5 ]; then idle=$((idle + 30)); else idle=0; fi
    [ $idle -ge "$IDLE_S" ] && gone "GPU idle ${IDLE_S}s"
done
G
chmod +x /root/guard.sh
nohup setsid /root/guard.sh > /dev/null 2>&1 < /dev/null &
