#!/usr/bin/env bash
# launch.sh <offer_id | "GPU name"> <label> : rent one Vast offer from the Jarvo server (vastai in ~/.local/bin, key
# ~/.ssh/vast_kernel), arm two kill timers (on-instance self-destruct via CONTAINER_API_KEY after LIFE_S+600 s, local
# watchdog after LIFE_S), then BEFORE any download check the host with ../hostguard.sh (owner rule 2026-11-17: power
# limit and max memory clock >= 85% of factory, idle < 80 C). A failed host is destroyed, its machine_id goes to
# ../hosty-zle.txt, and with a GPU name the next offer is tried (max 3; hosty-zle.txt machines are never picked).
# Hosts stuck in loading > 10 min or refusing SSH are destroyed and listed too. Then copies the runners, starts
# run.sh; run2.sh; run3.sh detached and starts fetch.sh locally (copies /root/res to res/<label>/ when DONE3 appears,
# then destroys the instance). Destroy by id only: vastai destroy instance <id> -y.
set -euo pipefail
export PATH=$HOME/.local/bin:$PATH
target=$1 label=$2 LIFE_S=${LIFE_S:-4200}
D=$(cd "$(dirname "$0")" && pwd); ST=$D/state; mkdir -p "$ST"
. "$D/../hostguard.sh"
KEY=$HOME/.ssh/vast_kernel
S=(-i "$KEY" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile="$ST/known_hosts" -o ConnectTimeout=20)

drop() {  # iid reason : destroy, stop its watchdog, list the machine
    local mid; mid=$(vastai show instance "$1" --raw 2>/dev/null | jq -r '.machine_id // empty')
    vastai destroy instance "$1" -y > /dev/null || true
    pkill -f "vastai destroy instance $1 -y" || true
    [ -n "$mid" ] && printf '%s\t%s\t%s\t%s\n' "$mid" "$(date +%F)" "$label" "$2" >> "$HG_BAD"
    echo "dropped $1: $2"
}

try_offer() {  # offer -> 0 started, 2 bad host (try next), 1 create failed
    local offer=$1 out iid j H P
    hg_offer_ok "$offer" 11 || return 2   # transfer-cost + blacklist gate, as up.sh (download ~10.4 GB model + ~0.7 GB engine)
    cat > "$ST/onstart-$label.sh" <<EOF
env | grep -E '^(CONTAINER_ID|CONTAINER_API_KEY)=' >> /etc/environment
command -v curl > /dev/null || { apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq curl ca-certificates; } > /root/onstart-curl.log 2>&1
nohup setsid bash -c 'sleep $((LIFE_S + 600)); curl -fsS -X DELETE -H "Authorization: Bearer \$CONTAINER_API_KEY" "https://console.vast.ai/api/v0/instances/\$CONTAINER_ID/"' > /root/self-destruct.log 2>&1 < /dev/null &
EOF
    out=$(vastai create instance "$offer" --image nvidia/cuda:12.8.1-base-ubuntu24.04 --disk 30 --ssh --direct \
          --label "$label" --cancel-unavail --onstart "$ST/onstart-$label.sh" --raw) || true
    iid=$(jq -r '.new_contract // empty' <<<"$out" 2>/dev/null || true)
    [ -n "$iid" ] || { echo "create failed for offer $offer: $out" >&2; return 1; }
    echo "$iid" > "$ST/$label.iid"
    systemd-run --user --collect -q --unit="vast-watchdog-$iid" bash -c "sleep $LIFE_S; $HOME/.local/bin/vastai destroy instance $iid -y"
    echo "instance $iid ($label, offer $offer), local watchdog in ${LIFE_S}s"
    for _ in $(seq 60); do
        j=$(vastai show instance "$iid" --raw 2>/dev/null || true)
        [ "$(jq -r '.actual_status // ""' <<<"$j")" = running ] && break; sleep 10
    done
    [ "$(jq -r '.actual_status // ""' <<<"$j")" = running ] || { drop "$iid" "stuck in loading > 10 min"; return 2; }
    H=$(jq -r '.public_ipaddr // empty' <<<"$j" | tr -d '[:space:]'); P=$(jq -r '.ports["22/tcp"][0].HostPort // empty' <<<"$j")
    [ -n "$H" ] && [ -n "$P" ] || { H=$(jq -r .ssh_host <<<"$j"); P=$(jq -r .ssh_port <<<"$j"); }
    echo "$H $P" > "$ST/$label.ssh"
    local ok=0; for _ in $(seq 30); do ssh "${S[@]}" -p "$P" root@"$H" true 2>/dev/null && { ok=1; break; }; sleep 10; done
    [ $ok = 1 ] || { drop "$iid" "SSH refuses the registered key"; return 2; }
    hg_check "$iid" "$H" "$P" "${S[@]}" || { pkill -f "vastai destroy instance $iid -y" || true; return 2; }
    ssh "${S[@]}" -p "$P" root@"$H" 'mkdir -p /root/k114'
    scp "${S[@]}" -P "$P" "$D/run.sh" "$D/run2.sh" "$D/run3.sh" "$D/bench.py" "$D/pf.py" "$D/lp.py" "$D/pdl.sh" root@"$H":/root/k114/
    ssh -n "${S[@]}" -p "$P" root@"$H" 'setsid nohup bash -c "bash /root/k114/run.sh; bash /root/k114/run2.sh; bash /root/k114/run3.sh" > /dev/null 2>&1 < /dev/null & sleep 5; cat /root/res/phases.txt'
    # systemd-run, not setsid nohup: jobs started from the agent's tool session die with it (2026-11-19: fetch.sh and
    # the local watchdogs were killed, 4 instances sat idle ~70 min until destroyed by hand)
    systemd-run --user --collect -q --unit="fetch-$label-$iid" -E LIFE_S="$LIFE_S" "$D/fetch.sh" "$label"
    echo "started on $iid (fetch.sh collects and destroys)"
}

if [[ $target =~ ^[0-9]+$ ]]; then
    try_offer "$target"; exit $?
fi
n=0
for offer in $(hg_pick "$target" ${HG_EXTRA:-}); do   # HG_EXTRA: extra vastai search filters, e.g. cpu_cores_effective>=8
    n=$((n + 1)); [ $n -le 3 ] || break
    rc=0; try_offer "$offer" || rc=$?
    [ $rc = 0 ] && exit 0
done
echo "no full-power $target host started (tried $((n > 3 ? 3 : n)))" >&2; exit 2
