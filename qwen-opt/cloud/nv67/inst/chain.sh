#!/usr/bin/env bash
# ON the host: wait for the running campaign job, then run each card json (its own "res" dir) in order.
#   chain.sh /root/nv/a.json [/root/nv/b.json ...]
while pgrep -f '^python3 /root/nv/nv67.py' > /dev/null || pgrep -f '^bash setup' > /dev/null; do sleep 20; done
cd /root/nv || exit 1
for j in "$@"; do
    echo "=== chain $j $(date +%T)"
    bash setup-f.sh "$j"
done
echo "=== chain done $(date +%T)"
