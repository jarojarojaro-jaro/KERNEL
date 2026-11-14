#!/usr/bin/env bash
# k103-ssh.sh <cmd...> | k103-ssh.sh --put <files...>  (instance 60693822, via lib.sh SSH_OPTS)
. ~/qwen-opt/cloud/lib.sh >/dev/null 2>&1
inst_ssh 60693822 || { echo "no ssh info"; exit 1; }
if [ "$1" = --put ]; then shift; scp "${SSH_OPTS[@]}" -P "$SSH_PORT" "$@" root@"$SSH_HOST":/root/k103/
elif [ "$1" = --get ]; then shift; scp -r "${SSH_OPTS[@]}" -P "$SSH_PORT" root@"$SSH_HOST":"$1" "$2"
else ssh "${SSH_OPTS[@]}" -p "$SSH_PORT" root@"$SSH_HOST" "$@"; fi
