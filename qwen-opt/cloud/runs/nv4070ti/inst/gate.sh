#!/usr/bin/env bash
# ON the box: [TENV=.. TV=.. TK=.. CTX=..] gate.sh <label> — T server, gate_chat (6 prompts x T=0/T=1 s1), copy_bench mvs
# + short at T=0; canonical md5 list -> gate/md5.<label>.txt. Compare two labels with cmp/diff.
set -uo pipefail
. /root/cloud/lib4070.sh
lab=$1
say "gate $lab TENV='$TENV' TV=$TV TK=$TK"
srv T "$G/gate.$lab.server.log" || { say "gate $lab: server failed"; tail -5 "$G/gate.$lab.server.log"; exit 1; }
(cd $H && $BC python3 gate_chat.py --label "gate.$lab" --port $PORT --out "$G/gate_chat.jsonl") > /dev/null
$BC python3 $H/copy_bench.py --label "gate.$lab" --port $PORT --set mvs --temps 0.0 --tokens 1024 --out "$G/copy_bench.jsonl" > /dev/null
$BC python3 $H/copy_bench.py --label "gate.$lab" --port $PORT --set short --temps 0.0 --tokens 512 --out "$G/copy_bench.jsonl" > /dev/null
srv_stop
{ jq -r --arg l "gate.$lab" 'select(.label == $l) | "\(.prompt) \(.temp) \(.md5)"' "$G/gate_chat.jsonl"
  jq -r --arg l "gate.$lab" 'select(.label == $l) | .set as $s | .prompts | to_entries[] | "\($s) \(.key) \(.value.md5 | join(","))"' "$G/copy_bench.jsonl"; } > "$G/md5.$lab.txt" 2>/dev/null
say "gate $lab rows=$(wc -l < "$G/md5.$lab.txt")"
