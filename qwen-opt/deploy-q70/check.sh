#!/usr/bin/env bash
# Gate before the swap: the q70 arms must reproduce the production references bit-exactly.
set -uo pipefail
q=$HOME/qwen-opt; ok=1
l=$(grep '^Q70 long32768' $q/fa-d256/res/long_md5.txt | tail -1 | awk '{print $4}')
f=$(grep -A0 '"text_md5"' $q/fa-d256/res/fill.txt | tail -1 | python3 -c 'import json,sys;print(json.loads(sys.stdin.read())["text_md5"])')
s=$(grep '"label": "Q70", "item": "md5"' $q/cachesave/results.jsonl | tail -1 | python3 -c 'import json,sys;print(json.loads(sys.stdin.read())["md5"])')
echo "long32k $l (ref e460e3b6) | fill255k $f (ref 31b6525a) | switch $s (ref ea3bda5b)"
[ "$l" = e460e3b6 ] && [ "$f" = 31b6525a ] && [ "$s" = ea3bda5b ] || ok=0
[ $ok = 1 ] && { touch $q/deploy-q70/GATE_OK; echo GATE OK; } || { rm -f $q/deploy-q70/GATE_OK; echo "GATE FAIL: no swap"; exit 1; }
