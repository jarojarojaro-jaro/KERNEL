#!/usr/bin/env bash
# run a command on the 4070 Ti box: r.sh 'cmd'  (IID default 56904321)
iid=${IID:-56904321}
read -r H P < "$HOME/qwen-opt/cloud/runs/nv4070ti/state/ssh-$iid"
exec ssh -i "$HOME/.ssh/cloud_ed25519" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile="$HOME/qwen-opt/cloud/state/known_hosts" -o ServerAliveInterval=30 -o ConnectTimeout=20 -o LogLevel=ERROR -p "$P" "root@$H" "$@"
