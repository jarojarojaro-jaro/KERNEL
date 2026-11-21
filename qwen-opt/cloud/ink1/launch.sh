#!/usr/bin/env bash
# ink1/launch.sh: Inkling 2 Mini on a rented NVIDIA card (copy of k114/launch.sh: CUDA devel image, 22 GB download). launch.sh <offer_id | "GPU name"> <label> : rent one Vast offer from the Jarvo server (vastai in ~/.local/bin, key
# ~/.ssh/vast_kernel) with the instance-side cost guard (../onstart-guard.sh: deletes itself when the runner is gone,
# the GPU idles 15 min after "ready", 10 min after FINISHED, or after LIFE_S), then BEFORE any download check the host
# with ../hostguard.sh (owner rule 2026-11-17: power limit and max memory clock >= 85% of factory, idle < 80 C). A failed
# host is destroyed, its machine_id goes to ../hosty-zle.txt, and with a GPU name the next offer is tried (max 3;
# hosty-zle.txt machines are never picked). Hosts stuck in loading > 10 min or refusing SSH are destroyed and listed too.
# Then copies the runners and starts run.sh; run2.sh; run3.sh; touch FINISHED detached. Collecting the results and
# destroying the instance is ../vast-reaper.sh (systemd --user timer, every 2 min, independent of any agent session;
# owner 2026-11-19: cards never sit idle). Destroy by id only: vastai destroy instance <id> -y.
# Run launch.sh itself with systemd-run --user (a launch started from an agent tool session dies with the session).
set -euo pipefail
export PATH=$HOME/.local/bin:$PATH
target=$1 label=$2 LIFE_S=${LIFE_S:-4200}
systemctl --user is-active -q vast-reaper.timer || { echo "vast-reaper.timer is not active: refusing to rent (nobody would collect and destroy)" >&2; exit 3; }
D=$(cd "$(dirname "$0")" && pwd); ST=$D/state; mkdir -p "$ST"
. "$D/../hostguard.sh"
KEY=$HOME/.ssh/vast_kernel
S=(-i "$KEY" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile="$ST/known_hosts" -o ConnectTimeout=20)

drop() {  # iid reason : destroy, list the machine
    local mid; mid=$(vastai show instance "$1" --raw 2>/dev/null | jq -r '.machine_id // empty')
    vastai destroy instance "$1" -y > /dev/null || true
    [ -n "$mid" ] && printf '%s\t%s\t%s\t%s\n' "$mid" "$(date +%F)" "$label" "$2" >> "$HG_BAD"
    echo "dropped $1: $2"
}

try_offer() {  # offer -> 0 started, 2 bad host (try next), 1 create failed
    local offer=$1 out iid j H P
    hg_offer_ok "$offer" 22 || return 2   # transfer-cost + blacklist gate, as up.sh (download ~10.4 GB model + ~0.7 GB engine)
    { printf 'LIFE_S=%s IDLE_S=%s GRACE_S=%s SETUP_S=%s\n' "$LIFE_S" "${IDLE_S:-900}" "${GRACE_S:-600}" "${SETUP_S:-1500}"
      cat "$D/../onstart-guard.sh"; } > "$ST/onstart-$label.sh"
    out=$(vastai create instance "$offer" --image nvidia/cuda:12.8.1-devel-ubuntu24.04 --disk 60 --ssh --direct \
          --label "$label" --cancel-unavail --onstart "$ST/onstart-$label.sh" --raw) || true
    iid=$(jq -r '.new_contract // empty' <<<"$out" 2>/dev/null || true)
    [ -n "$iid" ] || { echo "create failed for offer $offer: $out" >&2; return 1; }
    echo "$iid" > "$ST/$label.iid"
    echo "instance $iid ($label, offer $offer); on-instance guard + vast-reaper.timer"
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
    hg_check "$iid" "$H" "$P" "${S[@]}" || return 2
    ssh "${S[@]}" -p "$P" root@"$H" 'mkdir -p /root/k114'
    scp "${S[@]}" -P "$P" "$D/run.sh" "$D/run2.sh" "$D/run3.sh" "$D/xbench.py" "$D/test_serve.py" "$D/pdl.sh" root@"$H":/root/k114/
    ssh -n "${S[@]}" -p "$P" root@"$H" 'setsid nohup bash -c "bash /root/k114/run.sh; bash /root/k114/run2.sh; bash /root/k114/run3.sh; touch /root/res/FINISHED" > /dev/null 2>&1 < /dev/null & sleep 5; cat /root/res/phases.txt; pgrep -f "[/]root/guard.sh" > /dev/null && echo "guard alive" || echo "GUARD MISSING"'
    echo "started on $iid (vast-reaper collects and destroys)"
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
