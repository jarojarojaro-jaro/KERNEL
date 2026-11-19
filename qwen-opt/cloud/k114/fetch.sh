#!/usr/bin/env bash
# fetch.sh <label> : run detached on the Jarvo server next to launch.sh. Every 60 s checks the instance of <label> for
# /root/res/DONE3 (or a runner that died: no run*.sh process for 3 checks), copies /root/res to res/<label>/, then
# destroys the instance by id (vastai destroy instance <id> -y) and stops its local watchdog. Gives up at LIFE_S.
set -uo pipefail
export PATH=$HOME/.local/bin:$PATH
label=$1 LIFE_S=${LIFE_S:-6000}
D=$(cd "$(dirname "$0")" && pwd); ST=$D/state
iid=$(cat "$ST/$label.iid"); read -r H P < "$ST/$label.ssh"
S=(-i "$HOME/.ssh/vast_kernel" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile="$ST/known_hosts" -o ConnectTimeout=20)
log() { echo "$(date +%T) $*" >> "$ST/fetch-$label.log"; }
grab() { mkdir -p "$D/res/$label"; scp -q -r "${S[@]}" -P "$P" root@"$H":/root/res/. "$D/res/$label/" && log "copied res"; }
dead=0 t0=$SECONDS
while [ $((SECONDS - t0)) -lt "$LIFE_S" ]; do
    sleep 60
    st=$(ssh "${S[@]}" -p "$P" root@"$H" '[ -f /root/res/DONE3 ] && echo done || { pgrep -f "k114/run[0-9]*[.]sh" > /dev/null && echo run || echo dead; }' 2>/dev/null)
    case $st in
        done) grab; break ;;
        dead) dead=$((dead + 1)); log "runner not running ($dead)"; [ $dead -ge 3 ] && { grab; break; } ;;
        run) dead=0 ;;
        *) log "ssh failed" ;;
    esac
done
[ -d "$D/res/$label" ] || grab
vastai destroy instance "$iid" -y >> "$ST/fetch-$label.log" 2>&1
pkill -f "vastai destroy instance $iid -y" || true
log "destroyed $iid"
