#!/usr/bin/env bash
# launch.sh <offer_id> <label> : rent one Vast offer from the Jarvo server (vastai in ~/.local/bin, key ~/.ssh/vast_kernel),
# arm two kill timers (on-instance self-destruct via CONTAINER_API_KEY after LIFE_S+600 s, local watchdog after LIFE_S),
# copy run.sh + bench.py, start the runner detached. Prints the instance id. Destroy by id only: vastai destroy instance <id>.
set -euo pipefail
export PATH=$HOME/.local/bin:$PATH
offer=$1 label=$2 LIFE_S=${LIFE_S:-4200}
D=$(cd "$(dirname "$0")" && pwd); ST=$D/state; mkdir -p "$ST"
KEY=$HOME/.ssh/vast_kernel
cat > "$ST/onstart-$label.sh" <<EOF
env | grep -E '^(CONTAINER_ID|CONTAINER_API_KEY)=' >> /etc/environment
command -v curl > /dev/null || { apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq curl ca-certificates; } > /root/onstart-curl.log 2>&1
nohup setsid bash -c 'sleep $((LIFE_S + 600)); curl -fsS -X DELETE -H "Authorization: Bearer \$CONTAINER_API_KEY" "https://console.vast.ai/api/v0/instances/\$CONTAINER_ID/"' > /root/self-destruct.log 2>&1 < /dev/null &
EOF
out=$(vastai create instance "$offer" --image nvidia/cuda:12.8.1-base-ubuntu24.04 --disk 30 --ssh --direct \
      --label "$label" --cancel-unavail --onstart "$ST/onstart-$label.sh" --raw)
iid=$(jq -r '.new_contract // empty' <<<"$out")
[ -n "$iid" ] || { echo "create failed: $out" >&2; exit 1; }
echo "$iid" > "$ST/$label.iid"
setsid nohup bash -c "sleep $LIFE_S; $HOME/.local/bin/vastai destroy instance $iid -y" > "$ST/watchdog-$iid.log" 2>&1 < /dev/null &
echo "instance $iid ($label), local watchdog in ${LIFE_S}s"
for _ in $(seq 60); do
    j=$(vastai show instance "$iid" --raw 2>/dev/null || true)
    [ "$(jq -r '.actual_status // ""' <<<"$j")" = running ] && break; sleep 10
done
H=$(jq -r '.public_ipaddr // empty' <<<"$j" | tr -d '[:space:]'); P=$(jq -r '.ports["22/tcp"][0].HostPort // empty' <<<"$j")
[ -n "$H" ] && [ -n "$P" ] || { H=$(jq -r .ssh_host <<<"$j"); P=$(jq -r .ssh_port <<<"$j"); }
echo "$H $P" > "$ST/$label.ssh"
S=(-i "$KEY" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile="$ST/known_hosts" -o ConnectTimeout=20)
for _ in $(seq 30); do ssh "${S[@]}" -p "$P" root@"$H" true 2>/dev/null && break; sleep 10; done
ssh "${S[@]}" -p "$P" root@"$H" 'mkdir -p /root/k114'
scp "${S[@]}" -P "$P" "$D/run.sh" "$D/run2.sh" "$D/bench.py" "$D/pf.py" "$D/pdl.sh" root@"$H":/root/k114/
ssh "${S[@]}" -p "$P" root@"$H" 'setsid nohup bash -c "bash /root/k114/run.sh; bash /root/k114/run2.sh" > /dev/null 2>&1 < /dev/null & sleep 5; cat /root/res/phases.txt'
echo "started on $iid"
