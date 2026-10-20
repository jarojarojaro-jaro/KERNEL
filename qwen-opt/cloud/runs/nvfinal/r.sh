#!/usr/bin/env bash
# run a command on one of our instances: IID=<id> r.sh 'cmd'
. "$(dirname "$0")/lib.sh" > /dev/null 2>&1
iid=${IID:?set IID}
if [ ! -f "$STATE/ssh-$iid" ]; then inst_ssh "$iid" && echo "$SSH_HOST $SSH_PORT" > "$STATE/ssh-$iid"; fi
read -r SSH_HOST SSH_PORT < "$STATE/ssh-$iid"
exec ssh "${SSH_OPTS[@]}" -o LogLevel=ERROR -p "$SSH_PORT" "root@$SSH_HOST" "$*"
